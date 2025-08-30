#!/usr/bin/env python3
"""
Aura智能浏览器自动化系统 - 主启动脚本

这是Aura系统的主入口点，负责：
1. 初始化系统配置
2. 启动核心服务
3. 提供命令行接口
4. 处理系统生命周期

使用方法:
    python main.py                    # 启动完整系统
    python main.py --mode api         # 仅启动API服务
    python main.py --mode cli         # 启动命令行界面
    python main.py --config dev       # 使用开发环境配置
    python main.py --help             # 显示帮助信息
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.orchestrator import Orchestrator
from src.modules.command_parser import CommandParser
from src.modules.skill_library import SkillLibrary
from src.modules.site_explorer import SiteExplorer
from config.settings import AuraConfig, load_config
from src.utils.logger import setup_logging
from src.utils.exceptions import AuraSystemError


class AuraSystem:
    """Aura系统主类，负责系统的初始化、启动和管理"""
    
    def __init__(self, config: AuraConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # 核心组件
        self.orchestrator: Optional[Orchestrator] = None
        self.command_parser: Optional[CommandParser] = None
        self.skill_library: Optional[SkillLibrary] = None
        self.site_explorer: Optional[SiteExplorer] = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def initialize(self) -> None:
        """初始化系统组件"""
        try:
            self.logger.info("正在初始化Aura系统...")
            
            # 初始化技能库
            self.logger.info("初始化技能库...")
            self.skill_library = SkillLibrary(self.config.skill_library)
            await self.skill_library.load_existing_skills()
            
            # 初始化站点探索器
            self.logger.info("初始化站点探索器...")
            self.site_explorer = SiteExplorer(self.config.site_explorer)
            await self.site_explorer.initialize()
            
            # 初始化命令解析器
            self.logger.info("初始化命令解析器...")
            self.command_parser = CommandParser(
                skill_library=self.skill_library,
                llm_config=self.config.llm
            )
            
            # 初始化核心调度器
            self.logger.info("初始化核心调度器...")
            self.orchestrator = Orchestrator(
                skill_library=self.skill_library,
                site_explorer=self.site_explorer,
                command_parser=self.command_parser,
                config=self.config
            )
            
            self.logger.info("Aura系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            raise AuraSystemError(f"系统初始化失败: {e}")
    
    async def start_api_server(self) -> None:
        """启动API服务器"""
        try:
            import uvicorn
            from src.api.main import create_app
            
            self.logger.info("启动API服务器...")
            
            # 创建FastAPI应用
            app = create_app(self.orchestrator, self.config)
            
            # 启动服务器
            config = uvicorn.Config(
                app=app,
                host=self.config.api.host,
                port=self.config.api.port,
                log_level="info" if self.config.logging.level == "INFO" else "debug",
                reload=self.config.api.reload,
                workers=1 if self.config.api.reload else self.config.api.workers
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except ImportError:
            self.logger.error("缺少API服务器依赖，请安装: pip install uvicorn fastapi")
            raise
        except Exception as e:
            self.logger.error(f"API服务器启动失败: {e}")
            raise
    
    async def start_cli_interface(self) -> None:
        """启动命令行界面"""
        self.logger.info("启动命令行界面...")
        self.running = True
        
        print("\n" + "="*60)
        print("🤖 欢迎使用Aura智能浏览器自动化系统")
        print("="*60)
        print("输入自然语言指令，我将帮您自动化浏览器操作")
        print("输入 'help' 查看帮助，输入 'quit' 退出系统")
        print("="*60 + "\n")
        
        while self.running:
            try:
                # 获取用户输入
                user_input = input("🎯 请输入指令: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 感谢使用Aura系统，再见！")
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'status':
                    await self._show_status()
                    continue
                
                # 处理用户指令
                await self._process_command(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 感谢使用Aura系统，再见！")
                break
            except Exception as e:
                self.logger.error(f"处理命令时出错: {e}")
                print(f"❌ 处理命令时出错: {e}")
    
    async def _process_command(self, command: str) -> None:
        """处理用户命令"""
        try:
            print(f"🔄 正在处理指令: {command}")
            
            # 创建任务
            task_id = await self.orchestrator.create_task(
                goal=command,
                constraints={},
                budget_tokens=3000
            )
            
            print(f"📋 任务已创建，ID: {task_id}")
            
            # 等待任务完成
            while True:
                status = await self.orchestrator.get_task_status(task_id)
                
                if status.status.value == "completed":
                    print(f"✅ 任务完成: {status.result}")
                    break
                elif status.status.value == "failed":
                    print(f"❌ 任务失败: {status.error}")
                    break
                elif status.status.value == "cancelled":
                    print(f"⏹️ 任务已取消")
                    break
                else:
                    print(f"⏳ 任务状态: {status.status.value}")
                    await asyncio.sleep(2)
                    
        except Exception as e:
            self.logger.error(f"处理命令失败: {e}")
            print(f"❌ 处理命令失败: {e}")
    
    def _show_help(self) -> None:
        """显示帮助信息"""
        help_text = """
📖 Aura系统帮助信息

🎯 支持的指令类型:
  • 网页导航: "打开百度首页", "访问GitHub"
  • 搜索操作: "在淘宝搜索iPhone", "查找Python教程"
  • 表单填写: "填写登录表单", "提交注册信息"
  • 数据提取: "获取商品价格", "提取文章标题"
  • 复合操作: "登录网站并查看订单"

🔧 系统命令:
  • help    - 显示此帮助信息
  • status  - 显示系统状态
  • quit    - 退出系统

💡 使用技巧:
  • 使用自然语言描述您的需求
  • 尽量具体描述目标网站和操作
  • 系统会自动选择最佳执行策略
"""
        print(help_text)
    
    async def _show_status(self) -> None:
        """显示系统状态"""
        try:
            skill_count = len(self.skill_library.skills) if self.skill_library else 0
            model_count = len(self.site_explorer.site_models) if self.site_explorer else 0
            
            status_text = f"""
📊 Aura系统状态

🔧 核心组件:
  • 调度器: {'✅ 运行中' if self.orchestrator else '❌ 未启动'}
  • 命令解析器: {'✅ 运行中' if self.command_parser else '❌ 未启动'}
  • 技能库: {'✅ 运行中' if self.skill_library else '❌ 未启动'}
  • 站点探索器: {'✅ 运行中' if self.site_explorer else '❌ 未启动'}

📈 统计信息:
  • 已加载技能: {skill_count} 个
  • 站点模型: {model_count} 个
  • 配置环境: {self.config.environment.value}

⚙️ 配置信息:
  • LLM模型: {self.config.llm.model}
  • 浏览器模式: {'无头模式' if self.config.playwright.headless else '可视模式'}
  • 日志级别: {self.config.logging.level.value}
"""
            print(status_text)
            
        except Exception as e:
            print(f"❌ 获取系统状态失败: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}，正在关闭系统...")
        self.running = False
    
    async def shutdown(self) -> None:
        """关闭系统"""
        try:
            self.logger.info("正在关闭Aura系统...")
            
            if self.orchestrator:
                await self.orchestrator.shutdown()
            
            if self.site_explorer:
                await self.site_explorer.shutdown()
            
            self.logger.info("Aura系统已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭系统时出错: {e}")


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Aura智能浏览器自动化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动完整系统（CLI模式）
  python main.py --mode api         # 仅启动API服务
  python main.py --mode cli         # 启动命令行界面
  python main.py --config dev       # 使用开发环境配置
  python main.py --port 8080        # 指定API端口
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["api", "cli", "full"],
        default="cli",
        help="启动模式: api(仅API服务), cli(命令行界面), full(完整系统)"
    )
    
    parser.add_argument(
        "--config",
        choices=["dev", "prod", "test"],
        default="dev",
        help="配置环境: dev(开发), prod(生产), test(测试)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="API服务端口（覆盖配置文件设置）"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        help="API服务主机（覆盖配置文件设置）"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别（覆盖配置文件设置）"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="启用浏览器无头模式"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Aura v1.0.0"
    )
    
    return parser.parse_args()


async def main() -> None:
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 加载配置
        config = load_config(args.config)
        
        # 应用命令行参数覆盖
        if args.port:
            config.api.port = args.port
        if args.host:
            config.api.host = args.host
        if args.log_level:
            config.logging.level = args.log_level
        if args.headless:
            config.playwright.headless = True
        
        # 设置日志
        setup_logging(config.logging)
        logger = logging.getLogger(__name__)
        
        logger.info(f"启动Aura系统，模式: {args.mode}, 环境: {args.config}")
        
        # 创建系统实例
        system = AuraSystem(config)
        
        try:
            # 初始化系统
            await system.initialize()
            
            # 根据模式启动相应服务
            if args.mode == "api":
                await system.start_api_server()
            elif args.mode == "cli":
                await system.start_cli_interface()
            elif args.mode == "full":
                # 启动完整系统（API + CLI）
                # 这里可以实现并发启动多个服务
                await system.start_cli_interface()
            
        finally:
            # 确保系统正确关闭
            await system.shutdown()
    
    except KeyboardInterrupt:
        print("\n👋 用户中断，系统退出")
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        logging.error(f"系统启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())