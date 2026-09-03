# Changelog

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Changed
- **工程规范（第二梯队）**：
  - 测试统一为 **pytest 结构**：测试文件迁移至 `tests/`（conftest 自动清理临时目录），支持 `pytest tests/` + 覆盖率（pytest-cov）；CI 改为 pytest 运行
  - **配置中心化**：Agent 运行参数（`max_iterations` / `window_size` / `compress_threshold` / `approval_timeout`）从硬编码常量抽到 `config.yaml` 的 `agent` 段（不配置时行为不变）
  - **依赖拆分**：`requirements-core.txt`（核心，不含 torch）+ `requirements-rag.txt`（RAG 可选）+ `requirements-dev.txt`（pytest/ruff/pre-commit）；`requirements.txt` = core + rag
  - **Docker 镜像瘦身**：默认只装核心依赖（`--build-arg INSTALL_RAG=1` 启用 RAG），避免 torch 使镜像膨胀到 2GB+
  - **ruff + pre-commit**：`.pre-commit-config.yaml`（lint/format/基础检查）+ pyproject `[tool.ruff]`；CI 增加 ruff 门禁

### Added
- **GitHub Actions CI**：三个 job——后端（pytest + ruff + code_exec Docker 沙箱真实执行验证）、RAG（test_rag）、前端（Vitest + lint + build）；README 挂 CI badge
- **MIT License**；README「界面预览」章节（截图占位 + 生成指引，`docs/screenshots/`）
- **前端工程化**：单文件 `static/index.html` 迁移为 `frontend/` React 19 + Vite + TypeScript 工程（组件化、类型化、可测试、可维护；功能与视觉 1:1 等价，后端 `/api/*` 零改动）
  - 12 个核心交互区全部迁移：SSE 流式聊天（判别联合事件类型 + 增量解析）、HITL 审批弹窗（60s 倒计时）、会话管理（新建/切换/删除 + localStorage 兼容 `smartflow_session_id`）、API Token（兼容 `smartflow_api_token`）、Token/成本/工具调用遥测、技能/工具/记忆/输出文件面板（轮询频率与旧版一致）
  - 技术栈：Tailwind v4 本地构建（`@theme` 迁移 cyber 色板与动画，视觉零漂移）、react-markdown（替换 CDN marked）、@fontsource 本地字体（离线可用）、React Context + hooks 状态管理（弃 Zustand）
  - 测试与质量：Vitest 17 用例（SSE 解析/鉴权头/审批倒计时/会话 store/消息渲染）、ESLint 0 error、Prettier
  - 伺服：`app.py` 检测到 `frontend/dist` 即挂载 `/`（位于所有 API 路由之后，Starlette 顺序匹配）；开发模式 `npm run dev` + Vite proxy；Dockerfile 多阶段构建（node 构建 → python 伺服）
  - 旧 `static/` 与旧挂载已移除
- **更多工具**：Agent 新增 4 个工具，扩展外部世界访问能力
  - `web_search`（low）：Tavily 联网检索，返回标题/链接/摘要列表；Key 走 `tools.web_search.api_key` 或环境变量 `WEB_SEARCH_API_KEY`（不落日志、不进 tool 参数）；未配置 Key 时工具返回明确提示
  - `http_get`（medium）：只读 HTTP GET，响应体截断 20KB；**SSRF 防护强制**（解析后校验 IP，拦截回环/私网/链路本地/保留地址，含 IPv6），`follow_redirects=False` + 手动重定向重新校验
  - `http_post`（high）：JSON/表单提交外部 URL，复用 SSRF 防护；有副作用，执行前自动触发 HITL 人工审批
  - `code_exec`（high）：Docker 隔离沙箱执行 Python 代码（`--network=none` 网络隔离 + `--memory=256m/--cpus=1/--pids-limit=128` 资源限制 + `--rm` 无持久化，仅挂载 `workspace/outputs` 到 `/sandbox`）；超时强制终止；无 Docker 环境返回提示；执行前自动触发 HITL 人工审批
  - 配置注入：`config.yaml` 新增 `tools` 段（`web_search.api_key` / `code_exec.enabled` / `code_exec.docker_image`），环境变量优先，经 `SessionManager` → `build_shared(tool_config=...)` 注入（向后兼容）
  - 新增测试 `test_more_tools.py`：SSRF 单元测试（mock DNS）+ 工具 mock 测试（MockTransport）+ 高风险工具 HITL 链集成测试（ScriptedClient）
- **上下文压缩**：超过 24 条活跃消息时，把最早一批完整轮次（≤10 条，按轮次边界截止，不切孤儿 tool）交给 LLM 压缩成 ≤300 字摘要
  - SQLite 新增 `summaries` 表（按 `session_id` 隔离）；先写摘要、成功后再删原文，失败兜底不删任何消息、不阻塞对话
  - 摘要注入 `build_system_prompt` 的「早前对话摘要」段，与窗口截断并行——窗口外早期上下文不再丢失
  - `clear_history` 与 `DELETE /api/sessions/{id}` 同步清理摘要
  - 新增测试 `test_compress.py`（单元 + 集成，mock 摘要模型）
- **可观测性面板**：SQLite 新增 `tool_calls` / `rounds` 表，自动采集每次工具调用（名称/参数/结果摘要）与每轮 LLM token 明细
  - 新接口 `GET /api/stats?session=`：token 总量 / 轮数 / 工具调用次数 / **预估成本**（`llm.pricing` 配置，可选）+ 工具调用排行与最近时间线
  - 前端 Telemetry 面板扩展：成本估算显示 + 工具调用列表（按风险着色：exec 红 / write·edit 黄 / 只读绿）
  - `chat_stream` 自动采集：`tool_call_start/end` 事件合成完整工具记录，`token_usage` 事件记入 rounds 表
- **评估集（Eval Harness）**：`eval/` 目录 + 7 个端到端任务，量化 Agent 行为质量
  - **mock 模式**（零成本，CI 友好）：脚本化 FakeClient 验证工具调用链与 HITL 审批链路
  - **real 模式**（需 LLM API Key）：真实模型跑完整链路，按 checks 校验输出产物（文件/关键词）并统计 token
  - 结构化报告：成功率、平均轮数、平均 token、失败原因（控制台 + `eval/report.json`）
- **多会话隔离**：新增 `SessionManager`，按 `session_id` 隔离对话记忆与审批状态；无状态组件（LLM client / skills / knowledge / tools）全局共享、只构建一次
- 会话管理 API：`GET/POST /api/sessions`、`DELETE /api/sessions/{id}`（列表聚合消息数/最后活跃时间，支持删除）
- 前端左侧栏新增 **Sessions 面板**：会话列表、新建、切换、删除，当前会话存 localStorage
- 现有接口支持会话参数：`/api/chat`（body）、`/api/history`、`/api/memory`、`/api/clear`（query）
- 审批跨会话路由：`/api/approve` 带 `session` 字段，定位到正确的 ApprovalManager

### Security
- 鉴权范围扩展：开启 Token 后，`/outputs/*` 文件下载同样受保护（此前可直接访问 Agent 生成的文件）
- 新增受鉴权的下载接口 `GET /api/outputs/download/{filename}`，前端文件打开/下载改走该接口
- 清除本地 `config.yaml` / `.env` 中明文保存的 API Key（改为占位符，需在服务商重置后重新配置）

## [1.1.0] - 2026-08-25

### Added
- **接口鉴权（可选）**：设置 `SMARTFLOW_API_TOKEN`（或 `config.yaml` 的 `server.api_token`）后，所有 `/api/*` 接口必须携带 `Authorization: Bearer <token>`，防止 API Key 被白嫖或高危工具被滥用；未配置时保持无鉴权（本地演示模式）
- 前端左侧栏新增 **API Token 配置入口**：Token 存 localStorage，自动附加到所有请求，401 时聊天区友好提示
- README 新增「接口鉴权」「Roadmap」章节，并补全 API 文档（outputs 列表/删除、knowledge 导入/统计/清空等接口）

### Fixed
- **RAG 依赖缺失**：`requirements.txt` 补充 `chromadb` 与 `sentence-transformers`，Docker / 全新安装后知识库功能不再报 ImportError
- **上传接口路径穿越漏洞**：`/api/upload` 与 `/api/knowledge/add` 的文件名经 `os.path.basename()` 消毒，无法再通过 `../../` 逃逸工作区
- **流式 tool_call 名称拼接 bug**：部分 OpenAI 兼容后端在多个分片重复发送完整函数名，会拼成 `read_fileread_file`；现仅在名称为空时赋值
- **Docker 生产环境误开热重载**：`uvicorn reload` 改为 `APP_RELOAD` 环境变量控制，默认关闭（开发模式 `APP_RELOAD=true python app.py`）

### Changed
- 恢复并更新配置模板 `config.yaml.example` / `.env.example`，与新增配置项（鉴权、开发模式）保持一致
- `docker-compose.yml` 增加 `SMARTFLOW_API_TOKEN` 环境变量透传

### Removed
- 移除了误提交进 git 的运行时二进制产物：`_test_rag_tmp/`（测试临时 ChromaDB）、`workspace/knowledge_db/`（向量库）、占位文件 `hello`，并补充 `.gitignore` 规则

## [1.0.0] - 2026-07-06

### Added
- README 全面完善，项目对外可用的第一个稳定版本

## [0.4.0] - 2026-06-09

### Added
- Docker 部署：`Dockerfile` + `docker-compose.yml`，环境变量注入 API 配置，`workspace` 卷挂载持久化数据

## [0.3.0] - 2026-06-08

### Added
- 面试复习手册（`面试复习手册.md`）：逐行代码讲解 + Agent 开发岗面试题精讲（RAG / HITL 章节）

### Changed
- 对话存储从 JSON 文件迁移到 **SQLite**：并发安全、按 `session_id` 隔离、token 统计持久化

## [0.2.0] - 2026-06-01

### Added
- **RAG 知识库**：ChromaDB 向量检索 + 本地 Embedding 模型（sentence-transformers，支持中英文）
- 知识检索工具 `search_knowledge`：Agent 可检索已导入的私域文档，减少幻觉
- 知识库管理 API：导入文档（.txt/.md）、统计、清空
- 文件管理 API：上传到工作区、输出文件列表与删除

## [0.1.0] - 2026-05-31

### Added
- 轻量级 AI Agent 框架：**ReAct 循环引擎**（`max_iterations` 防死循环、流式 tool_call 碎片重组）
- **Human-in-the-Loop 人工审批机制**（核心亮点功能）：高风险工具（Shell）执行前弹窗确认，`asyncio.Event` 异步挂起/唤醒不阻塞其他请求，超时自动拒绝
- 流式输出（SSE），首字响应 < 1s，兼容 OpenAI / DeepSeek / 通义千问等 OpenAI 兼容后端
- 工具系统：`read_file` / `write_file` / `edit_file` / `exec`（含高危命令黑名单、执行超时、输出截断）
- 技能插件系统：放一个 `SKILL.md` 即装即用，两档加载策略（`always_load` 常驻 / 按需读取）节省 token
- 对话记忆：短期历史窗口（安全截断，保证工具调用链完整）+ 长期 Markdown 记忆
- FastAPI 后端 + 单文件前端（Tailwind 赛博终端风格，Markdown 渲染）
