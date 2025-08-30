"""命令解析器测试"""
import pytest
from unittest.mock import Mock, AsyncMock

from src.modules.command_parser import CommandParser, IntentType, Priority
from src.utils.exceptions import ValidationError, CommandParsingError


class TestCommandParser:
    """命令解析器测试类"""

    @pytest.mark.asyncio
    async def test_parse_simple_search_command(self, command_parser):
        """测试解析简单搜索命令"""
        # 模拟LLM响应
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "search_product",
                "parameters": {
                    "query": "laptop",
                    "site": "amazon.com"
                },
                "confidence": 0.95,
                "risk_level": "low",
                "reasoning": "Simple product search with clear intent"
            }''',
            'usage': {'tokens': 150}
        })
        
        result = await command_parser.parse_command("search for laptop on amazon")
        
        assert result['intent'] == 'search_product'
        assert result['parameters']['query'] == 'laptop'
        assert result['parameters']['site'] == 'amazon.com'
        assert result['confidence'] == 0.95
        assert result['risk_level'] == 'low'

    @pytest.mark.asyncio
    async def test_parse_navigation_command(self, command_parser):
        """测试解析导航命令"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "navigate",
                "parameters": {
                    "url": "https://github.com",
                    "target": "homepage"
                },
                "confidence": 0.9,
                "risk_level": "low",
                "reasoning": "Direct navigation to a known safe site"
            }''',
            'usage': {'tokens': 120}
        })
        
        result = await command_parser.parse_command("go to github homepage")
        
        assert result['intent'] == 'navigate'
        assert result['parameters']['url'] == 'https://github.com'
        assert result['risk_level'] == 'low'

    @pytest.mark.asyncio
    async def test_parse_form_filling_command(self, command_parser):
        """测试解析表单填写命令"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "fill_form",
                "parameters": {
                    "form_type": "contact",
                    "fields": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "message": "Hello world"
                    }
                },
                "confidence": 0.85,
                "risk_level": "medium",
                "reasoning": "Form filling with personal information"
            }''',
            'usage': {'tokens': 200}
        })
        
        result = await command_parser.parse_command(
            "fill the contact form with name John Doe, email john@example.com, message Hello world"
        )
        
        assert result['intent'] == 'fill_form'
        assert result['parameters']['fields']['name'] == 'John Doe'
        assert result['parameters']['fields']['email'] == 'john@example.com'
        assert result['risk_level'] == 'medium'

    @pytest.mark.asyncio
    async def test_parse_high_risk_command(self, command_parser):
        """测试解析高风险命令"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "delete_account",
                "parameters": {
                    "confirmation": "yes",
                    "account_type": "user"
                },
                "confidence": 0.8,
                "risk_level": "high",
                "reasoning": "Account deletion is irreversible and high risk"
            }''',
            'usage': {'tokens': 180}
        })
        
        result = await command_parser.parse_command("delete my account")
        
        assert result['intent'] == 'delete_account'
        assert result['risk_level'] == 'high'
        assert result['confidence'] == 0.8

    @pytest.mark.asyncio
    async def test_parse_ambiguous_command(self, command_parser):
        """测试解析模糊命令"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "search",
                "parameters": {
                    "query": "apple"
                },
                "confidence": 0.4,
                "risk_level": "low",
                "reasoning": "Ambiguous query - could be fruit, company, or product",
                "clarification_needed": true,
                "suggested_clarifications": [
                    "Are you looking for Apple products?",
                    "Do you want to search for apple fruit?",
                    "Are you looking for Apple Inc. information?"
                ]
            }''',
            'usage': {'tokens': 250}
        })
        
        result = await command_parser.parse_command("find apple")
        
        assert result['intent'] == 'search'
        assert result['confidence'] < 0.5
        assert 'clarification_needed' in result
        assert len(result['suggested_clarifications']) > 0

    @pytest.mark.asyncio
    async def test_parse_multi_step_command(self, command_parser):
        """测试解析多步骤命令"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "multi_step_task",
                "parameters": {
                    "steps": [
                        {
                            "action": "navigate",
                            "target": "shopping_site"
                        },
                        {
                            "action": "search",
                            "query": "wireless headphones"
                        },
                        {
                            "action": "filter",
                            "criteria": {"price_max": 100, "brand": "Sony"}
                        },
                        {
                            "action": "add_to_cart",
                            "item_index": 0
                        }
                    ]
                },
                "confidence": 0.88,
                "risk_level": "medium",
                "reasoning": "Multi-step shopping task with purchase intent"
            }''',
            'usage': {'tokens': 300}
        })
        
        result = await command_parser.parse_command(
            "go to shopping site, search for wireless headphones under $100 from Sony, and add the first one to cart"
        )
        
        assert result['intent'] == 'multi_step_task'
        assert len(result['parameters']['steps']) == 4
        assert result['parameters']['steps'][0]['action'] == 'navigate'
        assert result['parameters']['steps'][1]['query'] == 'wireless headphones'
        assert result['risk_level'] == 'medium'

    @pytest.mark.asyncio
    async def test_parse_with_context(self, command_parser):
        """测试带上下文的命令解析"""
        # 设置上下文
        context = {
            'current_page': 'https://example.com/products',
            'previous_actions': ['searched for laptops'],
            'user_preferences': {'brand': 'Dell', 'budget': 1000}
        }
        
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "refine_search",
                "parameters": {
                    "query": "Dell laptops under $1000",
                    "filters": {
                        "brand": "Dell",
                        "max_price": 1000
                    }
                },
                "confidence": 0.92,
                "risk_level": "low",
                "reasoning": "Refining previous search with user preferences"
            }''',
            'usage': {'tokens': 180}
        })
        
        result = await command_parser.parse_command(
            "show me options within my budget",
            context=context
        )
        
        assert result['intent'] == 'refine_search'
        assert result['parameters']['filters']['brand'] == 'Dell'
        assert result['parameters']['filters']['max_price'] == 1000

    @pytest.mark.asyncio
    async def test_parse_invalid_json_response(self, command_parser):
        """测试无效JSON响应处理"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': 'Invalid JSON response',
            'usage': {'tokens': 50}
        })
        
        with pytest.raises(ParseError, match="Failed to parse LLM response"):
            await command_parser.parse_command("search for something")

    @pytest.mark.asyncio
    async def test_parse_missing_required_fields(self, command_parser):
        """测试缺少必需字段的响应"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "parameters": {"query": "test"},
                "confidence": 0.8
            }''',
            'usage': {'tokens': 80}
        })
        
        with pytest.raises(ValidationError, match="Missing required field: intent"):
            await command_parser.parse_command("search for test")

    @pytest.mark.asyncio
    async def test_parse_empty_command(self, command_parser):
        """测试空命令处理"""
        with pytest.raises(ValidationError, match="Command cannot be empty"):
            await command_parser.parse_command("")
        
        with pytest.raises(ValidationError, match="Command cannot be empty"):
            await command_parser.parse_command("   ")

    @pytest.mark.asyncio
    async def test_parse_very_long_command(self, command_parser):
        """测试超长命令处理"""
        long_command = "search for " + "very long query " * 1000
        
        with pytest.raises(ValidationError, match="Command too long"):
            await command_parser.parse_command(long_command)

    @pytest.mark.asyncio
    async def test_get_intent_suggestions(self, command_parser):
        """测试获取意图建议"""
        suggestions = await command_parser.get_intent_suggestions("shop")
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # 验证建议格式
        for suggestion in suggestions:
            assert 'intent' in suggestion
            assert 'description' in suggestion
            assert 'example' in suggestion

    @pytest.mark.asyncio
    async def test_validate_parameters_success(self, command_parser):
        """测试参数验证成功"""
        intent = 'search_product'
        parameters = {
            'query': 'laptop',
            'site': 'amazon.com',
            'filters': {'price_max': 1000}
        }
        
        result = await command_parser.validate_parameters(intent, parameters)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_parameters_missing_required(self, command_parser):
        """测试缺少必需参数"""
        intent = 'search_product'
        parameters = {
            'site': 'amazon.com'  # 缺少query
        }
        
        with pytest.raises(ValidationError, match="Missing required parameter: query"):
            await command_parser.validate_parameters(intent, parameters)

    @pytest.mark.asyncio
    async def test_validate_parameters_invalid_type(self, command_parser):
        """测试无效参数类型"""
        intent = 'search_product'
        parameters = {
            'query': 123,  # 应该是字符串
            'site': 'amazon.com'
        }
        
        with pytest.raises(ValidationError, match="Invalid parameter type"):
            await command_parser.validate_parameters(intent, parameters)

    @pytest.mark.asyncio
    async def test_extract_entities(self, command_parser):
        """测试实体提取"""
        command = "search for iPhone 13 Pro Max on Apple Store with price under $1000"
        
        entities = await command_parser.extract_entities(command)
        
        assert isinstance(entities, dict)
        assert 'products' in entities or 'items' in entities
        assert 'sites' in entities or 'domains' in entities
        assert 'prices' in entities or 'numbers' in entities

    @pytest.mark.asyncio
    async def test_calculate_risk_score(self, command_parser):
        """测试风险评分计算"""
        # 低风险命令
        low_risk_intent = 'search_product'
        low_risk_params = {'query': 'laptop'}
        low_score = await command_parser.calculate_risk_score(low_risk_intent, low_risk_params)
        assert low_score < 0.3
        
        # 高风险命令
        high_risk_intent = 'delete_account'
        high_risk_params = {'confirmation': 'yes'}
        high_score = await command_parser.calculate_risk_score(high_risk_intent, high_risk_params)
        assert high_score > 0.7

    @pytest.mark.asyncio
    async def test_get_command_history(self, command_parser):
        """测试获取命令历史"""
        # 解析几个命令
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "search_product",
                "parameters": {"query": "test"},
                "confidence": 0.9,
                "risk_level": "low"
            }''',
            'usage': {'tokens': 100}
        })
        
        await command_parser.parse_command("search for test1")
        await command_parser.parse_command("search for test2")
        await command_parser.parse_command("search for test3")
        
        history = await command_parser.get_command_history(limit=2)
        
        assert len(history) == 2
        assert all('command' in item for item in history)
        assert all('result' in item for item in history)
        assert all('timestamp' in item for item in history)

    def test_intent_enum(self):
        """测试IntentType枚举"""
        assert IntentType.SEARCH.value == 'search'
        assert IntentType.NAVIGATE.value == 'navigate'
        assert IntentType.CLICK.value == 'click'
        assert IntentType.FILL_FORM.value == 'fill_form'
        assert IntentType.EXTRACT_DATA.value == 'extract_data'

    def test_priority_enum(self):
        """测试Priority枚举"""
        assert Priority.LOW.value == 'low'
        assert Priority.NORMAL.value == 'normal'
        assert Priority.HIGH.value == 'high'
        assert Priority.URGENT.value == 'urgent'

    @pytest.mark.asyncio
    async def test_llm_client_error_handling(self, command_parser):
        """测试LLM客户端错误处理"""
        command_parser.llm_client.chat = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        
        with pytest.raises(CommandParsingError, match="LLM service error"):
            await command_parser.parse_command("search for something")

    @pytest.mark.asyncio
    async def test_confidence_threshold(self, command_parser):
        """测试置信度阈值"""
        command_parser.llm_client.chat = AsyncMock(return_value={
            'content': '''{
                "intent": "unclear_intent",
                "parameters": {},
                "confidence": 0.2,
                "risk_level": "low",
                "reasoning": "Very unclear command"
            }''',
            'usage': {'tokens': 100}
        })
        
        result = await command_parser.parse_command("do something unclear")
        
        # 低置信度应该触发澄清请求
        assert result['confidence'] < 0.5
        assert 'clarification_needed' in result or result['confidence'] < command_parser.confidence_threshold