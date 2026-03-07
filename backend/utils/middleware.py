# 使用依赖代替拦截器，token验证
import logging

from fastapi import Header, HTTPException, Depends
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.utils.config import Config
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_app_state(request: Request):
    """从 Request 中获取应用的 state，避免直接导入 app 造成循环引用。"""
    return request.app.state


async def validate_token_and_refresh(request: Request):
    token = request.headers.get(Config.TOKEN_HEADER_KEY)
    user_id = request.headers.get("X-User-Id")
    
    if not token:
        logger.error("未传入token...")
        raise HTTPException(401, "请完成登录")
    if not user_id:
        logger.error("未传入user_id...")
        raise HTTPException(401, "请传入user_id")
    logger.debug(f"验证token - x_user_id: {user_id}, x_token: {token}")

    state = get_app_state(request)
    if not hasattr(state, "cache") or state.cache is None:
        logger.error("缓存未初始化")
        raise HTTPException(500, "缓存未初始化")

    stored_token = state.cache.get(f"users:{user_id}")
    if not stored_token or stored_token != token:
        logger.error(f"token不存在或无效，可能过期。stored_token: {stored_token}, x_token: {token}")
        raise HTTPException(401, "token不存在或无效，可能过期")

    # 续期
    state.cache.expire(f"users:{user_id}", Config.EXPIRE_TIME)
    logger.debug(f"token续期成功，{Config.EXPIRE_TIME}")


def create_middleware(app):
    """创建认证中间件"""
    @app.middleware("http")
    async def global_handler(request: Request, call_next):
        if request.url.path in Config.WHITE_LIST:
            response = await call_next(request)
            return response

        # 非白名单，需要鉴权
        try:
            await validate_token_and_refresh(request)
        except HTTPException as e:
            logger.info("鉴权失败")
            return JSONResponse(
                status_code=e.status_code,
                content={"code": e.status_code, "msg": e.detail}
            )
        except Exception as e:
            logger.error(f"鉴权过程中发生错误: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"code": 500, "msg": "服务器内部错误"}
            )

        # 鉴权成功，放行运行
        response = await call_next(request)
        return response
    return global_handler

