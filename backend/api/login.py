from fastapi import APIRouter, Body, HTTPException, Header, Request, Depends
from backend.utils.config import Config
from backend.utils.logger import get_logger

logger = get_logger(__name__)

login_router = APIRouter(prefix="/api", tags=["登录相关接口"])


def get_app_state(request: Request):
    """从 Request 中获取应用的 state，避免直接导入 app 造成循环引用。"""
    return request.app.state


# 登录的端点
@login_router.post("/login")
async def login(
        user_name: str = Body(..., embed=True),
        password: str = Body(..., embed=True),
        state=Depends(get_app_state),
):

    user_id = None
    if hasattr(state, "pg_pool") and state.pg_pool is not None:
        try:
            async with state.pg_pool.connection(timeout=30.0) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT user_id FROM users WHERE username = %s AND password = %s",
                        (user_name, password),
                    )
                    result = await cur.fetchone()
                    user_id = result[0] if result else None
        except Exception as e:
            logger.error(f"数据库查询失败: {str(e)}")
            user_id = None

    if not user_id:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    state.user_id = user_id
    logger.debug(f"用户ID: {user_id} ,已存储到应用状态中")

    # 生成token并存储到redis
    import uuid
    token = str(uuid.uuid4())
    if hasattr(state, "cache") and state.cache is not None:
        state.cache.set(f"users:{user_id}", token, ex=Config.EXPIRE_TIME)
    logger.info(f"用户 {user_name} 登录成功，生成token: {token}")

    return {"status": "success", "user_id": user_id, "token": token}


@login_router.delete("/logout")
async def logout(
        x_token: str = Header(None),
        x_user_id: str = Header(None),
        state=Depends(get_app_state),
):
    if not x_token:
        raise HTTPException(status_code=401, detail="未传入token")
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未传入user_id")

    if not hasattr(state, "cache") or state.cache is None:
        raise HTTPException(status_code=500, detail="缓存未初始化")

    # 使用user_id作为key直接查找token
    stored_token = state.cache.get(f"users:{x_user_id}")
    if stored_token == x_token:
        state.cache.delete(f"users:{x_user_id}")
        logger.info(f"用户 {x_user_id} 退出登录，token: {x_token} 已删除")
        return {"status": "success", "message": "退出登录成功"}
    else:
        raise HTTPException(status_code=401, detail="无效的token或已过期")
