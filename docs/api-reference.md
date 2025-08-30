# API 参考文档

本文档详细描述了 Aura 系统的核心 API 接口，包括各个模块的接口规范、参数说明和使用示例。

## 目录

- [Orchestrator API](#orchestrator-api)
- [Skill Library API](#skill-library-api)
- [Site Model Registry API](#site-model-registry-api)
- [Action Graph API](#action-graph-api)
- [MCP Manager API](#mcp-manager-api)
- [Policy Engine API](#policy-engine-api)
- [错误处理](#错误处理)
- [认证与授权](#认证与授权)

---

## Orchestrator API

### 任务管理

#### 创建任务

```python
class TaskRequest:
    task_id: str
    description: str
    target_url: str
    execution_mode: ExecutionMode  # AI_MODE, SCRIPT_MODE, HYBRID_MODE
    parameters: Dict[str, Any]
    priority: TaskPriority  # HIGH, MEDIUM, LOW
    timeout: int  # 超时时间（秒）
    retry_count: int  # 重试次数
    callback_url: Optional[str]  # 回调URL

class TaskResult:
    task_id: str
    status: TaskStatus  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    result: Dict[str, Any]
    execution_time: float
    error_message: Optional[str]
    action_graph: Optional[ActionGraph]
    screenshots: List[str]  # 截图路径列表
    logs: List[LogEntry]
```

#### API 端点

```python
# 创建任务
POST /api/v1/tasks
Content-Type: application/json

{
    "description": "登录网站并获取用户信息",
    "target_url": "https://example.com/login",
    "execution_mode": "HYBRID_MODE",
    "parameters": {
        "username": "user@example.com",
        "password": "password123"
    },
    "priority": "HIGH",
    "timeout": 300,
    "retry_count": 3
}

# 响应
{
    "task_id": "task_12345",
    "status": "PENDING",
    "created_at": "2024-01-15T10:30:00Z"
}
```

#### 查询任务状态

```python
# 获取任务状态
GET /api/v1/tasks/{task_id}

# 响应
{
    "task_id": "task_12345",
    "status": "COMPLETED",
    "result": {
        "user_info": {
            "name": "John Doe",
            "email": "john@example.com"
        }
    },
    "execution_time": 45.2,
    "action_graph": {...},
    "screenshots": ["/logs/task_12345/screenshot_1.png"]
}
```

#### 取消任务

```python
# 取消任务
DELETE /api/v1/tasks/{task_id}

# 响应
{
    "task_id": "task_12345",
    "status": "CANCELLED",
    "cancelled_at": "2024-01-15T10:35:00Z"
}
```

### 批量操作

```python
# 批量创建任务
POST /api/v1/tasks/batch

{
    "tasks": [
        {
            "description": "任务1",
            "target_url": "https://site1.com",
            "execution_mode": "AI_MODE"
        },
        {
            "description": "任务2",
            "target_url": "https://site2.com",
            "execution_mode": "SCRIPT_MODE"
        }
    ]
}

# 响应
{
    "batch_id": "batch_67890",
    "tasks": [
        {"task_id": "task_12345", "status": "PENDING"},
        {"task_id": "task_12346", "status": "PENDING"}
    ]
}
```

---

## Skill Library API

### 技能包管理

#### 技能包结构

```python
class SkillManifest:
    name: str
    version: str
    description: str
    author: str
    tags: List[str]
    parameters: Dict[str, ParameterSchema]
    assertions: List[AssertionRule]
    dependencies: List[str]
    compatibility: Dict[str, str]  # 兼容性要求

class ParameterSchema:
    name: str
    type: str  # string, number, boolean, object, array
    required: bool
    default: Any
    description: str
    validation: Dict[str, Any]  # 验证规则

class AssertionRule:
    name: str
    condition: str  # 断言条件
    error_message: str
    severity: str  # ERROR, WARNING, INFO
```

#### API 端点

```python
# 获取技能包列表
GET /api/v1/skills

# 查询参数
?category=web_automation&tags=login,form&page=1&limit=20

# 响应
{
    "skills": [
        {
            "name": "web_login",
            "version": "1.2.0",
            "description": "通用网站登录技能包",
            "author": "Aura Team",
            "tags": ["login", "authentication"],
            "rating": 4.8,
            "downloads": 1250
        }
    ],
    "total": 45,
    "page": 1,
    "limit": 20
}
```

#### 安装技能包

```python
# 安装技能包
POST /api/v1/skills/install

{
    "name": "web_login",
    "version": "1.2.0",
    "source": "registry"  # registry, git, local
}

# 响应
{
    "name": "web_login",
    "version": "1.2.0",
    "status": "installed",
    "installed_at": "2024-01-15T10:30:00Z"
}
```

#### 执行技能包

```python
# 执行技能包
POST /api/v1/skills/{skill_name}/execute

{
    "parameters": {
        "url": "https://example.com/login",
        "username": "user@example.com",
        "password": "password123",
        "remember_me": true
    },
    "context": {
        "session_id": "session_123",
        "user_agent": "custom_agent"
    }
}

# 响应
{
    "execution_id": "exec_789",
    "status": "COMPLETED",
    "result": {
        "success": true,
        "login_token": "token_abc123",
        "user_profile": {...}
    },
    "assertions": [
        {
            "name": "login_success",
            "status": "PASSED",
            "message": "登录成功验证通过"
        }
    ]
}
```

---

## Site Model Registry API

### 网站模型管理

#### 模型结构

```python
class SiteModel:
    site_id: str
    domain: str
    version: str
    elements: Dict[str, ElementModel]
    workflows: Dict[str, WorkflowModel]
    metadata: SiteMetadata
    created_at: datetime
    updated_at: datetime

class ElementModel:
    element_id: str
    semantic_locator: str  # 语义定位符
    css_selectors: List[str]  # CSS选择器列表
    xpath: str
    attributes: Dict[str, str]
    element_type: str  # button, input, link, etc.
    confidence: float  # 置信度
    last_verified: datetime

class WorkflowModel:
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    success_rate: float
    avg_execution_time: float
```

#### API 端点

```python
# 获取网站模型
GET /api/v1/sites/{domain}/model

# 响应
{
    "site_id": "example_com_v1_2",
    "domain": "example.com",
    "version": "1.2",
    "elements": {
        "login_button": {
            "semantic_locator": "button[role=login]",
            "css_selectors": [
                "#login-btn",
                ".login-button",
                "button[type=submit]"
            ],
            "element_type": "button",
            "confidence": 0.95
        }
    },
    "workflows": {
        "user_login": {
            "name": "用户登录流程",
            "success_rate": 0.98,
            "steps": [...]
        }
    }
}
```

#### 更新网站模型

```python
# 更新网站模型
PUT /api/v1/sites/{domain}/model

{
    "elements": {
        "new_element": {
            "semantic_locator": "input[role=search]",
            "css_selectors": ["#search-input"],
            "element_type": "input"
        }
    },
    "update_type": "incremental"  # full, incremental
}

# 响应
{
    "site_id": "example_com_v1_3",
    "version": "1.3",
    "updated_elements": ["new_element"],
    "updated_at": "2024-01-15T10:30:00Z"
}
```

---

## Action Graph API

### 动作图管理

#### 动作图结构

```python
class ActionGraph:
    graph_id: str
    nodes: List[ActionNode]
    edges: List[ActionEdge]
    metadata: GraphMetadata

class ActionNode:
    node_id: str
    node_type: NodeType  # ACTION, CONDITION, LOOP, PARALLEL
    action: Action
    status: NodeStatus  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    dependencies: List[str]  # 依赖的节点ID
    retry_config: RetryConfig

class Action:
    action_type: str  # click, type, wait, navigate, etc.
    target: str  # 目标元素
    parameters: Dict[str, Any]
    timeout: int
    assertions: List[AssertionRule]
```

#### API 端点

```python
# 创建动作图
POST /api/v1/action-graphs

{
    "nodes": [
        {
            "node_id": "node_1",
            "node_type": "ACTION",
            "action": {
                "action_type": "navigate",
                "target": "https://example.com",
                "parameters": {"wait_for": "load"}
            }
        },
        {
            "node_id": "node_2",
            "node_type": "ACTION",
            "action": {
                "action_type": "click",
                "target": "#login-button",
                "parameters": {}
            },
            "dependencies": ["node_1"]
        }
    ],
    "edges": [
        {
            "from": "node_1",
            "to": "node_2",
            "condition": "success"
        }
    ]
}

# 响应
{
    "graph_id": "graph_123",
    "status": "CREATED",
    "created_at": "2024-01-15T10:30:00Z"
}
```

#### 执行动作图

```python
# 执行动作图
POST /api/v1/action-graphs/{graph_id}/execute

{
    "context": {
        "session_id": "session_123",
        "variables": {
            "username": "user@example.com",
            "password": "password123"
        }
    },
    "execution_options": {
        "parallel_execution": true,
        "fail_fast": false,
        "screenshot_on_error": true
    }
}

# 响应
{
    "execution_id": "exec_456",
    "graph_id": "graph_123",
    "status": "RUNNING",
    "started_at": "2024-01-15T10:30:00Z"
}
```

---

## MCP Manager API

### MCP 连接管理

#### 连接配置

```python
class MCPServerConfig:
    name: str
    type: str  # playwright, filesystem, search, memory
    connection_params: Dict[str, Any]
    health_check_interval: int
    retry_config: RetryConfig
    circuit_breaker_config: CircuitBreakerConfig

class ConnectionState:
    server_name: str
    status: str  # CONNECTED, DISCONNECTED, RECONNECTING, ERROR
    last_heartbeat: datetime
    error_count: int
    last_error: Optional[str]
```

#### API 端点

```python
# 获取MCP服务器状态
GET /api/v1/mcp/servers

# 响应
{
    "servers": [
        {
            "name": "playwright",
            "type": "playwright",
            "status": "CONNECTED",
            "last_heartbeat": "2024-01-15T10:29:45Z",
            "error_count": 0,
            "uptime": 3600
        },
        {
            "name": "filesystem",
            "type": "filesystem",
            "status": "DISCONNECTED",
            "last_error": "Connection timeout",
            "error_count": 3
        }
    ]
}
```

#### 执行MCP命令

```python
# 执行MCP命令
POST /api/v1/mcp/execute

{
    "server_name": "playwright",
    "command": "browser_click",
    "parameters": {
        "element": "登录按钮",
        "ref": "#login-btn"
    },
    "timeout": 30
}

# 响应
{
    "execution_id": "mcp_exec_789",
    "server_name": "playwright",
    "command": "browser_click",
    "status": "COMPLETED",
    "result": {
        "success": true,
        "message": "点击成功"
    },
    "execution_time": 1.2
}
```

---

## Policy Engine API

### 策略管理

#### 策略规则

```python
class PolicyRule:
    rule_id: str
    name: str
    description: str
    conditions: List[PolicyCondition]
    actions: List[PolicyAction]
    priority: int
    enabled: bool

class PolicyCondition:
    field: str  # action_type, target_domain, user_role, etc.
    operator: str  # equals, contains, matches, etc.
    value: Any
    logic: str  # AND, OR, NOT

class PolicyAction:
    action_type: str  # ALLOW, DENY, REQUIRE_APPROVAL, LOG
    parameters: Dict[str, Any]
```

#### API 端点

```python
# 策略评估
POST /api/v1/policy/evaluate

{
    "action": {
        "action_type": "form_submit",
        "target_domain": "banking.example.com",
        "parameters": {
            "form_data": {
                "amount": 10000,
                "account": "123456789"
            }
        }
    },
    "context": {
        "user_id": "user_123",
        "session_id": "session_456",
        "ip_address": "192.168.1.100"
    }
}

# 响应
{
    "decision": "REQUIRE_APPROVAL",
    "matched_rules": [
        {
            "rule_id": "high_value_transaction",
            "name": "高额交易审批",
            "reason": "交易金额超过审批阈值"
        }
    ],
    "required_approvals": [
        {
            "approval_type": "MANAGER_APPROVAL",
            "approver_role": "manager",
            "timeout": 3600
        }
    ]
}
```

---

## 错误处理

### 错误响应格式

```python
{
    "error": {
        "code": "TASK_EXECUTION_FAILED",
        "message": "任务执行失败",
        "details": {
            "task_id": "task_123",
            "step": "element_click",
            "element": "#submit-button",
            "reason": "元素未找到"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req_789"
    }
}
```

### 错误代码

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `FORBIDDEN` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源未找到 |
| `TASK_TIMEOUT` | 408 | 任务执行超时 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

---

## 认证与授权

### API 密钥认证

```http
GET /api/v1/tasks
Authorization: Bearer your_api_key_here
Content-Type: application/json
```

### JWT 令牌认证

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "password123"
}

# 响应
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "token_type": "Bearer"
}
```

### 权限范围

| 权限范围 | 描述 |
|---------|------|
| `tasks:read` | 读取任务信息 |
| `tasks:write` | 创建和修改任务 |
| `tasks:execute` | 执行任务 |
| `skills:read` | 读取技能包信息 |
| `skills:install` | 安装技能包 |
| `admin:all` | 管理员权限 |

---

## 速率限制

| 端点类型 | 限制 | 时间窗口 |
|---------|------|----------|
| 任务创建 | 100次 | 1小时 |
| 任务查询 | 1000次 | 1小时 |
| 技能包执行 | 50次 | 1小时 |
| 管理接口 | 20次 | 1小时 |

---

## SDK 和客户端库

### Python SDK

```python
from aura_client import AuraClient

client = AuraClient(
    base_url="https://api.aura.example.com",
    api_key="your_api_key"
)

# 创建任务
task = client.tasks.create(
    description="登录并获取数据",
    target_url="https://example.com",
    execution_mode="HYBRID_MODE",
    parameters={"username": "user", "password": "pass"}
)

# 等待任务完成
result = client.tasks.wait_for_completion(task.task_id)
print(result.result)
```

### JavaScript SDK

```javascript
import { AuraClient } from '@aura/client';

const client = new AuraClient({
    baseUrl: 'https://api.aura.example.com',
    apiKey: 'your_api_key'
});

// 创建任务
const task = await client.tasks.create({
    description: '登录并获取数据',
    targetUrl: 'https://example.com',
    executionMode: 'HYBRID_MODE',
    parameters: { username: 'user', password: 'pass' }
});

// 监听任务状态
const result = await client.tasks.waitForCompletion(task.taskId);
console.log(result.result);
```

---

> 📖 **相关文档**
> - [系统概览](./system-overview.md)
> - [架构决策记录](./architecture-decisions.md)
> - [开发指南](./development-guide.md)
> - [技术规范](./technical-specifications.md)