"""统一日志配置"""
import logging, logging.handlers, sys, os

_LOG_CONFIGURED = False

def setup(name="survey", level=logging.INFO, log_file=None):
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return logging.getLogger(name)
    _LOG_CONFIGURED = True

    logger = logging.getLogger(name)
    logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
