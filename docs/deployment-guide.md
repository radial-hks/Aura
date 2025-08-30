# Aura 部署指南

本文档提供了 Aura 系统的完整部署指南，包括开发环境、测试环境和生产环境的部署方案。

---

## 目录

- [系统要求](#系统要求)
- [环境配置](#环境配置)
- [开发环境部署](#开发环境部署)
- [测试环境部署](#测试环境部署)
- [生产环境部署](#生产环境部署)
- [容器化部署](#容器化部署)
- [云平台部署](#云平台部署)
- [监控和日志](#监控和日志)
- [备份和恢复](#备份和恢复)
- [安全配置](#安全配置)
- [性能优化](#性能优化)
- [故障排除](#故障排除)

---

## 系统要求

### 最低系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | Ubuntu 20.04+ / CentOS 8+ / Windows 10+ | Ubuntu 22.04 LTS |
| **Python** | 3.9+ | 3.11+ |
| **内存** | 4GB | 8GB+ |
| **CPU** | 2 核心 | 4 核心+ |
| **存储** | 20GB | 100GB+ SSD |
| **网络** | 100Mbps | 1Gbps |

### 依赖服务

| 服务 | 版本要求 | 用途 |
|------|----------|------|
| **PostgreSQL** | 13+ | 主数据库 |
| **Redis** | 6+ | 缓存和会话存储 |
| **Node.js** | 18+ | Playwright 运行时 |
| **Docker** | 20+ | 容器化部署 |
| **Nginx** | 1.20+ | 反向代理 |

---

## 环境配置

### 环境变量

创建环境配置文件：

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=postgresql://aura_user:password@localhost:5432/aura_dev
REDIS_URL=redis://localhost:6379/0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# MCP 配置
MCP_SERVER_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_RETRY_DELAY=1

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Playwright 配置
PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
PLAYWRIGHT_HEADLESS=true

# 日志配置
LOG_FILE_PATH=./logs/aura.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql://aura_user:secure_password@db-server:5432/aura_prod
REDIS_URL=redis://redis-server:6379/0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# MCP 配置
MCP_SERVER_TIMEOUT=60
MCP_MAX_RETRIES=5
MCP_RETRY_DELAY=2

# 安全配置
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Playwright 配置
PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
PLAYWRIGHT_HEADLESS=true

# 监控配置
MONITORING_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# 日志配置
LOG_FILE_PATH=/var/log/aura/aura.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=10
```

### 配置管理

```python
# src/aura/config/settings.py
from pydantic import BaseSettings, Field
from typing import Optional
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # 数据库配置
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # API 配置
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # MCP 配置
    mcp_server_timeout: int = Field(default=30, env="MCP_SERVER_TIMEOUT")
    mcp_max_retries: int = Field(default=3, env="MCP_MAX_RETRIES")
    mcp_retry_delay: int = Field(default=1, env="MCP_RETRY_DELAY")
    
    # 安全配置
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # Playwright 配置
    playwright_browsers_path: Optional[str] = Field(None, env="PLAYWRIGHT_BROWSERS_PATH")
    playwright_headless: bool = Field(default=True, env="PLAYWRIGHT_HEADLESS")
    
    # 监控配置
    monitoring_enabled: bool = Field(default=False, env="MONITORING_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # 日志配置
    log_file_path: str = Field(default="./logs/aura.log", env="LOG_FILE_PATH")
    log_max_size: str = Field(default="10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def database_config(self) -> dict:
        """数据库连接配置"""
        return {
            "url": self.database_url,
            "echo": self.debug,
            "pool_size": 10 if self.is_production else 5,
            "max_overflow": 20 if self.is_production else 10,
            "pool_timeout": 30,
            "pool_recycle": 3600
        }
    
    @property
    def redis_config(self) -> dict:
        """Redis 连接配置"""
        return {
            "url": self.redis_url,
            "encoding": "utf-8",
            "decode_responses": True,
            "max_connections": 20 if self.is_production else 10,
            "retry_on_timeout": True,
            "socket_timeout": 5
        }

# 全局设置实例
settings = Settings()
```

---

## 开发环境部署

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/your-org/aura.git
cd aura

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 安装 Playwright 浏览器
playwright install

# 5. 配置环境变量
cp .env.example .env.development
# 编辑 .env.development 文件

# 6. 启动依赖服务
docker-compose -f docker-compose.dev.yml up -d

# 7. 运行数据库迁移
alembic upgrade head

# 8. 启动应用
python main.py
```

### Docker Compose 开发环境

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: aura_dev
      POSTGRES_USER: aura_user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aura_user -d aura_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

volumes:
  postgres_data:
  redis_data:
```

### 开发工具配置

```bash
# 安装开发工具
pip install pre-commit
pre-commit install

# 配置 IDE
# VS Code 推荐扩展：
# - Python
# - Pylance
# - Black Formatter
# - isort
# - GitLens
# - Docker
```

---

## 测试环境部署

### 自动化部署脚本

```bash
#!/bin/bash
# scripts/deploy-test.sh

set -e

echo "开始测试环境部署..."

# 环境变量
ENV="test"
APP_DIR="/opt/aura"
SERVICE_USER="aura"
BACKUP_DIR="/opt/aura/backups"

# 创建备份
echo "创建数据库备份..."
mkdir -p $BACKUP_DIR
pg_dump -h localhost -U aura_user aura_test > $BACKUP_DIR/aura_test_$(date +%Y%m%d_%H%M%S).sql

# 停止服务
echo "停止应用服务..."
sudo systemctl stop aura-test

# 更新代码
echo "更新应用代码..."
cd $APP_DIR
git fetch origin
git checkout test
git pull origin test

# 更新依赖
echo "更新 Python 依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 运行数据库迁移
echo "运行数据库迁移..."
alembic upgrade head

# 运行测试
echo "运行测试套件..."
pytest tests/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "测试失败，回滚部署..."
    git checkout HEAD~1
    alembic downgrade -1
    sudo systemctl start aura-test
    exit 1
fi

# 启动服务
echo "启动应用服务..."
sudo systemctl start aura-test
sudo systemctl enable aura-test

# 健康检查
echo "执行健康检查..."
sleep 10
curl -f http://localhost:8001/health || {
    echo "健康检查失败"
    exit 1
}

echo "测试环境部署完成！"
```

### Systemd 服务配置

```ini
# /etc/systemd/system/aura-test.service
[Unit]
Description=Aura Test Environment
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=aura
Group=aura
WorkingDirectory=/opt/aura
Environment=PATH=/opt/aura/venv/bin
EnvironmentFile=/opt/aura/.env.test
ExecStart=/opt/aura/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aura/logs /opt/aura/data

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

---

## 生产环境部署

### 生产环境架构

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/HAProxy]
    end
    
    subgraph "Application Tier"
        APP1[Aura Instance 1]
        APP2[Aura Instance 2]
        APP3[Aura Instance 3]
    end
    
    subgraph "Database Tier"
        PG_MASTER[PostgreSQL Master]
        PG_SLAVE[PostgreSQL Slave]
        REDIS_MASTER[Redis Master]
        REDIS_SLAVE[Redis Slave]
    end
    
    subgraph "Monitoring"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ALERTMANAGER[AlertManager]
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> PG_MASTER
    APP2 --> PG_MASTER
    APP3 --> PG_MASTER
    
    APP1 --> REDIS_MASTER
    APP2 --> REDIS_MASTER
    APP3 --> REDIS_MASTER
    
    PG_MASTER --> PG_SLAVE
    REDIS_MASTER --> REDIS_SLAVE
    
    APP1 --> PROMETHEUS
    APP2 --> PROMETHEUS
    APP3 --> PROMETHEUS
    
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERTMANAGER
```

### Nginx 配置

```nginx
# /etc/nginx/sites-available/aura
upstream aura_backend {
    least_conn;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name aura.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name aura.example.com;
    
    # SSL 配置
    ssl_certificate /etc/ssl/certs/aura.crt;
    ssl_certificate_key /etc/ssl/private/aura.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # 日志配置
    access_log /var/log/nginx/aura_access.log;
    error_log /var/log/nginx/aura_error.log;
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # 主要代理配置
    location / {
        proxy_pass http://aura_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # API 路由
    location /api/ {
        proxy_pass http://aura_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API 特定配置
        proxy_read_timeout 300s;  # API 可能需要更长时间
        client_max_body_size 10M;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://aura_backend;
        access_log off;
    }
    
    # 静态文件
    location /static/ {
        alias /opt/aura/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 监控端点（仅内网访问）
    location /metrics {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        proxy_pass http://aura_backend;
    }
}
```

### 生产部署脚本

```bash
#!/bin/bash
# scripts/deploy-production.sh

set -e

# 配置
APP_NAME="aura"
APP_DIR="/opt/aura"
BACKUP_DIR="/opt/aura/backups"
SERVICE_USER="aura"
GIT_BRANCH="main"
INSTANCES=(8001 8002 8003)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 预检查
precheck() {
    log_info "执行预检查..."
    
    # 检查用户权限
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 检查服务状态
    systemctl is-active --quiet postgresql || {
        log_error "PostgreSQL 服务未运行"
        exit 1
    }
    
    systemctl is-active --quiet redis || {
        log_error "Redis 服务未运行"
        exit 1
    }
    
    # 检查磁盘空间
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $DISK_USAGE -gt 80 ]; then
        log_warn "磁盘使用率超过 80%: ${DISK_USAGE}%"
        read -p "是否继续部署？ (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_info "预检查通过"
}

# 创建备份
backup() {
    log_info "创建数据库备份..."
    
    mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/aura_prod_$(date +%Y%m%d_%H%M%S).sql"
    
    sudo -u postgres pg_dump aura_prod > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        log_info "备份创建成功: $BACKUP_FILE"
    else
        log_error "备份创建失败"
        exit 1
    fi
    
    # 清理旧备份（保留最近 7 天）
    find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
}

# 更新代码
update_code() {
    log_info "更新应用代码..."
    
    cd $APP_DIR
    
    # 保存当前版本
    CURRENT_VERSION=$(git rev-parse HEAD)
    echo $CURRENT_VERSION > .previous_version
    
    # 更新代码
    git fetch origin
    git checkout $GIT_BRANCH
    git pull origin $GIT_BRANCH
    
    NEW_VERSION=$(git rev-parse HEAD)
    
    if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
        log_info "代码已是最新版本"
    else
        log_info "代码更新完成: $CURRENT_VERSION -> $NEW_VERSION"
    fi
}

# 更新依赖
update_dependencies() {
    log_info "更新 Python 依赖..."
    
    cd $APP_DIR
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_info "依赖更新完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    cd $APP_DIR
    source venv/bin/activate
    
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log_info "数据库迁移完成"
    else
        log_error "数据库迁移失败"
        rollback
        exit 1
    fi
}

# 运行测试
run_tests() {
    log_info "运行生产前测试..."
    
    cd $APP_DIR
    source venv/bin/activate
    
    # 运行关键测试
    pytest tests/integration/ tests/api/ -v --tb=short
    
    if [ $? -ne 0 ]; then
        log_error "测试失败，停止部署"
        rollback
        exit 1
    fi
    
    log_info "测试通过"
}

# 滚动部署
rolling_deploy() {
    log_info "开始滚动部署..."
    
    for port in "${INSTANCES[@]}"; do
        log_info "部署实例 $port..."
        
        # 停止实例
        systemctl stop aura@$port
        
        # 等待实例完全停止
        sleep 5
        
        # 启动实例
        systemctl start aura@$port
        
        # 健康检查
        log_info "等待实例 $port 启动..."
        for i in {1..30}; do
            if curl -f http://localhost:$port/health >/dev/null 2>&1; then
                log_info "实例 $port 启动成功"
                break
            fi
            
            if [ $i -eq 30 ]; then
                log_error "实例 $port 启动失败"
                rollback
                exit 1
            fi
            
            sleep 2
        done
        
        # 等待一段时间再部署下一个实例
        sleep 10
    done
    
    log_info "滚动部署完成"
}

# 回滚
rollback() {
    log_warn "开始回滚..."
    
    if [ -f .previous_version ]; then
        PREVIOUS_VERSION=$(cat .previous_version)
        log_info "回滚到版本: $PREVIOUS_VERSION"
        
        cd $APP_DIR
        git checkout $PREVIOUS_VERSION
        
        # 回滚数据库（如果需要）
        # alembic downgrade -1
        
        # 重启所有实例
        for port in "${INSTANCES[@]}"; do
            systemctl restart aura@$port
        done
        
        log_info "回滚完成"
    else
        log_error "无法找到前一个版本信息"
    fi
}

# 部署后验证
post_deploy_verification() {
    log_info "执行部署后验证..."
    
    # 检查所有实例状态
    for port in "${INSTANCES[@]}"; do
        if ! systemctl is-active --quiet aura@$port; then
            log_error "实例 $port 未运行"
            exit 1
        fi
    done
    
    # 检查负载均衡器
    if ! curl -f https://aura.example.com/health >/dev/null 2>&1; then
        log_error "负载均衡器健康检查失败"
        exit 1
    fi
    
    # 检查数据库连接
    cd $APP_DIR
    source venv/bin/activate
    python -c "from src.aura.database import engine; engine.execute('SELECT 1')"
    
    if [ $? -ne 0 ]; then
        log_error "数据库连接检查失败"
        exit 1
    fi
    
    log_info "部署后验证通过"
}

# 主函数
main() {
    log_info "开始生产环境部署..."
    
    precheck
    backup
    update_code
    update_dependencies
    run_migrations
    run_tests
    rolling_deploy
    post_deploy_verification
    
    log_info "生产环境部署完成！"
    
    # 发送通知（可选）
    # curl -X POST -H 'Content-type: application/json' \
    #      --data '{"text":"Aura 生产环境部署完成"}' \
    #      $SLACK_WEBHOOK_URL
}

# 信号处理
trap 'log_error "部署被中断"; rollback; exit 1' INT TERM

# 执行主函数
main "$@"
```

---

## 容器化部署

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -r aura && useradd -r -g aura aura

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install --with-deps chromium

# 复制应用代码
COPY . .

# 设置权限
RUN chown -R aura:aura /app

# 切换到应用用户
USER aura

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py"]
```

### Docker Compose 生产配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  aura-app:
    build:
      context: .
      dockerfile: Dockerfile
    image: aura:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://aura_user:${DB_PASSWORD}@postgres:5432/aura_prod
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - aura-network
    volumes:
      - app-logs:/app/logs
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.aura.rule=Host(`aura.example.com`)"
      - "traefik.http.routers.aura.tls=true"
      - "traefik.http.routers.aura.tls.certresolver=letsencrypt"

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: aura_prod
      POSTGRES_USER: aura_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    networks:
      - aura-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aura_user -d aura_prod"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - aura-network
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      - aura-app
    networks:
      - aura-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M

  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - aura-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - aura-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

networks:
  aura-network:
    driver: overlay
    attachable: true

volumes:
  postgres-data:
  redis-data:
  app-logs:
  nginx-logs:
  prometheus-data:
  grafana-data:
```

### Kubernetes 部署

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aura
  labels:
    name: aura

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aura-config
  namespace: aura
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  MCP_SERVER_TIMEOUT: "60"
  MCP_MAX_RETRIES: "5"
  PLAYWRIGHT_HEADLESS: "true"
  MONITORING_ENABLED: "true"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aura-secrets
  namespace: aura
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
  SECRET_KEY: <base64-encoded-secret-key>
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aura-app
  namespace: aura
  labels:
    app: aura
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aura
  template:
    metadata:
      labels:
        app: aura
    spec:
      containers:
      - name: aura
        image: aura:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: aura-config
        - secretRef:
            name: aura-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: app-logs
          mountPath: /app/logs
      volumes:
      - name: app-logs
        emptyDir: {}
      restartPolicy: Always

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: aura-service
  namespace: aura
  labels:
    app: aura
spec:
  selector:
    app: aura
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aura-ingress
  namespace: aura
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - aura.example.com
    secretName: aura-tls
  rules:
  - host: aura.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aura-service
            port:
              number: 80

---
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aura-hpa
  namespace: aura
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aura-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 云平台部署

### AWS 部署

```yaml
# aws/cloudformation.yml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Aura Application Infrastructure'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues: [development, staging, production]
  
  InstanceType:
    Type: String
    Default: t3.medium
    AllowedValues: [t3.small, t3.medium, t3.large]
  
  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: EC2 Key Pair for SSH access

Resources:
  # VPC
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-vpc'

  # Subnets
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-public-subnet-1'

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-public-subnet-2'

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.3.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-private-subnet-1'

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.4.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-private-subnet-2'

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-igw'

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # Route Tables
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-public-rt'

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  # RDS Database
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for Aura database
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-db-subnet-group'

  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub '${Environment}-aura-db'
      DBInstanceClass: db.t3.micro
      Engine: postgres
      EngineVersion: '13.7'
      MasterUsername: aura_user
      MasterUserPassword: !Ref DBPassword
      AllocatedStorage: 20
      StorageType: gp2
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref DatabaseSecurityGroup
      BackupRetentionPeriod: 7
      MultiAZ: !If [IsProduction, true, false]
      StorageEncrypted: true
      DeletionProtection: !If [IsProduction, true, false]
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-database'

  # ElastiCache Redis
  CacheSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      Description: Subnet group for Aura cache
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

  RedisCache:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheClusterId: !Sub '${Environment}-aura-redis'
      Engine: redis
      CacheNodeType: cache.t3.micro
      NumCacheNodes: 1
      CacheSubnetGroupName: !Ref CacheSubnetGroup
      VpcSecurityGroupIds:
        - !Ref CacheSecurityGroup
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-redis'

  # Application Load Balancer
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub '${Environment}-aura-alb'
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref LoadBalancerSecurityGroup
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-alb'

  # Auto Scaling Group
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub '${Environment}-aura-launch-template'
      LaunchTemplateData:
        ImageId: ami-0c02fb55956c7d316  # Amazon Linux 2
        InstanceType: !Ref InstanceType
        KeyName: !Ref KeyPairName
        SecurityGroupIds:
          - !Ref ApplicationSecurityGroup
        IamInstanceProfile:
          Arn: !GetAtt InstanceProfile.Arn
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y docker git
            service docker start
            usermod -a -G docker ec2-user
            
            # Install Docker Compose
            curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            
            # Clone and deploy application
            cd /opt
            git clone https://github.com/your-org/aura.git
            cd aura
            
            # Set environment variables
            cat > .env.production << EOF
            ENVIRONMENT=production
            DATABASE_URL=postgresql://aura_user:${DBPassword}@${Database.Endpoint.Address}:5432/aura_prod
            REDIS_URL=redis://${RedisCache.RedisEndpoint.Address}:6379/0
            SECRET_KEY=${SecretKey}
            JWT_SECRET_KEY=${JWTSecretKey}
            EOF
            
            # Deploy with Docker Compose
            docker-compose -f docker-compose.prod.yml up -d

  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub '${Environment}-aura-asg'
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      MinSize: 2
      MaxSize: 10
      DesiredCapacity: 3
      VPCZoneIdentifier:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      TargetGroupARNs:
        - !Ref TargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-aura-instance'
          PropagateAtLaunch: true

Conditions:
  IsProduction: !Equals [!Ref Environment, production]

Parameters:
  DBPassword:
    Type: String
    NoEcho: true
    Description: Database password
  
  SecretKey:
    Type: String
    NoEcho: true
    Description: Application secret key
  
  JWTSecretKey:
    Type: String
    NoEcho: true
    Description: JWT secret key

Outputs:
  LoadBalancerDNS:
    Description: DNS name of the load balancer
    Value: !GetAtt ApplicationLoadBalancer.DNSName
    Export:
      Name: !Sub '${Environment}-aura-alb-dns'
  
  DatabaseEndpoint:
    Description: Database endpoint
    Value: !GetAtt Database.Endpoint.Address
    Export:
      Name: !Sub '${Environment}-aura-db-endpoint'
```

### Terraform 配置

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "aura-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Aura"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "${var.environment}-aura-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  
  tags = {
    Name = "${var.environment}-aura-vpc"
  }
}

# RDS
module "database" {
  source = "terraform-aws-modules/rds/aws"
  
  identifier = "${var.environment}-aura-db"
  
  engine            = "postgres"
  engine_version    = "13.7"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"
  
  db_name  = "aura_prod"
  username = "aura_user"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = module.vpc.database_subnet_group
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  deletion_protection = var.environment == "production"
  
  tags = {
    Name = "${var.environment}-aura-database"
  }
}

# ElastiCache
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.environment}-aura-redis-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.environment}-aura-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis6.x"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  tags = {
    Name = "${var.environment}-aura-redis"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-aura-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "${var.environment}-aura-cluster"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "aura" {
  family                   = "${var.environment}-aura"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    {
      name  = "aura"
      image = "your-account.dkr.ecr.us-west-2.amazonaws.com/aura:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "DATABASE_URL"
          value = "postgresql://aura_user:${var.db_password}@${module.database.db_instance_endpoint}/aura_prod"
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.aura.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
  
  tags = {
    Name = "${var.environment}-aura-task"
  }
}

# ECS Service
resource "aws_ecs_service" "aura" {
  name            = "${var.environment}-aura-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.aura.arn
  desired_count   = 3
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.aura.arn
    container_name   = "aura"
    container_port   = 8000
  }
  
  depends_on = [aws_lb_listener.aura]
  
  tags = {
    Name = "${var.environment}-aura-service"
  }
}
```

---

## 监控和日志

### Prometheus 配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'aura-app'
    static_configs:
      - targets: ['aura-app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
```

### 告警规则

```yaml
# monitoring/alert_rules.yml
groups:
  - name: aura_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to PostgreSQL database"
```

### 日志配置

```python
# src/aura/logging_config.py
import logging
import logging.config
from pythonjsonlogger import jsonlogger
from src.aura.config import settings

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': jsonlogger.JsonFormatter,
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json' if settings.is_production else 'standard',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': settings.log_file_path,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'aura': {
            'handlers': ['console', 'file'],
            'level': settings.log_level,
            'propagate': False,
        },
        'uvicorn': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    }
}

def setup_logging():
    """配置日志系统"""
    logging.config.dictConfig(LOGGING_CONFIG)
```

---

## 备份和恢复

### 数据库备份脚本

```bash
#!/bin/bash
# scripts/backup-database.sh

set -e

# 配置
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="aura_prod"
DB_USER="aura_user"
BACKUP_DIR="/opt/aura/backups"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# 生成备份文件名
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/aura_${DB_NAME}_${TIMESTAMP}.sql"

echo "开始数据库备份..."

# 执行备份
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "备份成功: $BACKUP_FILE"
    
    # 压缩备份文件
    gzip $BACKUP_FILE
    echo "备份文件已压缩: ${BACKUP_FILE}.gz"
    
    # 清理旧备份
    find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "已清理 $RETENTION_DAYS 天前的备份文件"
else
    echo "备份失败"
    exit 1
fi
```

### 数据恢复脚本

```bash
#!/bin/bash
# scripts/restore-database.sh

set -e

if [ $# -ne 1 ]; then
    echo "用法: $0 <backup_file>"
    echo "示例: $0 /opt/aura/backups/aura_prod_20231201_120000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="aura_prod"
DB_USER="aura_user"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "警告: 此操作将覆盖现有数据库 $DB_NAME"
read -p "确认继续？ (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "操作已取消"
    exit 1
fi

echo "开始数据库恢复..."

# 停止应用服务
sudo systemctl stop aura

# 解压备份文件（如果需要）
if [[ $BACKUP_FILE == *.gz ]]; then
    TEMP_FILE="/tmp/restore_$(basename $BACKUP_FILE .gz)"
    gunzip -c $BACKUP_FILE > $TEMP_FILE
    RESTORE_FILE=$TEMP_FILE
else
    RESTORE_FILE=$BACKUP_FILE
fi

# 删除现有数据库
dropdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

# 创建新数据库
createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

# 恢复数据
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < $RESTORE_FILE

if [ $? -eq 0 ]; then
    echo "数据库恢复成功"
    
    # 清理临时文件
    if [ -n "$TEMP_FILE" ]; then
        rm -f $TEMP_FILE
    fi
    
    # 启动应用服务
    sudo systemctl start aura
    
    echo "应用服务已重启"
else
    echo "数据库恢复失败"
    exit 1
fi
```

---

## 安全配置

### SSL/TLS 配置

```bash
# 生成自签名证书（开发环境）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/aura.key \
    -out /etc/ssl/certs/aura.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=aura.local"

# 设置权限
chmod 600 /etc/ssl/private/aura.key
chmod 644 /etc/ssl/certs/aura.crt
```

### 防火墙配置

```bash
# UFW 防火墙配置
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许应用端口（仅内网）
sudo ufw allow from 10.0.0.0/8 to any port 8000
sudo ufw allow from 172.16.0.0/12 to any port 8000
sudo ufw allow from 192.168.0.0/16 to any port 8000

# 启用防火墙
sudo ufw --force enable

# 查看状态
sudo ufw status verbose
```

### 系统安全加固

```bash
#!/bin/bash
# scripts/security-hardening.sh

set -e

echo "开始系统安全加固..."

# 更新系统
apt update && apt upgrade -y

# 安装安全工具
apt install -y fail2ban unattended-upgrades

# 配置 fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
EOF

# 启动 fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# 配置自动安全更新
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades
systemctl enable unattended-upgrades

# 禁用不必要的服务
systemctl disable bluetooth
systemctl disable cups

# 设置内核参数
cat >> /etc/sysctl.conf << EOF
# 网络安全
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.ip_forward = 0
EOF

sysctl -p

echo "系统安全加固完成"
```

---

## 性能优化

### 数据库优化

```sql
-- postgresql.conf 优化配置
-- 内存配置
shared_buffers = 256MB                 -- 25% of RAM
effective_cache_size = 1GB             -- 75% of RAM
work_mem = 4MB                         -- Per connection
maintenance_work_mem = 64MB

-- 连接配置
max_connections = 100

-- 检查点配置
checkpoint_completion_target = 0.9
wal_buffers = 16MB

-- 日志配置
log_min_duration_statement = 1000      -- Log slow queries
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

-- 统计配置
track_activities = on
track_counts = on
track_io_timing = on
track_functions = all
```

### 应用性能优化

```python
# src/aura/performance.py
import asyncio
import time
from functools import wraps
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

# Prometheus 指标
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')
TASK_QUEUE_SIZE = Gauge('task_queue_size', 'Task queue size')

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='success').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='error').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.connection_pool_size = 20
        self.max_workers = 4
        self.cache_ttl = 300
    
    async def optimize_database_queries(self):
        """优化数据库查询"""
        # 实现查询优化逻辑
        pass
    
    async def setup_connection_pooling(self):
        """设置连接池"""
        # 实现连接池配置
        pass
    
    async def enable_query_caching(self):
        """启用查询缓存"""
        # 实现查询缓存
        pass
```

---

## 故障排除

### 常见问题

#### 1. 应用启动失败

```bash
# 检查日志
journalctl -u aura -f

# 检查配置文件
python -c "from src.aura.config import settings; print(settings.dict())"

# 检查依赖服务
systemctl status postgresql
systemctl status redis

# 检查端口占用
netstat -tlnp | grep 8000
```

#### 2. 数据库连接问题

```bash
# 测试数据库连接
psql -h localhost -U aura_user -d aura_prod -c "SELECT 1;"

# 检查数据库日志
tail -f /var/log/postgresql/postgresql-13-main.log

# 检查连接数
psql -h localhost -U aura_user -d aura_prod -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 3. 性能问题

```bash
# 检查系统资源
top
htop
iotop

# 检查数据库性能
psql -h localhost -U aura_user -d aura_prod -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 检查应用指标
curl http://localhost:8000/metrics
```

### 故障排除清单

| 问题类型 | 检查项目 | 解决方案 |
|----------|----------|----------|
| **启动失败** | 配置文件、依赖服务、端口冲突 | 修复配置、重启服务、释放端口 |
| **数据库连接** | 连接字符串、权限、网络 | 检查配置、授权、防火墙 |
| **性能问题** | CPU、内存、磁盘、网络 | 优化配置、扩容资源 |
| **内存泄漏** | 进程内存、连接池 | 重启服务、调整池大小 |
| **磁盘空间** | 日志文件、备份文件 | 清理日志、删除旧备份 |

---

## 总结

本部署指南涵盖了 Aura 系统从开发环境到生产环境的完整部署流程，包括：

- **环境配置**：详细的环境变量和配置管理
- **部署方案**：开发、测试、生产环境的不同部署策略
- **容器化**：Docker 和 Kubernetes 部署方案
- **云平台**：AWS 和 Terraform 基础设施即代码
- **监控日志**：Prometheus、Grafana 监控体系
- **备份恢复**：数据库备份和恢复策略
- **安全配置**：SSL、防火墙、系统加固
- **性能优化**：数据库和应用性能调优
- **故障排除**：常见问题的诊断和解决方案

通过遵循本指南，可以确保 Aura 系统在各种环境中稳定、安全、高效地运行。

---

## 相关文档

- [系统概览](./system-overview.md)
- [开发指南](./development-guide.md)
- [测试指南](./testing-guide.md)
- [API 参考](./api-reference.md)
- [技术规范](./technical-specifications.md)