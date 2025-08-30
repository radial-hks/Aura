"""Aura系统配置文件

包含系统的所有配置项，支持环境变量覆盖和配置验证。

配置层级：
1. 默认配置（此文件）
2. 环境变量覆盖
3. 配置文件覆盖（config.yaml）
4. 运行时参数覆盖
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"  # sqlite, postgresql, mysql
    host: str = "localhost"
    port: int = 5432
    database: str = "aura.db"
    username: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    decode_responses: bool = True


@dataclass
class PlaywrightConfig:
    """Playwright配置"""
    browser: str = "chromium"  # chromium, firefox, webkit
    headless: bool = True
    slow_mo: int = 0  # 毫秒
    timeout: int = 30000  # 毫秒
    navigation_timeout: int = 30000  # 毫秒
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    permissions: List[str] = field(default_factory=lambda: ["geolocation", "notifications"])
    ignore_https_errors: bool = False
    bypass_csp: bool = False
    java_script_enabled: bool = True
    accept_downloads: bool = True
    record_video: bool = False
    record_har: bool = False
    trace: bool = False
    max_concurrent_browsers: int = 3
    browser_pool_size: int = 5
    page_pool_size: int = 10


@dataclass
class LLMConfig:
    """大语言模型配置"""
    provider: str = "openai"  # openai, anthropic, azure, local
    model: str = "gpt-4"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_rpm: int = 60  # requests per minute
    rate_limit_tpm: int = 90000  # tokens per minute
    fallback_models: List[str] = field(default_factory=lambda: ["gpt-3.5-turbo"])


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # 秒
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_symbols: bool = False
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 秒
    session_timeout: int = 1800  # 秒
    csrf_protection: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    rate_limit_per_minute: int = 100
    enable_audit_log: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_enabled: bool = True
    file_path: str = "logs/aura.log"
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 5
    console_enabled: bool = True
    json_format: bool = False
    include_trace: bool = False
    log_sql: bool = False
    log_requests: bool = True
    log_responses: bool = False
    sensitive_fields: List[str] = field(default_factory=lambda: [
        "password", "token", "api_key", "secret", "credit_card"
    ])


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    backend: str = "redis"  # redis, memory, file
    default_timeout: int = 300  # 秒
    key_prefix: str = "aura:"
    version: int = 1
    site_model_ttl: int = 86400  # 24小时
    skill_cache_ttl: int = 3600  # 1小时
    session_cache_ttl: int = 1800  # 30分钟
    max_memory_cache_size: int = 1000
    compression_enabled: bool = True
    compression_level: int = 6


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    health_check_enabled: bool = True
    prometheus_enabled: bool = False
    prometheus_port: int = 9090
    jaeger_enabled: bool = False
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    sentry_enabled: bool = False
    sentry_dsn: Optional[str] = None
    alert_webhook: Optional[str] = None
    performance_threshold_ms: int = 5000
    error_rate_threshold: float = 0.05
    memory_threshold_mb: int = 1024


@dataclass
class SkillLibraryConfig:
    """技能库配置"""
    enabled: bool = True
    registry_url: str = "https://skills.aura.ai"
    local_path: str = "skills"
    auto_update: bool = True
    update_interval: int = 3600  # 秒
    signature_verification: bool = True
    trusted_publishers: List[str] = field(default_factory=lambda: ["official"])
    max_skill_size: int = 10 * 1024 * 1024  # 10MB
    execution_timeout: int = 300  # 秒
    sandbox_enabled: bool = True
    allowed_permissions: List[str] = field(default_factory=lambda: [
        "readPublic", "writePublic", "network"
    ])
    version_retention: int = 5


@dataclass
class SiteExplorerConfig:
    """站点探索配置"""
    enabled: bool = True
    max_depth: int = 3
    max_pages_per_domain: int = 100
    crawl_delay: float = 1.0  # 秒
    respect_robots_txt: bool = True
    user_agent: str = "Aura-Explorer/1.0"
    timeout: int = 30
    max_concurrent_requests: int = 5
    screenshot_enabled: bool = True
    screenshot_quality: int = 80
    element_detection_enabled: bool = True
    semantic_analysis_enabled: bool = True
    model_update_threshold: float = 0.3
    model_retention_days: int = 30


@dataclass
class PolicyEngineConfig:
    """策略引擎配置"""
    enabled: bool = True
    strict_mode: bool = False
    default_permission_level: str = "read"
    require_approval_for_write: bool = True
    require_approval_for_sensitive: bool = True
    approval_timeout: int = 300  # 秒
    policy_cache_ttl: int = 3600  # 秒
    audit_all_actions: bool = True
    block_suspicious_domains: bool = True
    suspicious_domains: List[str] = field(default_factory=list)
    allowed_file_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".csv", ".json", ".xml", ".pdf", ".png", ".jpg", ".jpeg"
    ])


@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    request_timeout: int = 300  # 秒
    keepalive_timeout: int = 5
    cors_enabled: bool = True
    docs_enabled: bool = True
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    api_prefix: str = "/api/v1"
    rate_limiting_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # 秒


class AuraConfig:
    """Aura系统主配置类"""
    
    def __init__(self, env: Optional[Environment] = None):
        self.env = env or Environment(os.getenv("AURA_ENV", "development"))
        self.project_root = Path(__file__).parent.parent
        
        # 加载配置
        self._load_default_config()
        self._load_environment_config()
        self._load_config_file()
        self._validate_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.playwright = PlaywrightConfig()
        self.llm = LLMConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        self.cache = CacheConfig()
        self.monitoring = MonitoringConfig()
        self.skill_library = SkillLibraryConfig()
        self.site_explorer = SiteExplorerConfig()
        self.policy_engine = PolicyEngineConfig()
        self.api = APIConfig()
        
        # 环境特定配置
        if self.env == Environment.DEVELOPMENT:
            self._apply_development_config()
        elif self.env == Environment.TESTING:
            self._apply_testing_config()
        elif self.env == Environment.PRODUCTION:
            self._apply_production_config()
    
    def _apply_development_config(self):
        """应用开发环境配置"""
        self.playwright.headless = False
        self.playwright.slow_mo = 100
        self.logging.level = LogLevel.DEBUG
        self.logging.console_enabled = True
        self.api.debug = True
        self.api.reload = True
        self.monitoring.enabled = False
        self.cache.enabled = False
        self.policy_engine.strict_mode = False
    
    def _apply_testing_config(self):
        """应用测试环境配置"""
        self.database.database = ":memory:"
        self.playwright.headless = True
        self.logging.level = LogLevel.WARNING
        self.logging.file_enabled = False
        self.cache.backend = "memory"
        self.skill_library.auto_update = False
        self.site_explorer.enabled = False
        self.monitoring.enabled = False
    
    def _apply_production_config(self):
        """应用生产环境配置"""
        self.playwright.headless = True
        self.logging.level = LogLevel.INFO
        self.logging.json_format = True
        self.api.debug = False
        self.api.workers = 4
        self.monitoring.enabled = True
        self.security.csrf_protection = True
        self.policy_engine.strict_mode = True
        self.cache.compression_enabled = True
    
    def _load_environment_config(self):
        """从环境变量加载配置"""
        # 数据库配置
        if os.getenv("DATABASE_URL"):
            self._parse_database_url(os.getenv("DATABASE_URL"))
        
        # Redis配置
        if os.getenv("REDIS_URL"):
            self._parse_redis_url(os.getenv("REDIS_URL"))
        
        # LLM配置
        if os.getenv("OPENAI_API_KEY"):
            self.llm.api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("OPENAI_API_BASE"):
            self.llm.api_base = os.getenv("OPENAI_API_BASE")
        if os.getenv("OPENAI_MODEL"):
            self.llm.model = os.getenv("OPENAI_MODEL")
        
        # 安全配置
        if os.getenv("SECRET_KEY"):
            self.security.secret_key = os.getenv("SECRET_KEY")
        
        # API配置
        if os.getenv("API_HOST"):
            self.api.host = os.getenv("API_HOST")
        if os.getenv("API_PORT"):
            self.api.port = int(os.getenv("API_PORT"))
        
        # 日志级别
        if os.getenv("LOG_LEVEL"):
            self.logging.level = LogLevel(os.getenv("LOG_LEVEL"))
    
    def _parse_database_url(self, url: str):
        """解析数据库URL"""
        # 简化的URL解析，实际应该使用更robust的解析器
        if url.startswith("sqlite://"):
            self.database.type = "sqlite"
            self.database.database = url.replace("sqlite://", "")
        elif url.startswith("postgresql://"):
            self.database.type = "postgresql"
            # 解析PostgreSQL URL
        elif url.startswith("mysql://"):
            self.database.type = "mysql"
            # 解析MySQL URL
    
    def _parse_redis_url(self, url: str):
        """解析Redis URL"""
        # 简化的Redis URL解析
        if url.startswith("redis://"):
            # 解析Redis URL
            pass
    
    def _load_config_file(self):
        """从配置文件加载配置"""
        config_files = [
            self.project_root / "config" / f"{self.env.value}.yaml",
            self.project_root / "config" / "config.yaml",
            Path.home() / ".aura" / "config.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    import yaml
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    self._apply_config_data(config_data)
                    break
                except Exception as e:
                    print(f"Warning: Failed to load config file {config_file}: {e}")
    
    def _apply_config_data(self, config_data: Dict[str, Any]):
        """应用配置数据"""
        for section, values in config_data.items():
            if hasattr(self, section) and isinstance(values, dict):
                config_obj = getattr(self, section)
                for key, value in values.items():
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
    
    def _validate_config(self):
        """验证配置"""
        errors = []
        
        # 验证必需的配置
        if not self.security.secret_key or self.security.secret_key == "your-secret-key-change-in-production":
            if self.env == Environment.PRODUCTION:
                errors.append("SECRET_KEY must be set in production")
        
        if self.llm.provider == "openai" and not self.llm.api_key:
            errors.append("OpenAI API key is required when using OpenAI provider")
        
        # 验证端口范围
        if not (1 <= self.api.port <= 65535):
            errors.append(f"Invalid API port: {self.api.port}")
        
        # 验证路径
        log_dir = Path(self.logging.file_path).parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create log directory {log_dir}: {e}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        db = self.database
        if db.type == "sqlite":
            return f"sqlite:///{db.database}"
        elif db.type == "postgresql":
            return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
        elif db.type == "mysql":
            return f"mysql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
        else:
            raise ValueError(f"Unsupported database type: {db.type}")
    
    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        redis = self.redis
        auth = f":{redis.password}@" if redis.password else ""
        return f"redis://{auth}{redis.host}:{redis.port}/{redis.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                attr_value = getattr(self, attr_name)
                if hasattr(attr_value, '__dict__'):
                    result[attr_name] = attr_value.__dict__
                else:
                    result[attr_name] = attr_value
        return result
    
    def save_to_file(self, file_path: Union[str, Path]):
        """保存配置到文件"""
        config_dict = self.to_dict()
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_path.suffix.lower() == '.json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                raise ImportError("PyYAML is required to save YAML config files")
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")


# 全局配置实例
config = AuraConfig()


# 配置工具函数
def get_config() -> AuraConfig:
    """获取全局配置实例"""
    return config


def reload_config(env: Optional[Environment] = None) -> AuraConfig:
    """重新加载配置"""
    global config
    config = AuraConfig(env)
    return config


def validate_environment():
    """验证环境配置"""
    try:
        config._validate_config()
        print(f"✓ Configuration validation passed for {config.env.value} environment")
        return True
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # 配置验证和测试
    print(f"Aura Configuration - Environment: {config.env.value}")
    print(f"Database URL: {config.get_database_url()}")
    print(f"Redis URL: {config.get_redis_url()}")
    print(f"API Server: {config.api.host}:{config.api.port}")
    print(f"Log Level: {config.logging.level.value}")
    
    # 验证配置
    if validate_environment():
        print("Configuration is valid!")
    else:
        print("Configuration validation failed!")