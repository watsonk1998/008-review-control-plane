# 008-review-control-plane

命名理由：延续 `/Users/lucas/repos/review/007-deepresearch` 的编号体系，且本项目不再把能力重心放在“审查器本体”，而是明确定位为 **review control plane**——即统一入口、总控编排、能力路由与未来运行时底座。

## 项目定位

`008-review-control-plane` 是一个新的多 Agent 总控平台骨架，同时开始承载一条独立的正式结构化审查子域：

- **前端**：统一任务入口、能力边界说明、任务状态与链路展示
- **后端**：FastAPI 任务 API、SQLite 状态存储、artifacts 落盘
- **DeepResearchAgent 兼容层**：`planner + router + coordinator + runtime`
- **能力服务层**：DeepTutor / GPT Researcher / FastGPT / 本地 LLM
- **Review 子域**：`parse -> facts -> rules -> evidence -> report` 的 `structured_review` 正式结构化审查流水线
- **知识层**：FastGPT chunks 检索优先，避免把 Fast 当成黑盒答案机

## 双轨能力

- `review_assist`：保留为快速辅助总结，结果里明确声明“不等于正式审查结论”
- `structured_review`：新增为正式结构化审查，输出 issues / matrices / Markdown report / JSON artifacts

## 目录结构

```text
/Users/lucas/repos/review/008-review-control-plane
├── README.md
├── DELIVERY_REPORT.md
├── Makefile
├── .env.example
├── docs/
├── apps/
│   ├── api/
│   └── web/
├── fixtures/
├── artifacts/
├── logs/
└── scripts/
```

## 已实现能力

- `knowledge_qa`：DeepResearchRuntime → FastGPT Mode A/B → DeepTutor 或 LLM 整理
- `deep_research`：DeepResearchRuntime → GPT Researcher → LLM 摘要
- `document_research`：fixture/docx → GPT Researcher 本地文档研究
- `review_assist`：FastGPT + DeepTutor + GPT Researcher + LLM 总结为辅助审查要点
- `structured_review`：DocumentLoader / review parser → facts → rule engine → evidence builder → formal report / matrices

## 快速启动

```bash
cd /Users/lucas/repos/review/008-review-control-plane
make bootstrap
make dev
```

默认端口：

- DeepTutor bridge: `http://127.0.0.1:8121`
- API: `http://127.0.0.1:8018`
- Web: `http://127.0.0.1:3008`

## 常用命令

```bash
make dev-bridge
make dev-api
make dev-web
make test
make test-review-unit
make test-review-integration
make eval-review
make smoke
make verify-connectivity
```

## 配置原则

- LLM 配置默认读取 `/Users/lucas/tools/from-obsidian/AI/config/century.json`
- FastGPT 配置默认读取 `/Users/lucas/tools/from-obsidian/AI/config/gbcs-fast.json`
- 真实密钥只允许服务端读取
- 不把 API key、dataset key、collection key 硬编码进仓库

## 关键文档

- 资产勘查：`/Users/lucas/repos/review/008-review-control-plane/docs/discovery.md`
- 架构说明：`/Users/lucas/repos/review/008-review-control-plane/docs/architecture.md`
- 运行说明：`/Users/lucas/repos/review/008-review-control-plane/docs/runbook.md`
- 测试记录：`/Users/lucas/repos/review/008-review-control-plane/docs/testing.md`
- 最终交付：`/Users/lucas/repos/review/008-review-control-plane/DELIVERY_REPORT.md`
