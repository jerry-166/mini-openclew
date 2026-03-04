import os


class Config:
    # 日志配置
    LOG_FILE = os.getenv("LOG_FILE", "./log/app.log")
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    TIME_ROTATE_WHEN = "d"  # 按天轮转
    MAX_BYTES = 10 * 1024 * 1024  # 单个日志文件最大10MB
    TIME_ROTATE_INTERVAL = 1  # 间隔1个单位轮转
    BACKUP_COUNT = 7  # 保留最近7个历史文件
    ENCODING = "utf-8"  # 日志文件编码，保证可读
    UTC = False  # 使用本地时间（True是utc时间）

    # 数据库连接配置
    DB_URL = os.getenv("DB_URL", "postgresql://postgres:1234@127.0.0.1:5432/mini_openclaw?sslmode=disable")
    MIN_SIZE = 4
    MAX_SIZE = 10
    TIMEOUT = 60.0

    # redis
    HOST = "127.0.0.1"
    PORT = 6379
    EXPIRE_TIME = 3600
    TOKEN_HEADER_KEY = "X-Token"
    # 无需鉴权的接口路径（白名单）
    WHITE_LIST = ["/api/login", "/docs", "/openapi.json", "/redoc"]  # 包含接口文档相关路径




