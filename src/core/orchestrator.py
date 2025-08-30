"""Orchestrator - 核心任务调度器

负责系统的任务调度、执行策略选择和结果处理。
实现混合智能架构的核心逻辑。
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
        self.tasks: Dict[str, TaskResult] = {}
        self.command_parser = CommandParser()
        self.skill_library = SkillLibrary()
        self.site_explorer = SiteExplorer()
        self.policy_engine = PolicyEngine()
        self.risk_engine = RiskEngine()
        self.action_graph_executor = ActionGraphEngine()
        
        # MCP 集成
        self.mcp_config = MCPConfig()
        self.mcp_manager = MCPManager()
        self._mcp_initialized = False
        
        # 执行统计
        self.stats = {
            "total_tasks": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "token_usage": 0
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
        """执行任务的内部方法
        
        Args:
            task_id: 任务ID
            request: 任务请求
        """
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting task execution: {task_id}")
            
            # 1. 解析用户指令
            parsed_command = await self.command_parser.parse_command(request.goal)
            task.execution_log.append({
                "step": "command_parsing",
                "timestamp": datetime.now().isoformat(),
                "data": parsed_command
            })
            
            # 2. 风险评估
            risk_assessment = await self.risk_engine.assess_risk(
                parsed_command, request.risk_level
            )
            
            # 3. 策略检查
            policy_check = await self.policy_engine.check_policy(
                parsed_command, risk_assessment
            )
            
            if not policy_check.allowed:
                raise TaskExecutionError(f"Policy violation: {policy_check.reason}")
            
            # 4. 选择执行策略
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
            
            # 5. 执行任务
            result = await self._execute_strategy(task_id, execution_strategy, request)
            
            # 6. 处理结果
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.execution_time = (task.completed_at - start_time).total_seconds()
            
            logger.info(f"Task completed successfully: {task_id}")
            
        except Exception as e:
            logger.error(f"Task execution failed: {task_id}, error: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            task.execution_time = (task.completed_at - start_time).total_seconds()
            
            # 尝试降级处理
            if request.retry_count > 0:
                logger.info(f"Attempting fallback execution for task: {task_id}")
                request.retry_count -= 1
                await asyncio.sleep(1)  # 短暂延迟
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
        """获取执行统计信息
        
        Returns:
            统计信息
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
        """初始化 MCP 管理器
        
        Returns:
            初始化是否成功
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
        """关闭 Orchestrator
        
        清理资源和连接
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