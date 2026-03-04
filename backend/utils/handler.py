import logging
import os.path
import time

from concurrent_log_handler import ConcurrentTimedRotatingFileHandler, LogFilenameType

from backend.utils.config import Config


class DualRotateFileHandler(ConcurrentTimedRotatingFileHandler):
    def __init__(self, filename: LogFilenameType, max_bytes: int, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.max_bytes = max_bytes  # 最大轮转文件大小

    def emit(self, record: logging.LogRecord) -> None:
        """重写emit方法，写入前检查文件大小，超过则主动轮转"""
        if os.path.exists(self.baseFilename) and os.path.getsize(self.baseFilename) >= self.max_bytes:
            # 判断文件大小是否超过设定的最大值，超过则进行轮转，调用父类的方法
            self.doRollover()
        # 执行原始的日志写入逻辑
        super().emit(record)


if __name__ == "__main__":
    # 配置日志信息
    logger = logging.getLogger(__name__)
    # 设置日志级别
    logger.setLevel(logging.DEBUG)
    # 清空默认的处理器，避免重复日志
    logger.handlers = []
    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - %(name)s - %(process)d - %(thread)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"  # 统一时间格式
    )
    # 添加自定义的DualRotateFileHandler
    time_file_handler = DualRotateFileHandler(
        filename=Config.LOG_FILE,
        max_bytes=Config.MAX_BYTES,  # 大小轮转：5MB
        when=Config.TIME_ROTATE_WHEN,  # 时间轮转：按天
        interval=Config.TIME_ROTATE_INTERVAL,  # 每天轮转1次
        backupCount=Config.BACKUP_COUNT,  # 保留10个历史文件
        encoding=Config.ENCODING,  # 指定编码
        utc=Config.UTC  # 使用本地时间（True=UTC时间）
    )
    time_file_handler.setLevel(logging.DEBUG)
    time_file_handler.setFormatter(formatter)
    logger.addHandler(time_file_handler)

    # 模拟生成大量日志，触发大小轮转
    for i in range(100):
        logger.debug(f"测试双轮转日志 - {i}")
        time.sleep(0.001)  # 轻微延迟，避免生成过快

    # # 等待一段时间后（或手动修改系统时间），验证时间轮转
    # time.sleep(86400)  # 等待1天（测试按天轮转）
    # logger.info("测试时间轮转触发")
