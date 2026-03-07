from psycopg_pool import AsyncConnectionPool
import logging

logger = logging.getLogger(__name__)

async def init_db(pool: AsyncConnectionPool):
    """
    初始化数据库表结构
    """
    try:
        async with pool.connection(timeout=30.0) as conn:
            async with conn.cursor() as cur:
                # 初始化users表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id     integer generated always as identity
                            constraint user_pkey
                                primary key,
                        username    varchar(50)  not null
                            constraint user_username_key
                                unique,
                        password    varchar(255) not null,
                        create_time timestamp default now()
                    )
                """)
                logger.debug("users表初始化完成")
                
                # 初始化sessions表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        thread_id  varchar(255) not null
                            constraint conversations_pkey
                                primary key,
                        user_id    integer         not null,
                        title      varchar(255),
                        created_at timestamp with time zone default now(),
                        updated_at timestamp with time zone default now()
                    )
                """)
                logger.debug("sessions表初始化完成")
                
                # 创建索引
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id
                        on sessions (user_id)
                """)
                logger.debug("索引创建完成")
                
                # 添加默认用户
                await cur.execute("""
                    INSERT INTO users (username, password) VALUES ('admin', '1234') ON CONFLICT (username) DO NOTHING
                """)
                await cur.execute("""
                    INSERT INTO users (username, password) VALUES ('user1', '654321') ON CONFLICT (username) DO NOTHING
                """)
                logger.debug("默认用户添加完成")
        
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
