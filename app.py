import json
import logging
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, UploadFile, File
from pydantic import BaseModel

import os
import yaml
from core.agent import TinyAgent

# 加载配置文件
config_path = "config.yaml"
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

llm_config = config.get("llm", {})

workspace_path = "./workspace"
outputs_path = os.path.join(workspace_path, "outputs")
os.makedirs(outputs_path, exist_ok=True)

agent = TinyAgent(
    workspace_dir=workspace_path, 
    openai_api_key=llm_config.get("api_key"),
    base_url=llm_config.get("base_url"),
    model=llm_config.get("model", "gpt-4o-mini")
)

app = FastAPI(title="Tiny Agent Backend")

# 挂载静态资源
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

@app.get("/")
async def root():
    """返回前端主页"""
    return FileResponse("static/index.html")

class ChatRequest(BaseModel):
    message: str

class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    流式对话接口。使用 GET / POST 无所谓，这里为了获取 query 用 POST 接收 message 后，
    将其转换成 SSE (Server-Sent Events) 返回。
    """
    async def sse_generator() -> AsyncGenerator[str, None]:
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
    """
    ok = agent.resolve_approval(req.approval_id, req.approved)
    if ok:
        return {"status": "ok", "approved": req.approved}
    # 请求不存在或已超时被清理
    return {"status": "error", "message": "审批请求不存在或已超时"}

@app.get("/api/status")
async def get_status():
    """获取侧边栏展示的相关状态（刷新并返回技能和支持的工具）"""
    agent.skills.load_all_skills() # Dynamic reload
    return {
        "skills": agent.get_skills_summary(),
        "tools": agent.get_tools_summary()
    }

@app.get("/api/memory")
async def get_memory():
    """获取当前 agent 的上下文和长期记忆"""
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
async def get_history():
    """获取完整的历史会话和累积 token 消耗用于前端恢复渲染"""
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

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件到 workspace outputs 目录"""
    if not os.path.exists(outputs_path):
        os.makedirs(outputs_path, exist_ok=True)
    file_path = os.path.join(outputs_path, file.filename)
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/clear")
async def clear_memory():
    """清理内存会话记录"""
    agent.clear_memory()
    return {"status": "ok"}

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
    save_path = os.path.join(outputs_path, file.filename)
    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        return {"status": "error", "message": f"文件保存失败: {e}"}

    result = agent.knowledge.add_document(save_path)
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
    return agent.knowledge.get_stats()

@app.delete("/api/knowledge/clear")
async def clear_knowledge():
    """清空知识库"""
    agent.knowledge.clear()
    return {"status": "ok", "message": "知识库已清空"}

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting Tiny Agent server on http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
