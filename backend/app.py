import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage, AIMessageChunk
from langchain_openai import ChatOpenAI

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
    model=llm
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
def get_session_file(session_id: str) -> str:
    return os.path.join("sessions", f"{session_id}.json")


def load_session(session_id: str) -> List[Dict[str, Any]]:
    session_file = get_session_file(session_id)
    if os.path.exists(session_file):

        with open(session_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_session(session_id: str, messages: List[Dict[str, Any]]):
    session_file = get_session_file(session_id)
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


# API接口
@app.post("/api/chat")
async def chat(
        message: str = Body(..., embed=True),
        session_id: str = Body(..., embed=True),
        stream: bool = Body(True, embed=True)
):
    """核心对话接口"""
    # 加载会话历史
    messages = load_session(session_id)

    # 添加用户消息
    messages.append({"role": "user", "content": message})

    # 使用Agent处理用户请求
    async def generate_response():
        try:
            # 生成思考过程
            payload = {"type": "thought", "content": "正在分析用户请求..."}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.5)

            # 调用Agent（使用invoke方法，LangChain 1.x的新API）
            result = agent.invoke({"messages": messages})

            # 生成工具调用过程（简化版，实际项目中可以捕获工具调用事件）
            for msg in result["messages"]:
                if isinstance(msg, AIMessage):
                    if not msg.tool_calls:
                        break
                    for tool_call in msg.tool_calls:
                        print(f"正在调用{tool_call['name']}处理请求...")
                        payload = {"type": "tool_call", "content": f"正在调用{tool_call['name']}处理请求..."}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.5)
                if isinstance(msg, ToolMessage):
                    if msg.status == "success":
                        print(f"[{msg.type}] {msg.tool_call_id}-{msg.name}调用成功，结果: {msg.text}")
                        payload = {"type": "tool_result", "content": f"{msg.name}调用成功，结果: {msg.text}"}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 生成最终回复
            payload = {"type": "message", "content": result["messages"][-1].content}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 保存会话
            messages.append({"role": "assistant", "content": result["messages"][-1].content})
            save_session(session_id, messages)
        except Exception as e:
            # 处理错误
            error_message = f"处理请求时发生错误: {str(e)}"
            payload = {"type": "error", "content": error_message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 保存错误信息到会话
            messages.append({"role": "assistant", "content": error_message})
            save_session(session_id, messages)

    if stream:
        return StreamingResponse(generate_response(), media_type="text/event-stream")
    else:
        # 非流式响应
        try:
            agent_input = {"messages": messages}
            result = agent.invoke(agent_input)
            messages.append({"role": "assistant", "content": result["messages"][-1].content})
            save_session(session_id, messages)
            return {"response": result["messages"][-1].content}
        except Exception as e:
            error_message = f"处理请求时发生错误: {str(e)}"
            messages.append({"role": "assistant", "content": error_message})
            save_session(session_id, messages)
            raise HTTPException(status_code=500, detail=error_message)


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """获取指定会话的历史消息，返回格式为[{role: "user/assistant", content: "消息内容"}, ...]"""
    try:
        messages = load_session(session_id)
        return {"messages": messages}
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
async def get_sessions():
    """获取所有历史会话列表"""
    try:
        sessions_dir = "sessions"
        if not os.path.exists(sessions_dir):
            return {"sessions": []}

        sessions = []
        for filename in os.listdir(sessions_dir):
            if filename.endswith(".json"):
                session_id = filename[:-5]  # 去掉.json后缀
                sessions.append(session_id)

        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    try:
        session_file = get_session_file(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
