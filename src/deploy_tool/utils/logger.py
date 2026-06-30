"""Loguru 日志系统配置"""
import os
import sys

from loguru import logger as _logger

from ..config.paths import logs_dir


def setup_logger(level: str = "INFO"):
    """初始化 loguru，控制台 + 文件输出，返回 logger 实例"""
    _logger.remove()

    # 控制台（开发期用）
    _logger.add(
        sys.stderr,
        level=level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> <level>{level: <8}</level> {message}",
    )

    # 文件（按天轮转，保留 30 天）
    _logger.add(
        os.path.join(logs_dir(), "deploy_{time:YYYY-MM-DD}.log"),
        level=level,
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )
    return _logger


def get_logger():
    return _logger
