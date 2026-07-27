"""
日志模块 —— 统一 logging 配置，替代 print。
"""

import logging
import sys
import os
import os


def get_logger(name: str = "ExamApp") -> logging.Logger:
    """获取或创建 logger，确保 handler 不重复。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        fh = logging.FileHandler("logs/client.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
    except Exception:
        pass
    return logger


def get_error_logger(name: str = "ExamApp.Error") -> logging.Logger:
    """获取错误日志记录器，写入 logs/error.log。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    if logger.handlers:
        return logger
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        fh = logging.FileHandler("logs/error.log", encoding="utf-8")
        fh.setLevel(logging.ERROR)
        fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)
    except Exception:
        pass
    return logger


def set_level(level: int) -> None:
    logging.getLogger("ExamApp").setLevel(level)