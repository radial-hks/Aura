# 开发指南

本文档为 Aura 项目的开发者提供详细的开发指南，包括环境搭建、开发流程、调试技巧和最佳实践。

## 目录

- [快速开始](#快速开始)
- [开发环境搭建](#开发环境搭建)
- [项目结构](#项目结构)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [调试技巧](#调试技巧)
- [性能优化](#性能优化)
- [故障排除](#故障排除)
- [贡献指南](#贡献指南)

---

## 快速开始

### 前置要求

- Python 3.9+
- Node.js 16+ (用于前端开发)
- Git
- Docker (可选，用于容器化部署)
- Redis (用于缓存和消息队列)
- PostgreSQL (生产环境推荐)

### 一键启动

```bash
# 克隆项目
git clone https://github.com/your-org/aura.git
cd aura

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py

# 启动开发服务器
python main.py --dev
```

### Docker 快速启动

```bash
# 使用 Docker Compose 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f aura-api
```

---

## 开发环境搭建

### 1. Python 环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 2. 数据库设置

#### SQLite (开发环境)

```bash
# 创建数据库
python -c "from src.aura.models.database import create_tables; create_tables()"
```

#### PostgreSQL (生产环境)

```bash
# 安装 PostgreSQL
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE aura_db;
CREATE USER aura_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aura_db TO aura_user;
\q

# 运行迁移
alembic upgrade head
```

### 3. Redis 设置

```bash
# 安装 Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# 启动 Redis
redis-server

# 测试连接
redis-cli ping
```

### 4. MCP 服务器设置

```bash
# 安装 Playwright MCP 服务器
npm install -g @modelcontextprotocol/server-playwright

# 安装浏览器
playwright install

# 测试 MCP 连接
python scripts/test_mcp_connection.py
```

### 5. 环境变量配置

创建 `.env` 文件：

```bash
# 应用配置
APP_NAME=Aura
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=postgresql://aura_user:your_password@localhost:5432/aura_db
# 或使用 SQLite (开发环境)
# DATABASE_URL=sqlite:///./aura.db

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-encryption-key

# MCP 配置
MCP_SERVERS_CONFIG_PATH=./config/mcp_servers.json

# 外部服务
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# 文件存储
FILE_STORAGE_PATH=./storage
MAX_FILE_SIZE=10485760  # 10MB

# 任务配置
MAX_CONCURRENT_TASKS=10
TASK_TIMEOUT=300
MAX_RETRY_COUNT=3

# 限流配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=3600
```

---

## 项目结构

```
aura/
├── .env                        # 环境变量
├── .gitignore                  # Git 忽略文件
├── .pre-commit-config.yaml     # 预提交钩子
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # Docker 镜像
├── main.py                     # 应用入口
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── pyproject.toml             # 项目配置
├── alembic.ini                # 数据库迁移配置
├── pytest.ini                # 测试配置
├── config/                    # 配置文件
│   ├── mcp_servers.json       # MCP 服务器配置
│   ├── logging.yaml           # 日志配置
│   └── skills/                # 技能包配置
├── docs/                      # 文档
│   ├── system-overview.md     # 系统概览
│   ├── architecture-decisions.md # 架构决策
│   ├── api-reference.md       # API 参考
│   ├── technical-specifications.md # 技术规范
│   ├── development-guide.md   # 开发指南
│   └── deployment-guide.md    # 部署指南
├── src/                       # 源代码
│   └── aura/
│       ├── __init__.py
│       ├── core/              # 核心模块
│       │   ├── orchestrator.py
│       │   ├── action_graph.py
│       │   └── exceptions.py
│       ├── skills/            # 技能包模块
│       ├── sites/             # 网站模型模块
│       ├── mcp/               # MCP 模块
│       ├── policy/            # 策略引擎
│       ├── api/               # API 模块
│       ├── utils/             # 工具模块
│       └── models/            # 数据模型
├── tests/                     # 测试代码
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── e2e/                   # 端到端测试
│   └── fixtures/              # 测试数据
├── scripts/                   # 脚本工具
│   ├── init_db.py            # 数据库初始化
│   ├── migrate.py            # 数据迁移
│   └── test_mcp_connection.py # MCP 连接测试
├── logs/                      # 日志文件
├── storage/                   # 文件存储
└── examples/                  # 示例代码
    ├── basic_usage.py
    ├── skill_development.py
    └── api_client.py
```

---

## 开发流程

### 1. 功能开发流程

```mermaid
flowchart TD
    A[创建功能分支] --> B[编写代码]
    B --> C[编写测试]
    C --> D[运行测试]
    D --> E{测试通过?}
    E -->|否| B
    E -->|是| F[代码审查]
    F --> G[合并到主分支]
    G --> H[部署到测试环境]
    H --> I[验收测试]
    I --> J[部署到生产环境]
```

### 2. Git 工作流

```bash
# 1. 创建功能分支
git checkout -b feature/new-skill-system

# 2. 开发过程中定期提交
git add .
git commit -m "feat: add skill validation logic"

# 3. 推送到远程分支
git push origin feature/new-skill-system

# 4. 创建 Pull Request
# 在 GitHub/GitLab 上创建 PR

# 5. 代码审查通过后合并
git checkout main
git pull origin main
git branch -d feature/new-skill-system
```

### 3. 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**类型说明：**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例：**
```bash
git commit -m "feat(orchestrator): add task priority queue"
git commit -m "fix(mcp): handle connection timeout gracefully"
git commit -m "docs: update API documentation"
```

---

## 代码规范

### 1. Python 代码规范

使用以下工具确保代码质量：

```bash
# 安装代码质量工具
pip install black isort flake8 mypy pre-commit

# 代码格式化
black src/ tests/

# 导入排序
isort src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

### 2. 预提交钩子

创建 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.9
  
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
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

安装预提交钩子：

```bash
pre-commit install
```

### 3. 代码审查清单

- [ ] 代码符合项目编码规范
- [ ] 包含适当的类型注解
- [ ] 有完整的文档字符串
- [ ] 包含相应的单元测试
- [ ] 测试覆盖率达到要求
- [ ] 没有安全漏洞
- [ ] 性能影响可接受
- [ ] 向后兼容性考虑
- [ ] 错误处理完善
- [ ] 日志记录适当

---

## 测试指南

### 1. 测试结构

```
tests/
├── unit/                      # 单元测试
│   ├── test_orchestrator.py   # 编排器测试
│   ├── test_action_graph.py   # 动作图测试
│   ├── test_skill_library.py  # 技能库测试
│   └── test_mcp_manager.py    # MCP 管理器测试
├── integration/               # 集成测试
│   ├── test_api_endpoints.py  # API 端点测试
│   ├── test_database.py       # 数据库测试
│   └── test_mcp_integration.py # MCP 集成测试
├── e2e/                       # 端到端测试
│   ├── test_user_workflows.py # 用户工作流测试
│   └── test_skill_execution.py # 技能执行测试
├── performance/               # 性能测试
│   ├── test_load.py          # 负载测试
│   └── test_stress.py        # 压力测试
├── fixtures/                  # 测试数据
│   ├── sample_tasks.json     # 示例任务
│   ├── sample_skills.json    # 示例技能
│   └── sample_sites.json     # 示例网站模型
└── conftest.py               # pytest 配置
```

### 2. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_orchestrator.py

# 运行特定测试函数
pytest tests/unit/test_orchestrator.py::test_create_task

# 运行测试并生成覆盖率报告
pytest --cov=src/aura --cov-report=html

# 运行测试并显示详细输出
pytest -v

# 运行测试并在第一个失败时停止
pytest -x

# 运行标记的测试
pytest -m "not slow"
```

### 3. 测试配置

`pytest.ini` 配置：

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
    --cov-fail-under=80
testpaths = tests
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
    unit: marks tests as unit tests
```

### 4. 测试示例

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.aura.core.orchestrator import Orchestrator, TaskRequest
from src.aura.core.exceptions import TaskExecutionError

class TestOrchestrator:
    """编排器测试类"""
    
    @pytest.fixture
    async def orchestrator(self):
        """创建编排器实例"""
        # 创建模拟依赖
        skill_library = Mock()
        site_registry = Mock()
        action_engine = Mock()
        policy_engine = Mock()
        mcp_manager = Mock()
        
        orchestrator = Orchestrator(
            skill_library=skill_library,
            site_registry=site_registry,
            action_engine=action_engine,
            policy_engine=policy_engine,
            mcp_manager=mcp_manager
        )
        
        yield orchestrator
        
        # 清理资源
        await orchestrator.cleanup()
    
    @pytest.fixture
    def sample_task_request(self):
        """示例任务请求"""
        return TaskRequest(
            task_id="test_task_123",
            description="测试任务",
            target_url="https://example.com",
            execution_mode="AI_MODE",
            parameters={"username": "test", "password": "test123"}
        )
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, orchestrator, sample_task_request):
        """测试成功创建任务"""
        # 模拟策略检查通过
        orchestrator.policy_engine.evaluate = AsyncMock(
            return_value=Mock(allowed=True)
        )
        
        # 执行测试
        task_id = await orchestrator.create_task(sample_task_request)
        
        # 验证结果
        assert task_id == "test_task_123"
        assert sample_task_request.task_id in orchestrator._tasks
        orchestrator.policy_engine.evaluate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_with_retry(self, orchestrator, sample_task_request):
        """测试任务执行重试机制"""
        # 模拟前两次执行失败，第三次成功
        call_count = 0
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TaskExecutionError("临时错误")
            return {"success": True, "result": "执行成功"}
        
        orchestrator._execute_task_internal = mock_execute
        
        # 执行测试
        result = await orchestrator.execute_task(sample_task_request.task_id)
        
        # 验证结果
        assert result.status == "COMPLETED"
        assert result.result["success"] is True
        assert call_count == 3  # 验证重试了3次
    
    @pytest.mark.integration
    async def test_full_task_workflow(self, orchestrator, sample_task_request):
        """集成测试：完整任务工作流"""
        # 这是一个集成测试，测试完整的任务执行流程
        with patch('src.aura.mcp.manager.MCPManager') as mock_mcp:
            # 配置 MCP 管理器模拟
            mock_mcp.return_value.execute_command = AsyncMock(
                return_value={"success": True, "data": "模拟结果"}
            )
            
            # 执行完整流程
            task_id = await orchestrator.create_task(sample_task_request)
            result = await orchestrator.execute_task(task_id)
            
            # 验证结果
            assert result.status == "COMPLETED"
            assert "data" in result.result

# 性能测试示例
class TestPerformance:
    """性能测试类"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """测试并发任务执行性能"""
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        # 创建多个任务
        tasks = []
        for i in range(50):
            task = TaskRequest(
                task_id=f"perf_task_{i}",
                description=f"性能测试任务 {i}",
                target_url="https://httpbin.org/delay/1",
                execution_mode="SCRIPT_MODE",
                parameters={}
            )
            tasks.append(task)
        
        # 测试并发执行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._execute_task, task) for task in tasks]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证性能要求
        assert len(results) == 50
        assert execution_time < 30  # 50个任务应在30秒内完成
        
        # 计算吞吐量
        throughput = len(results) / execution_time
        assert throughput > 1.5  # 吞吐量应大于1.5 tasks/second
    
    def _execute_task(self, task):
        """模拟任务执行"""
        import time
        time.sleep(0.5)  # 模拟任务执行时间
        return {"task_id": task.task_id, "status": "completed"}
```

---

## 调试技巧

### 1. 日志调试

```python
import structlog

# 配置结构化日志
logger = structlog.get_logger(__name__)

# 在代码中添加调试日志
logger.debug("开始执行任务", task_id=task_id, parameters=parameters)
logger.info("任务执行完成", task_id=task_id, execution_time=execution_time)
logger.error("任务执行失败", task_id=task_id, error=str(e))
```

### 2. 断点调试

```python
# 使用 pdb 进行调试
import pdb; pdb.set_trace()

# 或使用 ipdb (更友好的界面)
import ipdb; ipdb.set_trace()

# 在 pytest 中使用断点
pytest --pdb  # 在测试失败时进入调试器
pytest --pdbcls=IPython.terminal.debugger:Pdb  # 使用 IPython 调试器
```

### 3. 远程调试

```python
# 使用 debugpy 进行远程调试
import debugpy

# 启动调试服务器
debugpy.listen(("0.0.0.0", 5678))
print("等待调试器连接...")
debugpy.wait_for_client()
```

### 4. 性能分析

```python
# 使用 cProfile 进行性能分析
import cProfile
import pstats

def profile_function():
    # 你的代码
    pass

# 运行性能分析
cProfile.run('profile_function()', 'profile_stats')

# 查看结果
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### 5. 内存分析

```python
# 使用 memory_profiler 进行内存分析
from memory_profiler import profile

@profile
def memory_intensive_function():
    # 你的代码
    pass

# 运行分析
# python -m memory_profiler your_script.py
```

---

## 性能优化

### 1. 数据库优化

```python
# 使用连接池
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# 使用索引
class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(UUID, primary_key=True)
    status = Column(String(20), index=True)  # 添加索引
    created_at = Column(DateTime, index=True)  # 添加索引
    
    # 复合索引
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
    )

# 使用批量操作
async def bulk_insert_tasks(tasks: List[Task]):
    async with async_session() as session:
        session.add_all(tasks)
        await session.commit()
```

### 2. 缓存优化

```python
from functools import lru_cache
from cachetools import TTLCache
import asyncio

# 使用 LRU 缓存
@lru_cache(maxsize=1000)
def get_site_model(domain: str):
    # 获取网站模型的逻辑
    pass

# 使用 TTL 缓存
cache = TTLCache(maxsize=1000, ttl=300)  # 5分钟过期

# 异步缓存装饰器
def async_cache(ttl=300):
    cache = {}
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = await func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator

@async_cache(ttl=600)
async def get_expensive_data(param):
    # 耗时操作
    await asyncio.sleep(1)
    return f"result for {param}"
```

### 3. 异步优化

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 使用异步上下文管理器
class AsyncResourceManager:
    async def __aenter__(self):
        self.resource = await acquire_resource()
        return self.resource
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await release_resource(self.resource)

# 并发执行
async def process_tasks_concurrently(tasks):
    semaphore = asyncio.Semaphore(10)  # 限制并发数
    
    async def process_with_semaphore(task):
        async with semaphore:
            return await process_task(task)
    
    results = await asyncio.gather(
        *[process_with_semaphore(task) for task in tasks],
        return_exceptions=True
    )
    return results

# CPU 密集型任务使用线程池
executor = ThreadPoolExecutor(max_workers=4)

async def cpu_intensive_task(data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_data, data)
    return result
```

---

## 故障排除

### 1. 常见问题

#### 数据库连接问题

```bash
# 检查数据库连接
psql -h localhost -U aura_user -d aura_db

# 检查连接池状态
SELECT * FROM pg_stat_activity WHERE datname = 'aura_db';
```

#### Redis 连接问题

```bash
# 检查 Redis 状态
redis-cli ping

# 查看 Redis 信息
redis-cli info

# 监控 Redis 命令
redis-cli monitor
```

#### MCP 连接问题

```python
# 测试 MCP 连接
python scripts/test_mcp_connection.py

# 检查 MCP 服务器状态
curl -X GET http://localhost:8000/api/v1/mcp/servers
```

### 2. 日志分析

```bash
# 查看应用日志
tail -f logs/aura.log

# 过滤错误日志
grep "ERROR" logs/aura.log

# 分析访问日志
awk '{print $1}' logs/access.log | sort | uniq -c | sort -nr
```

### 3. 性能监控

```python
# 添加性能监控中间件
from time import time
from starlette.middleware.base import BaseHTTPMiddleware

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time()
        response = await call_next(request)
        process_time = time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        
        # 记录慢请求
        if process_time > 1.0:
            logger.warning(
                "慢请求检测",
                path=request.url.path,
                method=request.method,
                process_time=process_time
            )
        
        return response
```

### 4. 健康检查

```python
# 健康检查端点
from fastapi import APIRouter, HTTPException

health_router = APIRouter()

@health_router.get("/health")
async def health_check():
    """系统健康检查"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "mcp_servers": await check_mcp_servers(),
        "disk_space": check_disk_space(),
        "memory": check_memory_usage()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }

async def check_database():
    """检查数据库连接"""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def check_redis():
    """检查 Redis 连接"""
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        return True
    except Exception:
        return False
```

---

## 贡献指南

### 1. 贡献流程

1. **Fork 项目**：在 GitHub 上 fork 项目到你的账户
2. **创建分支**：`git checkout -b feature/your-feature-name`
3. **开发功能**：按照代码规范开发新功能
4. **编写测试**：为新功能编写相应的测试
5. **运行测试**：确保所有测试通过
6. **提交代码**：使用规范的提交信息
7. **创建 PR**：在 GitHub 上创建 Pull Request
8. **代码审查**：等待维护者审查代码
9. **合并代码**：审查通过后合并到主分支

### 2. 代码贡献要求

- [ ] 遵循项目编码规范
- [ ] 包含完整的类型注解
- [ ] 有详细的文档字符串
- [ ] 包含相应的单元测试
- [ ] 测试覆盖率不低于 80%
- [ ] 通过所有 CI 检查
- [ ] 更新相关文档

### 3. 文档贡献

- 修复文档中的错误
- 添加缺失的文档
- 改进文档的可读性
- 翻译文档到其他语言
- 添加使用示例

### 4. Bug 报告

使用以下模板报告 Bug：

```markdown
## Bug 描述
简要描述遇到的问题

## 复现步骤
1. 执行步骤 1
2. 执行步骤 2
3. 看到错误

## 期望行为
描述你期望发生的行为

## 实际行为
描述实际发生的行为

## 环境信息
- OS: [e.g. Ubuntu 20.04]
- Python: [e.g. 3.9.7]
- Aura: [e.g. 1.0.0]

## 附加信息
添加任何其他有助于解决问题的信息
```

### 5. 功能请求

使用以下模板请求新功能：

```markdown
## 功能描述
简要描述你希望添加的功能

## 使用场景
描述这个功能的使用场景和价值

## 详细设计
如果有的话，描述功能的详细设计

## 替代方案
描述你考虑过的其他解决方案

## 附加信息
添加任何其他相关信息
```

---

## 开发工具推荐

### 1. IDE 配置

#### VS Code

推荐插件：
- Python
- Pylance
- Python Docstring Generator
- GitLens
- Docker
- REST Client

配置文件 `.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

#### PyCharm

配置要点：
- 设置 Python 解释器为虚拟环境
- 配置代码格式化工具（Black）
- 启用类型检查（MyPy）
- 配置测试运行器（pytest）

### 2. 命令行工具

```bash
# 安装有用的命令行工具
pip install rich  # 美化终端输出
pip install httpie  # HTTP 客户端
pip install jq  # JSON 处理

# 使用 rich 美化输出
python -m rich.console "Hello, [bold red]World[/bold red]!"

# 使用 httpie 测试 API
http GET localhost:8000/api/v1/tasks Authorization:"Bearer token"

# 使用 jq 处理 JSON
curl -s localhost:8000/api/v1/tasks | jq '.data[] | .task_id'
```

### 3. 数据库工具

- **pgAdmin**: PostgreSQL 管理工具
- **Redis Desktop Manager**: Redis 可视化工具
- **DBeaver**: 通用数据库工具

---

> 📖 **相关文档**
> - [系统概览](./system-overview.md)
> - [API参考文档](./api-reference.md)
> - [技术规范](./technical-specifications.md)
> - [部署指南](./deployment-guide.md)

---

## 获取帮助

如果在开发过程中遇到问题，可以通过以下方式获取帮助：

- 📖 查看项目文档
- 🐛 在 GitHub 上创建 Issue
- 💬 加入开发者讨论群
- 📧 发送邮件到 dev@aura-project.com
- 🔍 搜索已有的 Issue 和 PR

记住，好的问题描述能帮助你更快地得到帮助！