import json
import logging
import os
import re
import secrets
import uuid
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, UploadFile, File
from pydantic import BaseModel

import yaml
from core.session import SessionManager

# 加载配置：环境变量优先，其次 config.yaml，最后默认值
# Docker 部署时通过 -e 参数传入，不需要把 Key 写进镜像
config_path = "config.yaml"
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

llm_config = config.get("llm", {})
server_config = config.get("server", {})

api_key   = os.environ.get("LLM_API_KEY")   or llm_config.get("api_key")
base_url  = os.environ.get("LLM_BASE_URL")  or llm_config.get("base_url")
model     = os.environ.get("LLM_MODEL")     or llm_config.get("model", "gpt-4o-mini")

# 接口鉴权 Token（可选）：环境变量 SMARTFLOW_API_TOKEN 优先，其次 config.yaml 的 server.api_token
# 未配置时鉴权关闭（本地演示模式）；配置后所有 /api/* 接口需要 Authorization: Bearer <token>
api_token = os.environ.get("SMARTFLOW_API_TOKEN") or server_config.get("api_token", "")

workspace_path = "./workspace"
outputs_path = os.path.join(workspace_path, "outputs")
os.makedirs(outputs_path, exist_ok=True)

# 会话管理器：全局共享无状态组件（LLM client/skills/knowledge/tools），
# 按 session_id 隔离对话记忆与审批状态（多会话支持）
manager = SessionManager(
    workspace_dir=workspace_path,
    openai_api_key=api_key,
    base_url=base_url,
    model=model
)

# 会话 ID 校验：仅允许字母数字与 -_（用于路径参数，防注入）
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

app = FastAPI(title="SmartFlow API")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    接口鉴权中间件（可选开启）。
    - 未配置 api_token 时：完全放行（本地演示模式）
    - 配置后：所有 /api/* 接口及 /outputs/* 文件下载必须携带
      Authorization: Bearer <token>
    - 静态资源（/ 页面、/static）保持开放，方便直接浏览 UI
    使用 secrets.compare_digest 做常数时间比较，防止时序攻击。
    """
    if not api_token:
        return await call_next(request)

    path = request.url.path
    if not path.startswith("/api/") and not path.startswith("/outputs/"):
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not secrets.compare_digest(token, api_token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: 缺少或错误的 API Token，请设置 SMARTFLOW_API_TOKEN"}
        )
    return await call_next(request)

# 挂载静态资源
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

@app.get("/")
async def root():
    """返回前端主页"""
    return FileResponse("static/index.html")

class ChatRequest(BaseModel):
    message: str
    session: str = "default"

class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool
    session: str = "default"

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    流式对话接口（SSE）。
    body 可带 session 字段（默认 default），不同会话记忆互相隔离。
    同一会话的并发请求通过 per-session Lock 串行化，
    且锁覆盖整个流式生成周期，防止流式期间插入新请求破坏工具调用链。
    """
    agent = manager.get(req.session)

    async def sse_generator() -> AsyncGenerator[str, None]:
        async with manager.lock(req.session):
            # 遍历 agent_loop 的每一个步骤触发的字典事件
            async for event in agent.chat_stream(req.message):
                # 将 python 字典格式化为 JSON 字符串
                data_str = json.dumps(event, ensure_ascii=False)
                # SSE 要求格式以 data: 开头，以 \n\n 结尾
                yield f"data: {data_str}\n\n"

    # 指定媒体类型为 text/event-stream 这是 SSE 标准的配置
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.post("/api/approve")
async def approve_endpoint(req: ApprovalRequest):
    """
    人工审批接口 (Human-in-the-Loop)。
    前端在收到 approval_required 事件后弹窗，用户点击同意/拒绝，
    通过本接口把结果回传，唤醒挂起在 loop 中的高风险工具调用。
    session 字段用于把审批路由到正确的会话（每个会话有独立的审批管理器）。
    """
    ok = manager.resolve_approval(req.session, req.approval_id, req.approved)
    if ok:
        return {"status": "ok", "approved": req.approved}
    # 请求不存在或已超时被清理
    return {"status": "error", "message": "审批请求不存在或已超时"}

@app.get("/api/status")
async def get_status():
    """获取侧边栏展示的相关状态（技能/工具为全局共享组件，与会话无关）"""
    return manager.get_status()

@app.get("/api/memory")
async def get_memory(session: str = "default"):
    """获取指定会话的上下文和长期记忆"""
    agent = manager.get(session)
    messages = agent.memory.get_messages(window_size=20)
    system_prompt = agent.context.build_system_prompt()
    long_term_memory = agent.memory.get_long_term_memory()
    
    # 统计信息
    stats = {
        "total_messages_in_window": len(messages),
        "has_long_term_memory": bool(long_term_memory)
    }
    
    return {
        "stats": stats,
        "long_term_memory": long_term_memory,
    }

@app.get("/api/history")
async def get_history(session: str = "default"):
    """获取指定会话的完整历史与累积 token 消耗用于前端恢复渲染"""
    agent = manager.get(session)
    return {
        "messages": agent.memory.messages,
        "tokens": agent.memory.get_tokens()
    }

@app.get("/api/outputs")
async def list_outputs():
    """获取工作区所有的输出文件列表"""
    files = []
    if os.path.exists(outputs_path):
        for f in os.listdir(outputs_path):
            file_path = os.path.join(outputs_path, f)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "name": f,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })
        # 按修改时间倒序（最新的在前面）
        files.sort(key=lambda x: x["mtime"], reverse=True)
    return {"files": files}

@app.delete("/api/outputs/{filename}")
async def delete_output(filename: str):
    """Delete a specific file from the workspace outputs directory"""
    # Security: Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return {"status": "error", "message": "Invalid filename"}
        
    file_path = os.path.join(outputs_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return {"status": "success", "message": f"Deleted {filename}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "error", "message": "File not found"}

@app.get("/api/outputs/download/{filename}")
async def download_output(filename: str):
    """
    下载/预览工作区输出文件。
    受鉴权中间件保护（/api/* 前缀），前端通过 fetch + Bearer Token 访问。
    开启鉴权后，静态挂载的 /outputs/* 路径同样被中间件拦截，因此文件必须走本接口。
    """
    # Security: Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse(status_code=400, content={"detail": "Invalid filename"})

    file_path = os.path.join(outputs_path, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return JSONResponse(status_code=404, content={"detail": "File not found"})

    return FileResponse(file_path, filename=filename)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件到 workspace outputs 目录"""
    if not os.path.exists(outputs_path):
        os.makedirs(outputs_path, exist_ok=True)
    # 安全防护：仅取文件名，防止路径穿越（如 ../../evil.py）
    safe_name = os.path.basename(file.filename or "")
    if not safe_name:
        return {"status": "error", "message": "Invalid filename"}
    file_path = os.path.join(outputs_path, safe_name)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"status": "success", "filename": safe_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/clear")
async def clear_memory(session: str = "default"):
    """清空指定会话的记忆（只影响该会话）"""
    manager.clear(session)
    return {"status": "ok"}

# ------------------------------------------------------------------ #
# 会话管理（多会话隔离）                                                #
# ------------------------------------------------------------------ #

@app.get("/api/sessions")
async def list_sessions():
    """获取所有会话的列表与统计（消息数、最后活跃时间）"""
    sessions = await _to_thread(manager.list_sessions)
    return {"sessions": sessions}

@app.post("/api/sessions")
async def create_session():
    """新建一个会话，返回 session_id"""
    session_id = uuid.uuid4().hex[:12]
    manager.get(session_id)  # 预创建：初始化 memory 目录与表
    return {"session_id": session_id}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话（记忆与统计一并清除）"""
    if not _SESSION_ID_RE.match(session_id):
        return {"status": "error", "message": "Invalid session_id"}
    if session_id == "default":
        return {"status": "error", "message": "默认会话不能删除"}
    ok = await _to_thread(manager.delete, session_id)
    if ok:
        return {"status": "success", "message": f"会话 {session_id} 已删除"}
    return {"status": "error", "message": "会话不存在或删除失败"}

# 同步函数包装到线程池，避免阻塞事件循环（SQLite 查询）
async def _to_thread(func, *args):
    import asyncio
    return await asyncio.to_thread(func, *args)

@app.post("/api/knowledge/add")
async def add_to_knowledge(file: UploadFile = File(...)):
    """
    上传文档到知识库（RAG）。
    支持 .txt / .md 格式。文档会被切片、向量化并存入本地向量数据库。
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".txt", ".md"]:
        return {"status": "error", "message": "仅支持 .txt 和 .md 格式"}

    # 先保存到 outputs 目录，再导入知识库
    # 安全防护：仅取文件名，防止路径穿越
    safe_name = os.path.basename(file.filename or "")
    if not safe_name:
        return {"status": "error", "message": "Invalid filename"}
    save_path = os.path.join(outputs_path, safe_name)
    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        return {"status": "error", "message": f"文件保存失败: {e}"}

    result = manager.shared_components()["knowledge"].add_document(save_path)
    if result["success"]:
        return {
            "status": "ok",
            "file": result["file"],
            "chunks": result["chunks"],
            "message": f"成功导入 {result['chunks']} 个文本片段"
        }
    return {"status": "error", "message": result.get("error", "导入失败")}

@app.get("/api/knowledge/stats")
async def knowledge_stats():
    """获取知识库统计信息"""
    return manager.shared_components()["knowledge"].get_stats()

@app.delete("/api/knowledge/clear")
async def clear_knowledge():
    """清空知识库"""
    manager.shared_components()["knowledge"].clear()
    return {"status": "ok", "message": "知识库已清空"}

if __name__ == "__main__":
    import uvicorn
    # 开发模式开启热重载：APP_RELOAD=true python app.py
    # 生产环境（Docker 等）默认关闭 reload，避免多余 watcher 进程
    reload_enabled = os.environ.get("APP_RELOAD", "false").lower() in ("1", "true", "yes")
    logging.info("Starting SmartFlow server on http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=reload_enabled)
