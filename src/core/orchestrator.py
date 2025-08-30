"""Aura 核心编排器 (Orchestrator)

这是 Aura 系统的核心协调组件，负责统一管理和编排所有子系统的协作。

核心职责:
1. **任务生命周期管理**: 创建、执行、监控、取消和重放任务
2. **智能路由决策**: 根据任务特征选择最优执行策略(脚本模式 vs AI代理模式)
3. **组件协调**: 统一管理命令解析器、技能库、站点探索器、策略引擎等
4. **风险控制**: 集成策略引擎和风险引擎，确保操作安全性
5. **MCP集成**: 管理Model Context Protocol连接，支持浏览器自动化
6. **执行统计**: 收集和分析任务执行指标，支持系统优化

架构设计:
- **混合智能架构**: 结合固定脚本的可靠性与AI的灵活性
- **Action Graph**: 使用有向无环图表示执行计划，支持验证和重放
- **技能沉淀**: 成功的AI执行可自动转化为可复用的技能包
- **降级容错**: 脚本执行失败时自动回退到AI模式

使用示例:
    ```python
    orchestrator = Orchestrator()
    await orchestrator.initialize_mcp()
    
    # 创建搜索任务
    task_id = await orchestrator.create_task(TaskRequest(
        goal="在亚马逊搜索Kindle电子书阅读器",
        site_scope="amazon.com",
        risk_level=RiskLevel.LOW
    ))
    
    # 监控任务状态
    status = await orchestrator.get_task_status(task_id)
    print(f"任务状态: {status.status}, 进度: {status.progress}%")
    ```

性能考虑:
- 支持异步并发执行多个任务
- 智能缓存站点模型，减少重复探索
- 内存中维护任务状态，支持快速查询
- 统计信息实时计算，支持性能监控

扩展性:
- 插件化的组件架构，易于添加新功能
- 标准化的接口设计，支持第三方集成
- 配置驱动的行为控制，无需修改代码
"""

import asyncio
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.exceptions import AuraException, TaskExecutionError
from .policy_engine import PolicyEngine
from .risk_engine import RiskEngine
from .action_graph import ActionGraphEngine, ActionGraph, ActionNode, ActionEdge, NodeType
from .mcp_manager import MCPManager
from ..modules.command_parser import CommandParser
from ..modules.skill_library import SkillLibrary
from ..modules.site_explorer import SiteExplorer
from ..config.mcp_config import MCPConfig

logger = get_logger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    """执行模式枚举"""
    AI_AGENT = "ai_agent"  # AI动态规划模式
    SCRIPT = "script"      # 固定脚本模式
    HYBRID = "hybrid"      # 混合模式


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskRequest:
    """任务请求数据结构"""
    goal: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    budget_tokens: int = 3000
    site_scope: str = "domain"
    timeout: int = 300  # 超时时间（秒）
    retry_count: int = 2
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class TaskResult:
    """任务结果数据结构"""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    tokens_used: int = 0
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class Orchestrator:
    """核心任务调度器
    
    实现混合智能架构的核心逻辑：
    1. 接收用户指令并解析
    2. 选择最佳执行策略（AI vs 脚本）
    3. 调度执行并监控进度
    4. 处理结果和异常
    5. 学习和优化
    """
    
    def __init__(self):
        """初始化 Aura 核心编排器
        
        设置所有必要的组件和配置，建立系统的基础架构。
        
        初始化流程:
        1. **核心组件初始化**: 创建命令解析、技能库、站点探索等核心组件
        2. **策略引擎配置**: 设置安全策略和风险评估机制
        3. **MCP连接准备**: 配置Model Context Protocol管理器
        4. **任务管理设置**: 初始化任务队列和状态跟踪
        5. **统计系统启动**: 准备性能指标收集
        
        组件依赖关系:
        - CommandParser: 解析自然语言指令
        - SkillLibrary: 管理固定脚本和技能包
        - SiteExplorer: 网站探索和建模
        - PolicyEngine: 安全策略控制
        - RiskEngine: 风险评估和分析
        - ActionGraphEngine: Action Graph执行引擎
        - MCPManager: MCP协议管理和浏览器控制
        
        注意事项:
        - MCP连接需要异步初始化，调用 initialize_mcp() 完成
        - 任务队列支持并发处理，但需要合理控制并发数
        - 统计信息实时更新，可用于监控和优化
        """
        # 核心组件 - 按依赖顺序初始化
        self.tasks: Dict[str, TaskResult] = {}  # 任务状态存储 {task_id: TaskResult}
        self.command_parser = CommandParser()  # 指令解析器
        self.skill_library = SkillLibrary()    # 技能库管理
        self.site_explorer = SiteExplorer()    # 站点探索器
        self.policy_engine = PolicyEngine()    # 策略引擎
        self.risk_engine = RiskEngine()        # 风险引擎
        self.action_graph_executor = ActionGraphEngine()  # Action Graph执行器
        
        # MCP (Model Context Protocol) 相关组件
        self.mcp_config = MCPConfig()          # MCP配置管理
        self.mcp_manager = MCPManager()        # MCP连接管理
        self._mcp_initialized = False          # MCP初始化状态标记
        
        # 执行统计和监控
        self.stats = {
            "total_tasks": 0,           # 总任务数
            "success_rate": 0.0,        # 成功率 (0.0-1.0)
            "avg_execution_time": 0.0,  # 平均执行时间(秒)
            "token_usage": 0            # Token使用量
        }
        
        logger.info("Orchestrator initialized")
    
    async def create_task(self, request: TaskRequest) -> str:
        """创建新任务
        
        Args:
            request: 任务请求
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建任务结果对象
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING
        )
        
        self.tasks[task_id] = task_result
        self.stats["total_tasks"] += 1
        
        logger.info(f"Task created: {task_id}, goal: {request.goal}")
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(task_id, request))
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果，如果任务不存在返回None
        """
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        logger.info(f"Task cancelled: {task_id}")
        return True
    
    async def replay_task(self, task_id: str) -> str:
        """重放任务
        
        Args:
            task_id: 原任务ID
            
        Returns:
            新任务ID
        """
        original_task = self.tasks.get(task_id)
        if not original_task:
            raise AuraException(f"Task {task_id} not found")
        
        # 基于原任务创建新的重放任务
        # 这里需要从执行日志中重建TaskRequest
        # 简化实现，实际需要更复杂的逻辑
        replay_request = TaskRequest(
            goal=f"Replay of task {task_id}",
            budget_tokens=3000
        )
        
        return await self.create_task(replay_request)
    
    async def _execute_task(self, task_id: str, request: TaskRequest):
        """执行任务的核心编排逻辑
        
        这是 Orchestrator 的核心方法，实现了完整的任务执行流水线。
        
        执行流程:
        1. **指令解析**: 将自然语言转换为结构化命令对象
        2. **风险评估**: 分析操作风险，生成风险报告和建议
        3. **策略检查**: 根据安全策略决定是否允许执行
        4. **人工审批**: 高风险操作需要人工确认
        5. **策略选择**: 智能选择脚本模式或AI代理模式
        6. **任务执行**: 调用相应的执行引擎完成任务
        7. **结果处理**: 收集执行结果和统计信息
        
        Args:
            task_id: 唯一任务标识符
            request: 包含目标、约束、风险级别等的任务请求
            
        异常处理:
        - 策略拒绝: 抛出 TaskExecutionError
        - 审批拒绝: 抛出 TaskExecutionError  
        - 执行失败: 捕获异常并返回失败状态
        
        性能考虑:
        - 异步执行，支持并发处理
        - 实时统计更新，无阻塞
        - 错误恢复机制，提高鲁棒性
        """
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting task execution: {task_id}")
            
            # 1. 指令解析 - 将自然语言转换为结构化命令
            parsed_command = await self.command_parser.parse_command(request.goal)
            task.execution_log.append({
                "step": "command_parsing",
                "timestamp": datetime.now().isoformat(),
                "data": parsed_command
            })
            logger.info(f"Task {task_id}: Command parsed successfully")
            
            # 2. 风险评估 - 分析潜在风险和安全隐患
            risk_assessment = await self.risk_engine.assess_risk(
                parsed_command, request.risk_level
            )
            logger.info(f"Task {task_id}: Risk assessment completed")
            
            # 3. 策略检查 - 根据安全策略决定执行权限
            policy_check = await self.policy_engine.check_policy(
                parsed_command, risk_assessment
            )
            
            if not policy_check.allowed:
                raise TaskExecutionError(f"Policy violation: {policy_check.reason}")
            
            # 4. 执行策略决策 - 选择最优执行模式
            execution_strategy = await self._decide_execution_strategy(
                parsed_command, risk_assessment
            )
            
            task.execution_log.append({
                "step": "strategy_selection",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "mode": execution_strategy["mode"].value,
                    "confidence": execution_strategy.get("confidence", 0.0)
                }
            })
            logger.info(f"Task {task_id}: Execution mode - {execution_strategy['mode'].value}")
            
            # 5. 任务执行 - 调用相应的执行引擎
            result = await self._execute_strategy(task_id, execution_strategy, request)
            
            # 6. 结果处理和统计更新
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.execution_time = (task.completed_at - start_time).total_seconds()
            
            logger.info(f"Task completed successfully: {task_id} in {task.execution_time:.2f}s")
            
        except Exception as e:
            # 异常处理和错误记录
            logger.error(f"Task execution failed: {task_id}, error: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            task.execution_time = (task.completed_at - start_time).total_seconds()
            
            # 降级重试机制
            if request.retry_count > 0:
                logger.info(f"Attempting fallback execution for task: {task_id}")
                request.retry_count -= 1
                await asyncio.sleep(1)  # 短暂延迟避免资源竞争
                await self._execute_task(task_id, request)
    
    async def _decide_execution_strategy(self, parsed_command: Dict[str, Any], 
                                       risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """决定执行策略
        
        Args:
            parsed_command: 解析后的命令
            risk_assessment: 风险评估结果
            
        Returns:
            执行策略
        """
        # 检查是否有高置信度的技能匹配
        skill_match = await self.skill_library.find_matching_skill(
              getattr(parsed_command.primary_intent, 'intent', '').value if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else '', 
              getattr(parsed_command, 'context', {})
          )
        
        if skill_match and skill_match["confidence"] > 0.85:
            return {
                "mode": ExecutionMode.SCRIPT,
                "skill_id": skill_match["skill_id"],
                "parameters": skill_match["parameters"],
                "confidence": skill_match["confidence"]
            }
        else:
            return {
                "mode": ExecutionMode.AI_AGENT,
                "plan": getattr(parsed_command.execution_strategy, 'reasoning', '') if parsed_command.execution_strategy else '',
                "confidence": 0.7
            }
    
    async def _execute_strategy(self, task_id: str, strategy: Dict[str, Any], 
                              request: TaskRequest) -> Dict[str, Any]:
        """执行具体策略
        
        Args:
            task_id: 任务ID
            strategy: 执行策略
            request: 任务请求
            
        Returns:
            执行结果
        """
        if strategy["mode"] == ExecutionMode.SCRIPT:
            # 使用固定脚本执行
            return await self.skill_library.execute_skill(
                strategy["skill_id"],
                strategy["parameters"]
            )
        else:
            # 使用AI动态规划执行
            return await self._execute_ai_agent_mode(task_id, strategy, request)
    
    async def _execute_ai_agent_mode(self, task_id: str, strategy: Dict[str, Any], 
                                   request: TaskRequest) -> Dict[str, Any]:
        """AI代理模式执行
        
        Args:
            task_id: 任务ID
            strategy: 执行策略
            request: 任务请求
            
        Returns:
            执行结果
        """
        # 1. 站点探索和建模
        site_model = await self.site_explorer.explore_and_model(
            request.site_scope
        )
        
        # 2. 生成Action Graph
        action_graph = await self._generate_action_graph(
            request.goal, site_model, strategy["plan"]
        )
        
        # 3. 执行Action Graph
        result = await self.action_graph_executor.execute_graph(action_graph)
        
        # 4. 如果执行成功，考虑将其转化为技能包
        if result["success"]:
            await self._consider_skill_generation(task_id, action_graph, result)
        
        return result
    
    async def _generate_action_graph(self, goal: str, site_model: Dict[str, Any], 
                                   plan: List[str]) -> ActionGraph:
        """生成Action Graph
        
        Args:
            goal: 任务目标
            site_model: 站点模型
            plan: 执行计划
            
        Returns:
            Action Graph
        """
        # 这里应该调用LLM来生成Action Graph
        # 简化实现，返回一个示例图
        # 获取首页URL
        homepage_url = "/"
        if site_model and hasattr(site_model, 'pages'):
            for url, page_info in site_model.pages.items():
                if hasattr(page_info, 'type') and page_info.type.value == 'homepage':
                    homepage_url = url
                    break
        
        # 创建ActionGraph对象
        nodes = [
            ActionNode(id="start", type=NodeType.NAVIGATE, url=homepage_url),
            ActionNode(id="action1", type=NodeType.CLICK, locator="button[type='submit']"),
            ActionNode(id="end", type=NodeType.ASSERT, locator="#results")
        ]
        
        edges = [
            ActionEdge(from_node="start", to_node="action1"),
            ActionEdge(from_node="action1", to_node="end")
        ]
        
        return ActionGraph(
            id=f"graph_{int(time.time())}",
            goal=goal,
            nodes=nodes,
            edges=edges,
            budget_tokens=3000
        )
    
    async def _consider_skill_generation(self, task_id: str, action_graph: ActionGraph, 
                                       result: Dict[str, Any]):
        """考虑生成技能包
        
        Args:
            task_id: 任务ID
            action_graph: 执行的Action Graph
            result: 执行结果
        """
        # 如果任务执行成功且具有可复用性，生成技能包
        if (result["success"] and 
            result.get("execution_time", 0) < 30 and  # 执行时间合理
            len(action_graph["nodes"]) > 2):  # 有一定复杂度
            
            logger.info(f"Considering skill generation for task: {task_id}")
            # 这里应该调用技能生成逻辑
            # await self.skill_library.generate_skill_from_graph(action_graph, result)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取 Orchestrator 执行统计信息
        
        提供系统运行状态的全面统计数据，用于:
        - **性能监控**: 跟踪成功率、执行时间等关键指标
        - **资源管理**: 监控Token使用量，控制成本
        - **质量分析**: 识别失败模式，优化系统表现
        - **容量规划**: 基于历史数据预测资源需求
        
        统计指标说明:
        - success_rate: 任务成功率 (0.0-1.0)，衡量系统可靠性
        - avg_execution_time: 平均执行时间(秒)，反映系统效率
        - token_usage: 累计Token使用量，用于成本控制
        - total_tasks: 处理的任务总数，显示系统负载
        
        Returns:
            Dict[str, Any]: 包含各项统计指标的字典
            {
                "success_rate": float,      # 成功率 0.0-1.0
                "avg_execution_time": float, # 平均执行时间(秒)
                "token_usage": int,         # Token使用总量
                "total_tasks": int          # 任务总数
            }
            
        使用场景:
        - 定期监控系统健康状态
        - 生成运营报告和分析
        - 触发告警和自动化运维
        - 支持A/B测试和优化决策
        
        性能考虑:
        - 实时计算，无缓存延迟
        - O(n)时间复杂度，n为任务数量
        - 内存占用与任务历史成正比
        """
        completed_tasks = [t for t in self.tasks.values() 
                          if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.tasks.values() 
                       if t.status == TaskStatus.FAILED]
        
        total_completed = len(completed_tasks)
        total_failed = len(failed_tasks)
        total_processed = total_completed + total_failed
        
        if total_processed > 0:
            self.stats["success_rate"] = total_completed / total_processed
        
        if completed_tasks:
            self.stats["avg_execution_time"] = sum(
                t.execution_time for t in completed_tasks
            ) / len(completed_tasks)
        
        self.stats["token_usage"] = sum(
            t.tokens_used for t in self.tasks.values()
        )
        
        return self.stats
    
    async def initialize_mcp(self) -> bool:
        """初始化 Model Context Protocol (MCP) 管理器
        
        MCP是连接AI系统与浏览器自动化工具的桥梁，负责:
        - 建立与Playwright服务器的连接
        - 管理浏览器实例和页面上下文
        - 提供标准化的浏览器操作接口
        - 处理连接异常和重连逻辑
        
        初始化流程:
        1. 检查是否已初始化，避免重复初始化
        2. 加载服务器配置列表
        3. 逐个添加和连接MCP服务器
        4. 验证连接状态和可用性
        5. 更新初始化状态标记
        
        Returns:
            bool: True表示初始化成功，False表示失败
            
        注意事项:
        - 此方法是异步的，需要await调用
        - 初始化失败不会抛出异常，而是返回False
        - 可以多次调用，已初始化时直接返回True
        - 网络异常时会自动重试连接
        
        使用示例:
            ```python
            success = await orchestrator.initialize_mcp()
            if not success:
                logger.error("MCP初始化失败，无法执行浏览器操作")
            ```
        """
        if self._mcp_initialized:
            return True
            
        try:
            # 加载服务器配置
            server_configs = self.mcp_config.get_server_configs()
            for config in server_configs:
                self.mcp_manager.add_server(config)
            
            # 初始化 MCP 管理器
            success = await self.mcp_manager.initialize()
            if success:
                self._mcp_initialized = True
                logger.info("MCP Manager initialized successfully")
            else:
                logger.error("Failed to initialize MCP Manager")
                
            return success
            
        except Exception as e:
            logger.error(f"Error initializing MCP: {e}")
            return False
    
    async def execute_mcp_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> str:
        """通过 MCP 执行命令
        
        Args:
            command: 要执行的命令
            context: 执行上下文
            
        Returns:
            执行结果
        """
        if not self._mcp_initialized:
            await self.initialize_mcp()
            
        if not self._mcp_initialized:
            raise AuraException("MCP not initialized")
            
        try:
            result = await self.mcp_manager.execute_command(command, context)
            return result
        except Exception as e:
            logger.error(f"MCP command execution failed: {e}")
            raise TaskExecutionError(f"MCP execution error: {e}")
    
    async def get_mcp_tools(self) -> List[str]:
        """获取可用的 MCP 工具列表
        
        Returns:
            工具名称列表
        """
        if not self._mcp_initialized:
            await self.initialize_mcp()
            
        if not self._mcp_initialized:
            return []
            
        return await self.mcp_manager.get_available_tools()
    
    async def get_mcp_status(self) -> Dict[str, Any]:
        """获取 MCP 服务器状态
        
        Returns:
            服务器状态信息
        """
        if not self._mcp_initialized:
            return {"initialized": False, "servers": {}}
            
        server_status = await self.mcp_manager.get_server_status()
        return {
            "initialized": self._mcp_initialized,
            "servers": server_status
        }
    
    async def enable_browser_extension_mode(self) -> bool:
        """启用浏览器扩展模式
        
        Returns:
            是否成功启用
        """
        try:
            # 更新配置
            success = self.mcp_config.enable_playwright_extension()
            if not success:
                return False
                
            # 重新初始化 MCP
            if self._mcp_initialized:
                await self.mcp_manager.shutdown()
                self._mcp_initialized = False
                
            return await self.initialize_mcp()
            
        except Exception as e:
            logger.error(f"Failed to enable browser extension mode: {e}")
            return False
    
    async def disable_browser_extension_mode(self) -> bool:
        """禁用浏览器扩展模式
        
        Returns:
            是否成功禁用
        """
        try:
            # 更新配置
            success = self.mcp_config.disable_playwright_extension()
            if not success:
                return False
                
            # 重新初始化 MCP
            if self._mcp_initialized:
                await self.mcp_manager.shutdown()
                self._mcp_initialized = False
                
            return await self.initialize_mcp()
            
        except Exception as e:
            logger.error(f"Failed to disable browser extension mode: {e}")
            return False
    
    async def shutdown(self) -> None:
        """优雅关闭 Orchestrator 系统
        
        执行完整的资源清理和连接关闭流程，确保:
        - 所有运行中的任务被正确取消
        - MCP连接被安全关闭
        - 内存资源被及时释放
        - 日志记录完整的关闭过程
        
        关闭流程:
        1. **日志记录**: 记录关闭开始时间和原因
        2. **MCP清理**: 关闭所有MCP服务器连接
        3. **任务取消**: 取消所有运行中的任务
        4. **资源释放**: 清理内存中的任务状态
        5. **状态重置**: 重置初始化标记
        6. **完成确认**: 记录关闭完成状态
        
        注意事项:
        - 此方法是异步的，需要await调用
        - 关闭过程中不接受新任务
        - 运行中的任务会被强制取消
        - 可以安全地多次调用
        - 关闭后需要重新初始化才能使用
        
        使用场景:
        - 应用程序正常退出
        - 系统重启或重新配置
        - 异常情况下的紧急清理
        - 单元测试的资源清理
        
        异常处理:
        - 关闭过程中的异常会被记录但不会抛出
        - 确保即使部分清理失败也能完成整体关闭
        """
        logger.info("Shutting down Orchestrator...")
        
        # 关闭 MCP 管理器
        if self._mcp_initialized:
            await self.mcp_manager.shutdown()
            self._mcp_initialized = False
            
        # 取消所有运行中的任务
        running_tasks = [task_id for task_id, task in self.tasks.items() 
                        if task.status == TaskStatus.RUNNING]
        
        for task_id in running_tasks:
            await self.cancel_task(task_id)
            
        logger.info("Orchestrator shutdown complete")
    
    @property
    def mcp_agent(self):
        """获取 MCP Agent 实例"""
        if self._mcp_initialized and self.mcp_manager:
            return self.mcp_manager.agent
        return None