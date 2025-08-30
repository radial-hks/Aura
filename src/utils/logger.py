#!/usr/bin/env python3
"""
Aura智能浏览器自动化系统 - 日志工具模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# 日志格式配置
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认日志级别
DEFAULT_LEVEL = logging.INFO

# 日志文件路径
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别，默认为INFO
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(level or DEFAULT_LEVEL)
    
    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = LOG_DIR / f"{name.replace('.', '_')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误文件处理器
    error_log_file = LOG_DIR / f"{name.replace('.', '_')}_error.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    设置全局日志配置
    
    Args:
        level: 日志级别字符串
        log_file: 可选的日志文件路径
    """
    # 转换日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # 基础配置
    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                log_file or LOG_DIR / f"aura_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
        ]
    )


def get_structured_logger(name: str) -> logging.Logger:
    """
    获取结构化日志记录器（为未来扩展预留）
    
    Args:
        name: 日志记录器名称
    
    Returns:
        日志记录器
    """
    # 目前返回标准日志记录器，未来可以集成structlog
    return get_logger(name)


class AuraLoggerAdapter(logging.LoggerAdapter):
    """
    Aura系统专用日志适配器，添加上下文信息
    """
    
    def process(self, msg, kwargs):
        """
        处理日志消息，添加上下文信息
        """
        extra = self.extra or {}
        
        # 添加任务ID（如果存在）
        if 'task_id' in extra:
            msg = f"[Task:{extra['task_id']}] {msg}"
        
        # 添加用户ID（如果存在）
        if 'user_id' in extra:
            msg = f"[User:{extra['user_id']}] {msg}"
        
        return msg, kwargs


def get_task_logger(name: str, task_id: str) -> AuraLoggerAdapter:
    """
    获取带任务ID的日志记录器
    
    Args:
        name: 日志记录器名称
        task_id: 任务ID
    
    Returns:
        带任务上下文的日志适配器
    """
    logger = get_logger(name)
    return AuraLoggerAdapter(logger, {'task_id': task_id})


# 预定义的日志记录器
core_logger = get_logger('aura.core')
api_logger = get_logger('aura.api')
modules_logger = get_logger('aura.modules')
utils_logger = get_logger('aura.utils')