# 使用依赖代替拦截器，token验证
import logging

from fastapi import Header, HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.app_t import app
from backend.utils.config import Config
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def validate_token_and_refresh(x_token: str = Header(None), x_user_id: str = Header(None)):
    if not x_token:
        logger.error("未传入token...")
        raise HTTPException(401, "请完成登录")
    if not x_user_id:
        logger.error("未传入user_id...")
        raise HTTPException(401, "请传入user_id")
    logger.debug(f"验证token - x_user_id: {x_user_id}, x_token: {x_token}")

    stored_token = app.state.cache.get(f"users:{x_user_id}")
    if not stored_token or stored_token != x_token:
        logger.error(f"token不存在或无效，可能过期。stored_token: {stored_token}, x_token: {x_token}")
        raise HTTPException(401, "token不存在或无效，可能过期")

    # 续期
    app.state.cache.expire(f"users:{x_user_id}", Config.EXPIRE_TIME)
    logger.info(f"token续期成功，{Config.EXPIRE_TIME}")


@app.middleware("http")
async def global_handler(request: Request, call_next):
    if request.url.path in Config.WHITE_LIST:
        response = await call_next(request)
        return response

    # 非白名单，需要鉴权
    try:
        token = request.headers.get(Config.TOKEN_HEADER_KEY)
        user_id = request.headers.get("X-User-Id")
        await validate_token_and_refresh(token, user_id)
    except Exception as e:
        logger.info("鉴权失败")
        return JSONResponse(
            status_code=e.status_code,
            content={"code": e.status_code, "msg": e.detail}
        )

    # 鉴权成功，放行运行
    response = await call_next(request)
    return response

