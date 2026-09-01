<p align="center">
  <img src="./logo.jpg" width="120" alt="SmartFlow Logo" />
</p>

<h1 align="center">SmartFlow</h1>

<p align="center">
  <strong>轻量级 AI Agent 框架：ReAct + HITL 人工审批 + 多会话 + RAG 知识库</strong><br/>
  用最少的代码，实现生产可用的 Agent 核心能力
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.0-4A90D9?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/framework-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LLM-OpenAI%20Compatible-412991?style=flat-square&logo=openai" alt="LLM" />
  <img src="https://img.shields.io/badge/feature-HITL%20Approval-ff6b35?style=flat-square" alt="HITL" />
  <img src="https://img.shields.io/badge/feature-RAG-00c853?style=flat-square" alt="RAG" />
</p>

---

## ✨ 项目简介

SmartFlow 是一个**模块化 AI Agent 框架**，基于 ReAct（Reasoning + Acting）模式，支持大模型自主决策多轮工具调用，并以流式方式输出。

在标准 Agent 能力之上，SmartFlow 面向**生产可用**做了四件事：

1. **安全可控** — Human-in-the-Loop（HITL）人工审批：高风险工具（如 Shell 命令）执行前自动暂停、弹窗确认，防止 Agent 失控
2. **多用户可用** — 会话隔离：每个会话独立的记忆与审批状态，无状态组件全局共享，支持并行服务
3. **私域知识** — RAG 知识库：本地向量检索，Agent 可回答私域文档问题，减少幻觉
4. **质量可衡量** — 内置评估集（Eval Harness）：端到端任务量化 Agent 行为，输出成功率与成本报告

> 📚 **配套学习资料**：
> - [面试复习手册](./面试复习手册.md) — 逐行讲解代码 + Agent 开发岗面试题精讲
> - [面试话术](./面试话术.md) — 项目叙事话术：30 秒自我介绍模板 + 追问准备 + 简历写法

## 📑 目录

- [核心特性](#-核心特性)
- [核心架构](#-核心架构)
- [Human-in-the-Loop 审批机制](#-human-in-the-loop-审批机制)
- [多会话隔离](#-多会话隔离)
- [评估集（Eval Harness）](#-评估集eval-harness)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [Docker 部署](#-docker-部署)
- [接口鉴权](#-接口鉴权可选)
- [项目结构](#-项目结构)
- [运行测试](#-运行测试)
- [API 接口](#-api-接口)
- [Roadmap](#-roadmap计划中)

## ✨ 核心特性

| 特性 | 说明 |
|---|---|
| **ReAct 循环引擎** | 大模型自主决策多轮工具调用，`max_iterations=10` 防死循环 |
| **流式输出** | AsyncGenerator + SSE 全链路流式，首字响应 < 1s |
| **流式 Tool Call 解析** | 碎片化 tool_call 拼接，兼容 OpenAI / DeepSeek / 通义千问等多后端 |
| **HITL 人工审批** | 高风险工具执行前弹窗确认，`asyncio.Event` 异步等待，超时自动拒绝 |
| **多会话隔离** | 按会话隔离记忆与审批，无状态组件全局共享，同会话并发自动串行 |
| **RAG 知识库** | 本地 Embedding + ChromaDB 向量检索，支持 .txt/.md 导入 |
| **对话记忆** | 短期历史窗口（安全截断）+ LLM 上下文压缩（摘要注入）+ 长期 Markdown 记忆 |
| **技能插件系统** | 放一个 `SKILL.md` 即装即用，两档加载策略节省 token |
| **评估集** | mock/real 双模式端到端任务，成功率 / 轮数 / token 报告 |
| **可观测性** | 工具调用时间线 + token 明细 + 成本估算（`/api/stats`） |
| **安全防护** | Shell 黑名单 + 执行超时 + 输出截断 + 可选接口鉴权 |
| **更多工具** | `web_search`（Tavily 联网检索）+ `http_get`/`http_post`（SSRF 防护强制）+ `code_exec`（Docker 隔离沙箱，`--network=none` + 资源限制，高风险工具自动 HITL 审批） |

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

**核心模块：**

| 模块 | 职责 |
|---|---|
| `agent.py` | 总指挥：组装共享组件 + 会话状态 |
| `session.py` | 会话管理器：隔离、审批路由、并发锁 |
| `loop.py` | ReAct 循环引擎 + HITL 审批逻辑 |
| `tools.py` | 工具注册、执行、风险分级 + ApprovalManager |
| `memory.py` | 短期（SQLite）+ 上下文压缩摘要 + 长期（Markdown）记忆 |
| `skills.py` | Markdown 技能加载器 |
| `context.py` | 上下文 & 系统提示词组装 |
| `knowledge.py` | RAG 知识库（ChromaDB + 本地 Embedding） |

## 🔒 Human-in-the-Loop 审批机制

Human-in-the-Loop（HITL）是 Agent 安全控制领域的常见设计模式（OpenAI Function Calling、LangChain 等均有类似机制）。SmartFlow 提供了自己的轻量实现：

- 基于 `asyncio.Event` 实现**异步审批等待**——挂起的是单个工具调用协程，不阻塞服务器，同一进程内可并行服务多个请求
- 工具**风险分级**（low / medium / high），只有高风险工具才触发人工确认
- **超时自动拒绝**（默认 60 秒），安全兜底
- 审批状态按**会话隔离**，多用户并行互不干扰

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

## 👥 多会话隔离

多用户/多会话并行时，每个会话的**记忆与审批状态完全隔离**，互不污染。

**设计核心：无状态组件共享 + 有状态组件隔离**

| 组件 | 类型 | 处理方式 |
|---|---|---|
| LLM client / skills / knowledge / tools | 无状态/只读 | **全局共享**，只构建一次 |
| MemoryStore / ApprovalManager | 有状态 | **按会话隔离**（SQLite 自带 `session_id` 字段，零改动） |

**三个并发边界：**

1. **审批跨会话路由** — `/api/approve` 带 `session` 字段，定位到正确的 ApprovalManager
2. **同会话并发串行** — 每个会话一把 `asyncio.Lock`，防止消息乱序
3. **锁覆盖整个流式周期** — 流式生成期间插入的新请求会被排队，保证工具调用链完整

前端左侧栏提供会话面板：新建 / 切换 / 删除，当前会话存 localStorage。

## 📊 评估集（Eval Harness）

用端到端任务量化 Agent 的行为质量，输出成功率 / 平均轮数 / 平均 token / 失败原因。

```bash
python eval/run_eval.py                    # mock 模式（零成本，验证工具调用链）
python eval/run_eval.py --mode real        # 真实 LLM 模式（需有效 API Key，校验产物）
python eval/run_eval.py --mode all         # 全部任务
python eval/run_eval.py --task shell_echo  # 只跑指定任务
```

- **mock 模式**：脚本化 FakeClient 让模型按计划调用工具，验证工具序列是否正确执行、结果是否正确回传（含 HITL 审批链路自动同意）
- **real 模式**：真实模型跑完整链路，按任务声明的 checks 校验输出文件/关键词，并统计 token 消耗

输出示例：

```
 Task                     Mode   Status   Rounds  Tokens   Detail
 edit_file_flow           mock   PASS     3       0        tools=['read_file', 'edit_file']
 shell_echo               mock   PASS     2       0        tools=['exec']
 Summary: 5/5 passed (100.0%)  avg_rounds=2.4  avg_tokens=0  skipped=0
```

报告同时保存为 `eval/report.json`。任务定义在 `eval/tasks/*.json`，新增任务只需加一个 JSON。

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| 后端框架 | FastAPI + Uvicorn（异步） |
| LLM 接入 | OpenAI 兼容 API（DeepSeek / 通义千问 / OpenAI / Infini-AI…） |
| 对话存储 | SQLite（会话隔离 + token 统计） |
| 向量检索 | ChromaDB + sentence-transformers（本地 Embedding，中英文） |
| 长期记忆 | Markdown 文件（MEMORY.md） |
| 前端 | React 19 + Vite + TypeScript + Tailwind v4（`frontend/`，构建产物由 FastAPI 伺服） |
| 测试 | test_hitl.py / test_rag.py + 评估集 run_eval.py |
| 部署 | Docker / docker-compose |

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

> **前端构建说明**：页面由 `frontend/`（React + Vite）构建，产物 `frontend/dist` 由 FastAPI 在启动时自动伺服（`app.py` 检测到 `frontend/dist` 即挂载）。前端改动需先构建：
>
> ```bash
> cd frontend
> npm install        # 首次
> npm run build      # 产物进 frontend/dist，刷新页面即生效
> ```
>
> 前端开发模式（Vite dev server + 代理到后端，热更新）：
>
> ```bash
> cd frontend
> npm run dev        # http://localhost:5173，/api 与 /outputs 代理到 :8000
> ```
>
> 测试与质量：`npm test`（Vitest，17 用例）、`npm run lint`（ESLint）、`npm run format`（Prettier）。
> 本机若在受限沙箱运行（npm 缓存需重定向 + vite 无法 spawn 子进程），参见 `frontend/vite-netuse-preload.cjs` 注释。

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

开启后，所有 `/api/*` 接口及 `/outputs/*` 文件下载必须携带请求头 `Authorization: Bearer <token>`：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'

# 下载 Agent 生成的输出文件（受鉴权保护）
curl http://localhost:8000/api/outputs/download/report.md \
  -H "Authorization: Bearer your-token" -o report.md
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
├── eval/               # 评估集：run_eval.py + tasks/*.json（mock/real 双模式）
├── 面试复习手册.md      # 代码讲解 + 面试题精讲
├── frontend/            # 前端工程（React + Vite + TS；npm run build 产物进 frontend/dist）
└── core/               # 核心模块
    ├── agent.py        #   总指挥，组装所有组件（支持共享组件注入）
    ├── session.py      #   会话管理器：多会话隔离 + 审批路由 + 并发锁
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

> 会话参数：`/api/chat`（body 的 `session` 字段）、`/api/history`、`/api/memory`、`/api/clear`（query 的 `session` 参数）用于指定会话，默认 `default`；不同会话的记忆互相隔离。

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/chat` | 流式对话（SSE，带 `session`） |
| `POST` | `/api/approve` | 提交工具审批结果（HITL，带 `session`） |
| `GET` | `/api/sessions` | 会话列表（消息数、最后活跃时间） |
| `POST` | `/api/sessions` | 新建会话 |
| `DELETE` | `/api/sessions/{id}` | 删除会话 |
| `GET` | `/api/status` | 获取技能和工具列表 |
| `GET` | `/api/memory?session=` | 查看指定会话记忆状态 |
| `GET` | `/api/history?session=` | 获取指定会话完整历史 |
| `GET` | `/api/stats?session=` | 可观测性统计（token/成本/工具调用时间线） |
| `POST` | `/api/upload` | 上传文件到工作区 |
| `DELETE` | `/api/outputs/{name}` | 删除工作区输出文件 |
| `GET` | `/api/outputs` | 列出工作区输出文件 |
| `GET` | `/api/outputs/download/{name}` | 下载/预览输出文件（受鉴权保护） |
| `POST` | `/api/clear?session=` | 清空指定会话记忆 |
| `POST` | `/api/knowledge/add` | 上传文档导入知识库（RAG，支持 .txt/.md） |
| `GET` | `/api/knowledge/stats` | 获取知识库统计 |
| `DELETE` | `/api/knowledge/clear` | 清空知识库 |

## 🗺️ Roadmap（计划中）

- [x] **多会话隔离** — 已实现：SessionManager + 前端会话面板 ✅
- [x] **评估集（Eval）** — 已实现：mock/real 双模式 + 成功率报告 ✅
- [x] **可观测性面板** — 已实现：token 明细 + 成本估算 + 工具调用时间线 ✅
- [x] **上下文压缩** — 已实现：超窗口历史用 LLM 摘要注入 system prompt ✅
- [x] **更多工具** — Web 搜索、HTTP 请求、代码执行沙箱
- [x] **前端工程化** — 迁移到 React/Vite，组件化 + 测试（2026-09-01）

---

<p align="center">
  <sub>SmartFlow · 用最少的代码，实现生产可用的 Agent 核心能力</sub>
</p>
