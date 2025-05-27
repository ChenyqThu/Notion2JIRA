"""
日志配置模块
提供结构化的日志管理功能
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "sync_service",
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        max_file_size: 单个日志文件最大大小
        backup_count: 保留的日志文件数量
        format_string: 日志格式字符串
    
    Returns:
        配置好的日志记录器
    """
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 默认日志格式
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )
    
    formatter = logging.Formatter(
        format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 使用RotatingFileHandler实现日志轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 防止日志向上传播到根日志记录器
    logger.propagate = False
    
    return logger


class StructuredLogger:
    """结构化日志记录器，提供更丰富的日志功能"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def info(self, message: str, **kwargs):
        """记录信息级别日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告级别日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误级别日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录调试级别日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误级别日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        if kwargs:
            # 将额外的键值对格式化为字符串
            extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            full_message = f"{message} | {extra_info}"
        else:
            full_message = message
        
        self.logger.log(level, full_message)
    
    def log_sync_event(self, event_type: str, page_id: str, status: str, **kwargs):
        """记录同步事件的专用方法"""
        self.info(
            f"同步事件: {event_type}",
            page_id=page_id,
            status=status,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )
    
    def log_api_call(self, service: str, method: str, url: str, status_code: int, duration: float, **kwargs):
        """记录API调用的专用方法"""
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self._log(
            level,
            f"API调用: {service}.{method}",
            url=url,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_error_with_context(self, error: Exception, context: dict):
        """记录带上下文的错误"""
        self.error(
            f"错误: {type(error).__name__}: {str(error)}",
            error_type=type(error).__name__,
            **context
        )


def get_logger(name: str = "sync_service") -> StructuredLogger:
    """
    获取结构化日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        结构化日志记录器实例
    """
    # 从环境变量获取配置
    level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE_PATH", "logs/sync_service.log")
    max_file_size = int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024)))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # 设置基础日志记录器
    base_logger = setup_logger(
        name=name,
        level=level,
        log_file=log_file,
        max_file_size=max_file_size,
        backup_count=backup_count
    )
    
    # 返回结构化日志记录器
    return StructuredLogger(base_logger)


# 为了向后兼容，提供一个简单的setup_logger函数
def setup_logger_simple() -> logging.Logger:
    """简单的日志设置函数，返回标准的logging.Logger"""
    return setup_logger() 