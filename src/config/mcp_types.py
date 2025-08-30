"""MCP类型定义模块

这个模块包含MCP相关的类型定义，避免循环导入问题。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


class MCPServerType(Enum):
    """MCP服务器类型枚举"""
    PLAYWRIGHT = "playwright"
    FILESYSTEM = "filesystem"
    SEARCH = "search"
    MEMORY = "memory"
    CUSTOM = "custom"


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    server_type: MCPServerType
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3
    health_check_interval: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "server_type": self.server_type.value,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "health_check_interval": self.health_check_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """从字典创建配置对象"""
        return cls(
            name=data["name"],
            server_type=MCPServerType(data["server_type"]),
            command=data["command"],
            args=data["args"],
            env=data.get("env"),
            enabled=data.get("enabled", True),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            health_check_interval=data.get("health_check_interval", 60)
        )