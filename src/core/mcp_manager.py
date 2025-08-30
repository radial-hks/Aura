"""MCP Manager for handling Model Context Protocol connections."""

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
        """初始化 MCP 管理器"""
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
        """执行命令通过 MCP Agent"""
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
        """获取可用的工具列表"""
        if not self._multi_mcp:
            return []
            
        try:
            tools = await self._multi_mcp.list_tools()
            return [tool.name for tool in tools]
        except Exception as e:
            self.logger.error(f"Error getting available tools: {e}")
            return []
            
    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务器状态"""
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
        """重连指定服务器"""
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
        """启动健康检查任务"""
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
        """执行健康检查"""
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
        """关闭 MCP 管理器"""
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
        """获取健康指标"""
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
        """诊断连接问题"""
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