#!/usr/bin/env python3
"""MCP 配置管理工具

提供命令行界面来管理 MCP 服务器配置，包括：
- 查看服务器状态
- 启用/禁用服务器
- 添加/删除服务器配置
- 测试服务器连接
- 导入/导出配置
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# 设置项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from config.mcp_config import MCPConfig
from core.mcp_manager import MCPManager, MCPServerConfig, MCPServerType


class MCPConfigManager:
    """MCP 配置管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = MCPConfig()
        
    def list_servers(self) -> None:
        """列出所有服务器配置"""
        servers = self.config.config_data.get("servers", {})
        
        if not servers:
            print("No servers configured.")
            return
            
        print("\n=== MCP Servers Configuration ===")
        print(f"{'Name':<20} {'Type':<12} {'Status':<8} {'Description':<40}")
        print("-" * 80)
        
        for name, config in servers.items():
            status = "Enabled" if config.get("enabled", False) else "Disabled"
            server_type = config.get("type", "unknown")
            description = config.get("description", "No description")
            print(f"{name:<20} {server_type:<12} {status:<8} {description:<40}")
            
    def show_server_details(self, server_name: str) -> None:
        """显示服务器详细信息"""
        server_config = self.config.get_server_config(server_name)
        
        if not server_config:
            print(f"Server '{server_name}' not found.")
            return
            
        print(f"\n=== Server Details: {server_name} ===")
        print(f"Type: {server_config.server_type.value}")
        print(f"Command: {server_config.command}")
        print(f"Arguments: {' '.join(server_config.args)}")
        print(f"Environment: {server_config.env or 'None'}")
        print(f"Enabled: {server_config.enabled}")
        print(f"Timeout: {server_config.timeout}s")
        print(f"Retry Count: {server_config.retry_count}")
        
    def enable_server(self, server_name: str) -> None:
        """启用服务器"""
        if self.config.enable_server(server_name):
            print(f"Server '{server_name}' enabled successfully.")
        else:
            print(f"Failed to enable server '{server_name}'. Server not found.")
            
    def disable_server(self, server_name: str) -> None:
        """禁用服务器"""
        if self.config.disable_server(server_name):
            print(f"Server '{server_name}' disabled successfully.")
        else:
            print(f"Failed to disable server '{server_name}'. Server not found.")
            
    def add_server(self, name: str, server_type: str, command: str, args: list, 
                   env: Dict[str, str] = None, enabled: bool = True) -> None:
        """添加新服务器配置"""
        try:
            mcp_type = MCPServerType(server_type)
            config = MCPServerConfig(
                name=name,
                server_type=mcp_type,
                command=command,
                args=args,
                env=env,
                enabled=enabled
            )
            
            self.config.add_server_config(config)
            print(f"Server '{name}' added successfully.")
            
        except ValueError as e:
            print(f"Invalid server type '{server_type}'. Valid types: {[t.value for t in MCPServerType]}")
        except Exception as e:
            print(f"Failed to add server: {e}")
            
    def remove_server(self, server_name: str) -> None:
        """删除服务器配置"""
        if self.config.remove_server_config(server_name):
            print(f"Server '{server_name}' removed successfully.")
        else:
            print(f"Failed to remove server '{server_name}'. Server not found.")
            
    async def test_server(self, server_name: str) -> None:
        """测试服务器连接"""
        server_config = self.config.get_server_config(server_name)
        
        if not server_config:
            print(f"Server '{server_name}' not found.")
            return
            
        print(f"Testing connection to server '{server_name}'...")
        
        # 创建临时 MCP 管理器进行测试
        test_config = MCPConfig()
        test_config.add_server_config(server_config)
        test_config.enable_server(server_name)
        
        manager = MCPManager(test_config)
        
        try:
            success = await manager.initialize()
            if success:
                tools = await manager.get_available_tools()
                print(f"✓ Connection successful! Available tools: {len(tools)}")
                if tools:
                    print(f"  Tools: {', '.join(tools[:5])}{'...' if len(tools) > 5 else ''}")
            else:
                print("✗ Connection failed during initialization.")
                
        except Exception as e:
            print(f"✗ Connection failed: {e}")
        finally:
            await manager.shutdown()
            
    async def test_all_servers(self) -> None:
        """测试所有启用的服务器"""
        enabled_servers = self.config.get_enabled_servers()
        
        if not enabled_servers:
            print("No enabled servers to test.")
            return
            
        print(f"Testing {len(enabled_servers)} enabled servers...")
        
        for server_name in enabled_servers:
            await self.test_server(server_name)
            print()  # 空行分隔
            
    def export_config(self, export_path: str) -> None:
        """导出配置"""
        if self.config.export_config(export_path):
            print(f"Configuration exported to '{export_path}' successfully.")
        else:
            print(f"Failed to export configuration to '{export_path}'.")
            
    def import_config(self, import_path: str) -> None:
        """导入配置"""
        if self.config.import_config(import_path):
            print(f"Configuration imported from '{import_path}' successfully.")
        else:
            print(f"Failed to import configuration from '{import_path}'.")
            
    def show_global_settings(self) -> None:
        """显示全局设置"""
        settings = self.config.config_data.get("global_settings", {})
        
        print("\n=== Global Settings ===")
        for key, value in settings.items():
            print(f"{key}: {value}")
            
    def set_global_setting(self, key: str, value: Any) -> None:
        """设置全局配置"""
        # 尝试转换值类型
        if value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        elif value.replace('.', '').isdigit():
            value = float(value)
            
        self.config.set_global_setting(key, value)
        print(f"Global setting '{key}' set to '{value}' successfully.")
        
    def setup_quick_config(self) -> None:
        """快速设置常用配置"""
        print("\n=== Quick Setup ===")
        print("This will enable commonly used MCP servers.")
        
        # 启用 Playwright
        self.config.enable_server("playwright")
        print("✓ Enabled Playwright server")
        
        # 询问是否启用文件系统服务器
        workspace = input("Enter workspace path for filesystem server (or press Enter to skip): ").strip()
        if workspace:
            self.config.enable_filesystem_server(workspace)
            print(f"✓ Enabled filesystem server with workspace: {workspace}")
            
        # 询问是否启用搜索服务器
        api_key = input("Enter Brave API key for search server (or press Enter to skip): ").strip()
        if api_key:
            self.config.enable_search_server(api_key)
            print("✓ Enabled Brave search server")
            
        # 启用内存服务器
        self.config.enable_server("memory")
        print("✓ Enabled memory server")
        
        print("\nQuick setup completed!")


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="MCP Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                              # List all servers
  %(prog)s show playwright                   # Show server details
  %(prog)s enable filesystem                 # Enable a server
  %(prog)s disable playwright               # Disable a server
  %(prog)s test playwright                   # Test server connection
  %(prog)s add myserver custom "python" "server.py"  # Add custom server
  %(prog)s export config_backup.json        # Export configuration
  %(prog)s quick-setup                       # Quick setup wizard
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    subparsers.add_parser("list", help="List all servers")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show server details")
    show_parser.add_argument("server", help="Server name")
    
    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a server")
    enable_parser.add_argument("server", help="Server name")
    
    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a server")
    disable_parser.add_argument("server", help="Server name")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test server connection")
    test_parser.add_argument("server", nargs="?", help="Server name (test all if not specified)")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new server")
    add_parser.add_argument("name", help="Server name")
    add_parser.add_argument("type", help="Server type", choices=[t.value for t in MCPServerType])
    add_parser.add_argument("command", help="Command to run")
    add_parser.add_argument("args", nargs="*", help="Command arguments")
    add_parser.add_argument("--env", help="Environment variables (JSON format)")
    add_parser.add_argument("--disabled", action="store_true", help="Add server as disabled")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a server")
    remove_parser.add_argument("server", help="Server name")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export configuration")
    export_parser.add_argument("path", help="Export file path")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import configuration")
    import_parser.add_argument("path", help="Import file path")
    
    # Global settings commands
    subparsers.add_parser("settings", help="Show global settings")
    
    set_parser = subparsers.add_parser("set", help="Set global setting")
    set_parser.add_argument("key", help="Setting key")
    set_parser.add_argument("value", help="Setting value")
    
    # Quick setup
    subparsers.add_parser("quick-setup", help="Quick setup wizard")
    
    return parser


async def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.WARNING,  # 只显示警告和错误
        format='%(levelname)s: %(message)s'
    )
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    manager = MCPConfigManager()
    
    try:
        if args.command == "list":
            manager.list_servers()
            
        elif args.command == "show":
            manager.show_server_details(args.server)
            
        elif args.command == "enable":
            manager.enable_server(args.server)
            
        elif args.command == "disable":
            manager.disable_server(args.server)
            
        elif args.command == "test":
            if args.server:
                await manager.test_server(args.server)
            else:
                await manager.test_all_servers()
                
        elif args.command == "add":
            env = json.loads(args.env) if args.env else None
            enabled = not args.disabled
            manager.add_server(args.name, args.type, args.command, args.args, env, enabled)
            
        elif args.command == "remove":
            manager.remove_server(args.server)
            
        elif args.command == "export":
            manager.export_config(args.path)
            
        elif args.command == "import":
            manager.import_config(args.path)
            
        elif args.command == "settings":
            manager.show_global_settings()
            
        elif args.command == "set":
            manager.set_global_setting(args.key, args.value)
            
        elif args.command == "quick-setup":
            manager.setup_quick_config()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())