# 更多工具（web_search / http_get / http_post / code_exec）Implementation Plan

> 状态：已批准（2026-09-01）。执行模式：内联执行（任务紧耦合：单文件累积 + 共享测试文件）。
> 规格来源：`更多工具-任务大纲.md`。

**Goal:** 为 Agent 新增 4 个工具：`web_search`（Tavily）、`http_get`（medium）、`http_post`（high）、`code_exec`（high），SSRF 防护强制、高风险工具走 HITL，全部既有测试回归通过。

**Architecture:** 全部新增代码放进现有单文件 `core/tools.py`（保持 BaseTool/ToolRegistry 模式）；SSRF 防护是共享函数 `_check_ssrf(url)`，http_get/http_post 都调用它；配置经 `build_shared(tool_config=...)` 注入 ToolRegistry；`risk_level="high"` 的工具自动触发现有 loop.py 的 HITL 链路，零改动。

**Tech Stack:** Python 3.11、`httpx`（显式加入 requirements.txt，环境中已装 0.28.1）、`subprocess` 调 docker CLI。无新依赖。

## Global Constraints

- Python 版本：3.11；测试命令固定用 `D:\mytools\miniforge3\envs\smartflow\python.exe`。
- 本机**未安装 Docker**：code_exec 实现照规格写，测试验证无 Docker 降级路径。
- 新增依赖仅 `httpx>=0.24.0`。
- 新工具产物只落 `workspace/outputs/`。
- Key 不落日志、不进 tool 参数；配置仅 `tools.web_search.api_key`，环境变量 `WEB_SEARCH_API_KEY` 优先。
- **对规格的三处裁剪（ponytail：YAGNI）**：
  1. 砍 SearchProvider 抽象接口 + SerperProvider + DDG 预留——只留 Tavily 单实现。
  2. 砍 `fallback_unsafe` 受限 Python 降级方案——无 Docker 直接返回提示。
  3. 砍规格「可选加分」的 eval/tasks 新任务——HITL 链由测试文件集成测试覆盖。
- 分支：`feature/more-tools`（已建）。

## Tasks

- **Task 1**：SSRF 共享函数 `_check_ssrf` + 单元测试（mock getaddrinfo）
- **Task 2**：`web_search`（Tavily，low）+ 格式化/无 Key 测试 + 注册
- **Task 3**：`http_get`（medium，SSRF 强制 + 手动重定向校验）+ MockTransport 测试
- **Task 4**：`http_post`（high，复用请求逻辑）+ HITL 集成测试（ScriptedClient）
- **Task 5**：`code_exec`（high，Docker 沙箱 `--network=none` + 资源限制 + 只挂 outputs）+ 无 Docker 测试
- **Task 6**：配置注入（requirements.txt / config.yaml.example / app.py / core/session.py / core/agent.py）+ /api/status 测试
- **Task 7**：文档（README 特性表 + Roadmap 勾选 + CHANGELOG）+ 全量回归

## 验收清单

- [ ] 4 个新工具注册并出现在 `/api/status`
- [ ] web_search：配置 Key 走 Tavily 真实检索；未配置返回明确提示（真检索需真实 Key，手动验证）
- [ ] SSRF：回环/私网/链路本地/IPv6/非 http(s) 全拦截；重定向目标重新校验
- [ ] code_exec：Docker 沙箱命令含 `--network=none` + 资源限制 + 只挂 outputs；无 Docker 返回提示（真执行需 Docker 环境，手动验证）
- [ ] 高风险工具（http_post / code_exec）走通 HITL 审批链路
- [ ] 全部既有回归通过
- [ ] README + CHANGELOG 更新

## 已知限制

- 本机无 Docker、无 Tavily Key：code_exec 真执行与 web_search 真检索无法本机自动化验证。
- SSRF 存在 DNS-rebinding 窗口（代码注释标明升级路径）。
- `test_rag.py` 因 smartflow 环境缺 chromadb/sentence-transformers 无法运行（基线环境限制）。
