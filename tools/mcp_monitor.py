#!/usr/bin/env python3
"""MCP Connection Monitor and Diagnostic Tool."""

import asyncio
import argparse
import json
import time
from datetime import datetime
from typing import Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.mcp_manager import MCPManager
from src.config.mcp_config import MCPConfig


class MCPMonitor:
    """MCP 连接监控器"""
    
    def __init__(self, config_path: str = None):
        self.config = MCPConfig(config_path) if config_path else MCPConfig()
        self.mcp_manager = MCPManager(self.config)
        self.monitoring = False
        
    async def initialize(self) -> bool:
        """初始化监控器"""
        try:
            success = await self.mcp_manager.initialize()
            if success:
                print("✅ MCP Manager initialized successfully")
            else:
                print("❌ Failed to initialize MCP Manager")
            return success
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
            
    async def show_status(self) -> None:
        """显示当前状态"""
        print("\n" + "="*60)
        print(f"MCP Connection Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 基本状态
        if not self.mcp_manager.is_initialized:
            print("❌ MCP Manager is not initialized")
            return
            
        # 连接状态
        connection_states = self.mcp_manager.get_connection_states()
        print("\n📡 Connection States:")
        for server, state in connection_states.items():
            status_icon = {
                'connected': '🟢',
                'connecting': '🟡',
                'reconnecting': '🟠',
                'failed': '🔴',
                'disconnected': '⚫',
                'circuit_open': '🚫'
            }.get(state, '❓')
            print(f"  {status_icon} {server}: {state}")
            
        # 健康指标
        health_metrics = self.mcp_manager.get_health_metrics()
        print("\n📊 Health Metrics:")
        print(f"  Total Servers: {health_metrics['total_servers']}")
        print(f"  Enabled: {health_metrics['enabled_servers']}")
        print(f"  Healthy: {health_metrics['healthy_servers']}")
        print(f"  Failed: {health_metrics['failed_servers']}")
        print(f"  Reconnecting: {health_metrics['reconnecting_servers']}")
        
        # 错误统计
        error_stats = self.mcp_manager.get_error_statistics()
        print("\n📈 Error Statistics:")
        print(f"  Overall Error Rate: {error_stats['overall_error_rate']:.2%}")
        print(f"  Healthy Connections: {error_stats['healthy_connections']}/{error_stats['total_connections']}")
        
        if error_stats['most_common_errors']:
            print("  Most Common Errors:")
            for error_type, count in sorted(error_stats['most_common_errors'].items(), 
                                          key=lambda x: x[1], reverse=True)[:3]:
                print(f"    - {error_type}: {count}")
                
        # 可用工具
        try:
            tools = await self.mcp_manager.get_available_tools()
            print(f"\n🔧 Available Tools: {len(tools)}")
            if tools:
                for tool in tools[:5]:  # 显示前5个工具
                    print(f"  - {tool}")
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more")
        except Exception as e:
            print(f"\n🔧 Tools: Error retrieving tools - {e}")
            
    async def diagnose(self) -> None:
        """运行诊断"""
        print("\n" + "="*60)
        print("🔍 Connection Diagnosis")
        print("="*60)
        
        try:
            diagnosis = await self.mcp_manager.diagnose_connection_issues()
            
            # 整体健康状况
            health_icon = {
                'healthy': '🟢',
                'degraded': '🟡',
                'recovering': '🟠',
                'unhealthy': '🔴'
            }.get(diagnosis['overall_health'], '❓')
            
            print(f"\n{health_icon} Overall Health: {diagnosis['overall_health'].upper()}")
            
            # 问题列表
            if diagnosis['issues']:
                print("\n⚠️  Issues Detected:")
                for i, issue in enumerate(diagnosis['issues'], 1):
                    print(f"  {i}. {issue}")
            else:
                print("\n✅ No issues detected")
                
            # 建议
            if diagnosis['recommendations']:
                print("\n💡 Recommendations:")
                for i, rec in enumerate(diagnosis['recommendations'], 1):
                    print(f"  {i}. {rec}")
                    
        except Exception as e:
            print(f"❌ Diagnosis failed: {e}")
            
    async def test_connections(self) -> None:
        """测试所有连接"""
        print("\n" + "="*60)
        print("🧪 Connection Tests")
        print("="*60)
        
        connection_states = self.mcp_manager.get_connection_states()
        
        for server_name in connection_states:
            print(f"\n🔍 Testing {server_name}...")
            
            try:
                # 测试基本连接
                start_time = time.time()
                tools = await self.mcp_manager.get_available_tools()
                response_time = (time.time() - start_time) * 1000
                
                print(f"  ✅ Connection OK ({response_time:.1f}ms)")
                print(f"  📊 Tools available: {len(tools)}")
                
                # 测试简单命令执行
                try:
                    start_time = time.time()
                    result = await self.mcp_manager.execute_command("list available tools")
                    exec_time = (time.time() - start_time) * 1000
                    print(f"  ✅ Command execution OK ({exec_time:.1f}ms)")
                except Exception as e:
                    print(f"  ⚠️  Command execution failed: {e}")
                    
            except Exception as e:
                print(f"  ❌ Connection test failed: {e}")
                
    async def monitor_continuous(self, interval: int = 30) -> None:
        """持续监控模式"""
        print(f"\n🔄 Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        self.monitoring = True
        
        try:
            while self.monitoring:
                await self.show_status()
                
                # 检查是否有严重问题
                health_metrics = self.mcp_manager.get_health_metrics()
                if health_metrics['failed_servers'] > 0:
                    print("\n⚠️  WARNING: Some servers are in failed state!")
                    
                error_stats = self.mcp_manager.get_error_statistics()
                if error_stats['overall_error_rate'] > 0.2:  # 20% 错误率
                    print("\n🚨 ALERT: High error rate detected!")
                    
                print(f"\n⏰ Next check in {interval} seconds...")
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            self.monitoring = False
            
    async def export_metrics(self, output_file: str) -> None:
        """导出指标到文件"""
        print(f"\n📤 Exporting metrics to {output_file}...")
        
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'connection_states': self.mcp_manager.get_connection_states(),
                'health_metrics': self.mcp_manager.get_health_metrics(),
                'error_statistics': self.mcp_manager.get_error_statistics(),
                'diagnosis': await self.mcp_manager.diagnose_connection_issues()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Metrics exported successfully")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            
    async def shutdown(self) -> None:
        """关闭监控器"""
        self.monitoring = False
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
            print("✅ MCP Manager shutdown complete")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MCP Connection Monitor')
    parser.add_argument('--config', '-c', help='MCP configuration file path')
    parser.add_argument('--monitor', '-m', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', '-i', type=int, default=30, help='Monitoring interval in seconds')
    parser.add_argument('--diagnose', '-d', action='store_true', help='Run connection diagnosis')
    parser.add_argument('--test', '-t', action='store_true', help='Test all connections')
    parser.add_argument('--export', '-e', help='Export metrics to JSON file')
    parser.add_argument('--status', '-s', action='store_true', help='Show current status (default)')
    
    args = parser.parse_args()
    
    # 如果没有指定任何操作，默认显示状态
    if not any([args.monitor, args.diagnose, args.test, args.export]):
        args.status = True
        
    monitor = MCPMonitor(args.config)
    
    try:
        # 初始化
        if not await monitor.initialize():
            print("❌ Failed to initialize monitor")
            return 1
            
        # 执行操作
        if args.status:
            await monitor.show_status()
            
        if args.diagnose:
            await monitor.diagnose()
            
        if args.test:
            await monitor.test_connections()
            
        if args.export:
            await monitor.export_metrics(args.export)
            
        if args.monitor:
            await monitor.monitor_continuous(args.interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        await monitor.shutdown()
        
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted")
        sys.exit(1)