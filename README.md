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

## P0 结构化审查收敛范围

当前 `structured_review` 已做实为正式结构化审查入口，输入支持以下二选一：

- `fixtureId`
- `sourceDocumentRef`

显式 profile 参数包括：

- `documentType`
- `disciplineTags`
- `strictMode`
- `policyPackIds`

同时结果契约升级为稳定 DTO：

- `summary`
- `visibility`
- `resolvedProfile`
- `issues`
- `matrices`
- `artifactIndex`
- `reportMarkdown`
- `unresolvedFacts`

其中：

- `artifactIndex` 与 `GET /api/tasks/{taskId}/artifacts` 共享同一套官方 catalog，且对新任务是 authoritative source（即使为空）
- `manualReviewNeeded` 是 canonical 字段；`whetherManualReviewNeeded` 仅在 legacy task replay 的只读兼容层输出
- `visibility` 是结构化结果中的 top-level canonical 可视域对象，并直接携带 `parseWarnings`；`summary.visibilitySummary` 仅保留为展示摘要
- `strictMode` 当前保留为兼容字段，状态为 `reserved / no-op`

当前 P0 正式支持文档类型仅包括：

- `construction_org`
- `hazardous_special_scheme`

以下类型已具备 ready base pack，但 documentType 当前只保留 experimental 入口，不计入 P0 成功标准：

- `construction_scheme`
- `supervision_plan`
- `review_support_material`

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

当前 pack 状态简表：

- ready / official base：`construction_org.base`、`hazardous_special_scheme.base`
- ready / experimental base：`construction_scheme.base`、`supervision_plan.base`、`review_support_material.base`
- ready scenario：`lifting_operations.base`、`temporary_power.base`、`hot_work.base`、`gas_area_ops.base`
- placeholder scenario：`special_equipment.base`、`working_at_height.base`

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
make eval-review-ablations
make eval-review-cross-pack
make eval-review-cross-model
make smoke
make verify-connectivity
```

## structured_review 请求示例

```json
{
  "taskType": "structured_review",
  "capabilityMode": "auto",
  "query": "对该危大专项方案执行正式结构化审查",
  "sourceDocumentRef": {
    "refId": "upload-ref-1",
    "sourceType": "upload",
    "fileName": "hazardous-special-scheme-demo.pdf",
    "fileType": "pdf",
    "storagePath": "/absolute/path/to/artifacts/uploads/upload-ref-1/hazardous-special-scheme-demo.pdf",
    "displayName": "hazardous-special-scheme-demo.pdf"
  },
  "documentType": "hazardous_special_scheme",
  "disciplineTags": ["lifting_operations"],
  "strictMode": true,
  "policyPackIds": []
}
```

## artifact API

- `POST /api/uploads/documents`
- `GET /api/tasks/support-scope`
- `GET /api/tasks/{taskId}/artifacts`
- `GET /api/tasks/{taskId}/artifacts/{artifactName}`
- `PUT /api/tasks/{taskId}/reviewer-decision`

## structured_review 结果约束

- `manualReviewNeeded` 是唯一 canonical 人工复核布尔语义
- `whetherManualReviewNeeded` 仅为 legacy replay 兼容 alias，不再作为第二真相源
- issue 结果会保留 `evidenceMissing` 与 `manualReviewReason`
- parse 结果会保留 typed `visibility` / `parseMode` / `parserLimited`
- `result.visibility` 是唯一 canonical visibility contract
- `summary.visibilitySummary` 统一表达附件状态计数、重复章节、parse warnings 与 visibility reason counts，但不再作为第二事实源
- `disable_visibility_check` 仅保留给 eval / ablation 内部路径，不能作为公开任务入口参数
- 任务详情现在支持最小 reviewer decision：task-level / issue-level / attachment-level 复核状态与备注
- 系统不得把“未解析附件 / 当前不可视”直接写成“文档缺失”

## 配置原则

- LLM 配置默认读取 `/Users/lucas/tools/from-obsidian/AI/config/century.json`
- FastGPT 配置默认读取 `/Users/lucas/tools/from-obsidian/AI/config/gbcs-fast.json`
- 真实密钥只允许服务端读取
- 不把 API key、dataset key、collection key 硬编码进仓库

## 关键文档

- 资产勘查：`/Users/lucas/repos/review/008-review-control-plane/docs/discovery.md`
- 架构说明：`/Users/lucas/repos/review/008-review-control-plane/docs/architecture.md`
- 正式审查说明：`/Users/lucas/repos/review/008-review-control-plane/docs/formal-review.md`
- 运行说明：`/Users/lucas/repos/review/008-review-control-plane/docs/runbook.md`
- 测试记录：`/Users/lucas/repos/review/008-review-control-plane/docs/testing.md`
- 最终交付：`/Users/lucas/repos/review/008-review-control-plane/DELIVERY_REPORT.md`
