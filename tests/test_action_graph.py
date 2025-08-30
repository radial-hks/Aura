"""Action Graph 执行引擎测试"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.core.action_graph import ActionGraphEngine, ActionNode, NodeType
from src.utils.exceptions import ValidationError, TaskExecutionError, TimeoutError


class TestActionGraphEngine:
    """Action Graph 执行器测试类"""

    @pytest.mark.asyncio
    async def test_validate_graph_success(self, action_graph_executor, sample_action_graph):
        """测试图验证成功"""
        result = await action_graph_executor.validate_graph(sample_action_graph)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_graph_missing_nodes(self, action_graph_executor):
        """测试缺少节点的图验证"""
        invalid_graph = {
            'goal': 'test',
            'edges': [{'from': 'node1', 'to': 'node2'}],
            'budgetTokens': 1000
        }
        
        with pytest.raises(ValidationError, match="Missing required field: nodes"):
            await action_graph_executor.validate_graph(invalid_graph)

    @pytest.mark.asyncio
    async def test_validate_graph_invalid_edge(self, action_graph_executor):
        """测试无效边的图验证"""
        invalid_graph = {
            'goal': 'test',
            'nodes': [
                {'id': 'node1', 'type': 'navigate', 'url': 'https://example.com'}
            ],
            'edges': [
                {'from': 'node1', 'to': 'nonexistent_node'}
            ],
            'budgetTokens': 1000
        }
        
        with pytest.raises(ValidationError, match="Edge references non-existent node"):
            await action_graph_executor.validate_graph(invalid_graph)

    @pytest.mark.asyncio
    async def test_validate_graph_cyclic(self, action_graph_executor):
        """测试循环图的验证"""
        cyclic_graph = {
            'goal': 'test',
            'nodes': [
                {'id': 'node1', 'type': 'navigate', 'url': 'https://example.com'},
                {'id': 'node2', 'type': 'click', 'locator': 'button'}
            ],
            'edges': [
                {'from': 'node1', 'to': 'node2'},
                {'from': 'node2', 'to': 'node1'}
            ],
            'budgetTokens': 1000
        }
        
        with pytest.raises(ValidationError, match="Graph contains cycles"):
            await action_graph_executor.validate_graph(cyclic_graph)

    @pytest.mark.asyncio
    async def test_execute_navigate_action(self, action_graph_executor, mock_browser):
        """测试导航操作执行"""
        browser, page = mock_browser
        action_graph_executor._page = page
        
        action = ActionNode(
            id='nav1',
            type=ActionType.NAVIGATE,
            url='https://example.com'
        )
        
        result = await action_graph_executor._execute_action(action)
        
        assert result['success'] is True
        page.goto.assert_called_once_with('https://example.com')

    @pytest.mark.asyncio
    async def test_execute_click_action(self, action_graph_executor, mock_browser):
        """测试点击操作执行"""
        browser, page = mock_browser
        action_graph_executor._page = page
        
        action = ActionNode(
            id='click1',
            type=ActionType.CLICK,
            locator='button#submit'
        )
        
        result = await action_graph_executor._execute_action(action)
        
        assert result['success'] is True
        page.click.assert_called_once_with('button#submit')

    @pytest.mark.asyncio
    async def test_execute_type_action(self, action_graph_executor, mock_browser):
        """测试输入操作执行"""
        browser, page = mock_browser
        action_graph_executor._page = page
        
        action = ActionNode(
            id='type1',
            type=ActionType.TYPE,
            locator='input[name="q"]',
            text='test query'
        )
        
        result = await action_graph_executor._execute_action(action)
        
        assert result['success'] is True
        page.fill.assert_called_once_with('input[name="q"]', 'test query')

    @pytest.mark.asyncio
    async def test_execute_assert_action(self, action_graph_executor, mock_browser):
        """测试断言操作执行"""
        browser, page = mock_browser
        action_graph_executor._page = page
        
        action = ActionNode(
            id='assert1',
            type=ActionType.ASSERT,
            locator='#results'
        )
        
        result = await action_graph_executor._execute_action(action)
        
        assert result['success'] is True
        page.wait_for_selector.assert_called_once_with('#results', timeout=30000)

    @pytest.mark.asyncio
    async def test_execute_extract_action(self, action_graph_executor, mock_browser):
        """测试提取操作执行"""
        browser, page = mock_browser
        action_graph_executor._page = page
        
        # 模拟页面内容
        page.query_selector_all = AsyncMock(return_value=[
            Mock(text_content=AsyncMock(return_value='Result 1')),
            Mock(text_content=AsyncMock(return_value='Result 2'))
        ])
        
        action = ActionNode(
            id='extract1',
            type=ActionType.EXTRACT,
            locator='.result-item',
            attribute='text'
        )
        
        result = await action_graph_executor._execute_action(action)
        
        assert result['success'] is True
        assert 'data' in result
        assert len(result['data']) == 2

    @pytest.mark.asyncio
    async def test_execute_full_graph(self, action_graph_executor, sample_action_graph, mock_browser):
        """测试完整图执行"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        result = await action_graph_executor.execute(sample_action_graph)
        
        assert result['success'] is True
        assert 'execution_log' in result
        assert len(result['execution_log']) == len(sample_action_graph['nodes'])
        
        # 验证操作顺序
        page.goto.assert_called_once()
        page.fill.assert_called_once()
        page.click.assert_called_once()
        page.wait_for_selector.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_failure(self, action_graph_executor, sample_action_graph, mock_browser):
        """测试执行失败处理"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        # 模拟点击失败
        page.click.side_effect = Exception("Element not found")
        
        result = await action_graph_executor.execute(sample_action_graph)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'execution_log' in result

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, action_graph_executor, mock_browser):
        """测试执行超时"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        # 模拟超时
        page.wait_for_selector.side_effect = asyncio.TimeoutError("Timeout")
        
        timeout_graph = {
            'goal': 'timeout_test',
            'nodes': [
                {'id': 'wait', 'type': 'assert', 'locator': '#never-exists'}
            ],
            'edges': [],
            'budgetTokens': 1000
        }
        
        result = await action_graph_executor.execute(timeout_graph)
        
        assert result['success'] is False
        assert 'timeout' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, action_graph_executor, mock_browser):
        """测试重试机制"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        # 第一次失败，第二次成功
        page.click.side_effect = [Exception("Temporary failure"), None]
        
        retry_graph = {
            'goal': 'retry_test',
            'nodes': [
                {'id': 'click', 'type': 'click', 'locator': 'button', 'retry': True}
            ],
            'edges': [],
            'budgetTokens': 1000
        }
        
        result = await action_graph_executor.execute(retry_graph)
        
        assert result['success'] is True
        assert page.click.call_count == 2

    @pytest.mark.asyncio
    async def test_parallel_execution(self, action_graph_executor, mock_browser):
        """测试并行执行"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        parallel_graph = {
            'goal': 'parallel_test',
            'nodes': [
                {'id': 'nav', 'type': 'navigate', 'url': 'https://example.com'},
                {'id': 'click1', 'type': 'click', 'locator': 'button1'},
                {'id': 'click2', 'type': 'click', 'locator': 'button2'}
            ],
            'edges': [
                {'from': 'nav', 'to': 'click1'},
                {'from': 'nav', 'to': 'click2'}
            ],
            'budgetTokens': 1000
        }
        
        result = await action_graph_executor.execute(parallel_graph)
        
        assert result['success'] is True
        # 验证并行节点都被执行
        assert page.click.call_count == 2

    @pytest.mark.asyncio
    async def test_conditional_execution(self, action_graph_executor, mock_browser):
        """测试条件执行"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        # 模拟条件检查
        page.query_selector = AsyncMock(return_value=Mock())  # 元素存在
        
        conditional_graph = {
            'goal': 'conditional_test',
            'nodes': [
                {'id': 'nav', 'type': 'navigate', 'url': 'https://example.com'},
                {
                    'id': 'conditional_click',
                    'type': 'click',
                    'locator': 'button',
                    'condition': {'selector': '.login-required', 'exists': True}
                }
            ],
            'edges': [
                {'from': 'nav', 'to': 'conditional_click'}
            ],
            'budgetTokens': 1000
        }
        
        result = await action_graph_executor.execute(conditional_graph)
        
        assert result['success'] is True
        page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_screenshot_capture(self, action_graph_executor, mock_browser):
        """测试截图捕获"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        screenshot_graph = {
            'goal': 'screenshot_test',
            'nodes': [
                {'id': 'nav', 'type': 'navigate', 'url': 'https://example.com'},
                {'id': 'screenshot', 'type': 'screenshot'}
            ],
            'edges': [
                {'from': 'nav', 'to': 'screenshot'}
            ],
            'budgetTokens': 1000,
            'observability': {'captureScreenshot': 'always'}
        }
        
        result = await action_graph_executor.execute(screenshot_graph)
        
        assert result['success'] is True
        assert 'screenshots' in result
        page.screenshot.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_on_failure(self, action_graph_executor, mock_browser):
        """测试失败时的清理"""
        browser, page = mock_browser
        action_graph_executor._browser = browser
        action_graph_executor._page = page
        
        # 模拟执行失败
        page.click.side_effect = Exception("Critical failure")
        
        cleanup_graph = {
            'goal': 'cleanup_test',
            'nodes': [
                {'id': 'nav', 'type': 'navigate', 'url': 'https://example.com'},
                {'id': 'fail', 'type': 'click', 'locator': 'button'}
            ],
            'edges': [
                {'from': 'nav', 'to': 'fail'}
            ],
            'budgetTokens': 1000
        }
        
        result = await action_graph_executor.execute(cleanup_graph)
        
        assert result['success'] is False
        # 验证浏览器被正确清理
        browser.close.assert_called_once()

    def test_action_node_creation(self):
        """测试ActionNode创建"""
        node = ActionNode(
            id='test1',
            type=ActionType.CLICK,
            locator='button',
            text='Click me'
        )
        
        assert node.id == 'test1'
        assert node.type == ActionType.CLICK
        assert node.locator == 'button'
        assert node.text == 'Click me'

    def test_action_type_enum(self):
        """测试ActionType枚举"""
        assert ActionType.NAVIGATE.value == 'navigate'
        assert ActionType.CLICK.value == 'click'
        assert ActionType.TYPE.value == 'type'
        assert ActionType.ASSERT.value == 'assert'
        assert ActionType.EXTRACT.value == 'extract'
        assert ActionType.SCREENSHOT.value == 'screenshot'