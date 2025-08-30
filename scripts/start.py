#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura系统启动脚本
提供多种启动模式：API服务器、CLI交互、完整系统
"""

import os
import sys
import asyncio
import argparse
import signal
import logging
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from config.settings import get_config, Environment
from src.api.app import create_app
from src.cli.interface import AuraCLI
from main import AuraSystem

class AuraLauncher:
    """Aura系统启动器"""
    
    def __init__(self):
        self.config = None
        self.system = None
        self.running = False
        
    def setup_logging(self, log_level: str = "INFO"):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/aura.log', encoding='utf-8')
            ]
        )
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n收到信号 {signum}，正在关闭系统...")
            self.running = False
            if self.system:
                asyncio.create_task(self.system.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_api_server(self, host: str = "0.0.0.0", port: int = 8000, 
                              reload: bool = False):
        """启动API服务器"""
        try:
            import uvicorn
            
            print(f"🚀 启动Aura API服务器...")
            print(f"📍 地址: http://{host}:{port}")
            print(f"📚 API文档: http://{host}:{port}/docs")
            print(f"🔄 热重载: {'开启' if reload else '关闭'}")
            
            # 创建FastAPI应用
            app = await create_app()
            
            # 启动服务器
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                reload=reload,
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except ImportError:
            print("❌ 请安装uvicorn: pip install uvicorn")
            sys.exit(1)
        except Exception as e:
            print(f"❌ API服务器启动失败: {e}")
            sys.exit(1)
    
    async def start_cli(self):
        """启动CLI交互模式"""
        try:
            print("🖥️  启动Aura CLI交互模式...")
            
            cli = AuraCLI()
            if await cli.initialize():
                await cli.run_interactive()
            else:
                print("❌ CLI初始化失败")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ CLI启动失败: {e}")
            sys.exit(1)
    
    async def start_full_system(self, api_port: int = 8000):
        """启动完整系统（API + 后台服务）"""
        try:
            print("🌟 启动Aura完整系统...")
            
            # 初始化系统
            self.system = AuraSystem()
            await self.system.initialize()
            
            # 启动API服务器（后台）
            api_task = asyncio.create_task(
                self.start_api_server(port=api_port, reload=False)
            )
            
            # 启动后台服务
            services_task = asyncio.create_task(
                self.system.start_background_services()
            )
            
            print(f"✅ 系统启动完成")
            print(f"📍 API服务: http://localhost:{api_port}")
            print(f"📚 API文档: http://localhost:{api_port}/docs")
            print(f"🔧 管理界面: http://localhost:{api_port}/admin")
            print(f"📊 监控面板: http://localhost:{api_port}/metrics")
            print("\n按 Ctrl+C 停止系统")
            
            self.running = True
            
            # 等待任务完成或中断
            try:
                await asyncio.gather(api_task, services_task)
            except asyncio.CancelledError:
                print("\n正在关闭系统...")
            
        except Exception as e:
            print(f"❌ 系统启动失败: {e}")
            sys.exit(1)
        finally:
            if self.system:
                await self.system.shutdown()
    
    async def execute_command(self, command: str):
        """执行单个命令"""
        try:
            print(f"⚡ 执行命令: {command}")
            
            cli = AuraCLI()
            if await cli.initialize():
                await cli.process_command(command)
            else:
                print("❌ 系统初始化失败")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ 命令执行失败: {e}")
            sys.exit(1)
    
    def check_dependencies(self):
        """检查依赖"""
        required_packages = [
            'fastapi', 'uvicorn', 'playwright', 'openai', 
            'redis', 'sqlalchemy', 'rich', 'click'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
            print(f"请运行: pip install {' '.join(missing_packages)}")
            return False
        
        return True
    
    def check_environment(self):
        """检查环境"""
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ 需要Python 3.8或更高版本")
            return False
        
        # 检查必要目录
        required_dirs = ['logs', 'data', 'cache']
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                print(f"📁 创建目录: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # 检查配置文件
        config_file = project_root / 'config' / 'development.yaml'
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        return True
    
    async def run(self, args):
        """运行启动器"""
        # 设置配置环境
        os.environ['AURA_ENV'] = args.env
        
        # 加载配置
        self.config = get_config()
        
        # 设置日志
        self.setup_logging(args.log_level)
        
        # 设置信号处理
        self.setup_signal_handlers()
        
        # 检查环境和依赖
        if not self.check_environment():
            sys.exit(1)
        
        if not self.check_dependencies():
            sys.exit(1)
        
        # 根据模式启动
        if args.mode == 'api':
            await self.start_api_server(
                host=args.host,
                port=args.port,
                reload=args.reload
            )
        elif args.mode == 'cli':
            await self.start_cli()
        elif args.mode == 'full':
            await self.start_full_system(api_port=args.port)
        elif args.mode == 'execute':
            if not args.command:
                print("❌ 执行模式需要指定命令")
                sys.exit(1)
            await self.execute_command(args.command)
        else:
            print(f"❌ 未知模式: {args.mode}")
            sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Aura智能浏览器自动化系统启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/start.py api                    # 启动API服务器
  python scripts/start.py cli                    # 启动CLI交互模式
  python scripts/start.py full                   # 启动完整系统
  python scripts/start.py execute "搜索Python"   # 执行单个命令
  python scripts/start.py api --port 9000        # 指定端口启动API
  python scripts/start.py api --reload           # 开发模式（热重载）
        """
    )
    
    # 基本参数
    parser.add_argument(
        'mode',
        choices=['api', 'cli', 'full', 'execute'],
        help='启动模式'
    )
    
    parser.add_argument(
        '--env', '-e',
        choices=['development', 'production', 'test'],
        default='development',
        help='环境配置 (默认: development)'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )
    
    # API服务器参数
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='API服务器主机 (默认: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='API服务器端口 (默认: 8000)'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='开启热重载（仅开发环境）'
    )
    
    # 执行命令参数
    parser.add_argument(
        '--command', '-c',
        help='要执行的命令（execute模式）'
    )
    
    # 版本信息
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Aura v1.0.0'
    )
    
    args = parser.parse_args()
    
    # 创建启动器并运行
    launcher = AuraLauncher()
    
    try:
        asyncio.run(launcher.run(args))
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()