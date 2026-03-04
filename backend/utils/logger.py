import logging
from backend.utils.config import Config
from backend.utils.handler import DualRotateFileHandler

# 日志格式
formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d - %(name)s - %(process)d - %(thread)d - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 文件Handler
file_handler = DualRotateFileHandler(
    filename=Config.LOG_FILE,
    max_bytes=Config.MAX_BYTES,
    when=Config.TIME_ROTATE_WHEN,
    interval=Config.TIME_ROTATE_INTERVAL,
    backupCount=Config.BACKUP_COUNT,
    encoding=Config.ENCODING,
    utc=Config.UTC
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# 控制台Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    """
    获取配置好的 logger，所有模块共享同样的 handler 配置。

    Args:
        name: 通常传 __name__ 或 __file__

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
