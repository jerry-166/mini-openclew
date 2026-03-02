import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Literal, Optional

import dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage, AIMessageChunk, HumanMessage, messages_from_dict, \
    message_to_dict, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from tools.core_tools import get_core_tools
from tools.memory_manager import MemoryManager
from tools.skills_manager import SkillsManager

# 初始化核心组件
skills_manager = SkillsManager()
memory_manager = MemoryManager()
core_tools = get_core_tools()

# 生成技能快照
skills_manager.generate_skills_snapshot()

dotenv.load_dotenv()

llm = ChatOpenAI(
    model=os.getenv("MODEL"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY", "sk-placeholder"),
    temperature=0.7
)

# 构建Agent
agent = create_agent(
    tools=core_tools,
    system_prompt=memory_manager.get_system_prompt(),
    model=llm,
    checkpointer=InMemorySaver()
)

app = FastAPI(
    title="Mini-OpenClaw API",
    description="基于LangChain的AI Agent系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 会话管理
def get_session_file_by_id(session_id: str) -> str:
    """根据 session ID 获取会话文件路径"""
    return os.path.join("sessions", f"{session_id}.json")

def get_session_name_by_id(session_id: str) -> str:
    """根据 session ID 获取 session name"""
    path = os.path.join("sessions", "name_id_map.json")
    # 确保文件存在
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(path, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    for item in data_list:
        if item["session_id"] == session_id:
            return item["session_name"]
    return session_id  # 如果未找到，返回 ID 本身

def get_session_id_by_name(session_name: str) -> str:
    """根据 session name 获取 session ID"""
    path = os.path.join("sessions", "name_id_map.json")
    # 确保文件存在
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(path, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    for item in data_list:
        if item["session_name"] == session_name:
            return item["session_id"]
    return session_name  # 如果未找到，返回 name 本身

def get_session_file_by_name(session_name: str) -> str:
    """根据 session name 获取会话文件路径"""
    session_id = get_session_id_by_name(session_name)
    return get_session_file_by_id(session_id)


def update_session_map(
        type: Literal["add", "delete", "rename"],
        session_name: str,
        session_id: Optional[str] = None
) -> bool:
    path = os.path.join("sessions", "name_id_map.json")
    # 创建目录
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 确保文件存在
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    # 读取文件
    with open(path, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    # 处理不同类型的操作
    if type == "add" and session_id:
        data_list.append({"session_name": session_name, "session_id": session_id})
    elif type == "delete":
        data_list = [item for item in data_list if item["session_name"] != session_name]
    elif type == "rename" and session_id:
        for item in data_list:
            if item["session_id"] == session_id:
                item["session_name"] = session_name
    # 保存文件
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    return True


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


# 修改 load_session：兼容新旧格式，并转换为 BaseMessage 列表
def load_session(session_id: str) -> List[BaseMessage]:
    session_file = get_session_file_by_id(session_id)
    if os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 如果是旧格式（仅有 role/content），转换为标准消息字典
        if data and "role" in data[0] and "content" in data[0] and "type" not in data[0]:
            # 旧格式转换：user->HumanMessage, assistant->AIMessage
            new_data = []
            for msg in data:
                if msg["role"] == "user":
                    new_data.append({"type": "human", "data": {"content": msg["content"]}})
                elif msg["role"] == "assistant":
                    new_data.append({"type": "ai", "data": {"content": msg["content"]}})
                # 旧格式没有 tool messages, 忽略
            data = new_data
        # 使用 LangChain 内置反序列化
        return messages_from_dict(data)
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
        session_id: str = Body(..., embed=True),
        stream: bool = Body(True, embed=True)
):
    # 加载会话历史（现为 BaseMessage 列表）
    messages = load_session(session_id)

    # 添加用户消息
    messages.append(HumanMessage(content=message))

    # 配置 LangGraph 的线程 ID，用于后续获取状态
    config = {"configurable": {"thread_id": session_id}}

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
            async for stream_mode, data in agent.astream(
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
            state = await agent.aget_state(config)
            final_messages = state.values.get("messages", [])

            # 保存完整消息历史
            save_session(session_id, final_messages)

        except Exception as e:
            # 错误处理
            error_message = f"处理请求时发生错误: {str(e)}"
            payload = {"type": "error", "content": error_message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            # 保存错误信息（作为 AI 消息）
            error_msg = AIMessage(content=error_message)
            save_session(session_id, messages + [error_msg])

    if stream:
        return StreamingResponse(generate_response(), media_type="text/event-stream")
    else:
        # 非流式响应
        try:
            result = agent.invoke({"messages": messages}, config=config)
            # result 通常是包含最终状态 dict，其中 "messages" 键为消息列表
            final_messages = result.get("messages", [])
            save_session(session_id, final_messages)
            # 返回最后一条 AI 消息的内容
            last_ai_message = next((msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)), None)
            return {"response": last_ai_message.content if last_ai_message else ""}
        except Exception as e:
            error_message = f"处理请求时发生错误: {str(e)}"
            error_msg = AIMessage(content=error_message)
            save_session(session_id, messages + [error_msg])
            raise HTTPException(status_code=500, detail=error_message)


# 修改 get_history 端点：返回历史消息时，转换为前端友好的格式
@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    try:
        messages = load_session(session_id)  # 返回 BaseMessage 列表
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


@app.get("/api/skills/list")
async def list_skills():
    """列出所有可用技能"""
    try:
        skills = skills_manager.scan_skills()
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


@app.get("/api/sessions")
async def get_sessions_map():
    """获取name_id_list"""
    try:
        sessions_dir = "sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        path = os.path.join(sessions_dir, f"name_id_map.json")

        if not os.path.exists(path):
            return {"sessions": []}

        with open(path, "r", encoding="utf-8") as f:
            name_id_map_list = json.load(f)

        return {"sessions": name_id_map_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    try:
        # 删除对应的文件和映射
        session_file = get_session_file_by_id(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
            # 删除映射(读取，删除，保存)
            session_name = get_session_name_by_id(session_id)
            update_session_map("delete", session_name)
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, name: str = Body(..., embed=True)):
    """重命名指定会话"""
    try:
        # 通过更改映射文件中的映射修改会话名称(读取，修改，保存)
        update_session_map("rename", name, session_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions")
async def create_session(session_id: str = Body(..., embed=True), session_name: str = Body(..., embed=True)):
    """创建新会话"""
    try:
        # 创建会话文件
        session_file = get_session_file_by_id(session_id)
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        # 添加到映射
        update_session_map("add", session_name, session_id)
        
        return {"status": "success", "session_id": session_id, "session_name": session_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
