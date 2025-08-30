#!/usr/bin/env python3
"""
Aura智能浏览器自动化系统 - 异常定义模块
"""

from typing import Optional, Dict, Any


class AuraException(Exception):
    """
    Aura系统基础异常类
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AURA_ERROR"
        self.details = details or {}
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class TaskExecutionError(AuraException):
    """
    任务执行异常
    """
    
    def __init__(self, message: str, task_id: Optional[str] = None, step: Optional[str] = None, **kwargs):
        super().__init__(message, "TASK_EXECUTION_ERROR", kwargs)
        self.task_id = task_id
        self.step = step


class CommandParsingError(AuraException):
    """
    指令解析异常
    """
    
    def __init__(self, message: str, command: Optional[str] = None, **kwargs):
        super().__init__(message, "COMMAND_PARSING_ERROR", kwargs)
        self.command = command


class SkillExecutionError(AuraException):
    """
    技能执行异常
    """
    
    def __init__(self, message: str, skill_id: Optional[str] = None, **kwargs):
        super().__init__(message, "SKILL_EXECUTION_ERROR", kwargs)
        self.skill_id = skill_id


class SiteExplorationError(AuraException):
    """
    站点探索异常
    """
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        super().__init__(message, "SITE_EXPLORATION_ERROR", kwargs)
        self.url = url


class ActionGraphError(AuraException):
    """
    Action Graph执行异常
    """
    
    def __init__(self, message: str, graph_id: Optional[str] = None, node_id: Optional[str] = None, **kwargs):
        super().__init__(message, "ACTION_GRAPH_ERROR", kwargs)
        self.graph_id = graph_id
        self.node_id = node_id


class ConfigurationError(AuraException):
    """
    配置异常
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, "CONFIGURATION_ERROR", kwargs)
        self.config_key = config_key


class ValidationError(AuraException):
    """
    数据验证异常
    """
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, "VALIDATION_ERROR", kwargs)
        self.field = field
        self.value = value


class BrowserError(AuraException):
    """
    浏览器操作异常
    """
    
    def __init__(self, message: str, action: Optional[str] = None, selector: Optional[str] = None, **kwargs):
        super().__init__(message, "BROWSER_ERROR", kwargs)
        self.action = action
        self.selector = selector


class TimeoutError(AuraException):
    """
    超时异常
    """
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None, **kwargs):
        super().__init__(message, "TIMEOUT_ERROR", kwargs)
        self.timeout_seconds = timeout_seconds


class AuthenticationError(AuraException):
    """
    认证异常
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "AUTHENTICATION_ERROR", kwargs)


class AuthorizationError(AuraException):
    """
    授权异常
    """
    
    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        super().__init__(message, "AUTHORIZATION_ERROR", kwargs)
        self.required_permission = required_permission


class RateLimitError(AuraException):
    """
    速率限制异常
    """
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, "RATE_LIMIT_ERROR", kwargs)
        self.retry_after = retry_after


class ResourceNotFoundError(AuraException):
    """
    资源未找到异常
    """
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        super().__init__(message, "RESOURCE_NOT_FOUND_ERROR", kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class NetworkError(AuraException):
    """
    网络异常
    """
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, "NETWORK_ERROR", kwargs)
        self.url = url
        self.status_code = status_code


class LLMError(AuraException):
    """
    LLM服务异常
    """
    
    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None, **kwargs):
        super().__init__(message, "LLM_ERROR", kwargs)
        self.provider = provider
        self.model = model


class StorageError(AuraException):
    """
    存储异常
    """
    
    def __init__(self, message: str, operation: Optional[str] = None, path: Optional[str] = None, **kwargs):
        super().__init__(message, "STORAGE_ERROR", kwargs)
        self.operation = operation
        self.path = path


class AuraSystemError(AuraException):
    """
    系统级异常
    """
    
    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        super().__init__(message, "SYSTEM_ERROR", kwargs)
        self.component = component


class PolicyViolationError(AuraException):
    """
    策略违规异常
    """
    
    def __init__(self, message: str, policy_name: Optional[str] = None, violation_type: Optional[str] = None, **kwargs):
        super().__init__(message, "POLICY_VIOLATION_ERROR", kwargs)
        self.policy_name = policy_name
        self.violation_type = violation_type


# 异常映射字典，用于快速查找
EXCEPTION_MAP = {
    "TASK_EXECUTION_ERROR": TaskExecutionError,
    "COMMAND_PARSING_ERROR": CommandParsingError,
    "SKILL_EXECUTION_ERROR": SkillExecutionError,
    "SITE_EXPLORATION_ERROR": SiteExplorationError,
    "ACTION_GRAPH_ERROR": ActionGraphError,
    "CONFIGURATION_ERROR": ConfigurationError,
    "VALIDATION_ERROR": ValidationError,
    "BROWSER_ERROR": BrowserError,
    "TIMEOUT_ERROR": TimeoutError,
    "AUTHENTICATION_ERROR": AuthenticationError,
    "AUTHORIZATION_ERROR": AuthorizationError,
    "RATE_LIMIT_ERROR": RateLimitError,
    "RESOURCE_NOT_FOUND_ERROR": ResourceNotFoundError,
    "NETWORK_ERROR": NetworkError,
    "LLM_ERROR": LLMError,
    "STORAGE_ERROR": StorageError,
    "SYSTEM_ERROR": AuraSystemError,
    "POLICY_VIOLATION_ERROR": PolicyViolationError,
}


def create_exception(error_code: str, message: str, **kwargs) -> AuraException:
    """
    根据错误代码创建对应的异常实例
    
    Args:
        error_code: 错误代码
        message: 错误消息
        **kwargs: 额外参数
    
    Returns:
        对应的异常实例
    """
    exception_class = EXCEPTION_MAP.get(error_code, AuraException)
    return exception_class(message, **kwargs)