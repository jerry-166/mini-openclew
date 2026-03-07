import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any

import dotenv
import redis
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage, AIMessageChunk, HumanMessage, message_to_dict, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool

from backend.api.login import login_router
from backend.api.user import user_router
from backend.utils.config import Config
from backend.utils.logger import get_logger
from backend.utils.middleware import create_middleware
from tools.core_tools import get_core_tools
from tools.memory_manager import MemoryManager
from tools.skills_manager import SkillsManager

# 使用统一的日志配置
logger = get_logger(__name__)
logger.debug("日志处理器加载完毕")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 初始化核心组件
        app.state.skills_manager = SkillsManager()
        app.state.memory_manager = MemoryManager()
        app.state.core_tools = get_core_tools()
        logger.info("核心组件初始化完成")

        # 生成技能快照
        app.state.skills_manager.generate_skills_snapshot()
        logger.debug("技能快照生成完成")

        # 配置Redis连接
        redis_client = redis.Redis(
            host="localhost",
            port=6379,
            db=6,
            # password="1234",  # 如果 Redis 没有配置密码，注释掉此行
            decode_responses=True,
        )
        app.state.cache = redis_client

        dotenv.load_dotenv()

        app.state.llm = ChatOpenAI(
            model=os.getenv("MODEL"),
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY", "sk-placeholder"),
            temperature=0.7
        )
        logger.debug("LLM模型加载完成")

        # 构建postgres异步连接
        pool = AsyncConnectionPool(
            conninfo=Config.DB_URL,
            open=False,
            min_size=Config.MIN_SIZE,
            max_size=Config.MAX_SIZE,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            timeout=Config.TIMEOUT,
        )
        app.state.pg_pool = pool
        await pool.open()
        logger.info("Postgres 连接池已创建并打开")

        # 使用一个临时连接做探针检活
        async with pool.connection(timeout=30.0) as conn:
            await conn.execute("SELECT 1")
            logger.debug("Postgres 连接池探针检活成功")

        # 创建异步postgres保存器和存储器
        saver = AsyncPostgresSaver(conn=pool)
        await saver.setup()  # 初始化数据库表结构
        store = AsyncPostgresStore(conn=pool)
        await store.setup()  # 初始化数据库表结构
        logger.info("数据库检查点保存器和存储已创建并初始化")
        
        # 初始化数据库表结构
        from backend.utils.db_init import init_db
        await init_db(pool)

        # 构建Agent
        app.state.agent = create_agent(
            tools=app.state.core_tools,
            system_prompt=app.state.memory_manager.get_system_prompt(),
            model=app.state.llm,
            checkpointer=saver,
            store=store,
            # context_schema="", 目前不使用
        )
        logger.info("智能体创建完成")

        yield  # 将控制交给应用
    except Exception as e:
        logger.error(f"应用启动时发生错误: {str(e)}")
        raise RuntimeError(f"服务初始化失败：{str(e)}")
    finally:
        if "pool" in locals() and pool is not None:
            await pool.close()
        if "redis_client" in locals() and redis_client is not None:
            redis_client.close()
        logger.info("关闭服务并完成资源清理")


app = FastAPI(
    title="Mini-OpenClaw API",
    description="基于LangChain的AI Agent系统API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建并添加认证中间件
create_middleware(app)

# 添加路由
app.include_router(login_router)
app.include_router(user_router)


# 会话管理
def get_session_file_by_id(session_id: str) -> str:
    """根据 session ID 获取会话文件路径"""
    return os.path.join("sessions", f"{session_id}.json")


# 新增辅助函数：将 LangChain 消息列表转换为可存储的字典列表
def serialize_for_json(value: Any) -> Any:
    """Recursively convert LangChain messages and containers into JSON-serializable data."""
    if isinstance(value, BaseMessage):
        return message_to_dict(value)
    if isinstance(value, list):
        return [serialize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_for_json(val) for key, val in value.items()}
    return value


def messages_to_serializable(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """将 BaseMessage 列表转换为可 JSON 序列化的字典列表"""
    return [message_to_dict(msg) for msg in messages]


async def load_session(session_id: str) -> List[BaseMessage]:
    try:
        # 从 LangGraph 检查点获取会话状态
        config = {"configurable": {"thread_id": session_id}}
        state = await app.state.agent.aget_state(config)
        messages = state.values.get("messages", [])
        return messages
    except Exception as e:
        logger.error(f"加载会话失败: {str(e)}")
        return []


# 修改 save_session：接收 BaseMessage 列表，序列化后保存
def save_session(session_id: str, messages: List[BaseMessage]):
    session_file = get_session_file_by_id(session_id)
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    serializable = messages_to_serializable(messages)
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


# 修改 chat 端点
@app.post("/api/chat")
async def chat(
        message: str = Body(..., embed=True),
        user_id: int = Body(..., embed=True),
        session_id: str = Body(..., embed=True),
        stream: bool = Body(True, embed=True)
):
    # 加载会话历史（现为 BaseMessage 列表）
    messages = await load_session(session_id)

    # 添加用户消息
    messages.append(HumanMessage(content=message))

    # 配置 LangGraph 的线程 ID，用于后续获取状态
    config = {"configurable": {"thread_id": session_id, "user_id": user_id}}

    # 使用 Agent 处理用户请求
    async def generate_response():
        try:
            # 生成思考过程
            payload = {"type": "thought", "content": "正在分析用户请求..."}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.5)

            # 存储最终消息列表的占位符（将在流结束后通过 get_state 获取）
            final_messages = None
            # 可选：收集工具调用/结果用于即时推送（与之前相同）
            async for stream_mode, data in app.state.agent.astream(
                    {"messages": messages},
                    stream_mode=["updates", "messages"],
                    config=config  # 传入 config
            ):
                if stream_mode == "messages":
                    if isinstance(data[0], AIMessageChunk):
                        # 推送文本块（与之前相同）
                        payload = {"type": "message_chunk", "content": data[0].content}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if stream_mode == "updates":
                    if "tools" in data:
                        tools_data = data['tools']
                        serializable_tools = serialize_for_json(tools_data)
                        payload = {"type": "tool_result", "content": serializable_tools}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    elif "model" in data:
                        if data['model']['messages'][0].tool_calls:
                            tool_calls = serialize_for_json(data['model']['messages'][0].tool_calls)
                            payload = {"type": "tool_call", "content": tool_calls}
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 流结束后，通过 agent.aget_state 获取最终状态中的消息列表
            state = await app.state.agent.aget_state(config)
            final_messages = state.values.get("messages", [])

            # 保存完整消息历史
            save_session(session_id, final_messages)
            logger.info("chat接口---会话保存成功，session_id: %s, 消息数量: %s", session_id, len(final_messages))
        except Exception as e:
            # 错误处理
            error_message = f"处理请求时发生错误: {str(e)}"
            payload = {"type": "error", "content": error_message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            # 保存错误信息（作为 AI 消息）
            error_msg = AIMessage(content=error_message)
            save_session(session_id, messages + [error_msg])
            logger.error("chat接口---发生错误，session_id: %s, 错误信息: %s", session_id, error_message)

    if stream:
        return StreamingResponse(generate_response(), media_type="text/event-stream")
    else:
        # 非流式响应
        try:
            result = app.state.agent.invoke({"messages": messages}, config=config)
            # result 通常是包含最终状态 dict，其中 "messages" 键为消息列表
            final_messages = result.get("messages", [])
            save_session(session_id, final_messages)
            # 返回最后一条 AI 消息的内容
            last_ai_message = next((msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)), None)
            logger.info("chat接口---非流式响应，session_id: %s, 消息数量: %s", session_id, len(final_messages))
            return {"response": last_ai_message.content if last_ai_message else ""}
        except Exception as e:
            error_message = f"处理请求时发生错误: {str(e)}"
            error_msg = AIMessage(content=error_message)
            save_session(session_id, messages + [error_msg])
            logger.error("chat接口---非流式响应发生错误，session_id: %s, 错误信息: %s", session_id, error_message)

            raise HTTPException(status_code=500, detail=error_message)


# 修改 get_history 端点：返回历史消息时，转换为前端友好的格式
@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    try:
        config = {"configurable": {"thread_id": session_id}}
        state = await app.state.agent.aget_state(config)
        messages = state.values.get("messages", [])
        logger.critical(f"获取历史消息，session_id: {session_id}, 消息数量: {len(messages)}")
        # 转换为前端可用的格式（保留原始结构，或简化）
        simplified = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                simplified.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                # 如果有 tool_calls，可以额外包含
                entry = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                simplified.append(entry)
            elif isinstance(msg, ToolMessage):
                simplified.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                    "content": msg.content
                })
        return {"messages": simplified}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# todo：需要根据不同用户去区分skills
@app.get("/api/skills/list")
async def list_skills():
    """列出所有可用技能"""
    try:
        skills = app.state.skills_manager.scan_skills()
        return {"skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def get_file(path: str):
    """读取指定文件的内容"""
    try:
        # 安全检查：防止路径遍历
        if ".." in path:
            raise HTTPException(status_code=403, detail="Invalid path")

        # 尝试不同的目录
        possible_paths = [
            os.path.join("memory", path),
            os.path.join("skills", path),
            os.path.join("workspace", path),
            Path(__file__).parent / path
        ]

        file_path = None
        for p in possible_paths:
            if os.path.exists(p):
                file_path = p
                break

        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files")
async def save_file(path: str = Body(..., embed=True), content: str = Body(..., embed=True)):
    """保存对Memory或Skill文件的修改"""
    try:
        # 安全检查：防止路径遍历
        if ".." in path:
            raise HTTPException(status_code=403, detail="Invalid path")

        # 尝试不同的目录
        possible_bases = ["memory", "skills", "workspace"]
        file_path = None

        # 检查路径是否已经包含基础目录
        for base in possible_bases:
            if path.startswith(base):
                file_path = path
                break

        # 如果不包含基础目录，默认保存到memory目录
        if not file_path:
            file_path = os.path.join("memory", path)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    try:
        # 删除数据库信息
        async with app.state.pg_pool.connection(timeout=30.0) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT thread_id FROM sessions WHERE thread_id = %s",
                    (session_id,)
                )
                result = await cur.fetchone()
                if not result or not result[0]:
                    logger.error("会话ID %s 不存在，无法删除", session_id)
                    raise HTTPException(status_code=404, detail="Session not found in database")

                await cur.execute(
                    "DELETE FROM sessions WHERE thread_id = %s",
                    (session_id,)
                )
                logger.debug("会话删除成功，session_id: %s", session_id)
        # 删除sessions目录下的会话文件（如果存在）
        session_file = get_session_file_by_id(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.debug("会话文件删除成功，session_id: %s, file_path: %s", session_id, session_file)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, name: str = Body(..., embed=True)):
    """重命名指定会话"""
    try:
        # 需要传入用户id吗？不需要，因为thread_id是主键，不会重复
        async with app.state.pg_pool.connection(timeout=30.0) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT thread_id FROM sessions WHERE thread_id = %s",
                    (session_id,)
                )
                result = await cur.fetchone()
                if not result or not result[0]:
                    logger.error("会话ID %s 不存在，无法重命名", session_id)
                    raise HTTPException(status_code=404, detail="Session not found in database")

                await cur.execute(
                    "UPDATE sessions SET title = %s WHERE thread_id = %s",
                    (name, session_id)
                )
                logger.debug("会话标题更新成功，session_id: %s, new_name: %s", session_id, name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions")
async def create_session(
        session_id: str = Body(..., embed=True),
        user_id: int = Body(..., embed=True),
        session_name: str = Body(..., embed=True)
):
    """创建新会话"""
    try:
        async with app.state.pg_pool.connection(timeout=30.0) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id FROM users WHERE user_id = %s",
                    (user_id,)
                )
                result = await cur.fetchone()
                if not result or not result[0]:
                    logger.error("用户ID %s 不存在，无法创建会话", user_id)
                    raise HTTPException(status_code=404, detail="没有发现该用户")

                await cur.execute(
                    "INSERT INTO sessions (thread_id, user_id, title) VALUES (%s, %s, %s)",
                    (session_id, user_id, session_name)
                )
                logger.debug("会话创建成功，session_id: %s, session_name: %s, user_id: %s", session_id, session_name, user_id)

        return {"status": "success", "session_id": session_id, "session_name": session_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def get_sessions(user_id: int = Query(...)):
    """获取用户的会话列表"""
    try:
        sessions = []
        
        # 从数据库中获取会话列表
        async with app.state.pg_pool.connection(timeout=30.0) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT thread_id, title FROM sessions WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                rows = await cur.fetchall()
                if not rows:
                    logger.info("用户ID %s 没有会话记录", user_id)

                for row in rows:
                    sessions.append({
                        "session_id": row[0],
                        "session_name": row[1]
                    })

        logger.info("获取会话列表成功，user_id: %s, 会话数量: %s", user_id, len(sessions))
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    from asyncio.windows_events import WindowsSelectorEventLoopPolicy
    import traceback

    try:
        print("Starting server...")
        # 确保 uvicorn 使用兼容的事件循环
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

        # 在当前策略下显式创建事件循环，避免ProactorEventLoop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        print("Server configuration created")
        config = uvicorn.Config(app, host="127.0.0.1", port=8002, loop="asyncio", log_level="info")
        server = uvicorn.Server(config)
        print("Starting server with uvicorn...")
        loop.run_until_complete(server.serve())
    except Exception as e:
        print(f"Error starting server: {e}")
        traceback.print_exc()
