#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura生产环境部署脚本
提供Docker容器化部署、系统服务安装、配置管理等功能
"""

import os
import sys
import argparse
import subprocess
import shutil
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import tempfile
import tarfile

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class AuraDeployer:
    """Aura部署管理器"""
    
    def __init__(self):
        self.project_root = project_root
        self.build_dir = project_root / "build"
        self.dist_dir = project_root / "dist"
        
    def run_command(self, command: List[str], cwd: Optional[Path] = None, 
                   check: bool = True) -> subprocess.CompletedProcess:
        """运行命令"""
        print(f"🔧 执行: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            cwd=cwd or self.project_root,
            capture_output=True,
            text=True,
            check=check
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result
    
    def create_dockerfile(self) -> Path:
        """创建Dockerfile"""
        dockerfile_content = """
# Aura智能浏览器自动化系统 - 生产环境镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 aura && \
    mkdir -p /app/logs /app/data /app/cache && \
    chown -R aura:aura /app

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器
RUN playwright install chromium

# 复制应用代码
COPY --chown=aura:aura . .

# 切换到非root用户
USER aura

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "scripts/start.py", "api", "--env", "production", "--host", "0.0.0.0", "--port", "8000"]
"""
        
        dockerfile_path = self.project_root / "Dockerfile"
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content.strip())
        
        print(f"✅ Dockerfile已创建: {dockerfile_path}")
        return dockerfile_path
    
    def create_docker_compose(self) -> Path:
        """创建docker-compose.yml"""
        compose_content = """
version: '3.8'

services:
  aura-api:
    build: .
    container_name: aura-api
    ports:
      - "8000:8000"
    environment:
      - AURA_ENV=production
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://aura:aura_password@postgres:5432/aura
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./cache:/app/cache
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
    networks:
      - aura-network
  
  redis:
    image: redis:7-alpine
    container_name: aura-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - aura-network
  
  postgres:
    image: postgres:15-alpine
    container_name: aura-postgres
    environment:
      - POSTGRES_DB=aura
      - POSTGRES_USER=aura
      - POSTGRES_PASSWORD=aura_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - aura-network
  
  nginx:
    image: nginx:alpine
    container_name: aura-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - aura-api
    restart: unless-stopped
    networks:
      - aura-network

volumes:
  redis_data:
  postgres_data:

networks:
  aura-network:
    driver: bridge
"""
        
        compose_path = self.project_root / "docker-compose.yml"
        with open(compose_path, "w", encoding="utf-8") as f:
            f.write(compose_content.strip())
        
        print(f"✅ docker-compose.yml已创建: {compose_path}")
        return compose_path
    
    def create_nginx_config(self) -> Path:
        """创建Nginx配置"""
        nginx_content = """
events {
    worker_connections 1024;
}

http {
    upstream aura_api {
        server aura-api:8000;
    }
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    server {
        listen 80;
        server_name _;
        
        # 重定向到HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name _;
        
        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        
        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
        
        # 访问日志
        access_log /var/log/nginx/aura_access.log main;
        error_log /var/log/nginx/aura_error.log;
        
        # API代理
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://aura_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        
        # 健康检查
        location /health {
            proxy_pass http://aura_api/health;
        }
        
        # 默认路由
        location / {
            proxy_pass http://aura_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""
        
        nginx_path = self.project_root / "nginx.conf"
        with open(nginx_path, "w", encoding="utf-8") as f:
            f.write(nginx_content.strip())
        
        print(f"✅ nginx.conf已创建: {nginx_path}")
        return nginx_path
    
    def create_systemd_service(self) -> Path:
        """创建systemd服务文件"""
        service_content = f"""
[Unit]
Description=Aura智能浏览器自动化系统
After=network.target
Wants=network.target

[Service]
Type=simple
User=aura
Group=aura
WorkingDirectory={self.project_root}
Environment=AURA_ENV=production
Environment=PYTHONPATH={self.project_root}
ExecStart={sys.executable} scripts/start.py full --env production
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={self.project_root}/logs {self.project_root}/data {self.project_root}/cache

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
"""
        
        service_path = self.project_root / "aura.service"
        with open(service_path, "w", encoding="utf-8") as f:
            f.write(service_content.strip())
        
        print(f"✅ systemd服务文件已创建: {service_path}")
        return service_path
    
    def create_deployment_config(self, environment: str) -> Path:
        """创建部署配置"""
        config = {
            "environment": environment,
            "version": "1.0.0",
            "deployment": {
                "method": "docker",  # docker, systemd, manual
                "replicas": 1,
                "resources": {
                    "cpu": "1000m",
                    "memory": "2Gi"
                }
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "aura",
                "user": "aura"
            },
            "redis": {
                "host": "localhost",
                "port": 6379
            },
            "monitoring": {
                "enabled": True,
                "prometheus_port": 9090,
                "grafana_port": 3000
            },
            "backup": {
                "enabled": True,
                "schedule": "0 2 * * *",  # 每天凌晨2点
                "retention_days": 30
            }
        }
        
        config_path = self.project_root / f"deploy-{environment}.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 部署配置已创建: {config_path}")
        return config_path
    
    def build_docker_image(self, tag: str = "aura:latest"):
        """构建Docker镜像"""
        print(f"🐳 构建Docker镜像: {tag}")
        
        # 创建Dockerfile
        self.create_dockerfile()
        
        # 构建镜像
        self.run_command(["docker", "build", "-t", tag, "."])
        
        print(f"✅ Docker镜像构建完成: {tag}")
    
    def deploy_docker(self, environment: str = "production"):
        """Docker部署"""
        print(f"🚀 开始Docker部署 ({environment})...")
        
        # 创建部署文件
        self.create_docker_compose()
        self.create_nginx_config()
        
        # 创建必要目录
        for dir_name in ["logs", "data", "cache", "ssl"]:
            (self.project_root / dir_name).mkdir(exist_ok=True)
        
        # 构建镜像
        self.build_docker_image()
        
        # 启动服务
        self.run_command(["docker-compose", "up", "-d"])
        
        print("✅ Docker部署完成")
        print("📍 API地址: http://localhost:8000")
        print("📚 API文档: http://localhost:8000/docs")
        print("🔧 管理命令:")
        print("  docker-compose logs -f    # 查看日志")
        print("  docker-compose stop       # 停止服务")
        print("  docker-compose restart    # 重启服务")
    
    def deploy_systemd(self, environment: str = "production"):
        """systemd部署"""
        print(f"🔧 开始systemd部署 ({environment})...")
        
        # 创建服务文件
        service_file = self.create_systemd_service()
        
        # 创建用户
        try:
            self.run_command(["sudo", "useradd", "-r", "-s", "/bin/false", "aura"], check=False)
        except subprocess.CalledProcessError:
            print("用户aura已存在")
        
        # 设置权限
        self.run_command(["sudo", "chown", "-R", "aura:aura", str(self.project_root)])
        
        # 安装服务文件
        self.run_command(["sudo", "cp", str(service_file), "/etc/systemd/system/"])
        
        # 重载systemd
        self.run_command(["sudo", "systemctl", "daemon-reload"])
        
        # 启用并启动服务
        self.run_command(["sudo", "systemctl", "enable", "aura"])
        self.run_command(["sudo", "systemctl", "start", "aura"])
        
        print("✅ systemd部署完成")
        print("🔧 管理命令:")
        print("  sudo systemctl status aura    # 查看状态")
        print("  sudo systemctl stop aura      # 停止服务")
        print("  sudo systemctl restart aura   # 重启服务")
        print("  sudo journalctl -u aura -f    # 查看日志")
    
    def create_backup_script(self) -> Path:
        """创建备份脚本"""
        backup_content = f"""
#!/bin/bash
# Aura系统备份脚本

set -e

BACKUP_DIR="/var/backups/aura"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aura_backup_$DATE.tar.gz"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

echo "开始备份Aura系统..."

# 备份应用数据
tar -czf $BACKUP_FILE \
    -C {self.project_root} \
    --exclude='logs/*' \
    --exclude='cache/*' \
    --exclude='__pycache__' \
    --exclude='.git' \
    .

# 备份数据库
if command -v pg_dump &> /dev/null; then
    pg_dump -h localhost -U aura aura > $BACKUP_DIR/database_$DATE.sql
    gzip $BACKUP_DIR/database_$DATE.sql
fi

# 清理旧备份
find $BACKUP_DIR -name "aura_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "database_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "备份完成: $BACKUP_FILE"
"""
        
        backup_path = self.project_root / "scripts" / "backup.sh"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(backup_content.strip())
        
        # 设置执行权限
        backup_path.chmod(0o755)
        
        print(f"✅ 备份脚本已创建: {backup_path}")
        return backup_path
    
    def create_monitoring_config(self) -> Path:
        """创建监控配置"""
        prometheus_config = """
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'aura-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
"""
        
        monitoring_dir = self.project_root / "monitoring"
        monitoring_dir.mkdir(exist_ok=True)
        
        prometheus_path = monitoring_dir / "prometheus.yml"
        with open(prometheus_path, "w", encoding="utf-8") as f:
            f.write(prometheus_config.strip())
        
        print(f"✅ 监控配置已创建: {prometheus_path}")
        return prometheus_path
    
    def package_release(self, version: str) -> Path:
        """打包发布版本"""
        print(f"📦 打包发布版本: {version}")
        
        # 创建构建目录
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        
        # 清理旧文件
        for file in self.build_dir.glob("*"):
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)
        
        # 复制源代码
        exclude_patterns = {
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            'logs', 'cache', 'build', 'dist', '.env*'
        }
        
        for item in self.project_root.iterdir():
            if item.name not in exclude_patterns:
                if item.is_file():
                    shutil.copy2(item, self.build_dir)
                else:
                    shutil.copytree(item, self.build_dir / item.name)
        
        # 创建版本信息
        version_info = {
            "version": version,
            "build_date": subprocess.check_output(
                ["date", "-Iseconds"], text=True
            ).strip(),
            "git_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip() if (self.project_root / ".git").exists() else "unknown"
        }
        
        with open(self.build_dir / "version.json", "w") as f:
            json.dump(version_info, f, indent=2)
        
        # 创建压缩包
        archive_name = f"aura-{version}.tar.gz"
        archive_path = self.dist_dir / archive_name
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.build_dir, arcname=f"aura-{version}")
        
        print(f"✅ 发布包已创建: {archive_path}")
        return archive_path
    
    def health_check(self, url: str = "http://localhost:8000"):
        """健康检查"""
        print(f"🏥 执行健康检查: {url}")
        
        try:
            import requests
            
            # 检查API健康状态
            response = requests.get(f"{url}/health", timeout=10)
            response.raise_for_status()
            
            health_data = response.json()
            print(f"✅ API健康状态: {health_data.get('status', 'unknown')}")
            
            # 检查各组件状态
            for component, status in health_data.get('components', {}).items():
                status_icon = "✅" if status == "healthy" else "❌"
                print(f"  {status_icon} {component}: {status}")
            
            return True
            
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Aura生产环境部署管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/deploy.py docker                    # Docker部署
  python scripts/deploy.py systemd                   # systemd部署
  python scripts/deploy.py build --tag aura:v1.0     # 构建Docker镜像
  python scripts/deploy.py package --version 1.0.0   # 打包发布版本
  python scripts/deploy.py health                     # 健康检查
        """
    )
    
    parser.add_argument(
        'command',
        choices=['docker', 'systemd', 'build', 'package', 'health', 'backup'],
        help='部署命令'
    )
    
    parser.add_argument(
        '--environment', '-e',
        choices=['production', 'staging'],
        default='production',
        help='部署环境 (默认: production)'
    )
    
    parser.add_argument(
        '--tag', '-t',
        default='aura:latest',
        help='Docker镜像标签 (默认: aura:latest)'
    )
    
    parser.add_argument(
        '--version', '-v',
        help='发布版本号'
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='健康检查URL (默认: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    deployer = AuraDeployer()
    
    try:
        if args.command == 'docker':
            deployer.deploy_docker(args.environment)
        
        elif args.command == 'systemd':
            deployer.deploy_systemd(args.environment)
        
        elif args.command == 'build':
            deployer.build_docker_image(args.tag)
        
        elif args.command == 'package':
            if not args.version:
                print("❌ 打包命令需要指定版本号")
                sys.exit(1)
            deployer.package_release(args.version)
        
        elif args.command == 'health':
            if not deployer.health_check(args.url):
                sys.exit(1)
        
        elif args.command == 'backup':
            deployer.create_backup_script()
        
    except Exception as e:
        print(f"❌ 部署命令失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()