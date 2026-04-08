# Docs

本目录是 `008-review-control-plane` 的统一文档入口。
目标不是堆更多文档，而是把 **产品定义、能力边界、设计实现、质量验收、运行维护、研究材料、历史归档** 分层组织，减少口径漂移与重复维护。

> [!NOTE]
> **本文档职责**
> - 负责：
>   - 提供 docs 主导航入口、阅读顺序、真相源分工表与分层维护规则
> - 不负责：
>   - 不复制各主文档正文
>   - 不替代产品、治理、设计、质量或运行层主文档
> - 主适用读者：
>   - 首次进入本项目的产品、研发、测试、评审与运维协作者
> - 冲突处理：
>   - 若与具体主题文档冲突，以对应层级主真相源文档为准
> - 文档状态：
>   - Docs 主入口 / 主真相源

## 阅读建议

若你第一次进入本项目，建议按下面顺序阅读：

1. `00-product/`
   - 先理解 008 是什么、面向谁、解决什么问题
2. `10-governance/`
   - 再理解 formal-review 的制度总纲、V1 能力边界、验收口径
3. `20-design/`
   - 再看系统如何落地这些产品与治理约束
4. `30-quality/`
   - 再看测试方式、已知限制、验证报告
5. `40-operations/`
   - 需要运行维护时再看
6. `50-research/`
   - 需要了解背景研究时再看
7. `90-archive/`
   - 仅在需要查看历史入口或编译产物时使用，不作为日常真相源

## 目录结构

```text
docs/
  README.md

  00-product/
    product-strategy.md
    008-validate-prd-v1.md

  10-governance/
    formal-review.md
    008-v1-capability-boundary.md
    008-v1-acceptance-spec.md

  20-design/
    architecture.md
    review-structure-overview.md
    008-v1-implementation-skeleton.md
    008-v1-pr1-pr8-workplan.md
    integration/

  30-quality/
    testing.md
    known-limitations.md
    prd-validation-report.md

  40-operations/
    runbook.md

  50-research/
    discovery.md

  90-archive/
    full-prd-compiled.md
    prd-index.md
```

## 真相源分工

| 主题 | 主真相源 |
|---|---|
| docs 导航入口 | `docs/README.md` |
| 008 的 V1 产品定义 | `docs/00-product/008-validate-prd-v1.md` |
| 008 的长期产品方向与路线 | `docs/00-product/product-strategy.md` |
| formal-review 制度总纲 | `docs/10-governance/formal-review.md` |
| V1 能力边界 | `docs/10-governance/008-v1-capability-boundary.md` |
| V1 验收与 official 判定口径 | `docs/10-governance/008-v1-acceptance-spec.md` |
| V1 实施总设计 / 任务书骨架 | `docs/20-design/008-v1-implementation-skeleton.md` |
| V1 PR1–PR8 拆分执行骨架 | `docs/20-design/008-v1-pr1-pr8-workplan.md` |
| 系统架构说明 | `docs/20-design/architecture.md` |
| 审查结构总览 | `docs/20-design/review-structure-overview.md` |
| 测试执行方式与回归入口 | `docs/30-quality/testing.md` |
| 当前已知限制 | `docs/30-quality/known-limitations.md` |
| PRD 验证结果与验证纪要 | `docs/30-quality/prd-validation-report.md` |
| 运行维护与操作步骤 | `docs/40-operations/runbook.md` |
| 研究背景与发现过程 | `docs/50-research/discovery.md` |

## 各层职责

### 00-product
回答“产品是什么”。

包含：产品身份、用户、价值主张、主战场、非目标、路线与阶段目标。

不负责：详细实现契约、测试细节、运行手册、历史验证纪要。

### 10-governance
回答“什么能力算成立，边界在哪里”。

包含：formal-review 制度框架、V1 能力边界、official / ready / experimental 口径、验收与晋升标准。

不负责：详细模块设计、运行步骤、背景研究展开。

### 20-design
回答“系统如何实现”。

包含：架构、结构模型、实施设计、PR 拆分骨架、集成设计。

不负责：定义产品身份、改写治理口径、取代验收文档。

### 30-quality
回答“怎么测、当前有什么限制”。

包含：测试入口、回归方式、已知限制、验证报告。

不负责：替代 PRD、替代能力边界声明、替代实施设计。

### 40-operations
回答“怎么运行、怎么维护”。

### 50-research
回答“为什么曾经这样想、有哪些背景发现”。

### 90-archive
存放历史入口和编译产物，仅供归档与一次性阅读，不作为日常协作真相源。

## 文档维护规则

1. 不新增“全能型主文档”
   - 新文档必须明确归属到某一层
   - 新文档必须说明自己负责什么、不负责什么
2. 不重复定义主真相源
   - 如需引用，优先链接，不复制整段定义
3. 不让 archive 重新成为主入口
   - `90-archive/` 中的文档不得作为日常协作主依据
4. 产品、治理、设计、质量、运行、研究分层维护
   - 不跨层偷放核心定义
5. 若发生冲突
   - 先看本 README 的真相源分工表
   - 再以对应主真相源文档为准

## 推荐阅读路径

### 产品经理 / 方案负责人
- `00-product/008-validate-prd-v1.md`
- `00-product/product-strategy.md`
- `10-governance/008-v1-capability-boundary.md`
- `10-governance/008-v1-acceptance-spec.md`

### 架构 / 研发
- `10-governance/formal-review.md`
- `20-design/architecture.md`
- `20-design/review-structure-overview.md`
- `20-design/008-v1-implementation-skeleton.md`
- `20-design/008-v1-pr1-pr8-workplan.md`

### 测试 / 验收 / 评审
- `10-governance/008-v1-acceptance-spec.md`
- `30-quality/testing.md`
- `30-quality/known-limitations.md`
- `30-quality/prd-validation-report.md`

### 运行 / 运维
- `40-operations/runbook.md`

## 备注

本目录当前处于 V1 文档体系收口阶段。
如发现旧文件路径、旧入口、旧命名仍被引用，应逐步修正到本目录结构下。
