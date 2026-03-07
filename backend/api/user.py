from fastapi import APIRouter, Body, HTTPException, Request, Depends, Query
import uuid
from backend.utils.logger import get_logger
from backend.utils.config import Config

logger = get_logger(__name__)

user_router = APIRouter(prefix="/api/user", tags=["用户管理"])


def get_app_state(request: Request):
    """从 Request 中获取应用的 state，避免直接导入 app 造成循环引用。"""
    return request.app.state


@user_router.post("/register")
async def register(
        user_name: str = Body(..., embed=True),
        password: str = Body(..., embed=True),
        state=Depends(get_app_state),
):
    """用户注册接口"""
    # 检查用户名是否已存在
    user_id = None
    if hasattr(state, "pg_pool") and state.pg_pool is not None:
        try:
            async with state.pg_pool.connection(timeout=30.0) as conn:
                async with conn.cursor() as cur:
                    # 检查用户名是否已存在
                    await cur.execute(
                        "SELECT user_id FROM users WHERE username = %s",
                        (user_name,),
                    )
                    result = await cur.fetchone()
                    if result:
                        raise HTTPException(status_code=400, detail="用户名已存在")
                    
                    # 插入新用户
                    await cur.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id",
                        (user_name, password),
                    )
                    # 先等待获取结果，再进行下标访问
                    result = await cur.fetchone()
                    user_id = result[0]
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail="注册失败，请稍后重试")
    else:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    
    # 生成token并存储到redis
    token = str(uuid.uuid4())
    if hasattr(state, "cache") and state.cache is not None:
        state.cache.set(f"users:{user_id}", token, ex=Config.EXPIRE_TIME)
    else:
        logger.warning("缓存未初始化，无法存储token")
    
    logger.info(f"用户 {user_name} 注册成功，用户ID: {user_id}")
    return {"status": "success", "message": "用户注册成功", "user_id": user_id, "token": token}


@user_router.post("/update-username")
async def update_username(
        user_id: int = Body(..., embed=True),
        new_username: str = Body(..., embed=True),
        state=Depends(get_app_state),
):
    """修改用户名接口"""
    if hasattr(state, "pg_pool") and state.pg_pool is not None:
        try:
            async with state.pg_pool.connection(timeout=30.0) as conn:
                async with conn.cursor() as cur:
                    # 检查用户是否存在
                    await cur.execute(
                        "SELECT user_id FROM users WHERE user_id = %s",
                        (user_id,),
                    )
                    result = await cur.fetchone()
                    if not result:
                        raise HTTPException(status_code=404, detail="用户不存在")
                    
                    # 检查新用户名是否已存在
                    await cur.execute(
                        "SELECT user_id FROM users WHERE username = %s AND user_id != %s",
                        (new_username, user_id),
                    )
                    result = await cur.fetchone()
                    if result:
                        raise HTTPException(status_code=400, detail="用户名已存在")
                    
                    # 更新用户名
                    await cur.execute(
                        "UPDATE users SET username = %s WHERE user_id = %s",
                        (new_username, user_id),
                    )
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail="修改用户名失败，请稍后重试")
    else:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    
    logger.info(f"用户ID {user_id} 修改用户名成功，新用户名: {new_username}")
    return {"status": "success", "message": "修改用户名成功", "new_username": new_username}


@user_router.post("/update-password")
async def update_password(
        user_id: int = Body(..., embed=True),
        old_password: str = Body(..., embed=True),
        new_password: str = Body(..., embed=True),
        state=Depends(get_app_state),
):
    """修改密码接口"""
    if hasattr(state, "pg_pool") and state.pg_pool is not None:
        try:
            async with state.pg_pool.connection(timeout=30.0) as conn:
                async with conn.cursor() as cur:
                    # 检查用户是否存在且旧密码正确
                    await cur.execute(
                        "SELECT user_id FROM users WHERE user_id = %s AND password = %s",
                        (user_id, old_password),
                    )
                    result = await cur.fetchone()
                    if not result:
                        raise HTTPException(status_code=401, detail="用户不存在或旧密码错误")
                    
                    # 更新密码
                    await cur.execute(
                        "UPDATE users SET password = %s WHERE user_id = %s",
                        (new_password, user_id),
                    )
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail="修改密码失败，请稍后重试")
    else:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    
    logger.info(f"用户ID {user_id} 修改密码成功")
    return {"status": "success", "message": "修改密码成功"}


@user_router.get("/info")
async def get_user_info(
        user_id: int = Query(..., embed=True),
        state=Depends(get_app_state),
):
    """获取用户信息接口"""
    if hasattr(state, "pg_pool") and state.pg_pool is not None:
        try:
            async with state.pg_pool.connection(timeout=30.0) as conn:
                async with conn.cursor() as cur:
                    # 查询用户信息
                    await cur.execute(
                        "SELECT user_id, username, create_time FROM users WHERE user_id = %s",
                        (user_id,),
                    )
                    result = await cur.fetchone()
                    if not result:
                        raise HTTPException(status_code=404, detail="用户不存在")
                    
                    user_info = {
                        "user_id": result[0],
                        "username": result[1],
                        "create_time": result[2]
                    }
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取用户信息失败，请稍后重试")
    else:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    
    logger.info(f"获取用户ID {user_id} 的信息成功")
    return {"status": "success", "user_info": user_info}