"""MCP Configuration management."""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from .mcp_types import MCPServerConfig, MCPServerType


class MCPConfig:
    """MCP 配置管理器
    
    负责加载、保存和管理 MCP 服务器配置
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config_data: Dict[str, Any] = {}
        self._load_config()
        
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "mcp_servers.json")
        
    def _load_config(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load MCP config from {self.config_path}: {e}")
                self._config_data = self._get_default_config()
        else:
            self._config_data = self._get_default_config()
            self._save_config()
            
    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save MCP config to {self.config_path}: {e}")
            
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0",
            "servers": {
                "playwright": {
                    "type": "playwright",
                    "command": "npx",
                    "args": ["-y", "@playwright/mcp"],
                    "env": {},
                    "enabled": True,
                    "timeout": 30,
                    "retry_count": 3,
                    "description": "Playwright MCP server for browser automation"
                },
                "playwright_extension": {
                    "type": "playwright",
                    "command": "npx",
                    "args": ["-y", "@playwright/mcp", "--extension"],
                    "env": {},
                    "enabled": False,
                    "timeout": 30,
                    "retry_count": 3,
                    "description": "Playwright MCP server with browser extension support"
                },
                "filesystem": {
                    "type": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "E:\\Code\\PythonDir\\Agents\\Aura"],
                    "env": {},
                    "enabled": False,
                    "timeout": 30,
                    "retry_count": 3,
                    "description": "Filesystem MCP server for file operations"
                },
                "brave_search": {
                    "type": "search",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "env": {
                        "BRAVE_API_KEY": "your-brave-api-key-here"
                    },
                    "enabled": False,
                    "timeout": 30,
                    "retry_count": 3,
                    "description": "Brave Search MCP server for web search"
                },
                "memory": {
                    "type": "custom",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"],
                    "env": {},
                    "enabled": False,
                    "timeout": 30,
                    "retry_count": 3,
                    "description": "Memory MCP server for persistent storage"
                }
            },
            "global_settings": {
                "auto_reconnect": True,
                "max_reconnect_attempts": 5,
                "reconnect_delay": 2,
                "log_level": "INFO",
                "concurrent_connections": 5,
                "health_check_interval": 60
            }
        }
        
    def get_server_configs(self) -> List[MCPServerConfig]:
        """获取所有服务器配置"""
        configs = []
        
        servers = self._config_data.get("servers", {})
        for name, server_data in servers.items():
            try:
                server_type = MCPServerType(server_data.get("type", "custom"))
                config = MCPServerConfig(
                    name=name,
                    server_type=server_type,
                    command=server_data.get("command", ""),
                    args=server_data.get("args", []),
                    env=server_data.get("env"),
                    enabled=server_data.get("enabled", True),
                    timeout=server_data.get("timeout", 30),
                    retry_count=server_data.get("retry_count", 3)
                )
                configs.append(config)
            except (ValueError, KeyError) as e:
                print(f"Warning: Invalid server config for {name}: {e}")
                
        return configs
        
    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """获取指定服务器配置"""
        servers = self._config_data.get("servers", {})
        if name not in servers:
            return None
            
        server_data = servers[name]
        try:
            server_type = MCPServerType(server_data.get("type", "custom"))
            return MCPServerConfig(
                name=name,
                server_type=server_type,
                command=server_data.get("command", ""),
                args=server_data.get("args", []),
                env=server_data.get("env"),
                enabled=server_data.get("enabled", True),
                timeout=server_data.get("timeout", 30),
                retry_count=server_data.get("retry_count", 3)
            )
        except (ValueError, KeyError) as e:
            print(f"Warning: Invalid server config for {name}: {e}")
            return None
            
    def add_server_config(self, config: MCPServerConfig) -> None:
        """添加服务器配置"""
        if "servers" not in self._config_data:
            self._config_data["servers"] = {}
            
        self._config_data["servers"][config.name] = {
            "type": config.server_type.value,
            "command": config.command,
            "args": config.args,
            "env": config.env or {},
            "enabled": config.enabled,
            "timeout": config.timeout,
            "retry_count": config.retry_count
        }
        
        self._save_config()
        
    def update_server_config(self, name: str, updates: Dict[str, Any]) -> bool:
        """更新服务器配置"""
        if "servers" not in self._config_data or name not in self._config_data["servers"]:
            return False
            
        server_config = self._config_data["servers"][name]
        server_config.update(updates)
        
        self._save_config()
        return True
        
    def remove_server_config(self, name: str) -> bool:
        """移除服务器配置"""
        if "servers" not in self._config_data or name not in self._config_data["servers"]:
            return False
            
        del self._config_data["servers"][name]
        self._save_config()
        return True
        
    def enable_server(self, name: str) -> bool:
        """启用服务器"""
        return self.update_server_config(name, {"enabled": True})
        
    def disable_server(self, name: str) -> bool:
        """禁用服务器"""
        return self.update_server_config(name, {"enabled": False})
        
    def get_global_setting(self, key: str, default: Any = None) -> Any:
        """获取全局设置"""
        return self._config_data.get("global_settings", {}).get(key, default)
        
    def set_global_setting(self, key: str, value: Any) -> None:
        """设置全局设置"""
        if "global_settings" not in self._config_data:
            self._config_data["global_settings"] = {}
            
        self._config_data["global_settings"][key] = value
        self._save_config()
        
    def get_playwright_extension_config(self) -> Optional[MCPServerConfig]:
        """获取 Playwright 扩展配置"""
        return self.get_server_config("playwright_extension")
        
    def enable_playwright_extension(self) -> bool:
        """启用 Playwright 浏览器扩展模式"""
        # 禁用普通 Playwright 服务器
        self.disable_server("playwright")
        # 启用扩展模式服务器
        return self.enable_server("playwright_extension")
        
    def disable_playwright_extension(self) -> bool:
        """禁用 Playwright 浏览器扩展模式"""
        # 禁用扩展模式服务器
        self.disable_server("playwright_extension")
        # 启用普通 Playwright 服务器
        return self.enable_server("playwright")
        
    def enable_filesystem_server(self, workspace_path: str = None) -> bool:
        """启用文件系统 MCP 服务器"""
        if workspace_path:
            return self.update_server_config("filesystem", {
                "args": ["npx", "-y", "@modelcontextprotocol/server-filesystem", workspace_path],
                "enabled": True
            })
        return self.enable_server("filesystem")
        
    def enable_search_server(self, api_key: str = None) -> bool:
        """启用搜索 MCP 服务器"""
        if api_key:
            return self.update_server_config("brave_search", {
                "env": {"BRAVE_API_KEY": api_key},
                "enabled": True
            })
        return self.enable_server("brave_search")
        
    def get_enabled_servers(self) -> List[str]:
        """获取已启用的服务器列表"""
        enabled = []
        servers = self._config_data.get("servers", {})
        for name, config in servers.items():
            if config.get("enabled", False):
                enabled.append(name)
        return enabled
        
    def get_server_by_type(self, server_type: str) -> List[str]:
        """根据类型获取服务器列表"""
        servers = []
        server_configs = self._config_data.get("servers", {})
        for name, config in server_configs.items():
            if config.get("type") == server_type:
                servers.append(name)
        return servers
        
    def export_config(self, export_path: str) -> bool:
        """导出配置到指定路径"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Failed to export config to {export_path}: {e}")
            return False
            
    def import_config(self, import_path: str) -> bool:
        """从指定路径导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
                
            # 验证配置格式
            if not isinstance(imported_data, dict) or "servers" not in imported_data:
                print("Invalid config format")
                return False
                
            self._config_data = imported_data
            self._save_config()
            return True
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to import config from {import_path}: {e}")
            return False
            
    @property
    def config_data(self) -> Dict[str, Any]:
        """获取完整配置数据"""
        return self._config_data.copy()