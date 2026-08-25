<p align="center">
  <img src="./logo.jpg" width="120" alt="SmartFlow Logo" />
</p>

<h1 align="center">SmartFlow</h1>

<p align="center">
  <strong>轻量级 AI Agent 框架，内置 Human-in-the-Loop 人工审批机制</strong><br/>
  用最少的代码，实现生产可用的 Agent 核心能力
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LLM-OpenAI%20Compatible-412991?style=flat-square&logo=openai" alt="LLM" />
  <img src="https://img.shields.io/badge/feature-HITL%20Approval-ff6b35?style=flat-square" alt="HITL" />
</p>

---

## ✨ 项目简介

SmartFlow 是一个**模块化 AI Agent 框架**，基于 ReAct（Reasoning + Acting）模式，支持大模型自主决策多轮工具调用。

在标准 Agent 能力之上，SmartFlow 实现了 **Human-in-the-Loop（HITL）人工审批机制**：当 Agent 想执行高风险操作（如 Shell 命令）时，自动暂停并向用户弹出审批窗口，用户确认后才继续执行，可以解决 Agent 失控问题。

> 📚 **配套学习资料**：项目附带 [面试复习手册](./面试复习手册.md)（1289 行），逐行讲解代码 + Agent 开发岗面试题精讲，面试前必看。

## 🏗️ 核心架构

```
用户消息 → ContextBuilder 组装上下文 → AgentLoop 调用 LLM
                                              ↓
                                        模型返回文本？→ 流式输出给用户
                                        模型要用工具？→ 检查风险等级
                                              ↓
                                        低/中风险 → ToolRegistry 直接执行
                                        高风险    → 触发 HITL 审批
                                              ↓
                                        用户同意 → 执行工具 → 结果注入上下文
                                        用户拒绝 → 跳过工具 → 告知模型
                                              ↓
                                        循环直到模型完成 → MemoryStore 保存
```

## 🔒 Human-in-the-Loop 审批机制

SmartFlow 的核心原创功能。基于 `asyncio.Event` 实现异步审批等待，不阻塞其他用户请求。

**工具风险分级：**

| 等级 | 工具 | 处理方式 |
|---|---|---|
| `low` | read_file | 直接执行 |
| `medium` | write_file、edit_file | 直接执行 |
| `high` | exec（Shell 命令） | 弹窗等待用户审批 |

**审批流程：**

```
Agent 触发高风险工具
      ↓
SSE 推送 approval_required 事件 → 前端弹出审批窗口
      ↓
asyncio.Event 挂起当前协程（不阻塞服务器）
      ↓
用户点击同意/拒绝 → POST /api/approve
      ↓
event.set() 唤醒协程 → 根据结果执行或跳过工具
```

超时（默认 60 秒）自动拒绝，安全兜底。

## 🛠️ 完整功能列表

- **ReAct 循环引擎** — 大模型自主决策多轮工具调用，`max_iterations=10` 防死循环
- **流式输出** — AsyncGenerator + SSE 全链路流式，首字响应 < 1s
- **流式 Tool Call 解析** — 碎片化 tool_call 拼接，兼容 OpenAI / DeepSeek / 通义千问等多后端
- **HITL 人工审批** — 高风险工具执行前弹窗确认，asyncio.Event 异步等待
- **对话记忆** — 短期历史窗口（安全截断，保证工具调用链完整）+ 长期 Markdown 记忆
- **技能插件系统** — 放一个 `SKILL.md` 即装即用，两档加载策略节省 token
- **安全防护** — Shell 命令黑名单 + 执行超时 + 输出截断

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> RAG 知识库功能依赖 `chromadb` 和 `sentence-transformers`（已在 requirements.txt 中）：
> 首次使用知识库时会自动下载约 120MB 的 Embedding 模型，稍等片刻即可。

### 2. 配置 LLM

复制配置模板并填入你的 API 信息（环境变量优先，也可以不写 config.yaml 直接导出环境变量）：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`：

```yaml
llm:
  api_key: "your-api-key"
  model: "deepseek-chat"
  base_url: "https://api.deepseek.com/v1"
```

支持所有 OpenAI 兼容 API：OpenAI、DeepSeek、通义千问、Infini-AI 等。

### 3. 启动服务

```bash
python app.py          # 生产模式（默认关闭热重载）
APP_RELOAD=true python app.py   # 开发模式（代码修改后自动重启）
```

访问 `http://localhost:8000` 开始对话。

试着发送：**"帮我执行 echo hello world"**，体验 HITL 审批弹窗。

## 🐳 Docker 部署

### 方式一：docker-compose（推荐）

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env，填入你的 API Key
# LLM_API_KEY=your-api-key
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat
# SMARTFLOW_API_TOKEN=你的鉴权Token（可选，建议生产环境设置）

# 3. 启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 方式二：docker run

```bash
# 构建镜像
docker build -t smartflow .

# 启动容器
docker run -d \
  -p 8000:8000 \
  -e LLM_API_KEY=your-api-key \
  -e LLM_BASE_URL=https://api.deepseek.com/v1 \
  -e LLM_MODEL=deepseek-chat \
  -e SMARTFLOW_API_TOKEN=your-token \
  -v $(pwd)/workspace:/app/workspace \
  --name smartflow \
  smartflow
```

访问 `http://localhost:8000` 开始使用。

## 🔐 接口鉴权（可选）

默认**不开启鉴权**，适合本地演示；部署到公网时强烈建议开启，防止他人白嫖你的 API Key 或调用高危工具。

**开启方式（任选其一）：**

```bash
# 方式一：环境变量（推荐，不落盘）
SMARTFLOW_API_TOKEN=$(openssl rand -hex 32) python app.py

# 方式二：config.yaml
# server:
#   api_token: "your-token"
```

开启后，所有 `/api/*` 接口必须携带请求头 `Authorization: Bearer <token>`：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

前端页面左侧栏内置了 API Token 输入框（保存在浏览器 localStorage），填写后自动带上鉴权头。

## 📁 项目结构

```
SmartFlow/
├── app.py              # FastAPI 入口，HTTP 路由 + SSE
├── CHANGELOG.md        # 更新日志（Keep a Changelog 规范）
├── config.yaml.example # LLM 配置模板（复制为 config.yaml 使用）
├── .env.example        # Docker 环境变量模板（复制为 .env 使用）
├── requirements.txt    # Python 依赖（含 RAG：chromadb + sentence-transformers）
├── test_hitl.py        # HITL 功能单元测试（mock，无需真实 API）
├── test_rag.py         # RAG 知识库功能测试
├── 面试复习手册.md      # 代码讲解 + 面试题精讲
├── static/             # 前端页面
└── core/               # 核心模块
    ├── agent.py        #   总指挥，组装所有组件
    ├── loop.py         #   ReAct 循环引擎 + HITL 审批逻辑
    ├── tools.py        #   工具注册、执行、风险分级 + ApprovalManager
    ├── memory.py       #   短期（SQLite）+ 长期（Markdown）记忆管理
    ├── skills.py       #   Markdown 技能加载器
    ├── context.py      #   上下文 & 系统提示词组装
    └── knowledge.py    #   RAG 知识库（ChromaDB + 本地 Embedding）
```

## 🧪 运行测试

HITL 功能测试（不消耗 API 额度）：

```bash
python test_hitl.py
```

输出示例：
```
测试场景：用户将选择 【同意】
  [前端] 收到审批请求: 工具=exec
  [用户] 已提交决定: 同意
  >>> 期望执行=True, 实际执行=True -> 测试通过 ✓

测试场景：用户将选择 【拒绝】
  [前端] 收到审批请求: 工具=exec
  [用户] 已提交决定: 拒绝
  >>> 期望执行=False, 实际执行=False -> 测试通过 ✓
```

## 📡 API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/chat` | 流式对话（SSE） |
| `POST` | `/api/approve` | 提交工具审批结果（HITL） |
| `GET` | `/api/status` | 获取技能和工具列表 |
| `GET` | `/api/memory` | 查看记忆状态 |
| `GET` | `/api/history` | 获取完整对话历史 |
| `POST` | `/api/upload` | 上传文件到工作区 |
| `DELETE` | `/api/outputs/{name}` | 删除工作区输出文件 |
| `GET` | `/api/outputs` | 列出工作区输出文件 |
| `POST` | `/api/clear` | 清空对话记忆 |
| `POST` | `/api/knowledge/add` | 上传文档导入知识库（RAG，支持 .txt/.md） |
| `GET` | `/api/knowledge/stats` | 获取知识库统计 |
| `DELETE` | `/api/knowledge/clear` | 清空知识库 |

## 🗺️ Roadmap（计划中）

- [ ] **多会话隔离** — 支持多用户/多会话并行，各自独立记忆
- [ ] **可观测性面板** — token 消耗、成本、工具调用时间线可视化
- [ ] **上下文压缩** — 历史超窗口时用 LLM 摘要，替代粗暴截断
- [ ] **更多工具** — Web 搜索、HTTP 请求、代码执行沙箱
- [ ] **评估集（Eval）** — 任务链自动化测试，量化 Agent 成功率
- [ ] **前端工程化** — 迁移到 React/Vite，组件化 + 测试
