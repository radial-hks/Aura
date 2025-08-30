"""Action Graph执行引擎

负责将AI生成的Action Graph转换为实际的浏览器操作，提供可验证、可重放、可迁移的执行基座。

主要功能：
- Action Graph的解析和验证
- 节点执行和状态管理
- 错误处理和重试机制
- 执行结果的收集和反馈
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime


class NodeType(Enum):
    """Action Graph节点类型"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    ASSERT = "assert"
    WAIT = "wait"
    EXTRACT = "extract"
    SCROLL = "scroll"
    HOVER = "hover"
    SELECT = "select"
    SCREENSHOT = "screenshot"


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """执行模式"""
    NORMAL = "normal"  # 正常执行
    DRY_RUN = "dry_run"  # 干跑模式，不实际执行
    DEBUG = "debug"  # 调试模式，逐步执行
    REPLAY = "replay"  # 回放模式


@dataclass
class ActionNode:
    """Action Graph节点"""
    id: str
    type: NodeType
    locator: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    timeout: int = 5000
    retry_count: int = 3
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Any] = None


@dataclass
class ActionEdge:
    """Action Graph边"""
    from_node: str
    to_node: str
    condition: Optional[str] = None  # 条件执行
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionGraph:
    """Action Graph数据结构"""
    id: str
    goal: str
    nodes: List[ActionNode]
    edges: List[ActionEdge]
    budget_tokens: int = 3000
    timeout: int = 60000  # 总超时时间（毫秒）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """执行结果"""
    graph_id: str
    success: bool
    completed_nodes: int
    total_nodes: int
    execution_time: float
    error_message: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)


class ActionGraphEngine:
    """Action Graph执行引擎"""
    
    def __init__(self):
        self.executor_registry: Dict[NodeType, Callable] = {}
        self.running_graphs: Dict[str, ActionGraph] = {}
        self.execution_history: List[ExecutionResult] = []
        self._register_default_executors()
    
    def _register_default_executors(self):
        """注册默认的节点执行器"""
        self.executor_registry[NodeType.NAVIGATE] = self._execute_navigate
        self.executor_registry[NodeType.CLICK] = self._execute_click
        self.executor_registry[NodeType.TYPE] = self._execute_type
        self.executor_registry[NodeType.ASSERT] = self._execute_assert
        self.executor_registry[NodeType.WAIT] = self._execute_wait
        self.executor_registry[NodeType.EXTRACT] = self._execute_extract
        self.executor_registry[NodeType.SCROLL] = self._execute_scroll
        self.executor_registry[NodeType.HOVER] = self._execute_hover
        self.executor_registry[NodeType.SELECT] = self._execute_select
        self.executor_registry[NodeType.SCREENSHOT] = self._execute_screenshot
    
    def parse_graph(self, graph_data: Dict[str, Any]) -> ActionGraph:
        """解析Action Graph数据"""
        try:
            # 解析节点
            nodes = []
            for node_data in graph_data.get('nodes', []):
                node = ActionNode(
                    id=node_data['id'],
                    type=NodeType(node_data['type']),
                    locator=node_data.get('locator'),
                    text=node_data.get('text'),
                    url=node_data.get('url'),
                    timeout=node_data.get('timeout', 5000),
                    retry_count=node_data.get('retry_count', 3),
                    description=node_data.get('description'),
                    metadata=node_data.get('metadata', {})
                )
                nodes.append(node)
            
            # 解析边
            edges = []
            for edge_data in graph_data.get('edges', []):
                edge = ActionEdge(
                    from_node=edge_data['from'],
                    to_node=edge_data['to'],
                    condition=edge_data.get('condition'),
                    metadata=edge_data.get('metadata', {})
                )
                edges.append(edge)
            
            # 创建图
            graph = ActionGraph(
                id=graph_data.get('id', str(uuid.uuid4())),
                goal=graph_data['goal'],
                nodes=nodes,
                edges=edges,
                budget_tokens=graph_data.get('budget_tokens', 3000),
                timeout=graph_data.get('timeout', 60000),
                metadata=graph_data.get('metadata', {})
            )
            
            return graph
            
        except Exception as e:
            raise ValueError(f"Failed to parse Action Graph: {str(e)}")
    
    def validate_graph(self, graph: ActionGraph) -> List[str]:
        """验证Action Graph的有效性"""
        errors = []
        
        # 检查节点ID唯一性
        node_ids = [node.id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Node IDs must be unique")
        
        # 检查边的有效性
        for edge in graph.edges:
            if edge.from_node not in node_ids:
                errors.append(f"Edge references non-existent node: {edge.from_node}")
            if edge.to_node not in node_ids:
                errors.append(f"Edge references non-existent node: {edge.to_node}")
        
        # 检查必需字段
        for node in graph.nodes:
            if node.type in [NodeType.NAVIGATE] and not node.url:
                errors.append(f"Navigate node {node.id} missing URL")
            if node.type in [NodeType.CLICK, NodeType.TYPE, NodeType.ASSERT] and not node.locator:
                errors.append(f"Node {node.id} missing locator")
            if node.type == NodeType.TYPE and not node.text:
                errors.append(f"Type node {node.id} missing text")
        
        return errors
    
    async def execute_graph(self, graph: ActionGraph, mode: ExecutionMode = ExecutionMode.NORMAL, 
                        page_context=None) -> ExecutionResult:
        """执行Action Graph"""
        # 验证图
        validation_errors = self.validate_graph(graph)
        if validation_errors:
            return ExecutionResult(
                graph_id=graph.id,
                success=False,
                completed_nodes=0,
                total_nodes=len(graph.nodes),
                execution_time=0,
                error_message=f"Validation failed: {'; '.join(validation_errors)}"
            )
        
        # 开始执行
        graph.status = NodeStatus.RUNNING
        graph.start_time = datetime.now()
        self.running_graphs[graph.id] = graph
        
        start_time = time.time()
        completed_nodes = 0
        screenshots = []
        extracted_data = {}
        
        try:
            # 构建执行顺序（拓扑排序）
            execution_order = self._topological_sort(graph)
            
            for node_id in execution_order:
                node = next(n for n in graph.nodes if n.id == node_id)
                
                if mode == ExecutionMode.DRY_RUN:
                    # 干跑模式，只记录不执行
                    node.status = NodeStatus.COMPLETED
                    self._log_execution(graph, f"DRY RUN: {node.type.value} on {node.locator or node.url}")
                    completed_nodes += 1
                    continue
                
                # 执行节点
                success = await self._execute_node(node, page_context, graph)
                
                if success:
                    completed_nodes += 1
                    if node.type == NodeType.SCREENSHOT and node.result:
                        screenshots.append(node.result)
                    elif node.type == NodeType.EXTRACT and node.result:
                        extracted_data[node.id] = node.result
                else:
                    # 节点执行失败
                    break
            
            # 判断执行结果
            success = completed_nodes == len(graph.nodes)
            
        except Exception as e:
            success = False
            error_message = str(e)
            self._log_execution(graph, f"Execution failed: {error_message}")
        
        # 完成执行
        execution_time = time.time() - start_time
        graph.status = NodeStatus.COMPLETED if success else NodeStatus.FAILED
        graph.end_time = datetime.now()
        
        result = ExecutionResult(
            graph_id=graph.id,
            success=success,
            completed_nodes=completed_nodes,
            total_nodes=len(graph.nodes),
            execution_time=execution_time,
            error_message=error_message if not success else None,
            screenshots=screenshots,
            extracted_data=extracted_data,
            execution_log=graph.execution_log.copy()
        )
        
        # 清理和记录
        if graph.id in self.running_graphs:
            del self.running_graphs[graph.id]
        self.execution_history.append(result)
        
        return result
    
    def _topological_sort(self, graph: ActionGraph) -> List[str]:
        """对节点进行拓扑排序"""
        # 简单实现：按边的顺序排列
        # 实际实现应该使用真正的拓扑排序算法
        if not graph.edges:
            return [node.id for node in graph.nodes]
        
        visited = set()
        result = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            # 访问所有前驱节点
            for edge in graph.edges:
                if edge.to_node == node_id:
                    visit(edge.from_node)
            
            result.append(node_id)
        
        # 访问所有节点
        for node in graph.nodes:
            visit(node.id)
        
        return result
    
    async def _execute_node(self, node: ActionNode, page_context, graph: ActionGraph) -> bool:
        """执行单个节点"""
        node.status = NodeStatus.RUNNING
        node.start_time = datetime.now()
        
        try:
            # 获取执行器
            executor = self.executor_registry.get(node.type)
            if not executor:
                raise ValueError(f"No executor found for node type: {node.type}")
            
            # 执行节点
            for attempt in range(node.retry_count):
                try:
                    result = await executor(node, page_context)
                    node.result = result
                    node.status = NodeStatus.COMPLETED
                    node.end_time = datetime.now()
                    
                    self._log_execution(graph, f"Node {node.id} completed successfully")
                    return True
                    
                except Exception as e:
                    if attempt == node.retry_count - 1:
                        # 最后一次尝试失败
                        raise e
                    else:
                        # 重试
                        self._log_execution(graph, f"Node {node.id} attempt {attempt + 1} failed: {str(e)}, retrying...")
                        await asyncio.sleep(1)  # 等待1秒后重试
        
        except Exception as e:
            node.status = NodeStatus.FAILED
            node.end_time = datetime.now()
            node.error_message = str(e)
            
            self._log_execution(graph, f"Node {node.id} failed: {str(e)}")
            return False
    
    def _log_execution(self, graph: ActionGraph, message: str):
        """记录执行日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        graph.execution_log.append(log_entry)
    
    # 节点执行器实现（占位符）
    async def _execute_navigate(self, node: ActionNode, page_context) -> Any:
        """执行导航操作"""
        # 实际实现需要调用Playwright MCP
        if not page_context:
            raise ValueError("Page context required for navigate operation")
        # await page_context.goto(node.url)
        return f"Navigated to {node.url}"
    
    async def _execute_click(self, node: ActionNode, page_context) -> Any:
        """执行点击操作"""
        if not page_context:
            raise ValueError("Page context required for click operation")
        # await page_context.click(node.locator)
        return f"Clicked on {node.locator}"
    
    async def _execute_type(self, node: ActionNode, page_context) -> Any:
        """执行输入操作"""
        if not page_context:
            raise ValueError("Page context required for type operation")
        # await page_context.fill(node.locator, node.text)
        return f"Typed '{node.text}' into {node.locator}"
    
    async def _execute_assert(self, node: ActionNode, page_context) -> Any:
        """执行断言操作"""
        if not page_context:
            raise ValueError("Page context required for assert operation")
        # await page_context.wait_for_selector(node.locator, timeout=node.timeout)
        return f"Asserted presence of {node.locator}"
    
    async def _execute_wait(self, node: ActionNode, page_context) -> Any:
        """执行等待操作"""
        wait_time = node.metadata.get('wait_time', 1000) / 1000  # 转换为秒
        await asyncio.sleep(wait_time)
        return f"Waited for {wait_time} seconds"
    
    async def _execute_extract(self, node: ActionNode, page_context) -> Any:
        """执行数据提取操作"""
        if not page_context:
            raise ValueError("Page context required for extract operation")
        # extracted_text = await page_context.text_content(node.locator)
        return f"Extracted data from {node.locator}"
    
    async def _execute_scroll(self, node: ActionNode, page_context) -> Any:
        """执行滚动操作"""
        if not page_context:
            raise ValueError("Page context required for scroll operation")
        # await page_context.scroll_into_view_if_needed(node.locator)
        return f"Scrolled to {node.locator}"
    
    async def _execute_hover(self, node: ActionNode, page_context) -> Any:
        """执行悬停操作"""
        if not page_context:
            raise ValueError("Page context required for hover operation")
        # await page_context.hover(node.locator)
        return f"Hovered over {node.locator}"
    
    async def _execute_select(self, node: ActionNode, page_context) -> Any:
        """执行选择操作"""
        if not page_context:
            raise ValueError("Page context required for select operation")
        # await page_context.select_option(node.locator, node.text)
        return f"Selected '{node.text}' from {node.locator}"
    
    async def _execute_screenshot(self, node: ActionNode, page_context) -> Any:
        """执行截图操作"""
        if not page_context:
            raise ValueError("Page context required for screenshot operation")
        # screenshot_path = f"screenshot_{int(time.time())}.png"
        # await page_context.screenshot(path=screenshot_path)
        return f"screenshot_{int(time.time())}.png"
    
    def get_execution_history(self, limit: int = 10) -> List[ExecutionResult]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def get_running_graphs(self) -> Dict[str, ActionGraph]:
        """获取正在运行的图"""
        return self.running_graphs.copy()
    
    def cancel_execution(self, graph_id: str) -> bool:
        """取消执行"""
        if graph_id in self.running_graphs:
            graph = self.running_graphs[graph_id]
            graph.status = NodeStatus.FAILED
            graph.end_time = datetime.now()
            del self.running_graphs[graph_id]
            return True
        return False


# 导入asyncio用于异步操作
import asyncio


# 示例使用
if __name__ == "__main__":
    # 创建示例Action Graph
    sample_graph_data = {
        "goal": "search_product",
        "nodes": [
            {"id": "openHome", "type": "navigate", "url": "https://example.com"},
            {"id": "findSearch", "type": "assert", "locator": "input[name='q']"},
            {"id": "fill", "type": "type", "locator": "input[name='q']", "text": "Kindle"},
            {"id": "submit", "type": "click", "locator": "button[type='submit']"},
            {"id": "assertResults", "type": "assert", "locator": "#results"}
        ],
        "edges": [
            {"from": "openHome", "to": "findSearch"},
            {"from": "findSearch", "to": "fill"},
            {"from": "fill", "to": "submit"},
            {"from": "submit", "to": "assertResults"}
        ],
        "budgetTokens": 3000
    }
    
    # 创建引擎并执行
    engine = ActionGraphEngine()
    graph = engine.parse_graph(sample_graph_data)
    
    # 验证图
    errors = engine.validate_graph(graph)
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Graph validation passed")
        
        # 异步执行示例
        async def run_example():
            result = await engine.execute_graph(graph, ExecutionMode.DRY_RUN)
            print(f"Execution result: Success={result.success}, Completed={result.completed_nodes}/{result.total_nodes}")
        
        # asyncio.run(run_example())


# 为了兼容性，提供ActionGraphExecutor别名
ActionGraphExecutor = ActionGraphEngine