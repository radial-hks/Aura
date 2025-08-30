#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura开发环境启动脚本
提供开发调试功能：热重载、测试运行、代码检查等
"""

import os
import sys
import asyncio
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import threading
import signal

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class AuraDeveloper:
    """Aura开发环境管理器"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n收到信号 {signum}，正在关闭开发环境...")
            self.running = False
            self.cleanup()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def cleanup(self):
        """清理进程"""
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None, 
                   background: bool = False) -> subprocess.Popen:
        """运行命令"""
        print(f"🔧 执行: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            cwd=cwd or project_root,
            stdout=subprocess.PIPE if background else None,
            stderr=subprocess.PIPE if background else None,
            text=True
        )
        
        if background:
            self.processes.append(process)
        
        return process
    
    def install_dependencies(self):
        """安装开发依赖"""
        print("📦 安装开发依赖...")
        
        # 安装基础依赖
        self.run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        # 安装开发依赖
        dev_packages = [
            "pytest", "pytest-asyncio", "pytest-cov",
            "black", "isort", "flake8", "mypy",
            "pre-commit", "watchdog"
        ]
        
        self.run_command([sys.executable, "-m", "pip", "install"] + dev_packages)
        
        # 安装Playwright浏览器
        print("🌐 安装Playwright浏览器...")
        self.run_command([sys.executable, "-m", "playwright", "install"])
        
        print("✅ 依赖安装完成")
    
    def setup_pre_commit(self):
        """设置pre-commit钩子"""
        print("🔗 设置pre-commit钩子...")
        
        # 创建.pre-commit-config.yaml
        pre_commit_config = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"""
        
        config_file = project_root / ".pre-commit-config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(pre_commit_config)
        
        # 安装钩子
        self.run_command(["pre-commit", "install"])
        
        print("✅ pre-commit钩子设置完成")
    
    def format_code(self):
        """格式化代码"""
        print("🎨 格式化代码...")
        
        # Black格式化
        self.run_command(["black", "src/", "scripts/", "tests/", "main.py"])
        
        # isort排序导入
        self.run_command(["isort", "src/", "scripts/", "tests/", "main.py", "--profile", "black"])
        
        print("✅ 代码格式化完成")
    
    def lint_code(self):
        """代码检查"""
        print("🔍 代码检查...")
        
        # Flake8检查
        try:
            self.run_command([
                "flake8", "src/", "scripts/", "tests/", "main.py",
                "--max-line-length=88", "--extend-ignore=E203,W503"
            ])
            print("✅ Flake8检查通过")
        except subprocess.CalledProcessError:
            print("❌ Flake8检查发现问题")
        
        # MyPy类型检查
        try:
            self.run_command(["mypy", "src/", "--ignore-missing-imports"])
            print("✅ MyPy类型检查通过")
        except subprocess.CalledProcessError:
            print("❌ MyPy类型检查发现问题")
    
    def run_tests(self, coverage: bool = True, verbose: bool = False):
        """运行测试"""
        print("🧪 运行测试...")
        
        cmd = ["pytest"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["tests/"])
        
        try:
            self.run_command(cmd)
            print("✅ 测试通过")
            
            if coverage:
                print("📊 覆盖率报告已生成: htmlcov/index.html")
        except subprocess.CalledProcessError:
            print("❌ 测试失败")
    
    def start_dev_server(self, port: int = 8000, reload: bool = True):
        """启动开发服务器"""
        print(f"🚀 启动开发服务器 (端口: {port})...")
        
        cmd = [
            sys.executable, "scripts/start.py", "api",
            "--env", "development",
            "--port", str(port),
            "--host", "127.0.0.1"
        ]
        
        if reload:
            cmd.append("--reload")
        
        process = self.run_command(cmd, background=True)
        
        # 等待服务器启动
        time.sleep(3)
        
        print(f"✅ 开发服务器已启动")
        print(f"📍 API地址: http://127.0.0.1:{port}")
        print(f"📚 API文档: http://127.0.0.1:{port}/docs")
        
        return process
    
    def watch_files(self):
        """监控文件变化"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("❌ 请安装watchdog: pip install watchdog")
            return
        
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, developer):
                self.developer = developer
                self.last_modified = 0
            
            def on_modified(self, event):
                if event.is_directory:
                    return
                
                # 避免重复触发
                current_time = time.time()
                if current_time - self.last_modified < 1:
                    return
                self.last_modified = current_time
                
                # 只处理Python文件
                if event.src_path.endswith('.py'):
                    print(f"📝 文件变化: {event.src_path}")
                    print("🔄 重新格式化代码...")
                    self.developer.format_code()
        
        observer = Observer()
        handler = ChangeHandler(self)
        
        # 监控源代码目录
        observer.schedule(handler, str(project_root / "src"), recursive=True)
        observer.schedule(handler, str(project_root / "scripts"), recursive=True)
        observer.schedule(handler, str(project_root / "tests"), recursive=True)
        
        observer.start()
        print("👀 开始监控文件变化...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            observer.stop()
            observer.join()
    
    def create_test_files(self):
        """创建测试文件模板"""
        print("📝 创建测试文件模板...")
        
        test_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "tests/fixtures"
        ]
        
        for test_dir in test_dirs:
            (project_root / test_dir).mkdir(parents=True, exist_ok=True)
            
            # 创建__init__.py
            init_file = project_root / test_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
        
        # 创建conftest.py
        conftest_content = """
import pytest
import asyncio
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def event_loop():
    # Create event loop
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def aura_config():
    # 试配置
    from config.settings import get_config
    return get_config('test')

@pytest.fixture
async def mock_browser():
    # 模拟浏览器
    # TODO: 实现模拟浏览器
    pass
"""
        
        conftest_file = project_root / "tests" / "conftest.py"
        if not conftest_file.exists():
            conftest_file.write_text(conftest_content)
        
        # 创建示例测试文件
        example_test = """
import pytest
from src.core.orchestrator import Orchestrator

class TestOrchestrator:
    # Orchestrator测试
    
    @pytest.mark.asyncio
    async def test_create_job(self, aura_config):
        #测试创建任务
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        
        # TODO: 实现测试逻辑
        assert True
    
    @pytest.mark.asyncio
    async def test_execute_job(self, aura_config):
        # 测试执行任务
        # TODO: 实现测试逻辑
        assert True
"""
        
        test_file = project_root / "tests" / "unit" / "test_orchestrator.py"
        if not test_file.exists():
            test_file.write_text(example_test)
        
        print("✅ 测试文件模板创建完成")
    
    def generate_docs(self):
        """生成文档"""
        print("📚 生成文档...")
        
        try:
            # 安装sphinx
            self.run_command([sys.executable, "-m", "pip", "install", "sphinx", "sphinx-rtd-theme"])
            
            # 创建docs目录
            docs_dir = project_root / "docs"
            docs_dir.mkdir(exist_ok=True)
            
            # 初始化sphinx
            if not (docs_dir / "conf.py").exists():
                self.run_command(["sphinx-quickstart", "docs", "--quiet", "--project=Aura", "--author=Aura Team"])
            
            # 生成API文档
            self.run_command(["sphinx-apidoc", "-o", "docs/source", "src/"])
            
            # 构建HTML文档
            self.run_command(["sphinx-build", "-b", "html", "docs/source", "docs/build/html"])
            
            print("✅ 文档生成完成: docs/build/html/index.html")
            
        except Exception as e:
            print(f"❌ 文档生成失败: {e}")
    
    def run_dev_mode(self, port: int = 8000):
        """运行开发模式"""
        print("🔥 启动开发模式...")
        
        # 启动开发服务器
        server_process = self.start_dev_server(port=port)
        
        # 在后台监控文件变化
        watch_thread = threading.Thread(target=self.watch_files)
        watch_thread.daemon = True
        watch_thread.start()
        
        print("\n开发模式已启动:")
        print(f"  🌐 API服务器: http://127.0.0.1:{port}")
        print(f"  📚 API文档: http://127.0.0.1:{port}/docs")
        print("  👀 文件监控: 已启用")
        print("  🎨 自动格式化: 已启用")
        print("\n按 Ctrl+C 停止开发模式")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止开发模式...")
        finally:
            self.cleanup()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Aura开发环境管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/dev.py setup          # 设置开发环境
  python scripts/dev.py dev            # 启动开发模式
  python scripts/dev.py test           # 运行测试
  python scripts/dev.py format         # 格式化代码
  python scripts/dev.py lint           # 代码检查
  python scripts/dev.py docs           # 生成文档
        """
    )
    
    parser.add_argument(
        'command',
        choices=['setup', 'dev', 'test', 'format', 'lint', 'docs', 'watch'],
        help='开发命令'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='开发服务器端口 (默认: 8000)'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='运行测试时生成覆盖率报告'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    developer = AuraDeveloper()
    developer.setup_signal_handlers()
    
    try:
        if args.command == 'setup':
            developer.install_dependencies()
            developer.setup_pre_commit()
            developer.create_test_files()
            print("✅ 开发环境设置完成")
        
        elif args.command == 'dev':
            developer.run_dev_mode(port=args.port)
        
        elif args.command == 'test':
            developer.run_tests(coverage=args.coverage, verbose=args.verbose)
        
        elif args.command == 'format':
            developer.format_code()
        
        elif args.command == 'lint':
            developer.lint_code()
        
        elif args.command == 'docs':
            developer.generate_docs()
        
        elif args.command == 'watch':
            developer.watch_files()
        
    except KeyboardInterrupt:
        print("\n👋 开发会话结束")
    except Exception as e:
        print(f"❌ 开发命令失败: {e}")
        sys.exit(1)
    finally:
        developer.cleanup()

if __name__ == "__main__":
    main()