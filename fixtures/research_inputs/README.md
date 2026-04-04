# Research Inputs — 精选样本级结构化证据

## 本目录定位

本目录是从 `artifacts/research-pack/`（本地运行产物）中**精选**出来的、适合长期入仓、供研究型 AI 通过 GitHub 直接读取的**样本级结构化证据层**。

**本目录不是：**
- 替代 `artifacts/research-pack/` 的完整运行产物包
- 长期版本化的 gold truth
- 系统边界真相源（那是 README.md / docs/formal-review.md / fixtures/review_eval/README.md）
- 永久性评测结论

**本目录是：**
- V0.2 structured_review 双样本运行结果的精选快照
- 研究型 AI 做三角对比研究、差距裁决、truth 分层的主要结构化证据输入
- 证据层级为：**第 2 层 — 样本级结构化证据源**

## 证据层级（四层体系）

| 层级 | 来源 | 定位 |
|------|------|------|
| 第 1 层 | GitHub 仓库事实（README / formal-review / review_eval/README） | **系统边界真相源** |
| **第 2 层** | **本目录 `fixtures/research_inputs/`** | **样本级结构化证据源** |
| 第 3 层 | `fixtures/supervision/` 中的 Markdown 报告 | 人类可读呈现层 |
| 第 4 层 | Gemini deepresearch 结果 | seed / candidate reference |

## 目录结构

```
fixtures/research_inputs/
├── README.md                         ← 本文件
├── manifest.json                     ← 完整工件清单（含来源、生成参数、时间戳）
├── latest-eval-summary.md            ← 当前治理状态快照（非长期真相）
├── sample-a-cold-rolling/            ← 样本 A：冷轧厂 2030 单元三台行车电气系统改造
│   ├── structured-review-result.json       ← 完整结果对象（issues / visibility / matrices）
│   ├── structured-review-l0-visibility.json ← L0 可视域快照
│   ├── structured-review-rule-hits.json     ← 规则命中清单
│   ├── structured-review-facts.json         ← 事实抽取结果
│   ├── attachment-visibility-matrix.json    ← 附件可视域矩阵
│   ├── conflict-matrix.json                 ← 冲突矩阵
│   ├── hazard-identification-matrix.json    ← 危险源识别矩阵
│   ├── rule-hit-matrix.json                 ← 规则命中矩阵
│   └── section-structure-matrix.json        ← 章节结构矩阵
└── sample-b-puhua-rainwater/         ← 样本 B：培花初期雨水调蓄池建设工程
    └── ...（同上 9 个文件）
```

## 精选原则

本目录只纳入"研究型 AI 做三角对比研究、差距裁决、truth 分层时直接需要消费的结构化工件"。不是所有运行产物都适合入仓。

### 为什么只保留这 9 类样本工件

| 文件 | 纳入理由 |
|------|---------|
| `structured-review-result.json` | **最核心** — 包含 issues / visibility / resolvedProfile 等完整结果对象，是差距分析和 truth 分层的主要依据 |
| `structured-review-l0-visibility.json` | **L0 关键** — 可视域快照，直接决定 visibility truth 判断 |
| `structured-review-rule-hits.json` | **L1/L2 关键** — 规则命中清单，差距裁决的直接证据 |
| `structured-review-facts.json` | **L2 关键** — 事实抽取结果，fact → rule hit → evidence 闭环的起点 |
| 5 种 matrix | **高密度** — 小文件（<73K），提供附件可视域 / 冲突 / 危险源 / 规则命中 / 章节结构的矩阵视图 |

### 为什么不纳入以下文件

| 文件 | 不纳入理由 |
|------|-----------|
| `structured-review-parse.json` | **过大**（576K~2.6M）——是原始 PDF 文本解析输出，研究型 AI 不直接消费它做差距分析；facts.json 已是其下游精选产物 |
| `structured-review-candidates.json` | **中间产物** — 候选问题列表，是 rules→issues 过程中的中间结果，result.json 已包含最终 issues |
| `structured-review-report.md` | **已有重复** — 同一份 Markdown 报告已在 `fixtures/supervision/V0.2-*.md` 中存在，无需二次入仓 |
| `structured-review-report-buckets.json` | **中间桶分类** — 报告分桶的中间产物，研究型 AI 不直接消费 |
| `eval/*.json`（4 文件，共 940K） | **评测系统专用** — 主要用于 `make eval-review` 等自动化评测，`latest-eval-summary.md`（3.8K）已提供足够的治理快照 |
| `logs/`（4 文件，共 960K） | **原始运行日志** — 调试用途，非研究输入 |

> **这不是遗漏，是有意精选。** 如果后续发现某个未纳入文件确实被研究型 AI 频繁需要，可以按"精选原则"评估后增补。

## 与其他目录的关系

| 目录 | 角色 | 关系 |
|------|------|------|
| `fixtures/research_inputs/` | 精选结构化证据 | 从 `artifacts/research-pack/` 精选而来 |
| `artifacts/research-pack/` | 本地完整运行产物 | 本目录的来源；被 .gitignore 排除 |
| `fixtures/supervision/` | 双样本原始材料 + Markdown 结果 | 源施组 / V0.0 / V0.2 / Gemini 的 Markdown 版本 |
| `fixtures/review_eval/` | 评测基础设施 | ground truth / metadata / versioned cases |

## 使用约束

1. **不得将本目录文件视为 gold truth** — 它们是 V0.2 运行结果的快照，属于 internal-reviewed 准备层
2. **不得因某次 eval 通过就认定差距已关闭** — latest-eval-summary.md 是快照，不是永久结论
3. **PDF 边界仍有效** — 所有结构化输出仍基于 `pdf_text_only + parserLimited=True`
4. **Gemini 仍只是 seed** — 本目录不含 Gemini 结果（Gemini 在 `fixtures/supervision/` 中以 Markdown 存在）

## 如何重新生成

如需刷新本目录内容：

1. 在本地运行 `make supervision-review`（或等效命令）生成双样本 V0.2 结构化审查结果
2. 运行 `make eval-review` 生成 eval 摘要
3. 从 `artifacts/research-pack/` 中按本文件"精选原则"手动复制更新
4. 更新 `latest-eval-summary.md`
5. 提交并推送

注意：`artifacts/research-pack/` 本身被 `.gitignore` 排除，不会被推送到 GitHub。
