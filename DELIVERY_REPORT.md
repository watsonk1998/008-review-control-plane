# DELIVERY REPORT — 008 Review Control Plane

> 注：本文件保留为阶段性交付记录。当前仓库的真实现状以 `README.md`、`docs/architecture.md`、`docs/formal-review.md`、`docs/testing.md` 为准；后续提交已补齐 structured_review schema/report/artifact API、SSE 实时流与 P0 收敛改造。

## 1. 架构说明

已在当前仓库根目录建立 008 项目，并将其定位为 **DeepResearchAgent 总控编排层 + 外部能力服务层 + 前后端统一入口**。DeepResearchAgent 在本项目中作为 planner/router/coordinator，而不是审查器本体。

## 2. 项目目录结构

- 前端：`apps/web`
- 后端：`apps/api`
- 编排层：`apps/api/src/orchestrator`
- adapter：`apps/api/src/adapters`
- fixtures：`fixtures`
- 工件：`artifacts`

## 3. 前端实现说明

前端使用 Next.js + React + TypeScript，已实现：

- 首页能力说明
- 任务创建表单
- health 概览
- 任务详情页
- plan / timeline / result / sources / debug 展示
- 轮询更新任务状态（历史阶段记录；当前代码已升级为 SSE 优先、断流回退轮询）

## 4. 后端实现说明

后端使用 FastAPI + SQLite + filesystem artifacts，已实现：

- `POST /api/tasks`
- `GET /api/tasks/{taskId}`
- `GET /api/tasks/{taskId}/result`
- `GET /api/tasks/{taskId}/events`
- `GET /api/capabilities`
- `GET /api/health`
- `GET /api/fixtures`

## 5. DeepResearchAgent 接入说明

采用 008 内部兼容 orchestrator 实现：

- `planner.py`
- `router.py`
- `deepresearch_runtime.py`

保证其角色是 orchestration/control plane，而非审查逻辑本体。

## 6. DeepTutor 接入说明

通过 `scripts/run_deeptutor_bridge.py` 暴露轻量 bridge，复用真实 DeepTutor ChatAgent。已完成 health 与 WebSocket chat 验证，并已被真实任务链路调用。

## 7. GPT Researcher 接入说明

通过 direct import 接入 `/tmp/008-discovery/gpt-researcher`，并由 008 侧注入 LLM / embedding / retriever 配置。

- 本地文档研究：008 自己提取文本，再交给 GPT Researcher report writer。
- 深度研究补强：当提供 `sourceUrls` 且 `useWeb=false` 时，008 会先抓取来源正文，再以 source-grounded static mode 生成研究报告，避免完全依赖外部搜索引擎。

## 8. Fast 知识库接入说明

已实现统一 Fast adapter：

- Mode A：dataset chunks 检索（首选）
- Mode B：collection 定向检索（严格 JSON parse）

输出结构已统一，且保留 raw response 以供调试。

## 9. 配置管理说明

- LLM：`century.json` + env override
- FastGPT：`gbcs-fast.json` + env override
- 敏感值只在服务端读取与脱敏展示

## 10. 运行说明

```bash
cd .
make bootstrap
make dev
```

## 11. 功能测试说明

已完成：

- backend pytest（`8 passed`）
- frontend lint/build
- 前端真实 knowledge_qa 端到端链路：`5e778a1c468340cf895846ffa3a3d146`
- API 深度研究成功链路：`0a76e1d975e2453c8fa263c6aa280412`
- API 文档研究成功链路：`7f0fc83965e94a66874e00b96e5a03ee`
- API 审查辅助成功链路：`23a57bd1d3a94454965452143325018b`
- 证据汇总：`artifacts/verification/task-matrix.json`

## 12. 联通验证说明

当前已打通：

- 本地 LLM health
- FastGPT Mode A
- DeepTutor health + chat
- DeepResearchRuntime → FastGPT → DeepTutor API 任务链路
- GPT Researcher import/health
- GPT Researcher local-doc research
- GPT Researcher source-grounded deep research
- 前端页面截图证据：`artifacts/verification/end-to-end-ui-or-api.png`

## 13. 已知限制

- DeepTutor 为轻量 bridge，不是官方全量平台镜像
- GPT Researcher 首次/长任务耗时较高；`useWeb=true` 或未提供 `sourceUrls` 时，仍更依赖外部搜索质量
- FastGPT Mode B 依赖 collectionId
- 当前仓库已升级为 SSE 优先、轮询回退；本条为历史阶段限制记录

## 14. 后续扩展方向

- 增加正式审查 pack registry
- 增加上传多文档研究
- 增加更多 reviewer workflow 与写回闭环
- 增加更广的结构化审查 pack / versioned goldens
