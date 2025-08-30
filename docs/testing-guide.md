# 测试指南

本文档详细介绍 Aura 项目的测试策略、测试类型、测试工具和最佳实践，帮助开发者编写高质量的测试代码。

## 目录

- [测试策略](#测试策略)
- [测试类型](#测试类型)
- [测试工具](#测试工具)
- [测试结构](#测试结构)
- [单元测试](#单元测试)
- [集成测试](#集成测试)
- [端到端测试](#端到端测试)
- [性能测试](#性能测试)
- [测试数据管理](#测试数据管理)
- [Mock 和 Stub](#mock-和-stub)
- [测试覆盖率](#测试覆盖率)
- [持续集成](#持续集成)
- [测试最佳实践](#测试最佳实践)
- [故障排除](#故障排除)

---

## 测试策略

### 测试金字塔

```mermaid
pyramid
    title 测试金字塔
    "UI Tests" : 10
    "Integration Tests" : 30
    "Unit Tests" : 60
```

- **单元测试 (60%)**：快速、独立、覆盖核心业务逻辑
- **集成测试 (30%)**：验证组件间交互、数据库操作、外部服务
- **端到端测试 (10%)**：模拟真实用户场景、关键业务流程

### 测试原则

1. **FIRST 原则**
   - **Fast**: 测试应该快速执行
   - **Independent**: 测试之间应该独立
   - **Repeatable**: 测试应该可重复执行
   - **Self-Validating**: 测试应该有明确的通过/失败结果
   - **Timely**: 测试应该及时编写

2. **AAA 模式**
   - **Arrange**: 准备测试数据和环境
   - **Act**: 执行被测试的操作
   - **Assert**: 验证结果

3. **测试驱动开发 (TDD)**
   - Red: 编写失败的测试
   - Green: 编写最少的代码使测试通过
   - Refactor: 重构代码保持测试通过

---

## 测试类型

### 1. 功能测试

- **单元测试**: 测试单个函数或方法
- **集成测试**: 测试组件间的交互
- **系统测试**: 测试完整的系统功能
- **验收测试**: 验证业务需求

### 2. 非功能测试

- **性能测试**: 测试系统性能指标
- **负载测试**: 测试系统在正常负载下的表现
- **压力测试**: 测试系统在极限条件下的表现
- **安全测试**: 测试系统安全性

### 3. 特殊测试

- **回归测试**: 确保新代码不破坏现有功能
- **烟雾测试**: 快速验证基本功能
- **契约测试**: 验证服务间的接口契约
- **混沌测试**: 测试系统的容错能力

---

## 测试工具

### 核心测试框架

```python
# pytest - 主要测试框架
pip install pytest
pip install pytest-asyncio  # 异步测试支持
pip install pytest-cov      # 覆盖率报告
pip install pytest-mock     # Mock 支持
pip install pytest-xdist    # 并行测试
pip install pytest-html     # HTML 报告
```

### 测试工具生态

```python
# Mock 和 Stub
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pytest_mock import mocker

# 测试数据生成
from faker import Faker
from factory_boy import Factory

# HTTP 测试
from httpx import AsyncClient
from fastapi.testclient import TestClient

# 数据库测试
from sqlalchemy_utils import create_database, drop_database
from alembic import command

# 性能测试
import pytest-benchmark
import locust
```

### 测试配置

`pytest.ini`:

```ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    --strict-markers
    --strict-config
    --cov=src/aura
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=80
    --tb=short
    --disable-warnings
testpaths = tests
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests
    security: marks tests as security tests
    contract: marks tests as contract tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## 测试结构

### 项目测试目录结构

```
tests/
├── conftest.py                    # pytest 全局配置
├── fixtures/                      # 测试数据
│   ├── __init__.py
│   ├── tasks.json                # 任务测试数据
│   ├── skills.json               # 技能测试数据
│   ├── sites.json                # 网站模型测试数据
│   └── users.json                # 用户测试数据
├── unit/                          # 单元测试
│   ├── __init__.py
│   ├── core/
│   │   ├── test_orchestrator.py   # 编排器测试
│   │   ├── test_action_graph.py   # 动作图测试
│   │   └── test_exceptions.py     # 异常处理测试
│   ├── skills/
│   │   ├── test_skill_library.py  # 技能库测试
│   │   └── test_skill_executor.py # 技能执行器测试
│   ├── sites/
│   │   ├── test_site_registry.py  # 网站注册表测试
│   │   └── test_site_model.py     # 网站模型测试
│   ├── mcp/
│   │   ├── test_mcp_manager.py    # MCP 管理器测试
│   │   ├── test_mcp_client.py     # MCP 客户端测试
│   │   └── test_mcp_error_handling.py # MCP 错误处理测试
│   ├── policy/
│   │   ├── test_policy_engine.py  # 策略引擎测试
│   │   └── test_risk_assessment.py # 风险评估测试
│   └── utils/
│       ├── test_helpers.py        # 工具函数测试
│       └── test_validators.py     # 验证器测试
├── integration/                   # 集成测试
│   ├── __init__.py
│   ├── test_api_endpoints.py      # API 端点测试
│   ├── test_database_operations.py # 数据库操作测试
│   ├── test_mcp_integration.py    # MCP 集成测试
│   ├── test_skill_execution.py    # 技能执行集成测试
│   └── test_workflow_integration.py # 工作流集成测试
├── e2e/                           # 端到端测试
│   ├── __init__.py
│   ├── test_user_workflows.py     # 用户工作流测试
│   ├── test_task_lifecycle.py     # 任务生命周期测试
│   └── test_system_scenarios.py   # 系统场景测试
├── performance/                   # 性能测试
│   ├── __init__.py
│   ├── test_load.py              # 负载测试
│   ├── test_stress.py            # 压力测试
│   ├── test_concurrency.py       # 并发测试
│   └── locustfile.py             # Locust 性能测试
├── security/                      # 安全测试
│   ├── __init__.py
│   ├── test_authentication.py    # 认证测试
│   ├── test_authorization.py     # 授权测试
│   └── test_input_validation.py  # 输入验证测试
└── contract/                      # 契约测试
    ├── __init__.py
    ├── test_api_contracts.py      # API 契约测试
    └── test_mcp_contracts.py      # MCP 契约测试
```

### 全局测试配置

`tests/conftest.py`:

```python
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.aura.main import create_app
from src.aura.models.database import Base, get_db
from src.aura.core.orchestrator import Orchestrator
from src.aura.mcp.manager import MCPManager

# 测试数据库 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 异步测试事件循环配置
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于整个测试会话"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 数据库相关 Fixtures
@pytest.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建数据库会话"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

# 应用相关 Fixtures
@pytest.fixture
def app(db_session):
    """创建 FastAPI 应用实例"""
    app = create_app()
    
    # 覆盖数据库依赖
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    return app

@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """创建测试客户端"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# 核心组件 Fixtures
@pytest.fixture
def mock_mcp_manager():
    """模拟 MCP 管理器"""
    manager = Mock(spec=MCPManager)
    manager.execute_command = AsyncMock(return_value={
        "success": True,
        "result": "模拟执行结果"
    })
    manager.get_server_status = AsyncMock(return_value={
        "playwright": {"status": "connected", "health": "healthy"}
    })
    return manager

@pytest.fixture
async def orchestrator(mock_mcp_manager, db_session):
    """创建编排器实例"""
    # 创建模拟依赖
    skill_library = Mock()
    site_registry = Mock()
    action_engine = Mock()
    policy_engine = Mock()
    
    orchestrator = Orchestrator(
        skill_library=skill_library,
        site_registry=site_registry,
        action_engine=action_engine,
        policy_engine=policy_engine,
        mcp_manager=mock_mcp_manager,
        db_session=db_session
    )
    
    yield orchestrator
    
    # 清理
    await orchestrator.cleanup()

# 测试数据 Fixtures
@pytest.fixture
def sample_task_data():
    """示例任务数据"""
    return {
        "task_id": "test_task_123",
        "description": "测试任务描述",
        "target_url": "https://example.com",
        "execution_mode": "AI_MODE",
        "parameters": {
            "username": "test_user",
            "password": "test_password"
        },
        "priority": "MEDIUM",
        "timeout": 300
    }

@pytest.fixture
def sample_skill_data():
    """示例技能数据"""
    return {
        "skill_id": "test_skill_001",
        "name": "测试技能",
        "description": "用于测试的技能",
        "category": "test",
        "version": "1.0.0",
        "script_content": "console.log('测试技能执行');",
        "parameters": {
            "required": ["target_element"],
            "optional": ["timeout"]
        }
    }

@pytest.fixture
def sample_site_model():
    """示例网站模型"""
    return {
        "domain": "example.com",
        "name": "示例网站",
        "selectors": {
            "login_form": "#login-form",
            "username_field": "input[name='username']",
            "password_field": "input[name='password']",
            "submit_button": "button[type='submit']"
        },
        "workflows": {
            "login": [
                {"action": "navigate", "url": "https://example.com/login"},
                {"action": "fill", "selector": "username_field", "value": "{{username}}"},
                {"action": "fill", "selector": "password_field", "value": "{{password}}"},
                {"action": "click", "selector": "submit_button"}
            ]
        }
    }

# 环境配置 Fixtures
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """设置测试环境变量"""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DEBUG", "true")

# 清理 Fixtures
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """测试后清理"""
    yield
    # 清理临时文件
    import tempfile
    import shutil
    temp_dir = tempfile.gettempdir()
    for file in os.listdir(temp_dir):
        if file.startswith("aura_test_"):
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

# 性能测试 Fixtures
@pytest.fixture
def benchmark_config():
    """性能测试配置"""
    return {
        "min_rounds": 5,
        "max_time": 10.0,
        "warmup": True,
        "warmup_iterations": 2
    }

# 并发测试 Fixtures
@pytest.fixture
def concurrency_config():
    """并发测试配置"""
    return {
        "max_workers": 10,
        "total_requests": 100,
        "timeout": 30
    }
```

---

## 单元测试

### 基本单元测试示例

```python
# tests/unit/core/test_orchestrator.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.aura.core.orchestrator import Orchestrator, TaskRequest, TaskResult
from src.aura.core.exceptions import TaskExecutionError, ValidationError

class TestOrchestrator:
    """编排器单元测试"""
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, orchestrator, sample_task_data):
        """测试成功创建任务"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True, risk_level="LOW")
        )
        
        # Act
        task_id = await orchestrator.create_task(task_request)
        
        # Assert
        assert task_id == sample_task_data["task_id"]
        assert task_id in orchestrator._tasks
        orchestrator.policy_engine.evaluate.assert_called_once()
        
        # 验证任务状态
        task = orchestrator._tasks[task_id]
        assert task.status == "PENDING"
        assert task.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_task_policy_rejection(self, orchestrator, sample_task_data):
        """测试策略拒绝任务创建"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=False, reason="高风险操作")
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="高风险操作"):
            await orchestrator.create_task(task_request)
        
        # 验证任务未被创建
        assert sample_task_data["task_id"] not in orchestrator._tasks
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator, sample_task_data):
        """测试成功执行任务"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 模拟技能执行成功
        orchestrator.skill_library.execute_skill = AsyncMock(
            return_value={"success": True, "result": "执行成功"}
        )
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        result = await orchestrator.execute_task(task_id)
        
        # Assert
        assert isinstance(result, TaskResult)
        assert result.status == "COMPLETED"
        assert result.success is True
        assert "执行成功" in str(result.result)
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_execute_task_with_retry(self, orchestrator, sample_task_data):
        """测试任务执行重试机制"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 模拟前两次失败，第三次成功
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TaskExecutionError("临时错误")
            return {"success": True, "result": "重试成功"}
        
        orchestrator.skill_library.execute_skill = mock_execute
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        result = await orchestrator.execute_task(task_id)
        
        # Assert
        assert result.status == "COMPLETED"
        assert result.success is True
        assert call_count == 3  # 验证重试了3次
        assert result.retry_count == 2  # 重试次数
    
    @pytest.mark.asyncio
    async def test_execute_task_max_retries_exceeded(self, orchestrator, sample_task_data):
        """测试超过最大重试次数"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 模拟总是失败
        orchestrator.skill_library.execute_skill = AsyncMock(
            side_effect=TaskExecutionError("持续错误")
        )
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        result = await orchestrator.execute_task(task_id)
        
        # Assert
        assert result.status == "FAILED"
        assert result.success is False
        assert "持续错误" in result.error_message
        assert result.retry_count == orchestrator.max_retries
    
    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, orchestrator, sample_task_data):
        """测试任务执行超时"""
        # Arrange
        sample_task_data["timeout"] = 1  # 1秒超时
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 模拟长时间执行
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(2)  # 睡眠2秒
            return {"success": True, "result": "不应该到达这里"}
        
        orchestrator.skill_library.execute_skill = slow_execute
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        result = await orchestrator.execute_task(task_id)
        
        # Assert
        assert result.status == "FAILED"
        assert result.success is False
        assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, orchestrator, sample_task_data):
        """测试获取任务状态"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        status = await orchestrator.get_task_status(task_id)
        
        # Assert
        assert status["task_id"] == task_id
        assert status["status"] == "PENDING"
        assert "created_at" in status
        assert "updated_at" in status
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, orchestrator, sample_task_data):
        """测试取消任务"""
        # Arrange
        task_request = TaskRequest(**sample_task_data)
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 创建任务
        task_id = await orchestrator.create_task(task_request)
        
        # Act
        success = await orchestrator.cancel_task(task_id)
        
        # Assert
        assert success is True
        
        # 验证任务状态
        status = await orchestrator.get_task_status(task_id)
        assert status["status"] == "CANCELLED"
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, orchestrator, sample_task_data):
        """测试列出任务"""
        # Arrange
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 创建多个任务
        task_ids = []
        for i in range(3):
            task_data = sample_task_data.copy()
            task_data["task_id"] = f"test_task_{i}"
            task_request = TaskRequest(**task_data)
            task_id = await orchestrator.create_task(task_request)
            task_ids.append(task_id)
        
        # Act
        tasks = await orchestrator.list_tasks()
        
        # Assert
        assert len(tasks) == 3
        returned_task_ids = [task["task_id"] for task in tasks]
        assert all(task_id in returned_task_ids for task_id in task_ids)
    
    def test_validate_task_request(self, orchestrator):
        """测试任务请求验证"""
        # 测试有效请求
        valid_request = TaskRequest(
            task_id="valid_task",
            description="有效任务",
            target_url="https://example.com",
            execution_mode="AI_MODE"
        )
        
        # 应该不抛出异常
        orchestrator._validate_task_request(valid_request)
        
        # 测试无效 URL
        with pytest.raises(ValidationError, match="无效的 URL"):
            invalid_request = TaskRequest(
                task_id="invalid_task",
                description="无效任务",
                target_url="not-a-url",
                execution_mode="AI_MODE"
            )
            orchestrator._validate_task_request(invalid_request)
        
        # 测试无效执行模式
        with pytest.raises(ValidationError, match="无效的执行模式"):
            invalid_request = TaskRequest(
                task_id="invalid_task",
                description="无效任务",
                target_url="https://example.com",
                execution_mode="INVALID_MODE"
            )
            orchestrator._validate_task_request(invalid_request)
```

### 参数化测试

```python
# 参数化测试示例
@pytest.mark.parametrize("execution_mode,expected_strategy", [
    ("AI_MODE", "ai_strategy"),
    ("SCRIPT_MODE", "script_strategy"),
    ("HYBRID_MODE", "hybrid_strategy"),
])
def test_strategy_selection(orchestrator, execution_mode, expected_strategy):
    """测试策略选择"""
    strategy = orchestrator._select_execution_strategy(execution_mode)
    assert strategy.name == expected_strategy

@pytest.mark.parametrize("url,expected_valid", [
    ("https://example.com", True),
    ("http://test.org", True),
    ("ftp://files.com", False),
    ("not-a-url", False),
    ("", False),
    (None, False),
])
def test_url_validation(orchestrator, url, expected_valid):
    """测试 URL 验证"""
    if expected_valid:
        assert orchestrator._validate_url(url) is True
    else:
        with pytest.raises(ValidationError):
            orchestrator._validate_url(url)
```

---

## 集成测试

### API 集成测试

```python
# tests/integration/test_api_endpoints.py
import pytest
import json
from httpx import AsyncClient
from fastapi import status

class TestTaskAPI:
    """任务 API 集成测试"""
    
    @pytest.mark.asyncio
    async def test_create_task_endpoint(self, async_client: AsyncClient, sample_task_data):
        """测试创建任务端点"""
        # Act
        response = await async_client.post(
            "/api/v1/tasks",
            json=sample_task_data
        )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["task_id"] == sample_task_data["task_id"]
        assert data["status"] == "PENDING"
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_get_task_endpoint(self, async_client: AsyncClient, sample_task_data):
        """测试获取任务端点"""
        # Arrange - 先创建任务
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=sample_task_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        task_id = sample_task_data["task_id"]
        
        # Act
        response = await async_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["task_id"] == task_id
        assert data["description"] == sample_task_data["description"]
    
    @pytest.mark.asyncio
    async def test_execute_task_endpoint(self, async_client: AsyncClient, sample_task_data):
        """测试执行任务端点"""
        # Arrange - 先创建任务
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=sample_task_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        task_id = sample_task_data["task_id"]
        
        # Act
        response = await async_client.post(f"/api/v1/tasks/{task_id}/execute")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["task_id"] == task_id
        assert "status" in data
        assert "execution_time" in data
    
    @pytest.mark.asyncio
    async def test_list_tasks_endpoint(self, async_client: AsyncClient, sample_task_data):
        """测试列出任务端点"""
        # Arrange - 创建多个任务
        task_ids = []
        for i in range(3):
            task_data = sample_task_data.copy()
            task_data["task_id"] = f"test_task_{i}"
            
            response = await async_client.post(
                "/api/v1/tasks",
                json=task_data
            )
            assert response.status_code == status.HTTP_201_CREATED
            task_ids.append(task_data["task_id"])
        
        # Act
        response = await async_client.get("/api/v1/tasks")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 3
        
        returned_task_ids = [task["task_id"] for task in data["tasks"]]
        assert all(task_id in returned_task_ids for task_id in task_ids)
    
    @pytest.mark.asyncio
    async def test_cancel_task_endpoint(self, async_client: AsyncClient, sample_task_data):
        """测试取消任务端点"""
        # Arrange - 先创建任务
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=sample_task_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        task_id = sample_task_data["task_id"]
        
        # Act
        response = await async_client.post(f"/api/v1/tasks/{task_id}/cancel")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        
        # 验证任务状态已更新
        status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        status_data = status_response.json()
        assert status_data["status"] == "CANCELLED"
    
    @pytest.mark.asyncio
    async def test_task_not_found(self, async_client: AsyncClient):
        """测试任务不存在的情况"""
        # Act
        response = await async_client.get("/api/v1/tasks/nonexistent_task")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_task_data(self, async_client: AsyncClient):
        """测试无效任务数据"""
        # Act
        invalid_data = {
            "task_id": "",  # 空任务 ID
            "description": "",  # 空描述
            "target_url": "not-a-url",  # 无效 URL
            "execution_mode": "INVALID_MODE"  # 无效执行模式
        }
        
        response = await async_client.post(
            "/api/v1/tasks",
            json=invalid_data
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
```

### 数据库集成测试

```python
# tests/integration/test_database_operations.py
import pytest
from sqlalchemy import select
from datetime import datetime, timedelta

from src.aura.models.task import Task, TaskStatus
from src.aura.models.skill import Skill
from src.aura.models.site import SiteModel

class TestDatabaseOperations:
    """数据库操作集成测试"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, db_session, sample_task_data):
        """测试创建任务"""
        # Arrange
        task = Task(
            task_id=sample_task_data["task_id"],
            description=sample_task_data["description"],
            target_url=sample_task_data["target_url"],
            execution_mode=sample_task_data["execution_mode"],
            parameters=sample_task_data["parameters"],
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Act
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        # Assert
        assert task.id is not None
        assert task.task_id == sample_task_data["task_id"]
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
    
    @pytest.mark.asyncio
    async def test_query_tasks_by_status(self, db_session, sample_task_data):
        """测试按状态查询任务"""
        # Arrange - 创建不同状态的任务
        tasks = []
        statuses = [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED]
        
        for i, status in enumerate(statuses):
            task = Task(
                task_id=f"task_{i}",
                description=f"任务 {i}",
                target_url="https://example.com",
                execution_mode="AI_MODE",
                status=status,
                created_at=datetime.utcnow()
            )
            tasks.append(task)
            db_session.add(task)
        
        await db_session.commit()
        
        # Act - 查询 PENDING 状态的任务
        stmt = select(Task).where(Task.status == TaskStatus.PENDING)
        result = await db_session.execute(stmt)
        pending_tasks = result.scalars().all()
        
        # Assert
        assert len(pending_tasks) == 1
        assert pending_tasks[0].task_id == "task_0"
        assert pending_tasks[0].status == TaskStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, db_session, sample_task_data):
        """测试更新任务状态"""
        # Arrange
        task = Task(
            task_id=sample_task_data["task_id"],
            description=sample_task_data["description"],
            target_url=sample_task_data["target_url"],
            execution_mode=sample_task_data["execution_mode"],
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        # Act
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await db_session.commit()
        
        # Assert
        await db_session.refresh(task)
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
    
    @pytest.mark.asyncio
    async def test_task_relationships(self, db_session, sample_task_data, sample_skill_data):
        """测试任务关系"""
        # Arrange - 创建技能
        skill = Skill(
            skill_id=sample_skill_data["skill_id"],
            name=sample_skill_data["name"],
            description=sample_skill_data["description"],
            category=sample_skill_data["category"],
            version=sample_skill_data["version"],
            script_content=sample_skill_data["script_content"]
        )
        db_session.add(skill)
        
        # 创建任务
        task = Task(
            task_id=sample_task_data["task_id"],
            description=sample_task_data["description"],
            target_url=sample_task_data["target_url"],
            execution_mode=sample_task_data["execution_mode"],
            status=TaskStatus.PENDING,
            skill_id=skill.skill_id,  # 关联技能
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        
        await db_session.commit()
        await db_session.refresh(task)
        
        # Act - 查询任务及其关联的技能
        stmt = select(Task).where(Task.task_id == sample_task_data["task_id"])
        result = await db_session.execute(stmt)
        retrieved_task = result.scalar_one()
        
        # Assert
        assert retrieved_task.skill_id == sample_skill_data["skill_id"]
        # 如果有关系映射，可以测试关联对象
        # assert retrieved_task.skill.name == sample_skill_data["name"]
    
    @pytest.mark.asyncio
    async def test_query_tasks_with_pagination(self, db_session):
        """测试分页查询任务"""
        # Arrange - 创建多个任务
        tasks = []
        for i in range(15):
            task = Task(
                task_id=f"task_{i:02d}",
                description=f"任务 {i}",
                target_url="https://example.com",
                execution_mode="AI_MODE",
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow() - timedelta(minutes=i)
            )
            tasks.append(task)
            db_session.add(task)
        
        await db_session.commit()
        
        # Act - 分页查询（第1页，每页5条）
        stmt = (
            select(Task)
            .order_by(Task.created_at.desc())
            .limit(5)
            .offset(0)
        )
        result = await db_session.execute(stmt)
        page1_tasks = result.scalars().all()
        
        # Act - 分页查询（第2页，每页5条）
        stmt = (
            select(Task)
            .order_by(Task.created_at.desc())
            .limit(5)
            .offset(5)
        )
        result = await db_session.execute(stmt)
        page2_tasks = result.scalars().all()
        
        # Assert
        assert len(page1_tasks) == 5
        assert len(page2_tasks) == 5
        
        # 验证排序（最新的任务在前）
        assert page1_tasks[0].task_id == "task_00"
        assert page2_tasks[0].task_id == "task_05"
        
        # 验证没有重复
        page1_ids = {task.task_id for task in page1_tasks}
        page2_ids = {task.task_id for task in page2_tasks}
        assert len(page1_ids.intersection(page2_ids)) == 0
```

---

## 端到端测试

### 用户工作流测试

```python
# tests/e2e/test_user_workflows.py
import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status

class TestUserWorkflows:
    """用户工作流端到端测试"""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_task_workflow(self, async_client: AsyncClient):
        """测试完整的任务工作流"""
        # 1. 创建任务
        task_data = {
            "task_id": "e2e_task_001",
            "description": "端到端测试任务",
            "target_url": "https://httpbin.org/forms/post",
            "execution_mode": "AI_MODE",
            "parameters": {
                "form_data": {
                    "custname": "测试用户",
                    "custtel": "1234567890",
                    "custemail": "test@example.com"
                }
            }
        }
        
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=task_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        task_id = task_data["task_id"]
        
        # 2. 验证任务已创建
        get_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == status.HTTP_200_OK
        
        task_info = get_response.json()
        assert task_info["status"] == "PENDING"
        
        # 3. 执行任务
        execute_response = await async_client.post(
            f"/api/v1/tasks/{task_id}/execute"
        )
        assert execute_response.status_code == status.HTTP_200_OK
        
        # 4. 等待任务完成（轮询状态）
        max_wait_time = 30  # 最多等待30秒
        wait_interval = 1   # 每秒检查一次
        
        for _ in range(max_wait_time):
            status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
            status_data = status_response.json()
            
            if status_data["status"] in ["COMPLETED", "FAILED"]:
                break
            
            await asyncio.sleep(wait_interval)
        
        # 5. 验证任务完成
        final_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        final_data = final_response.json()
        
        assert final_data["status"] == "COMPLETED"
        assert final_data["success"] is True
        assert "result" in final_data
        assert final_data["execution_time"] > 0
        
        # 6. 获取任务结果
        result_response = await async_client.get(
            f"/api/v1/tasks/{task_id}/result"
        )
        assert result_response.status_code == status.HTTP_200_OK
        
        result_data = result_response.json()
        assert "data" in result_data
        assert "screenshots" in result_data  # 如果有截图
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_skill_execution_workflow(self, async_client: AsyncClient):
        """测试技能执行工作流"""
        # 1. 上传技能
        skill_data = {
            "skill_id": "e2e_skill_001",
            "name": "表单填写技能",
            "description": "自动填写表单的技能",
            "category": "form",
            "version": "1.0.0",
            "script_content": """
                async function execute(page, parameters) {
                    await page.goto(parameters.target_url);
                    
                    // 填写表单
                    await page.fill('input[name="custname"]', parameters.form_data.custname);
                    await page.fill('input[name="custtel"]', parameters.form_data.custtel);
                    await page.fill('input[name="custemail"]', parameters.form_data.custemail);
                    
                    // 提交表单
                    await page.click('input[type="submit"]');
                    
                    // 等待结果
                    await page.waitForSelector('.result', { timeout: 5000 });
                    
                    return {
                        success: true,
                        message: '表单提交成功',
                        url: page.url()
                    };
                }
            """,
            "parameters": {
                "required": ["target_url", "form_data"],
                "optional": ["timeout"]
            }
        }
        
        skill_response = await async_client.post(
            "/api/v1/skills",
            json=skill_data
        )
        assert skill_response.status_code == status.HTTP_201_CREATED
        
        # 2. 创建使用该技能的任务
        task_data = {
            "task_id": "e2e_skill_task_001",
            "description": "使用技能执行任务",
            "target_url": "https://httpbin.org/forms/post",
            "execution_mode": "SCRIPT_MODE",
            "skill_id": skill_data["skill_id"],
            "parameters": {
                "target_url": "https://httpbin.org/forms/post",
                "form_data": {
                    "custname": "技能测试用户",
                    "custtel": "9876543210",
                    "custemail": "skill@example.com"
                }
            }
        }
        
        task_response = await async_client.post(
            "/api/v1/tasks",
            json=task_data
        )
        assert task_response.status_code == status.HTTP_201_CREATED
        
        # 3. 执行任务
        task_id = task_data["task_id"]
        execute_response = await async_client.post(
            f"/api/v1/tasks/{task_id}/execute"
        )
        assert execute_response.status_code == status.HTTP_200_OK
        
        # 4. 等待并验证结果
        # (类似上面的轮询逻辑)
        
        # 5. 清理 - 删除技能
        delete_response = await async_client.delete(
            f"/api/v1/skills/{skill_data['skill_id']}"
        )
        assert delete_response.status_code == status.HTTP_200_OK
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, async_client: AsyncClient):
        """测试错误处理工作流"""
        # 1. 创建会失败的任务
        task_data = {
            "task_id": "e2e_error_task_001",
            "description": "故意失败的任务",
            "target_url": "https://nonexistent-domain-12345.com",
            "execution_mode": "AI_MODE",
            "parameters": {}
        }
        
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=task_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        
        # 2. 执行任务
        task_id = task_data["task_id"]
        execute_response = await async_client.post(
            f"/api/v1/tasks/{task_id}/execute"
        )
        assert execute_response.status_code == status.HTTP_200_OK
        
        # 3. 等待任务失败
        max_wait_time = 30
        wait_interval = 1
        
        for _ in range(max_wait_time):
            status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "FAILED":
                break
            
            await asyncio.sleep(wait_interval)
        
        # 4. 验证错误信息
        final_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        final_data = final_response.json()
        
        assert final_data["status"] == "FAILED"
        assert final_data["success"] is False
        assert "error_message" in final_data
        assert final_data["error_message"] is not None
        assert len(final_data["error_message"]) > 0
        
        # 5. 验证重试次数
        assert "retry_count" in final_data
        assert final_data["retry_count"] > 0
```

---

## 性能测试

### 负载测试

```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient

class TestLoadPerformance:
    """负载性能测试"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, async_client: AsyncClient):
        """测试并发任务创建性能"""
        # 配置
        concurrent_requests = 50
        total_requests = 200
        
        # 准备测试数据
        tasks_data = []
        for i in range(total_requests):
            task_data = {
                "task_id": f"load_test_task_{i:03d}",
                "description": f"负载测试任务 {i}",
                "target_url": "https://httpbin.org/delay/1",
                "execution_mode": "AI_MODE",
                "parameters": {"test_id": i}
            }
            tasks_data.append(task_data)
        
        # 执行并发请求
        start_time = time.time()
        
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def create_task(task_data):
            async with semaphore:
                response = await async_client.post(
                    "/api/v1/tasks",
                    json=task_data
                )
                return response.status_code, response.json()
        
        results = await asyncio.gather(
            *[create_task(task_data) for task_data in tasks_data],
            return_exceptions=True
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证结果
        successful_requests = sum(
            1 for result in results 
            if not isinstance(result, Exception) and result[0] == 201
        )
        
        # 性能断言
        assert successful_requests >= total_requests * 0.95  # 95% 成功率
        assert total_time < 60  # 总时间不超过60秒
        
        # 计算性能指标
        throughput = successful_requests / total_time
        avg_response_time = total_time / total_requests
        
        print(f"\n性能指标:")
        print(f"总请求数: {total_requests}")
        print(f"成功请求数: {successful_requests}")
        print(f"成功率: {successful_requests/total_requests*100:.2f}%")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"吞吐量: {throughput:.2f} requests/second")
        print(f"平均响应时间: {avg_response_time:.3f}秒")
        
        # 性能要求
        assert throughput > 10  # 吞吐量应大于10 requests/second
        assert avg_response_time < 1.0  # 平均响应时间应小于1秒
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_task_execution_performance(self, async_client: AsyncClient):
        """测试任务执行性能"""
        # 创建任务
        task_data = {
            "task_id": "perf_exec_task_001",
            "description": "性能测试执行任务",
            "target_url": "https://httpbin.org/delay/2",
            "execution_mode": "AI_MODE",
            "parameters": {}
        }
        
        create_response = await async_client.post(
            "/api/v1/tasks",
            json=task_data
        )
        assert create_response.status_code == 201
        
        # 测量执行时间
        start_time = time.time()
        
        execute_response = await async_client.post(
            f"/api/v1/tasks/{task_data['task_id']}/execute"
        )
        assert execute_response.status_code == 200
        
        # 等待任务完成
        max_wait = 30
        for _ in range(max_wait):
            status_response = await async_client.get(
                f"/api/v1/tasks/{task_data['task_id']}"
            )
            status_data = status_response.json()
            
            if status_data["status"] in ["COMPLETED", "FAILED"]:
                break
            
            await asyncio.sleep(1)
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        
        # 验证性能
        final_response = await async_client.get(
            f"/api/v1/tasks/{task_data['task_id']}"
        )
        final_data = final_response.json()
        
        assert final_data["status"] == "COMPLETED"
        assert total_execution_time < 35  # 总时间应小于35秒
        
        print(f"\n任务执行性能:")
        print(f"总执行时间: {total_execution_time:.2f}秒")
        print(f"任务内部执行时间: {final_data.get('execution_time', 0):.2f}秒")

### Locust 性能测试

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import json
import random

class AuraUser(HttpUser):
    """Aura 系统用户行为模拟"""
    
    wait_time = between(1, 3)  # 用户操作间隔1-3秒
    
    def on_start(self):
        """用户开始时的初始化"""
        self.task_counter = 0
    
    @task(3)
    def create_task(self):
        """创建任务 (权重3)"""
        self.task_counter += 1
        task_data = {
            "task_id": f"locust_task_{self.task_counter}_{random.randint(1000, 9999)}",
            "description": f"Locust 测试任务 {self.task_counter}",
            "target_url": "https://httpbin.org/delay/1",
            "execution_mode": random.choice(["AI_MODE", "SCRIPT_MODE"]),
            "parameters": {
                "test_param": f"value_{random.randint(1, 100)}"
            }
        }
        
        with self.client.post(
            "/api/v1/tasks",
            json=task_data,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
                # 保存任务ID用于后续操作
                self.task_id = task_data["task_id"]
            else:
                response.failure(f"创建任务失败: {response.status_code}")
    
    @task(2)
    def get_task_status(self):
        """获取任务状态 (权重2)"""
        if hasattr(self, 'task_id'):
            with self.client.get(
                f"/api/v1/tasks/{self.task_id}",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"获取任务状态失败: {response.status_code}")
    
    @task(1)
    def list_tasks(self):
        """列出任务 (权重1)"""
        with self.client.get(
            "/api/v1/tasks?limit=10",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"列出任务失败: {response.status_code}")
    
    @task(1)
    def execute_task(self):
        """执行任务 (权重1)"""
        if hasattr(self, 'task_id'):
            with self.client.post(
                f"/api/v1/tasks/{self.task_id}/execute",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"执行任务失败: {response.status_code}")

class AdminUser(HttpUser):
    """管理员用户行为模拟"""
    
    wait_time = between(2, 5)
    
    @task
    def get_system_status(self):
        """获取系统状态"""
        with self.client.get(
            "/api/v1/system/status",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取系统状态失败: {response.status_code}")
    
    @task
    def get_metrics(self):
        """获取系统指标"""
        with self.client.get(
            "/api/v1/metrics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取系统指标失败: {response.status_code}")
```

运行 Locust 测试：

```bash
# 启动 Locust Web UI
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 命令行模式运行
locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
       --users 50 --spawn-rate 5 --run-time 5m --headless
```

---

## 测试数据管理

### 测试数据生成

```python
# tests/fixtures/data_factory.py
from faker import Faker
from factory import Factory, Sequence, SubFactory, LazyAttribute
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyDateTime
from datetime import datetime, timedelta
import random
import uuid

fake = Faker('zh_CN')  # 中文数据

class TaskDataFactory(Factory):
    """任务数据工厂"""
    
    task_id = LazyAttribute(lambda obj: f"task_{uuid.uuid4().hex[:8]}")
    description = LazyAttribute(lambda obj: fake.sentence())
    target_url = LazyAttribute(lambda obj: fake.url())
    execution_mode = FuzzyChoice(["AI_MODE", "SCRIPT_MODE", "HYBRID_MODE"])
    priority = FuzzyChoice(["LOW", "MEDIUM", "HIGH", "URGENT"])
    timeout = FuzzyInteger(60, 600)  # 1-10分钟
    
    @LazyAttribute
    def parameters(obj):
        return {
            "username": fake.user_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "custom_param": fake.word()
        }

class SkillDataFactory(Factory):
    """技能数据工厂"""
    
    skill_id = LazyAttribute(lambda obj: f"skill_{uuid.uuid4().hex[:8]}")
    name = LazyAttribute(lambda obj: fake.catch_phrase())
    description = LazyAttribute(lambda obj: fake.text(max_nb_chars=200))
    category = FuzzyChoice(["form", "navigation", "data_extraction", "automation"])
    version = LazyAttribute(lambda obj: f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}")
    
    @LazyAttribute
    def script_content(obj):
        return f"""
        async function execute(page, parameters) {{
            // {obj.description}
            await page.goto(parameters.target_url);
            
            // 模拟操作
            await page.waitForTimeout(1000);
            
            return {{
                success: true,
                message: '{obj.name} 执行成功',
                data: parameters
            }};
        }}
        """
    
    @LazyAttribute
    def parameters(obj):
        return {
            "required": ["target_url"],
            "optional": ["timeout", "retry_count"]
        }

class SiteModelDataFactory(Factory):
    """网站模型数据工厂"""
    
    domain = LazyAttribute(lambda obj: fake.domain_name())
    name = LazyAttribute(lambda obj: fake.company())
    
    @LazyAttribute
    def selectors(obj):
        return {
            "login_form": "#login-form",
            "username_field": "input[name='username']",
            "password_field": "input[name='password']",
            "submit_button": "button[type='submit']",
            "error_message": ".error-message"
        }
    
    @LazyAttribute
    def workflows(obj):
        return {
            "login": [
                {"action": "navigate", "url": f"https://{obj.domain}/login"},
                {"action": "fill", "selector": "username_field", "value": "{{username}}"},
                {"action": "fill", "selector": "password_field", "value": "{{password}}"},
                {"action": "click", "selector": "submit_button"},
                {"action": "wait", "selector": "dashboard", "timeout": 5000}
            ]
        }

# 使用示例
def generate_test_data():
    """生成测试数据"""
    # 生成单个对象
    task = TaskDataFactory()
    skill = SkillDataFactory()
    site = SiteModelDataFactory()
    
    # 生成多个对象
    tasks = [TaskDataFactory() for _ in range(10)]
    skills = [SkillDataFactory() for _ in range(5)]
    
    # 生成特定属性的对象
    urgent_task = TaskDataFactory(priority="URGENT", timeout=60)
    form_skill = SkillDataFactory(category="form")
    
    return {
        "tasks": tasks,
        "skills": skills,
        "sites": [site],
        "urgent_task": urgent_task,
        "form_skill": form_skill
    }
```

### 测试数据文件

```json
// tests/fixtures/sample_tasks.json
{
  "valid_tasks": [
    {
      "task_id": "sample_task_001",
      "description": "登录测试网站",
      "target_url": "https://httpbin.org/forms/post",
      "execution_mode": "AI_MODE",
      "parameters": {
        "username": "testuser",
        "password": "testpass123"
      },
      "priority": "MEDIUM",
      "timeout": 300
    },
    {
      "task_id": "sample_task_002",
      "description": "数据提取任务",
      "target_url": "https://httpbin.org/json",
      "execution_mode": "SCRIPT_MODE",
      "parameters": {
        "extract_fields": ["slideshow.title", "slideshow.author"]
      },
      "priority": "HIGH",
      "timeout": 180
    }
  ],
  "invalid_tasks": [
    {
      "task_id": "",
      "description": "无效任务 - 空ID",
      "target_url": "https://example.com",
      "execution_mode": "AI_MODE"
    },
    {
      "task_id": "invalid_url_task",
      "description": "无效任务 - 错误URL",
      "target_url": "not-a-valid-url",
      "execution_mode": "AI_MODE"
    }
  ]
}
```

### 数据库测试数据

```python
# tests/fixtures/db_fixtures.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.aura.models.task import Task, TaskStatus
from src.aura.models.skill import Skill
from src.aura.models.site import SiteModel

@pytest.fixture
async def sample_tasks(db_session: AsyncSession):
    """创建示例任务数据"""
    tasks = [
        Task(
            task_id="db_task_001",
            description="数据库测试任务1",
            target_url="https://example.com",
            execution_mode="AI_MODE",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        ),
        Task(
            task_id="db_task_002",
            description="数据库测试任务2",
            target_url="https://test.com",
            execution_mode="SCRIPT_MODE",
            status=TaskStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(minutes=30)
        )
    ]
    
    for task in tasks:
        db_session.add(task)
    
    await db_session.commit()
    
    # 刷新对象以获取生成的ID
    for task in tasks:
        await db_session.refresh(task)
    
    return tasks

@pytest.fixture
async def sample_skills(db_session: AsyncSession):
    """创建示例技能数据"""
    skills = [
        Skill(
            skill_id="db_skill_001",
            name="登录技能",
            description="自动登录网站的技能",
            category="authentication",
            version="1.0.0",
            script_content="async function execute(page, params) { /* 登录逻辑 */ }",
            created_at=datetime.utcnow()
        ),
        Skill(
            skill_id="db_skill_002",
            name="表单填写技能",
            description="自动填写表单的技能",
            category="form",
            version="1.1.0",
            script_content="async function execute(page, params) { /* 表单填写逻辑 */ }",
            created_at=datetime.utcnow()
        )
    ]
    
    for skill in skills:
        db_session.add(skill)
    
    await db_session.commit()
    
    for skill in skills:
        await db_session.refresh(skill)
    
    return skills
```

---

## Mock 和 Stub

### 基本 Mock 使用

```python
# Mock 示例
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

class TestMockExamples:
    """Mock 使用示例"""
    
    def test_basic_mock(self):
        """基本 Mock 使用"""
        # 创建 Mock 对象
        mock_service = Mock()
        
        # 配置返回值
        mock_service.get_data.return_value = {"key": "value"}
        
        # 使用 Mock
        result = mock_service.get_data()
        
        # 验证
        assert result == {"key": "value"}
        mock_service.get_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_mock(self):
        """异步 Mock 使用"""
        # 创建异步 Mock
        mock_service = AsyncMock()
        
        # 配置异步返回值
        mock_service.fetch_data.return_value = {"async": "data"}
        
        # 使用异步 Mock
        result = await mock_service.fetch_data()
        
        # 验证
        assert result == {"async": "data"}
        mock_service.fetch_data.assert_called_once()
    
    def test_mock_side_effect(self):
        """Mock 副作用使用"""
        mock_service = Mock()
        
        # 配置副作用 - 抛出异常
        mock_service.risky_operation.side_effect = ValueError("模拟错误")
        
        # 测试异常处理
        with pytest.raises(ValueError, match="模拟错误"):
            mock_service.risky_operation()
    
    def test_mock_multiple_calls(self):
        """Mock 多次调用"""
        mock_service = Mock()
        
        # 配置多次调用的返回值
        mock_service.get_counter.side_effect = [1, 2, 3]
        
        # 多次调用
        assert mock_service.get_counter() == 1
        assert mock_service.get_counter() == 2
        assert mock_service.get_counter() == 3
        
        # 验证调用次数
        assert mock_service.get_counter.call_count == 3
    
    @patch('src.aura.external.api_client.requests.get')
    def test_patch_decorator(self, mock_get):
        """使用 patch 装饰器"""
        # 配置 Mock 响应
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # 导入并使用被测试的函数
        from src.aura.external.api_client import fetch_external_data
        
        result = fetch_external_data("https://api.example.com/data")
        
        # 验证
        assert result == {"status": "success"}
        mock_get.assert_called_once_with("https://api.example.com/data")
    
    def test_patch_context_manager(self):
        """使用 patch 上下文管理器"""
        with patch('src.aura.utils.datetime') as mock_datetime:
            # 配置固定时间
            fixed_time = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time
            
            from src.aura.utils import get_current_timestamp
            
            result = get_current_timestamp()
            
            assert result == fixed_time
            mock_datetime.now.assert_called_once()
```

### 复杂 Mock 场景

```python
# 复杂 Mock 场景
class TestComplexMocking:
    """复杂 Mock 场景测试"""
    
    @pytest.mark.asyncio
    async def test_mock_mcp_manager(self, orchestrator):
        """Mock MCP 管理器"""
        # 配置 MCP 管理器的复杂行为
        orchestrator.mcp_manager.execute_command = AsyncMock()
        
        # 配置不同命令的不同响应
        def mock_execute_command(server, command, **kwargs):
            if command == "navigate":
                return {"success": True, "url": kwargs.get("url")}
            elif command == "click":
                return {"success": True, "element": kwargs.get("selector")}
            elif command == "screenshot":
                return {"success": True, "image": "base64_image_data"}
            else:
                return {"success": False, "error": "未知命令"}
        
        orchestrator.mcp_manager.execute_command.side_effect = mock_execute_command
        
        # 测试不同命令
        nav_result = await orchestrator.mcp_manager.execute_command(
            "playwright", "navigate", url="https://example.com"
        )
        assert nav_result["success"] is True
        assert nav_result["url"] == "https://example.com"
        
        click_result = await orchestrator.mcp_manager.execute_command(
            "playwright", "click", selector="#button"
        )
        assert click_result["success"] is True
        assert click_result["element"] == "#button"
    
    @patch.multiple(
        'src.aura.core.orchestrator',
        skill_library=Mock(),
        policy_engine=AsyncMock()
    )
    def test_multiple_patches(self):
        """多个 patch 使用"""
        # 这里可以测试需要多个依赖的功能
        pass
    
    def test_mock_property(self):
        """Mock 属性"""
        mock_obj = Mock()
        
        # 配置属性
        type(mock_obj).status = PropertyMock(return_value="active")
        
        assert mock_obj.status == "active"
    
    def test_mock_magic_methods(self):
        """Mock 魔术方法"""
        mock_obj = MagicMock()
        
        # 配置魔术方法
        mock_obj.__len__.return_value = 5
        mock_obj.__getitem__.return_value = "item"
        
        assert len(mock_obj) == 5
        assert mock_obj[0] == "item"
```

---

## 测试覆盖率

### 覆盖率配置

```ini
# .coveragerc
[run]
source = src/aura
omit = 
    */tests/*
    */venv/*
    */migrations/*
    */scripts/*
    */__pycache__/*
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

show_missing = True
skip_covered = False
precision = 2

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

### 覆盖率命令

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src/aura --cov-report=html --cov-report=term-missing

# 只生成覆盖率报告（不运行测试）
coverage report

# 生成 HTML 报告
coverage html

# 生成 XML 报告（用于 CI/CD）
coverage xml

# 查看特定文件的覆盖率
coverage report src/aura/core/orchestrator.py

# 显示未覆盖的行
coverage report --show-missing
```

### 覆盖率分析

```python
# tests/test_coverage_analysis.py
import pytest
import coverage
import os

def test_coverage_threshold():
    """测试覆盖率阈值"""
    # 读取覆盖率数据
    cov = coverage.Coverage()
    cov.load()
    
    # 获取总体覆盖率
    total_coverage = cov.report(show_missing=False, file=open(os.devnull, 'w'))
    
    # 验证覆盖率阈值
    assert total_coverage >= 80, f"代码覆盖率 {total_coverage}% 低于要求的 80%"

def test_critical_modules_coverage():
    """测试关键模块覆盖率"""
    cov = coverage.Coverage()
    cov.load()
    
    # 关键模块列表
    critical_modules = [
        'src/aura/core/orchestrator.py',
        'src/aura/core/action_graph.py',
        'src/aura/mcp/manager.py',
        'src/aura/policy/engine.py'
    ]
    
    for module in critical_modules:
        if os.path.exists(module):
            # 获取模块覆盖率
            analysis = cov.analysis2(module)
            total_lines = len(analysis[1]) + len(analysis[2])
            covered_lines = len(analysis[1])
            coverage_percent = (covered_lines / total_lines) * 100 if total_lines > 0 else 0
            
            assert coverage_percent >= 90, f"{module} 覆盖率 {coverage_percent:.1f}% 低于要求的 90%"
```

---

## 持续集成

### GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: aura_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y postgresql-client
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Install Playwright browsers
      run: |
        playwright install
    
    - name: Set up environment variables
      run: |
        echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aura_test" >> $GITHUB_ENV
        echo "REDIS_URL=redis://localhost:6379/0" >> $GITHUB_ENV
        echo "ENVIRONMENT=test" >> $GITHUB_ENV
    
    - name: Run database migrations
      run: |
        alembic upgrade head
    
    - name: Run linting
      run: |
        flake8 src/ tests/
        black --check src/ tests/
        isort --check-only src/ tests/
        mypy src/
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src/aura --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
    
    - name: Run security tests
      run: |
        pytest tests/security/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: true
    
    - name: Generate test report
      if: always()
      run: |
        pytest tests/ --html=report.html --self-contained-html
    
    - name: Upload test report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-report-${{ matrix.python-version }}
        path: report.html

  e2e-tests:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        playwright install
    
    - name: Start application
      run: |
        python main.py &
        sleep 10  # 等待应用启动
    
    - name: Run E2E tests
      run: |
        pytest tests/e2e/ -v --maxfail=1
    
    - name: Stop application
      if: always()
      run: |
        pkill -f "python main.py" || true

  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pip install locust
    
    - name: Start application
      run: |
        python main.py &
        sleep 10
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v -m "not slow"
    
    - name: Run Locust tests
      run: |
        locust -f tests/performance/locustfile.py \
               --host=http://localhost:8000 \
               --users 10 --spawn-rate 2 --run-time 2m --headless
```

---

## 测试最佳实践

### 1. 测试命名规范

```python
# 好的测试命名
def test_create_task_with_valid_data_should_return_task_id():
    pass

def test_execute_task_when_mcp_server_unavailable_should_retry():
    pass

def test_validate_task_request_with_invalid_url_should_raise_validation_error():
    pass

# 避免的测试命名
def test_task():  # 太模糊
    pass

def test_1():  # 无意义
    pass
```

### 2. 测试组织

```python
class TestTaskCreation:
    """任务创建相关测试"""
    
    def test_create_task_success(self):
        """测试成功创建任务"""
        pass
    
    def test_create_task_invalid_data(self):
        """测试无效数据创建任务"""
        pass
    
    def test_create_task_policy_rejection(self):
        """测试策略拒绝创建任务"""
        pass

class TestTaskExecution:
    """任务执行相关测试"""
    
    def test_execute_task_success(self):
        """测试成功执行任务"""
        pass
    
    def test_execute_task_timeout(self):
        """测试任务执行超时"""
        pass
```

### 3. 断言最佳实践

```python
# 好的断言
def test_task_creation():
    task = create_task("test_task", "description")
    
    # 具体的断言
    assert task.task_id == "test_task"
    assert task.description == "description"
    assert task.status == TaskStatus.PENDING
    assert task.created_at is not None
    
    # 使用 pytest 的断言助手
    with pytest.raises(ValidationError, match="无效的任务ID"):
        create_task("", "description")

# 避免的断言
def test_task_creation_bad():
    task = create_task("test_task", "description")
    
    # 模糊的断言
    assert task  # 不够具体
    assert task.task_id  # 只检查存在性
    assert len(task.task_id) > 0  # 间接检查
```

### 4. 测试数据管理

```python
# 使用 Fixture 管理测试数据
@pytest.fixture
def valid_task_data():
    return {
        "task_id": "test_task_001",
        "description": "测试任务",
        "target_url": "https://example.com",
        "execution_mode": "AI_MODE"
    }

# 使用参数化减少重复
@pytest.mark.parametrize("execution_mode,expected_strategy", [
    ("AI_MODE", "ai_strategy"),
    ("SCRIPT_MODE", "script_strategy"),
    ("HYBRID_MODE", "hybrid_strategy"),
])
def test_strategy_selection(execution_mode, expected_strategy):
    strategy = select_strategy(execution_mode)
    assert strategy.name == expected_strategy
```

### 5. 异步测试

```python
# 异步测试最佳实践
@pytest.mark.asyncio
async def test_async_operation():
    # 使用 AsyncMock 进行异步模拟
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"data": "value"}
    
    # 测试异步操作
    result = await async_operation(mock_service)
    
    # 验证结果
    assert result["data"] == "value"
    mock_service.fetch_data.assert_called_once()

# 测试异步异常
@pytest.mark.asyncio
async def test_async_exception():
    mock_service = AsyncMock()
    mock_service.fetch_data.side_effect = ConnectionError("连接失败")
    
    with pytest.raises(ConnectionError, match="连接失败"):
        await async_operation(mock_service)
```

---

## 故障排除

### 常见测试问题

#### 1. 测试数据库问题

```bash
# 问题：测试数据库连接失败
# 解决方案：检查数据库配置
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
pytest tests/

# 问题：测试数据残留
# 解决方案：使用事务回滚
@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()  # 回滚事务
```

#### 2. 异步测试问题

```python
# 问题：异步测试运行失败
# 解决方案：正确配置事件循环
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 问题：AsyncMock 不工作
# 解决方案：确保使用正确的 Mock 类型
mock_service = AsyncMock()  # 不是 Mock()
mock_service.async_method.return_value = "result"
```

#### 3. Mock 问题

```python
# 问题：Mock 没有被调用
# 解决方案：检查 patch 路径
# 错误的路径
@patch('requests.get')  # 如果代码中是 from requests import get

# 正确的路径
@patch('src.aura.module.requests.get')  # 根据实际导入路径

# 问题：Mock 配置不生效
# 解决方案：确保在正确的位置配置
mock_obj = Mock()
mock_obj.method.return_value = "value"  # 在调用之前配置
result = mock_obj.method()  # 然后调用
```

#### 4. 覆盖率问题

```bash
# 问题：覆盖率报告不准确
# 解决方案：清理旧的覆盖率数据
coverage erase
pytest --cov=src/aura

# 问题：某些文件未包含在覆盖率中
# 解决方案：检查 .coveragerc 配置
[run]
source = src/aura
omit = 
    */tests/*
    */venv/*
```

### 调试测试

```python
# 使用 pytest 调试选项
pytest --pdb  # 在失败时进入调试器
pytest --pdbcls=IPython.terminal.debugger:Pdb  # 使用 IPython 调试器
pytest -s  # 显示 print 输出
pytest -v  # 详细输出
pytest --tb=long  # 详细的错误回溯

# 在测试中添加调试点
def test_debug_example():
    result = some_function()
    import pdb; pdb.set_trace()  # 调试点
    assert result == expected_value
```

---

> 📖 **相关文档**
> - [开发指南](./development-guide.md)
> - [API参考文档](./api-reference.md)
> - [技术规范](./technical-specifications.md)
> - [部署指南](./deployment-guide.md)

---

## 总结

本测试指南涵盖了 Aura 项目的完整测试策略，包括：

- **测试策略**：遵循测试金字塔，平衡不同类型的测试
- **测试类型**：单元测试、集成测试、端到端测试、性能测试
- **测试工具**：pytest 生态系统和相关工具
- **测试数据**：使用 Factory 和 Fixture 管理测试数据
- **Mock 技术**：有效使用 Mock 和 Stub 进行隔离测试
- **覆盖率**：确保代码质量和测试完整性
- **持续集成**：自动化测试流程
- **最佳实践**：编写可维护、可读的测试代码

通过遵循这些指南，可以确保 Aura 项目的代码质量和系统稳定性。