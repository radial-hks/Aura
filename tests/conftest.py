"""Pytest 配置和共享夹具"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from src.core.orchestrator import Orchestrator
from src.core.action_graph import ActionGraphEngine
from src.modules.site_explorer import SiteExplorer
from src.modules.skill_library import SkillLibrary, SkillManifest, SkillInput, SkillOutput, SkillAssertion
from src.modules.command_parser import CommandParser


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """模拟配置对象"""
    return {
        'environment': 'test',
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'browser': {
            'headless': True,
            'timeout': 30000,
            'viewport': {'width': 1280, 'height': 720}
        },
        'ai': {
            'provider': 'mock',
            'model': 'test-model',
            'max_tokens': 1000
        },
        'security': {
            'allowed_domains': ['example.com', 'test.com'],
            'risk_threshold': 0.7
        },
        'storage': {
            'models_path': 'data/models',
            'skills_path': 'data/skills',
            'logs_path': 'logs'
        }
    }


@pytest.fixture
def mock_browser():
    """模拟浏览器对象"""
    browser = Mock()
    page = Mock()
    
    # 设置基本方法
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.screenshot = AsyncMock(return_value=b'fake_screenshot')
    page.content = AsyncMock(return_value='<html><body>Test</body></html>')
    
    browser.new_page = AsyncMock(return_value=page)
    browser.close = AsyncMock()
    
    return browser, page


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    client = Mock()
    client.chat = AsyncMock(return_value={
        'content': 'Mock response',
        'usage': {'tokens': 100}
    })
    return client


@pytest.fixture
def command_parser(mock_config, mock_llm_client):
    """创建命令解析器实例"""
    return CommandParser(mock_config, mock_llm_client)


@pytest.fixture
def skill_library(mock_config, temp_dir):
    """创建技能库实例"""
    skills_path = str(temp_dir / 'skills')
    return SkillLibrary(skills_path)


@pytest.fixture
def site_explorer(mock_config, mock_browser):
    """创建站点探索器实例"""
    browser, page = mock_browser
    explorer = SiteExplorer()
    explorer._browser = browser
    explorer._page = page
    return explorer


@pytest.fixture
def action_graph_executor(mock_browser):
    """创建Action Graph执行器实例"""
    browser, page = mock_browser
    executor = ActionGraphEngine()
    executor._browser = browser
    executor._page = page
    return executor


@pytest.fixture
def orchestrator():
    """创建编排器实例"""
    return Orchestrator()


@pytest.fixture
def sample_action_graph():
    """示例Action Graph"""
    return {
        'goal': 'search_product',
        'nodes': [
            {'id': 'navigate', 'type': 'navigate', 'url': 'https://example.com'},
            {'id': 'search', 'type': 'type', 'locator': 'input[name="q"]', 'text': 'test product'},
            {'id': 'submit', 'type': 'click', 'locator': 'button[type="submit"]'},
            {'id': 'verify', 'type': 'assert', 'locator': '#results'}
        ],
        'edges': [
            {'from': 'navigate', 'to': 'search'},
            {'from': 'search', 'to': 'submit'},
            {'from': 'submit', 'to': 'verify'}
        ],
        'budgetTokens': 1000
    }


@pytest.fixture
def sample_skill_manifest():
    """示例技能清单"""
    return SkillManifest(
        id='example.search',
        version='1.0.0',
        name='Example Search',
        description='Search products on example.com',
        author='test_author',
        target_domains=['example.com'],
        target_urls=[],
        inputs=[
            SkillInput(name='query', type='string', required=True, description='Search query')
        ],
        outputs=[
            SkillOutput(name='results', type='array', description='Search results')
        ],
        assertions=[
            SkillAssertion(name='HasResults', selector='#results', timeout_ms=10000)
        ]
    )


@pytest.fixture
def sample_site_model():
    """示例站点模型"""
    return {
        'metadata': {
            'domain': 'example.com',
            'version': '1.0.0',
            'lastExplored': '2024-01-01T00:00:00Z',
            'confidence': 0.9
        },
        'pages': {
            'homepage': {
                'url': '/',
                'title': 'Example Homepage',
                'description': 'Main landing page',
                'elements': {
                    'searchBox': {
                        'selectors': ['input[name="q"]', '#search'],
                        'type': 'text_input',
                        'purpose': 'Search functionality'
                    },
                    'searchButton': {
                        'selectors': ['button[type="submit"]', '.search-btn'],
                        'type': 'button',
                        'purpose': 'Submit search'
                    }
                }
            }
        },
        'navigationGraph': {
            'homepage': ['searchResults', 'categories']
        }
    }