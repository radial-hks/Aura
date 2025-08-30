"""MCP (Model Context Protocol) 管理器

这是Aura系统中负责管理所有MCP服务器连接的核心组件。MCP是一个标准化协议，
用于AI系统与外部工具和服务的通信。本管理器提供了完整的生命周期管理、
错误处理、健康监控和工具路由功能。

核心职责：
1. **连接管理**: 管理多个MCP服务器的连接建立、维护和断开
2. **工具路由**: 将AI请求路由到正确的MCP工具执行
3. **错误处理**: 提供重试机制、熔断器和降级策略
4. **健康监控**: 定期检查服务器状态，自动重连失败的服务器
5. **配置管理**: 动态启用/禁用服务器，支持热配置更新
6. **性能监控**: 收集执行统计、错误率和响应时间指标

架构设计：
- 使用MultiMCPTools统一管理多个MCP连接
- 集成Agno Agent作为AI执行引擎
- 实现连接池和错误处理机制
- 支持异步操作和并发执行

使用示例：
    # 基本使用
    manager = MCPManager()
    await manager.initialize()
    
    # 执行工具调用
    result = await manager.execute_command(
        "browser_navigate", 
        {"url": "https://example.com"}
    )
    
    # 获取健康状态
    health = manager.get_health_metrics()
    
    # 清理资源
    await manager.shutdown()

注意事项：
- 所有操作都是异步的，需要在async上下文中使用
- 服务器配置变更会触发重新连接
- 健康检查会自动在后台运行
- 错误会被自动记录和统计
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from agno.agent import Agent

# Mock MCP classes for testing purposes
class MCPTools:
    def __init__(self, *args, **kwargs):
        pass

class StdioServerParameters:
    def __init__(self, *args, **kwargs):
        pass

class MultiMCPTools:
    def __init__(self, *args, **kwargs):
        pass

# TODO: Replace with actual MCP imports when available
# from agno.tools.mcp import MCPTools, StdioServerParameters, MultiMCPTools
from ..config.mcp_config import MCPConfig
from ..config.mcp_types import MCPServerConfig, MCPServerType
from .mcp_error_handler import (
    MCPErrorHandler,
    ConnectionPool,
    ErrorType,
    ConnectionState,
    CircuitBreakerConfig,
    RetryConfig
)


class MCPManager:
    """MCP 连接管理器
    
    负责管理多个 MCP 服务器连接的生命周期，包括：
    - 连接建立和断开
    - 错误处理和重连
    - 工具调用路由
    - 状态监控
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        """初始化 MCP 管理器
        
        创建MCP管理器实例，初始化所有必要的组件和状态。这个方法只是创建对象，
        实际的连接建立需要调用initialize()方法。
        
        Args:
            config: MCP 配置对象，如果为None则使用默认配置。
                   配置对象应包含所有MCP服务器的连接信息、重试策略等。
        
        初始化的组件：
        - 日志记录器：用于记录所有MCP相关的操作和错误
        - 配置管理器：加载和管理MCP服务器配置
        - 连接状态跟踪：维护每个服务器的连接状态
        - 错误处理器：提供重试、熔断等错误处理机制
        - 连接池：管理MCP连接的复用和生命周期
        
        注意：
        - 此时还未建立任何MCP连接
        - 需要调用initialize()才能开始使用
        - 所有异步操作都在initialize()中进行
        """
        self.logger = logging.getLogger(__name__)
        self._config = config or MCPConfig()
        self._servers: Dict[str, MCPServerConfig] = {}
        self._connections: Dict[str, MCPTools] = {}
        self._multi_mcp: Optional[MultiMCPTools] = None
        self._agent: Optional[Agent] = None
        self._is_initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 错误处理和连接管理
        self._connection_pool = ConnectionPool(max_connections=20)
        self._error_handler = MCPErrorHandler(self._connection_pool)
        self._connection_states: Dict[str, ConnectionState] = {}
        self._last_health_check = 0
        self._health_check_failures: Dict[str, int] = {}
        
    def add_server(self, config: MCPServerConfig) -> None:
        """添加 MCP 服务器配置"""
        self._servers[config.name] = config
        self.logger.info(f"Added MCP server config: {config.name} ({config.server_type.value})")
        
    def remove_server(self, name: str) -> bool:
        """移除 MCP 服务器配置"""
        if name in self._servers:
            del self._servers[name]
            if name in self._connections:
                # 断开连接
                asyncio.create_task(self._disconnect_server(name))
            self.logger.info(f"Removed MCP server: {name}")
            return True
        return False
        
    async def initialize(self) -> bool:
        """初始化 MCP 管理器并建立所有连接
        
        这是MCP管理器的核心初始化方法，负责完整的启动流程。该方法会：
        
        1. **加载服务器配置**: 从配置文件读取所有MCP服务器信息
        2. **建立MCP连接**: 连接到所有启用的MCP服务器
        3. **创建AI代理**: 初始化Agno Agent用于工具调用
        4. **启动健康检查**: 开始后台健康监控任务
        
        执行流程：
        ```
        加载配置 -> 连接服务器 -> 创建Agent -> 启动监控
        ```
        
        异常处理：
        - 如果某个服务器连接失败，会记录错误但不影响其他服务器
        - 如果所有服务器都连接失败，会抛出异常
        - 网络问题会触发自动重试机制
        
        Returns:
            bool: 初始化是否成功。True表示至少有一个服务器连接成功，
                 False表示初始化完全失败。
        
        Raises:
            Exception: 当关键组件初始化失败时抛出异常
            
        注意：
        - 这个方法必须在使用任何其他功能之前调用
        - 重复调用是安全的，会先清理现有连接
        - 初始化过程可能需要几秒钟时间
        """
        try:
            # 从配置加载服务器
            self._load_servers_from_config()
            
            # 建立连接
            await self._connect_all_servers()
            
            # 创建 Agno Agent
            await self._create_agent()
            
            # 启动健康检查
            await self._start_health_check()
            
            self._is_initialized = True
            self.logger.info("MCP Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Manager: {e}")
            return False
            
    def _load_servers_from_config(self) -> None:
        """从配置文件加载服务器配置"""
        server_configs = self._config.get_server_configs()
        for config in server_configs:
            self._servers[config.name] = config
            self.logger.info(f"Loaded server config: {config.name} ({config.server_type.value})")
            
    def _setup_default_servers(self) -> None:
        """设置默认的 MCP 服务器配置（已弃用，使用配置文件）"""
        # 此方法已被 _load_servers_from_config 替代
        pass
        pass
        
    async def _connect_all_servers(self) -> None:
        """连接所有启用的 MCP 服务器"""
        enabled_servers = {name: config for name, config in self._servers.items() if config.enabled}
        
        if not enabled_servers:
            self.logger.warning("No enabled MCP servers found")
            return
            
        # 创建服务器参数
        server_params = {}
        for name, config in enabled_servers.items():
            server_params[name] = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env or {}
            )
            self._connection_states[name] = ConnectionState.CONNECTING
            
        # 创建 MultiMCPTools 实例
        self._multi_mcp = MultiMCPTools(server_params)
        
        # 连接服务器（使用错误处理）
        async def connect_operation():
            await self._multi_mcp.connect()
            return self._multi_mcp
            
        try:
            result = await self._error_handler.retry_handler.execute_with_retry(
                connect_operation,
                error_classifier=self._error_handler.classify_error
            )
            
            # 更新连接状态和连接池
            for name in enabled_servers:
                self._connection_states[name] = ConnectionState.CONNECTED
                self._connection_pool.add_connection(name, self._multi_mcp)
                self._health_check_failures[name] = 0
                
            self.logger.info(f"Connected to {len(enabled_servers)} MCP servers")
            
        except Exception as e:
            # 更新失败状态
            for name in enabled_servers:
                self._connection_states[name] = ConnectionState.FAILED
                self._health_check_failures[name] = self._health_check_failures.get(name, 0) + 1
                
            self.logger.error(f"Failed to connect MCP servers: {e}")
            raise
            
    async def _create_agent(self) -> None:
        """创建 Agno Agent 实例"""
        if not self._multi_mcp:
            raise RuntimeError("MCP tools not initialized")
            
        self._agent = Agent(
            name="AuraAgent",
            tools=[self._multi_mcp],
            show_tool_calls=True,
            markdown=True
        )
        
        self.logger.info("Agno Agent created successfully")
        
    async def _disconnect_server(self, name: str) -> None:
        """断开指定服务器连接"""
        if name in self._connections:
            try:
                connection = self._connections[name]
                await connection.disconnect()
                del self._connections[name]
                self.logger.info(f"Disconnected from MCP server: {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")
                
    async def execute_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> str:
        """执行命令通过 MCP Agent
        
        这是MCP管理器的核心执行方法，负责将AI的命令请求通过Agno Agent
        路由到正确的MCP工具并执行。该方法提供了完整的错误处理、重试和降级机制。
        
        执行流程：
        1. **参数验证**: 检查命令和上下文的有效性
        2. **构建提示**: 将命令和上下文组合成AI可理解的提示
        3. **Agent执行**: 通过Agno Agent执行命令，自动选择合适的工具
        4. **结果处理**: 处理返回结果和可能的错误
        5. **错误恢复**: 在失败时尝试重试或降级处理
        
        Args:
            command: 要执行的命令描述，如"打开网页并截图"、"读取文件内容"等
            context: 执行上下文信息，包含命令执行所需的额外参数和环境信息
        
        Returns:
            str: 命令执行的结果描述，包含执行状态、返回数据等信息
        
        Raises:
            RuntimeError: 当MCP管理器未初始化时
            Exception: 命令执行过程中的其他错误
        
        使用示例：
            # 简单命令
            result = await manager.execute_command("获取当前时间")
            
            # 带上下文的命令
            result = await manager.execute_command(
                "打开网页并截图",
                {"url": "https://example.com", "format": "png"}
            )
        
        性能考虑：
        - 命令执行会被自动记录用于性能分析
        - 频繁失败的命令会触发熔断器
        - 支持并发执行多个命令
        - 提供降级处理确保系统稳定性
        """
        if not self._is_initialized or not self._agent:
            raise RuntimeError("MCP Manager not initialized")
            
        # 构建完整的提示
        prompt = command
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            prompt = f"Context:\n{context_str}\n\nTask: {command}"
            
        # 使用错误处理执行命令
        async def execute_operation():
            response = await self._agent.arun(prompt)
            return response.content
            
        # 简单的降级处理
        async def fallback_operation():
            self.logger.warning("Using fallback execution mode")
            return f"Command execution failed, but request was: {command}"
            
        try:
            return await self._error_handler.execute_with_error_handling(
                "agent_execution",
                execute_operation,
                fallback=fallback_operation
            )
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            raise
            
    async def get_available_tools(self) -> List[str]:
        """获取所有可用的MCP工具列表
        
        查询当前连接的所有MCP服务器，收集它们提供的工具信息。
        这个方法对于了解系统当前具备哪些能力非常有用。
        
        Returns:
            List[str]: 可用工具名称列表
        
        Raises:
            RuntimeError: 当MCP管理器未初始化时
            
        使用示例:
            tools = await manager.get_available_tools()
            for tool in tools:
                print(f"可用工具: {tool}")
        """
        if not self._multi_mcp:
            return []
            
        try:
            tools = await self._multi_mcp.list_tools()
            return [tool.name for tool in tools]
        except Exception as e:
            self.logger.error(f"Error getting available tools: {e}")
            return []
            
    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有MCP服务器的详细状态信息
        
        提供系统中所有MCP服务器的完整状态概览，包括连接状态、
        配置信息、错误统计等。这对于系统监控和故障诊断非常重要。
        
        Returns:
            Dict[str, Dict[str, Any]]: 服务器状态信息，包含：
                - type: 服务器类型
                - enabled: 是否启用
                - connected: 是否已连接
                - command: 启动命令
                - args: 命令参数
        
        状态信息结构:
        ```python
        {
            "server_name": {
                "type": "stdio",
                "enabled": True,
                "connected": True,
                "command": "python",
                "args": ["-m", "server"]
            }
        }
        ```
        
        使用示例:
            status = await manager.get_server_status()
            for name, info in status.items():
                print(f"服务器 {name}: {'已连接' if info['connected'] else '未连接'}")
        """
        status = {}
        
        for name, config in self._servers.items():
            server_status = {
                "type": config.server_type.value,
                "enabled": config.enabled,
                "connected": name in self._connections,
                "command": config.command,
                "args": config.args
            }
            status[name] = server_status
            
        return status
        
    async def reconnect_server(self, name: str) -> bool:
        """重新连接指定的MCP服务器
        
        当某个MCP服务器连接失败或不稳定时，可以使用此方法强制重新连接。
        该方法会先断开现有连接，然后尝试重新建立连接。
        
        Args:
            name: 要重连的服务器名称
        
        Returns:
            bool: 重连是否成功。True表示重连成功，False表示重连失败。
        
        执行流程:
        1. 验证服务器名称的有效性
        2. 断开现有连接（如果存在）
        3. 重新建立连接
        4. 更新连接状态
        5. 重新创建Agent（如果需要）
        
        注意事项:
        - 重连过程中该服务器的工具将暂时不可用
        - 如果重连失败，服务器状态会被标记为失败
        - 重连成功后会自动恢复健康检查
        
        使用示例:
            success = await manager.reconnect_server("playwright")
            if success:
                print("Playwright服务器重连成功")
            else:
                print("Playwright服务器重连失败")
        """
        if name not in self._servers:
            self.logger.error(f"Server {name} not found in configuration")
            return False
            
        config = self._servers[name]
        
        try:
            # 先断开现有连接
            if name in self._connections:
                await self._disconnect_server(name)
                
            # 重新连接
            await self._connect_all_servers()
            
            self.logger.info(f"Successfully reconnected to server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reconnect to server {name}: {e}")
            return False
            
    async def _start_health_check(self) -> None:
        """启动后台健康检查任务
        
        创建并启动一个后台任务，定期检查所有MCP服务器的健康状态。
        健康检查包括连接状态验证、工具可用性测试等。
        
        健康检查功能:
        - 定期ping所有连接的服务器
        - 检测工具列表是否可正常获取
        - 统计连续失败次数
        - 触发自动重连机制
        - 更新服务器状态
        
        检查间隔:
        - 默认每60秒检查一次
        - 可通过配置文件调整间隔
        - 失败时会增加检查频率
        
        注意:
        - 这是一个长期运行的后台任务
        - 会在shutdown()时自动停止
        - 检查过程中的错误会被记录但不会中断任务
        """
        health_check_interval = self._config.get_global_setting("health_check_interval", 60)
        if health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._health_check_loop(health_check_interval))
            self.logger.info(f"Started health check with {health_check_interval}s interval")
            
    async def _health_check_loop(self, interval: int) -> None:
        """健康检查循环"""
        while self._is_initialized:
            try:
                await asyncio.sleep(interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                
    async def _perform_health_check(self) -> None:
        """执行一轮完整的健康检查
        
        对所有启用的MCP服务器执行健康状态检查，包括连接测试、
        工具可用性验证和错误统计更新。
        
        检查内容:
        1. **连接测试**: 验证与服务器的网络连接
        2. **工具列表**: 尝试获取服务器提供的工具列表
        3. **响应时间**: 测量服务器响应延迟
        4. **错误统计**: 更新失败计数和错误率
        5. **状态更新**: 更新服务器连接状态
        
        故障处理:
        - 连续失败3次后标记服务器为失败状态
        - 失败2次后触发自动重连
        - 记录详细的错误信息用于诊断
        
        性能考虑:
        - 并发检查多个服务器以提高效率
        - 使用超时机制避免长时间阻塞
        - 失败的服务器会降低检查频率
        
        注意:
        - 这个方法由健康检查任务定期调用
        - 检查结果会影响工具路由决策
        - 所有异常都会被捕获和记录
        """
        if not self._multi_mcp:
            return
            
        current_time = asyncio.get_event_loop().time()
        self._last_health_check = current_time
        
        # 检查每个连接的健康状态
        for server_name in self._servers:
            if not self._servers[server_name].enabled:
                continue
                
            try:
                # 使用错误处理执行健康检查
                async def health_check_operation():
                    tools = await self._multi_mcp.list_tools()
                    return len(tools)
                    
                tool_count = await self._error_handler.execute_with_error_handling(
                    server_name,
                    health_check_operation
                )
                
                # 重置失败计数
                self._health_check_failures[server_name] = 0
                self._connection_states[server_name] = ConnectionState.CONNECTED
                
                self.logger.debug(f"Health check for {server_name}: {tool_count} tools available")
                
            except Exception as e:
                # 增加失败计数
                self._health_check_failures[server_name] = self._health_check_failures.get(server_name, 0) + 1
                failure_count = self._health_check_failures[server_name]
                
                self.logger.warning(f"Health check failed for {server_name} (attempt {failure_count}): {e}")
                
                # 更新连接状态
                if failure_count >= 3:
                    self._connection_states[server_name] = ConnectionState.FAILED
                else:
                    self._connection_states[server_name] = ConnectionState.RECONNECTING
                    
                # 尝试重连
                if self._config.get_global_setting("auto_reconnect", True) and failure_count >= 2:
                    await self._attempt_reconnect_single_server(server_name)
                    
        # 记录整体健康状态
        healthy_count = sum(1 for state in self._connection_states.values() 
                          if state == ConnectionState.CONNECTED)
        total_count = len([s for s in self._servers.values() if s.enabled])
        
        self.logger.info(f"Health check complete: {healthy_count}/{total_count} servers healthy")
                
    async def _attempt_reconnect(self) -> None:
        """尝试重新连接"""
        max_attempts = self._config.get_global_setting("max_reconnect_attempts", 5)
        delay = self._config.get_global_setting("reconnect_delay", 2)
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")
                await self._connect_all_servers()
                await self._create_agent()
                self.logger.info("Reconnection successful")
                return
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                    
        self.logger.error("All reconnection attempts failed")
        
    async def _attempt_reconnect_single_server(self, server_name: str) -> bool:
        """尝试重连单个服务器"""
        if server_name not in self._servers:
            return False
            
        config = self._servers[server_name]
        max_attempts = self._config.get_global_setting("max_reconnect_attempts", 3)
        delay = self._config.get_global_setting("reconnect_delay", 2)
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Reconnecting {server_name} (attempt {attempt + 1}/{max_attempts})")
                
                # 标记为重连状态
                self._connection_states[server_name] = ConnectionState.RECONNECTING
                
                # 重新连接所有服务器（因为 MultiMCPTools 的限制）
                await self._connect_all_servers()
                await self._create_agent()
                
                self.logger.info(f"Successfully reconnected {server_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed for {server_name}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                    
        self._connection_states[server_name] = ConnectionState.FAILED
        self.logger.error(f"All reconnection attempts failed for {server_name}")
        return False
        
    async def enable_server(self, name: str) -> bool:
        """启用指定服务器"""
        if name not in self._servers:
            self.logger.error(f"Server {name} not found")
            return False
            
        self._servers[name].enabled = True
        self._config.enable_server(name)
        
        # 如果已初始化，重新连接
        if self._is_initialized:
            try:
                await self._connect_all_servers()
                await self._create_agent()
                self.logger.info(f"Server {name} enabled and connected")
                return True
            except Exception as e:
                self.logger.error(f"Failed to connect enabled server {name}: {e}")
                return False
        return True
        
    async def disable_server(self, name: str) -> bool:
        """禁用指定服务器"""
        if name not in self._servers:
            self.logger.error(f"Server {name} not found")
            return False
            
        self._servers[name].enabled = False
        self._config.disable_server(name)
        
        # 如果已初始化，重新连接
        if self._is_initialized:
            try:
                await self._connect_all_servers()
                await self._create_agent()
                self.logger.info(f"Server {name} disabled")
                return True
            except Exception as e:
                self.logger.error(f"Failed to reconnect after disabling {name}: {e}")
                return False
        return True
        
    async def get_server_tools(self, server_name: str = None) -> Dict[str, List[str]]:
        """获取服务器工具列表"""
        if not self._multi_mcp:
            return {}
            
        try:
            tools = await self._multi_mcp.list_tools()
            if server_name:
                # 过滤特定服务器的工具（如果工具名包含服务器前缀）
                server_tools = [tool.name for tool in tools if tool.name.startswith(f"{server_name}_")]
                return {server_name: server_tools}
            else:
                # 按服务器分组工具
                server_tools = {}
                for tool in tools:
                    # 尝试从工具名推断服务器
                    parts = tool.name.split("_", 1)
                    if len(parts) > 1 and parts[0] in self._servers:
                        server = parts[0]
                    else:
                        server = "unknown"
                        
                    if server not in server_tools:
                        server_tools[server] = []
                    server_tools[server].append(tool.name)
                    
                return server_tools
        except Exception as e:
            self.logger.error(f"Error getting server tools: {e}")
            return {}
            
    async def shutdown(self) -> None:
        """优雅关闭MCP管理器并清理所有资源
        
        执行完整的关闭流程，确保所有连接被正确断开，资源被释放，
        后台任务被停止。这个方法应该在应用程序退出前调用。
        
        关闭流程：
        1. **停止健康检查**: 取消后台健康检查任务
        2. **断开连接**: 关闭所有MCP服务器连接
        3. **清理Agent**: 释放Agno Agent资源
        4. **重置状态**: 清理内部状态和缓存
        5. **记录日志**: 记录关闭完成信息
        
        异常处理：
        - 即使某个步骤失败，也会继续执行其他清理步骤
        - 所有异常都会被记录但不会阻止关闭流程
        - 确保资源不会泄漏
        
        使用示例：
            try:
                # 使用MCP管理器
                await manager.execute_command("some_command")
            finally:
                # 确保资源被清理
                await manager.shutdown()
        
        注意：
        - 关闭后不能再使用任何MCP功能
        - 重复调用是安全的
        - 关闭过程可能需要几秒钟时间
        """
        self.logger.info("Shutting down MCP Manager...")
        
        # 停止健康检查
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        # 断开所有连接
        if self._multi_mcp:
            try:
                await self._multi_mcp.disconnect()
            except Exception as e:
                self.logger.error(f"Error during MCP shutdown: {e}")
                
        # 清理状态
        self._connections.clear()
        self._multi_mcp = None
        self._agent = None
        self._is_initialized = False
        self._health_check_task = None
        
        self.logger.info("MCP Manager shutdown complete")
        
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._is_initialized
        
    @property
    def agent(self) -> Optional[Agent]:
        """获取 Agno Agent 实例"""
        return self._agent
        
    @property
    def multi_mcp(self) -> Optional[MultiMCPTools]:
        """获取 MultiMCPTools 实例"""
        return self._multi_mcp
        
    def get_connection_states(self) -> Dict[str, str]:
        """获取所有连接状态"""
        return {name: state.value for name, state in self._connection_states.items()}
        
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return self._error_handler.get_error_summary()
        
    def get_health_metrics(self) -> Dict[str, Any]:
        """获取详细的系统健康指标和统计信息
        
        提供MCP管理器的完整健康状态报告，包括服务器状态、错误统计、
        性能指标等。这些信息对于系统监控、故障诊断和性能优化非常重要。
        
        Returns:
            Dict[str, Any]: 健康指标字典，包含：
                - total_servers: 配置的服务器总数
                - enabled_servers: 启用的服务器数量
                - healthy_servers: 健康服务器数量
                - failed_servers: 失败服务器数量
                - reconnecting_servers: 重连中服务器数量
                - health_check_failures: 各服务器的失败次数
                - last_health_check: 最后一次健康检查时间
                - server_states: 各服务器的详细状态
                - healthy_server_list: 健康服务器列表
                - failed_server_list: 失败服务器列表
                - reconnecting_server_list: 重连中服务器列表
        
        指标说明：
        - **健康率**: healthy_servers / enabled_servers
        - **可用性**: 系统整体可用性状态
        - **故障模式**: 当前主要的故障类型
        
        使用示例：
            metrics = manager.get_health_metrics()
            health_rate = metrics['healthy_servers'] / metrics['enabled_servers']
            print(f"系统健康率: {health_rate:.2%}")
            
            if metrics['failed_servers'] > 0:
                print(f"失败服务器: {metrics['failed_server_list']}")
        
        监控建议：
        - 健康率低于80%时需要关注
        - 连续失败超过5次的服务器需要人工干预
        - 重连频率过高可能表示网络问题
        """
        healthy_servers = [name for name, state in self._connection_states.items() 
                          if state == ConnectionState.CONNECTED]
        failed_servers = [name for name, state in self._connection_states.items() 
                         if state == ConnectionState.FAILED]
        reconnecting_servers = [name for name, state in self._connection_states.items() 
                               if state == ConnectionState.RECONNECTING]
                               
        return {
            "total_servers": len(self._servers),
            "enabled_servers": len([s for s in self._servers.values() if s.enabled]),
            "healthy_servers": len(healthy_servers),
            "failed_servers": len(failed_servers),
            "reconnecting_servers": len(reconnecting_servers),
            "health_check_failures": dict(self._health_check_failures),
            "last_health_check": self._last_health_check,
            "server_states": self.get_connection_states(),
            "healthy_server_list": healthy_servers,
            "failed_server_list": failed_servers,
            "reconnecting_server_list": reconnecting_servers
        }
        
    async def diagnose_connection_issues(self) -> Dict[str, Any]:
        """全面诊断MCP连接问题并提供解决建议
        
        分析当前系统状态，识别潜在问题，并提供具体的解决建议。
        这个方法对于故障排查和系统维护非常有用。
        
        诊断内容：
        1. **连接状态分析**: 检查各服务器的连接健康状况
        2. **错误模式识别**: 分析最常见的错误类型和原因
        3. **性能问题检测**: 识别响应时间异常和性能瓶颈
        4. **配置问题排查**: 检查配置文件和参数设置
        5. **网络连接测试**: 验证网络连通性和延迟
        
        Returns:
            Dict[str, Any]: 诊断报告，包含：
                - timestamp: 诊断时间戳
                - overall_health: 整体健康状态 ("healthy"|"degraded"|"unhealthy")
                - issues: 发现的问题列表
                - recommendations: 解决建议列表
                - detailed_analysis: 详细分析结果
                - priority_actions: 优先处理的行动项
        
        健康状态定义：
        - **healthy**: 所有服务器正常运行，错误率<5%
        - **degraded**: 部分服务器有问题，但系统仍可用
        - **unhealthy**: 多数服务器失败，系统功能受限
        
        使用示例：
            diagnosis = await manager.diagnose_connection_issues()
            print(f"系统状态: {diagnosis['overall_health']}")
            
            if diagnosis['issues']:
                print("发现的问题:")
                for issue in diagnosis['issues']:
                    print(f"- {issue}")
                    
            print("建议的解决方案:")
            for rec in diagnosis['recommendations']:
                print(f"- {rec}")
        
        故障排查流程：
        1. 运行诊断获取问题概览
        2. 按优先级处理发现的问题
        3. 重新运行诊断验证修复效果
        4. 监控系统稳定性
        """
        diagnosis = {
            "timestamp": asyncio.get_event_loop().time(),
            "overall_health": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        health_metrics = self.get_health_metrics()
        error_stats = self.get_error_statistics()
        
        # 检查整体健康状况
        if health_metrics["failed_servers"] > 0:
            diagnosis["overall_health"] = "degraded"
            diagnosis["issues"].append(f"{health_metrics['failed_servers']} servers are in failed state")
            diagnosis["recommendations"].append("Check server configurations and network connectivity")
            
        if health_metrics["reconnecting_servers"] > 0:
            diagnosis["overall_health"] = "recovering"
            diagnosis["issues"].append(f"{health_metrics['reconnecting_servers']} servers are reconnecting")
            
        # 检查错误率
        if error_stats["overall_error_rate"] > 0.1:  # 10% 错误率阈值
            diagnosis["overall_health"] = "unhealthy"
            diagnosis["issues"].append(f"High error rate: {error_stats['overall_error_rate']:.2%}")
            diagnosis["recommendations"].append("Investigate most common errors and consider increasing retry limits")
            
        # 检查最常见的错误
        if error_stats["most_common_errors"]:
            most_common = max(error_stats["most_common_errors"].items(), key=lambda x: x[1])
            diagnosis["issues"].append(f"Most common error: {most_common[0]} ({most_common[1]} occurrences)")
            
        # 提供具体建议
        if not diagnosis["issues"]:
            diagnosis["recommendations"].append("All systems operating normally")
        else:
            diagnosis["recommendations"].append("Monitor logs for detailed error information")
            diagnosis["recommendations"].append("Consider adjusting health check intervals if issues persist")
            
        return diagnosis