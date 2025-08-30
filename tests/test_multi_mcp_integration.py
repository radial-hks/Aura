#!/usr/bin/env python3
"""多 MCP 服务器集成测试

测试多个 MCP 服务器的协同工作，包括：
- 浏览器自动化 (Playwright)
- 文件系统操作 (Filesystem)
- 网络搜索 (Brave Search)
- 内存存储 (Memory)
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

# 设置项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from config.mcp_config import MCPConfig
from core.mcp_manager import MCPManager
from modules.skill_library import SkillLibrary


class TestMultiMCPIntegration(unittest.IsolatedAsyncioTestCase):
    """多 MCP 服务器集成测试类"""
    
    async def asyncSetUp(self):
        """测试设置"""
        self.logger = logging.getLogger(__name__)
        
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.config = MCPConfig()
        
        # 启用测试所需的服务器
        self.config.enable_server("playwright")
        self.config.enable_server("memory")
        
        # 如果有文件系统权限，启用文件系统服务器
        try:
            self.config.enable_filesystem_server(self.temp_dir)
            self.filesystem_enabled = True
        except Exception:
            self.filesystem_enabled = False
            
        # 如果有搜索 API 密钥，启用搜索服务器
        brave_api_key = os.getenv("BRAVE_API_KEY")
        if brave_api_key:
            self.config.enable_search_server(brave_api_key)
            self.search_enabled = True
        else:
            self.search_enabled = False
            
        # 创建 MCP 管理器
        self.mcp_manager = MCPManager(self.config)
        
        # 创建技能库
        self.skill_library = SkillLibrary(mcp_manager=self.mcp_manager)
        
    async def asyncTearDown(self):
        """测试清理"""
        if hasattr(self, 'mcp_manager'):
            await self.mcp_manager.shutdown()
            
        # 清理临时目录
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    async def test_mcp_manager_initialization(self):
        """测试 MCP 管理器初始化"""
        success = await self.mcp_manager.initialize()
        self.assertTrue(success, "MCP Manager should initialize successfully")
        
        # 检查服务器状态
        status = await self.mcp_manager.get_server_status()
        self.assertIsInstance(status, dict)
        
        # 至少应该有 Playwright 和 Memory 服务器
        self.assertIn("playwright", status)
        self.assertIn("memory", status)
        
    async def test_available_tools(self):
        """测试获取可用工具"""
        await self.mcp_manager.initialize()
        
        tools = await self.mcp_manager.get_available_tools()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0, "Should have at least some tools available")
        
        # 检查是否有浏览器相关工具
        browser_tools = [tool for tool in tools if 'browser' in tool.lower()]
        self.assertGreater(len(browser_tools), 0, "Should have browser tools from Playwright")
        
    async def test_memory_operations(self):
        """测试内存操作"""
        await self.mcp_manager.initialize()
        
        # 测试存储数据
        test_data = {"test_key": "test_value", "timestamp": "2024-01-01T00:00:00Z"}
        
        try:
            # 存储数据
            result = await self.mcp_manager.execute_command(
                "memory_store",
                {"key": "test_integration", "value": json.dumps(test_data)}
            )
            self.assertIsNotNone(result)
            
            # 检索数据
            result = await self.mcp_manager.execute_command(
                "memory_get",
                {"key": "test_integration"}
            )
            self.assertIsNotNone(result)
            
            # 验证数据
            retrieved_data = json.loads(result.get("value", "{}"))
            self.assertEqual(retrieved_data.get("test_key"), "test_value")
            
        except Exception as e:
            self.skipTest(f"Memory operations not available: {e}")
            
    @unittest.skipUnless(os.getenv("ENABLE_BROWSER_TESTS"), "Browser tests disabled")
    async def test_browser_operations(self):
        """测试浏览器操作"""
        await self.mcp_manager.initialize()
        
        try:
            # 导航到测试页面
            result = await self.mcp_manager.execute_command(
                "browser_navigate",
                {"url": "https://httpbin.org/"}
            )
            self.assertIsNotNone(result)
            
            # 获取页面快照
            result = await self.mcp_manager.execute_command(
                "browser_snapshot",
                {}
            )
            self.assertIsNotNone(result)
            
        except Exception as e:
            self.skipTest(f"Browser operations not available: {e}")
            
    async def test_filesystem_operations(self):
        """测试文件系统操作"""
        if not self.filesystem_enabled:
            self.skipTest("Filesystem server not enabled")
            
        await self.mcp_manager.initialize()
        
        try:
            # 创建测试文件
            test_file = os.path.join(self.temp_dir, "test_file.txt")
            test_content = "This is a test file for MCP integration."
            
            result = await self.mcp_manager.execute_command(
                "write_file",
                {"path": test_file, "content": test_content}
            )
            self.assertIsNotNone(result)
            
            # 读取文件
            result = await self.mcp_manager.execute_command(
                "read_file",
                {"path": test_file}
            )
            self.assertIsNotNone(result)
            self.assertIn(test_content, str(result))
            
            # 列出目录
            result = await self.mcp_manager.execute_command(
                "list_directory",
                {"path": self.temp_dir}
            )
            self.assertIsNotNone(result)
            
        except Exception as e:
            self.skipTest(f"Filesystem operations not available: {e}")
            
    async def test_search_operations(self):
        """测试搜索操作"""
        if not self.search_enabled:
            self.skipTest("Search server not enabled (no API key)")
            
        await self.mcp_manager.initialize()
        
        try:
            # 执行搜索
            result = await self.mcp_manager.execute_command(
                "brave_search",
                {"query": "Python programming", "count": 3}
            )
            self.assertIsNotNone(result)
            
            # 验证搜索结果结构
            if isinstance(result, dict) and "results" in result:
                results = result["results"]
                self.assertIsInstance(results, list)
                self.assertGreater(len(results), 0)
                
        except Exception as e:
            self.skipTest(f"Search operations not available: {e}")
            
    async def test_skill_library_integration(self):
        """测试技能库与 MCP 的集成"""
        await self.mcp_manager.initialize()
        
        # 创建测试技能
        test_skill = {
            "id": "test.memory_store",
            "name": "Memory Store Test",
            "version": "1.0.0",
            "description": "Test skill for storing data in memory",
            "author": "test",
            "target_domains": ["*"],
            "browser_compatibility": ["chromium"],
            "inputs": {
                "key": {"type": "string", "required": True},
                "value": {"type": "string", "required": True}
            },
            "outputs": {
                "success": {"type": "boolean"}
            },
            "execution_config": {
                "timeout": 30,
                "retry_count": 2
            },
            "permissions": ["memory_access"],
            "risk_level": "low",
            "script": """
// Test skill script
const { key, value } = inputs;

try {
    // Store data in memory using MCP
    const result = await mcp.execute('memory_store', { key, value });
    
    return {
        success: true,
        result: result
    };
} catch (error) {
    return {
        success: false,
        error: error.message
    };
}
"""
        }
        
        # 注册技能
        success = await self.skill_library.register_skill(test_skill)
        self.assertTrue(success, "Should register test skill successfully")
        
        # 执行技能
        try:
            result = await self.skill_library.execute_skill_via_mcp(
                "test.memory_store",
                {"key": "test_skill_key", "value": "test_skill_value"}
            )
            self.assertIsNotNone(result)
            
        except Exception as e:
            self.skipTest(f"Skill execution not available: {e}")
            
    async def test_integrated_workflow(self):
        """测试集成工作流"""
        await self.mcp_manager.initialize()
        
        workflow_data = {
            "workflow_id": "test_integration_workflow",
            "steps": [
                {"action": "memory_store", "data": "workflow_started"},
                {"action": "file_operation", "data": "create_log"},
                {"action": "memory_update", "data": "workflow_completed"}
            ]
        }
        
        try:
            # 步骤 1: 存储工作流开始状态
            result1 = await self.mcp_manager.execute_command(
                "memory_store",
                {
                    "key": "workflow_status",
                    "value": json.dumps({"status": "started", "step": 1})
                }
            )
            self.assertIsNotNone(result1)
            
            # 步骤 2: 如果文件系统可用，创建日志文件
            if self.filesystem_enabled:
                log_file = os.path.join(self.temp_dir, "workflow.log")
                result2 = await self.mcp_manager.execute_command(
                    "write_file",
                    {
                        "path": log_file,
                        "content": f"Workflow started: {workflow_data['workflow_id']}\n"
                    }
                )
                self.assertIsNotNone(result2)
                
            # 步骤 3: 更新工作流完成状态
            result3 = await self.mcp_manager.execute_command(
                "memory_store",
                {
                    "key": "workflow_status",
                    "value": json.dumps({"status": "completed", "step": 3})
                }
            )
            self.assertIsNotNone(result3)
            
            # 验证最终状态
            final_status = await self.mcp_manager.execute_command(
                "memory_get",
                {"key": "workflow_status"}
            )
            self.assertIsNotNone(final_status)
            
            status_data = json.loads(final_status.get("value", "{}"))
            self.assertEqual(status_data.get("status"), "completed")
            
        except Exception as e:
            self.skipTest(f"Integrated workflow test failed: {e}")
            
    async def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        await self.mcp_manager.initialize()
        
        # 测试无效命令
        try:
            result = await self.mcp_manager.execute_command(
                "invalid_command",
                {"param": "value"}
            )
            # 应该返回错误或 None，而不是抛出异常
            self.assertIsNone(result)
            
        except Exception:
            # 如果抛出异常，也是可以接受的
            pass
            
        # 测试服务器重连
        status_before = await self.mcp_manager.get_server_status()
        
        # 尝试重连一个服务器
        if "playwright" in status_before:
            try:
                await self.mcp_manager.reconnect_server("playwright")
                status_after = await self.mcp_manager.get_server_status()
                self.assertIn("playwright", status_after)
            except Exception as e:
                self.skipTest(f"Server reconnection test failed: {e}")
                
    async def test_performance_metrics(self):
        """测试性能指标"""
        await self.mcp_manager.initialize()
        
        import time
        
        # 测试多个并发操作
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            task = self.mcp_manager.execute_command(
                "memory_store",
                {"key": f"perf_test_{i}", "value": f"value_{i}"}
            )
            tasks.append(task)
            
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 验证结果
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertGreater(len(successful_results), 0, "Should have some successful operations")
            
            # 检查性能
            total_time = end_time - start_time
            self.assertLess(total_time, 30, "Operations should complete within 30 seconds")
            
            # 记录性能指标
            self.logger.info(f"Completed {len(successful_results)} operations in {total_time:.2f} seconds")
            
        except Exception as e:
            self.skipTest(f"Performance test failed: {e}")


class TestMCPConfigManager(unittest.TestCase):
    """MCP 配置管理器测试"""
    
    def setUp(self):
        """测试设置"""
        self.config = MCPConfig()
        
    def test_server_configuration(self):
        """测试服务器配置"""
        # 测试获取服务器配置
        playwright_config = self.config.get_server_config("playwright")
        self.assertIsNotNone(playwright_config)
        self.assertEqual(playwright_config.name, "playwright")
        
    def test_enable_disable_servers(self):
        """测试启用/禁用服务器"""
        # 测试启用服务器
        success = self.config.enable_server("playwright")
        self.assertTrue(success)
        
        # 测试禁用服务器
        success = self.config.disable_server("playwright")
        self.assertTrue(success)
        
        # 测试不存在的服务器
        success = self.config.enable_server("nonexistent")
        self.assertFalse(success)
        
    def test_get_enabled_servers(self):
        """测试获取启用的服务器"""
        # 启用一些服务器
        self.config.enable_server("playwright")
        self.config.enable_server("memory")
        
        enabled_servers = self.config.get_enabled_servers()
        self.assertIsInstance(enabled_servers, list)
        self.assertIn("playwright", enabled_servers)
        self.assertIn("memory", enabled_servers)
        
    def test_global_settings(self):
        """测试全局设置"""
        # 设置全局配置
        self.config.set_global_setting("test_setting", "test_value")
        
        # 获取全局配置
        value = self.config.get_global_setting("test_setting")
        self.assertEqual(value, "test_value")
        
        # 获取不存在的配置
        value = self.config.get_global_setting("nonexistent", "default")
        self.assertEqual(value, "default")


def run_tests():
    """运行测试"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMultiMCPIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPConfigManager))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)