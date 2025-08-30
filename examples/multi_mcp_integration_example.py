#!/usr/bin/env python3
"""多 MCP 服务器集成示例

展示如何使用 Aura 系统集成多个 MCP 服务器：
- Playwright: 浏览器自动化
- Filesystem: 文件系统操作
- Brave Search: 网络搜索
- Memory: 持久化存储
"""

import asyncio
import logging
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root / "src"))

from config.mcp_config import MCPConfig
from core.mcp_manager import MCPManager


class MultiMCPDemo:
    """多 MCP 服务器集成演示"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = MCPConfig()
        self.mcp_manager = MCPManager(self.config)
        
    async def setup_servers(self):
        """设置和配置 MCP 服务器"""
        self.logger.info("Setting up MCP servers...")
        
        # 启用 Playwright 服务器（浏览器自动化）
        self.config.enable_server("playwright")
        
        # 启用文件系统服务器
        workspace_path = str(project_root)
        self.config.enable_filesystem_server(workspace_path)
        
        # 启用内存服务器（持久化存储）
        self.config.enable_server("memory")
        
        # 注意：Brave Search 需要 API Key，这里暂时不启用
        # self.config.enable_search_server("your-brave-api-key")
        
        self.logger.info(f"Enabled servers: {self.config.get_enabled_servers()}")
        
    async def initialize_mcp_manager(self):
        """初始化 MCP 管理器"""
        self.logger.info("Initializing MCP Manager...")
        success = await self.mcp_manager.initialize()
        if not success:
            raise RuntimeError("Failed to initialize MCP Manager")
            
        # 显示服务器状态
        status = await self.mcp_manager.get_server_status()
        self.logger.info(f"Server status: {status}")
        
        # 显示可用工具
        tools = await self.mcp_manager.get_server_tools()
        self.logger.info(f"Available tools by server: {tools}")
        
    async def demo_file_operations(self):
        """演示文件系统操作"""
        self.logger.info("\n=== File Operations Demo ===")
        
        try:
            # 创建测试文件
            command = "Create a test file named 'mcp_test.txt' with content 'Hello from MCP!'"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"File creation result: {result}")
            
            # 读取文件内容
            command = "Read the content of 'mcp_test.txt' file"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"File read result: {result}")
            
        except Exception as e:
            self.logger.error(f"File operations error: {e}")
            
    async def demo_memory_operations(self):
        """演示内存存储操作"""
        self.logger.info("\n=== Memory Operations Demo ===")
        
        try:
            # 存储数据
            command = "Store the key 'user_preference' with value 'dark_mode' in memory"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"Memory store result: {result}")
            
            # 检索数据
            command = "Retrieve the value for key 'user_preference' from memory"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"Memory retrieve result: {result}")
            
        except Exception as e:
            self.logger.error(f"Memory operations error: {e}")
            
    async def demo_browser_operations(self):
        """演示浏览器操作"""
        self.logger.info("\n=== Browser Operations Demo ===")
        
        try:
            # 打开网页并截图
            command = "Navigate to https://example.com and take a screenshot"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"Browser navigation result: {result}")
            
            # 获取页面标题
            command = "Get the title of the current page"
            result = await self.mcp_manager.execute_command(command)
            self.logger.info(f"Page title result: {result}")
            
        except Exception as e:
            self.logger.error(f"Browser operations error: {e}")
            
    async def demo_integrated_workflow(self):
        """演示集成工作流"""
        self.logger.info("\n=== Integrated Workflow Demo ===")
        
        try:
            # 复合任务：浏览器 + 文件系统 + 内存
            workflow_command = """
            Perform the following integrated workflow:
            1. Navigate to https://httpbin.org/json
            2. Extract the JSON data from the page
            3. Save the JSON data to a file named 'api_response.json'
            4. Store a summary of the operation in memory with key 'last_operation'
            """
            
            result = await self.mcp_manager.execute_command(workflow_command)
            self.logger.info(f"Integrated workflow result: {result}")
            
        except Exception as e:
            self.logger.error(f"Integrated workflow error: {e}")
            
    async def demo_server_management(self):
        """演示服务器管理功能"""
        self.logger.info("\n=== Server Management Demo ===")
        
        try:
            # 获取服务器状态
            status = await self.mcp_manager.get_server_status()
            self.logger.info(f"Current server status: {status}")
            
            # 动态禁用和启用服务器
            self.logger.info("Disabling memory server...")
            await self.mcp_manager.disable_server("memory")
            
            # 检查状态变化
            status = await self.mcp_manager.get_server_status()
            self.logger.info(f"Status after disabling memory: {status}")
            
            # 重新启用
            self.logger.info("Re-enabling memory server...")
            await self.mcp_manager.enable_server("memory")
            
            status = await self.mcp_manager.get_server_status()
            self.logger.info(f"Status after re-enabling memory: {status}")
            
        except Exception as e:
            self.logger.error(f"Server management error: {e}")
            
    async def run_demo(self):
        """运行完整演示"""
        try:
            # 设置服务器
            await self.setup_servers()
            
            # 初始化 MCP 管理器
            await self.initialize_mcp_manager()
            
            # 运行各种演示
            await self.demo_file_operations()
            await self.demo_memory_operations()
            await self.demo_browser_operations()
            await self.demo_integrated_workflow()
            await self.demo_server_management()
            
            self.logger.info("\n=== Demo completed successfully! ===")
            
        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
            raise
        finally:
            # 清理
            await self.mcp_manager.shutdown()
            

async def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Multi-MCP Integration Demo")
    
    # 运行演示
    demo = MultiMCPDemo()
    await demo.run_demo()
    
    logger.info("Demo finished")


if __name__ == "__main__":
    asyncio.run(main())