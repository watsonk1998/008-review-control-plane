# DELIVERY REPORT — 008 Review Control Plane

## 1. 架构说明

已在 `/Users/lucas/repos/review/008-review-control-plane` 新建 008 项目，并将其定位为 **DeepResearchAgent 总控编排层 + 外部能力服务层 + 前后端统一入口**。DeepResearchAgent 在本项目中作为 planner/router/coordinator，而不是审查器本体。

## 2. 项目目录结构

- 前端：`/Users/lucas/repos/review/008-review-control-plane/apps/web`
- 后端：`/Users/lucas/repos/review/008-review-control-plane/apps/api`
- 编排层：`/Users/lucas/repos/review/008-review-control-plane/apps/api/src/orchestrator`
- adapter：`/Users/lucas/repos/review/008-review-control-plane/apps/api/src/adapters`
- fixtures：`/Users/lucas/repos/review/008-review-control-plane/fixtures`
- 工件：`/Users/lucas/repos/review/008-review-control-plane/artifacts`

## 3. 前端实现说明

前端使用 Next.js + React + TypeScript，已实现：

- 首页能力说明
- 任务创建表单
- health 概览
- 任务详情页
- plan / timeline / result / sources / debug 展示
- 轮询更新任务状态

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

通过 direct import 接入 `/tmp/008-discovery/gpt-researcher`，并由 008 侧注入 LLM / embedding / retriever 配置。本地文档研究改用 008 自己提取文本后交给 GPT Researcher report writer 的方式。

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
cd /Users/lucas/repos/review/008-review-control-plane
make bootstrap
make dev
```

## 11. 功能测试说明

已完成：

- backend pytest
- frontend lint/build
- 真实 knowledge_qa API 链路
- 其余能力通过 `make verify-connectivity` 持续生成证据

## 12. 联通验证说明

当前已打通：

- 本地 LLM health
- FastGPT Mode A
- DeepTutor health + chat
- DeepResearchRuntime → FastGPT → DeepTutor API 任务链路
- GPT Researcher import/health

## 13. 已知限制

- DeepTutor 为轻量 bridge，不是官方全量平台镜像
- GPT Researcher 首次/长任务耗时较高
- FastGPT Mode B 依赖 collectionId
- 当前前端进度更新采用轮询

## 14. 后续扩展方向

- 增加正式审查 pack registry
- 增加上传多文档研究
- 增加 SSE / websocket 进度流
- 增加结构化审查 issue schema 与报告导出
