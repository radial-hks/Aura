# Aura CLI命令行界面
# 提供交互式命令行操作，支持自然语言指令输入和实时反馈

import asyncio
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import uuid
from pathlib import Path

# 第三方库
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
except ImportError:
    print("请安装rich库: pip install rich")
    sys.exit(1)

try:
    import click
except ImportError:
    print("请安装click库: pip install click")
    sys.exit(1)

# 项目模块
from ..core.orchestrator import Orchestrator, JobRequest, JobStatus
from ..modules.command_parser import CommandParser
from ..modules.skill_library import SkillLibrary
from ..modules.site_explorer import SiteExplorer
from config.settings import get_config

class AuraCLI:
    """Aura命令行界面"""
    
    def __init__(self):
        self.console = Console()
        self.config = get_config()
        self.orchestrator = None
        self.command_parser = None
        self.skill_library = None
        self.site_explorer = None
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self.current_job = None
        
    async def initialize(self):
        """初始化CLI组件"""
        try:
            with self.console.status("[bold green]初始化Aura系统..."):
                self.orchestrator = Orchestrator()
                self.command_parser = CommandParser()
                self.skill_library = SkillLibrary()
                self.site_explorer = SiteExplorer()
                
                # 初始化各组件
                await self.orchestrator.initialize()
                await self.command_parser.initialize()
                await self.skill_library.initialize()
                await self.site_explorer.initialize()
                
            self.console.print("[bold green]✓[/bold green] Aura系统初始化完成")
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]✗[/bold red] 初始化失败: {str(e)}")
            return False
    
    def show_welcome(self):
        """显示欢迎信息"""
        welcome_text = Text()
        welcome_text.append("🌟 欢迎使用 ", style="bold blue")
        welcome_text.append("Aura智能浏览器自动化系统", style="bold cyan")
        welcome_text.append(" 🌟", style="bold blue")
        
        panel = Panel(
            Align.center(welcome_text),
            title="Aura CLI",
            subtitle="通过自然语言操作浏览器",
            border_style="blue"
        )
        
        self.console.print(panel)
        self.console.print()
        
        # 显示帮助信息
        help_table = Table(show_header=False, box=None, padding=(0, 2))
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        
        help_table.add_row("help", "显示帮助信息")
        help_table.add_row("status", "显示系统状态")
        help_table.add_row("jobs", "列出任务")
        help_table.add_row("skills", "列出技能")
        help_table.add_row("history", "显示对话历史")
        help_table.add_row("clear", "清屏")
        help_table.add_row("exit/quit", "退出系统")
        
        self.console.print(Panel(
            help_table,
            title="可用命令",
            border_style="green"
        ))
        self.console.print()
    
    async def run_interactive(self):
        """运行交互式CLI"""
        self.show_welcome()
        
        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask(
                    "[bold cyan]Aura[/bold cyan]",
                    default=""
                ).strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['exit', 'quit', 'q']:
                    if Confirm.ask("确定要退出Aura吗?"):
                        break
                    continue
                
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                
                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                
                if user_input.lower() == 'status':
                    await self.show_status()
                    continue
                
                if user_input.lower() == 'jobs':
                    await self.show_jobs()
                    continue
                
                if user_input.lower() == 'skills':
                    await self.show_skills()
                    continue
                
                if user_input.lower() == 'history':
                    self.show_history()
                    continue
                
                # 处理自然语言指令
                await self.process_command(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]使用 'exit' 命令退出系统[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]错误: {str(e)}[/red]")
        
        self.console.print("[bold blue]感谢使用Aura! 👋[/bold blue]")
    
    async def process_command(self, command: str):
        """处理自然语言指令"""
        try:
            # 添加到对话历史
            self.conversation_history.append({
                "timestamp": datetime.now(),
                "type": "user",
                "content": command
            })
            
            # 解析指令
            with self.console.status("[bold yellow]解析指令中..."):
                parsed = await self.command_parser.parse_command(
                    command,
                    context={
                        "session_id": self.session_id,
                        "history": self.conversation_history[-5:]  # 最近5条历史
                    }
                )
            
            # 显示解析结果
            self.show_parsed_command(parsed)
            
            # 风险评估
            if parsed.risk_assessment.level.value in ['high', 'critical']:
                if not Confirm.ask(
                    f"[yellow]检测到{parsed.risk_assessment.level.value}风险操作，是否继续?[/yellow]"
                ):
                    self.console.print("[yellow]操作已取消[/yellow]")
                    return
            
            # 创建任务
            job_request = JobRequest(
                goal=command,
                constraints={},
                risk_level=parsed.risk_assessment.level.value,
                budget_tokens=parsed.estimated_tokens,
                site_scope=parsed.parameters.get('domain')
            )
            
            # 执行任务
            await self.execute_job(job_request)
            
        except Exception as e:
            self.console.print(f"[red]处理指令失败: {str(e)}[/red]")
            
            # 添加错误到历史
            self.conversation_history.append({
                "timestamp": datetime.now(),
                "type": "error",
                "content": str(e)
            })
    
    def show_parsed_command(self, parsed):
        """显示解析结果"""
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("意图", parsed.intent.value)
        table.add_row("置信度", f"{parsed.confidence:.2%}")
        table.add_row("执行模式", parsed.execution_strategy.mode.value)
        table.add_row("预估Token", str(parsed.estimated_tokens))
        table.add_row("风险等级", parsed.risk_assessment.level.value)
        
        if parsed.parameters:
            params_str = ", ".join([f"{k}={v}" for k, v in parsed.parameters.items()])
            table.add_row("参数", params_str)
        
        self.console.print(Panel(
            table,
            title="指令解析结果",
            border_style="blue"
        ))
    
    async def execute_job(self, job_request: JobRequest):
        """执行任务"""
        try:
            # 创建任务
            job = await self.orchestrator.create_job(job_request)
            self.current_job = job
            
            self.console.print(f"[green]任务已创建: {job.id}[/green]")
            
            # 创建进度显示
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                task = progress.add_task("执行中...", total=100)
                
                # 执行任务并监听进度
                async for update in self.orchestrator.execute_job(job.id):
                    progress.update(
                        task,
                        completed=update.get('progress', 0),
                        description=update.get('message', '执行中...')
                    )
                    
                    # 显示详细信息
                    if update.get('status') == 'completed':
                        progress.update(task, completed=100, description="完成")
                        break
                    elif update.get('status') == 'failed':
                        progress.update(task, description="失败")
                        break
            
            # 获取最终结果
            final_job = await self.orchestrator.get_job(job.id)
            self.show_job_result(final_job)
            
            # 添加结果到历史
            self.conversation_history.append({
                "timestamp": datetime.now(),
                "type": "result",
                "content": final_job.result or final_job.error
            })
            
        except Exception as e:
            self.console.print(f"[red]任务执行失败: {str(e)}[/red]")
    
    def show_job_result(self, job):
        """显示任务结果"""
        if job.status == JobStatus.COMPLETED:
            self.console.print(Panel(
                f"[green]✓ 任务完成[/green]\n\n{job.result or '无结果信息'}",
                title="执行结果",
                border_style="green"
            ))
        elif job.status == JobStatus.FAILED:
            self.console.print(Panel(
                f"[red]✗ 任务失败[/red]\n\n{job.error or '无错误信息'}",
                title="执行结果",
                border_style="red"
            ))
        else:
            self.console.print(Panel(
                f"[yellow]任务状态: {job.status.value}[/yellow]",
                title="执行结果",
                border_style="yellow"
            ))
    
    def show_help(self):
        """显示帮助信息"""
        help_content = """
[bold cyan]Aura智能浏览器自动化系统 - 帮助[/bold cyan]

[bold]基本用法:[/bold]
• 直接输入自然语言指令，如: "帮我在淘宝搜索MacBook Pro"
• 系统会自动解析指令并执行相应操作

[bold]系统命令:[/bold]
• help - 显示此帮助信息
• status - 显示系统状态
• jobs - 列出所有任务
• skills - 列出可用技能
• history - 显示对话历史
• clear - 清屏
• exit/quit - 退出系统

[bold]示例指令:[/bold]
• "在百度搜索Python教程"
• "登录我的GitHub账户"
• "在京东购买一台iPhone 15"
• "帮我填写这个表单"
• "截图保存当前页面"

[bold]注意事项:[/bold]
• 高风险操作会要求确认
• 所有操作都会记录日志
• 可以随时使用Ctrl+C中断操作
"""
        
        self.console.print(Panel(
            help_content,
            title="帮助信息",
            border_style="blue"
        ))
    
    async def show_status(self):
        """显示系统状态"""
        try:
            # 获取系统指标
            metrics = await self.orchestrator.get_metrics()
            
            status_table = Table(show_header=False, box=None)
            status_table.add_column("Metric", style="cyan")
            status_table.add_column("Value", style="white")
            
            status_table.add_row("系统状态", "[green]运行中[/green]")
            status_table.add_row("会话ID", self.session_id[:8] + "...")
            status_table.add_row("总任务数", str(metrics.get('total_jobs', 0)))
            status_table.add_row("成功率", f"{metrics.get('success_rate', 0):.1%}")
            status_table.add_row("平均执行时间", f"{metrics.get('avg_execution_time', 0):.1f}s")
            status_table.add_row("可用技能数", str(metrics.get('available_skills', 0)))
            status_table.add_row("站点模型数", str(metrics.get('site_models', 0)))
            
            self.console.print(Panel(
                status_table,
                title="系统状态",
                border_style="green"
            ))
            
        except Exception as e:
            self.console.print(f"[red]获取状态失败: {str(e)}[/red]")
    
    async def show_jobs(self):
        """显示任务列表"""
        try:
            jobs = await self.orchestrator.list_jobs(limit=10)
            
            if not jobs:
                self.console.print("[yellow]暂无任务[/yellow]")
                return
            
            jobs_table = Table()
            jobs_table.add_column("ID", style="cyan")
            jobs_table.add_column("状态", style="white")
            jobs_table.add_column("进度", style="white")
            jobs_table.add_column("创建时间", style="white")
            
            for job in jobs:
                status_color = {
                    'completed': 'green',
                    'failed': 'red',
                    'running': 'yellow',
                    'pending': 'blue'
                }.get(job.status.value, 'white')
                
                jobs_table.add_row(
                    job.id[:8] + "...",
                    f"[{status_color}]{job.status.value}[/{status_color}]",
                    f"{job.progress}%",
                    job.created_at.strftime("%H:%M:%S")
                )
            
            self.console.print(Panel(
                jobs_table,
                title="任务列表",
                border_style="blue"
            ))
            
        except Exception as e:
            self.console.print(f"[red]获取任务列表失败: {str(e)}[/red]")
    
    async def show_skills(self):
        """显示技能列表"""
        try:
            skills = await self.skill_library.find_skills(limit=10)
            
            if not skills:
                self.console.print("[yellow]暂无可用技能[/yellow]")
                return
            
            skills_table = Table()
            skills_table.add_column("名称", style="cyan")
            skills_table.add_column("版本", style="white")
            skills_table.add_column("域名", style="white")
            skills_table.add_column("评分", style="white")
            skills_table.add_column("使用次数", style="white")
            
            for skill in skills:
                skills_table.add_row(
                    skill.name,
                    skill.version,
                    ", ".join(skill.target_domains[:2]),
                    f"{skill.rating:.1f}⭐",
                    str(skill.usage_count)
                )
            
            self.console.print(Panel(
                skills_table,
                title="可用技能",
                border_style="green"
            ))
            
        except Exception as e:
            self.console.print(f"[red]获取技能列表失败: {str(e)}[/red]")
    
    def show_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            self.console.print("[yellow]暂无对话历史[/yellow]")
            return
        
        for entry in self.conversation_history[-10:]:  # 显示最近10条
            timestamp = entry['timestamp'].strftime("%H:%M:%S")
            entry_type = entry['type']
            content = entry['content']
            
            type_colors = {
                'user': 'cyan',
                'result': 'green',
                'error': 'red'
            }
            
            color = type_colors.get(entry_type, 'white')
            self.console.print(f"[{color}][{timestamp}] {entry_type.upper()}:[/{color}] {content}")

# ==================== Click命令行接口 ====================

@click.group()
def cli():
    """Aura智能浏览器自动化系统CLI"""
    pass

@cli.command()
@click.option('--config', '-c', default='development', help='配置环境')
def interactive(config):
    """启动交互式CLI"""
    async def run():
        cli_app = AuraCLI()
        if await cli_app.initialize():
            await cli_app.run_interactive()
    
    asyncio.run(run())

@cli.command()
@click.argument('command')
@click.option('--config', '-c', default='development', help='配置环境')
def execute(command, config):
    """执行单个命令"""
    async def run():
        cli_app = AuraCLI()
        if await cli_app.initialize():
            await cli_app.process_command(command)
    
    asyncio.run(run())

@cli.command()
def version():
    """显示版本信息"""
    click.echo("Aura智能浏览器自动化系统 v1.0.0")

if __name__ == "__main__":
    cli()