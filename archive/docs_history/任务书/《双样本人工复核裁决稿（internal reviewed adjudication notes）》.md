# 《双样本人工复核裁决稿（internal reviewed adjudication notes）》草案

**状态**：draft for `v0.2.0-internal-reviewed` preparation  
**样本范围**：样本 A（冷轧厂 2030 单元三台行车电气系统改造）、样本 B（培花初期雨水调蓄池建设工程）  
**文档性质**：内部复核底稿，不是 expert-golden，不是实施任务书，不是 Gemini 对照报告

---

## 0. 文档定位

本文不是 `v1.0.0-expert-golden`，也不是 implementation plan，更不是把 Gemini deepresearch 结果包装成“标准答案”的对照报告。本文的唯一目标，是在当前仓库边界、当前 research pack 结构化证据、当前双样本监督材料、当前治理边界与当前缺乏正式人工专家 gold 的现实下，形成一份**可追溯、可治理、强防过拟合**的 `internal reviewed adjudication notes` 草案，供后续 `v0.2.0-internal-reviewed` 版本化样本池准备使用。

本文因此只裁决到以下层级：  
1. 在当前可视域内，哪些 issue truth 可以成立；  
2. 哪些条目本质上是 visibility truth；  
3. 哪些条目只能停在 evidence truth / Needs Supplement；  
4. 哪些条目只能作为 enhancement only 或 seed reference；  
5. 哪些命题应被明确驳回，以防 versioned truth 被样本表面特征或 Gemini wording 污染。

---

## 1. 证据基础与裁决边界

### 1.1 证据层级

| 证据层级 | 具体材料 | 在本文中的角色 | 使用方式与限制 |
| --- | --- | --- | --- |
| 第 1 层：系统边界真相源 | `README.md`、`docs/formal-review.md`、`fixtures/review_eval/README.md` | 最高优先级边界 | 定义项目定位、正式 contract、version 语义与非协商边界；不得被样本观察或 Gemini 结果推翻。 |
| 第 2 层：样本级结构化证据源 | `fixtures/research_inputs/README.md`、样本 A/B 的 `structured-review-result.json`、`structured-review-l0-visibility.json`、`structured-review-facts.json`、`structured-review-rule-hits.json`、5 类 matrix | 样本 adjudication 主证据 | 本稿逐 issue 裁决以此层为主。当前入仓 research pack 是 **selected slice**：每样本 9 个结构化工件，而不是完整运行产物全集。 |
| 第 3 层：人类可读呈现层 | `fixtures/supervision/` 中 V0.0 / V0.2 / Gemini 六份 Markdown；`latest-eval-summary.md` | 对照与辅助说明 | 可用于横向比较、识别 wording 倾向与阶段性快照；不得盖过第 2 层 JSON / matrix。 |
| 第 4 层：seed / candidate reference | Gemini deepresearch 结果 | 候选问题 inventory 与差距探针 | 只允许用于 candidate discovery、auxiliary contrast、bootstrap reference；不得充当 truth 仲裁者。 |
| repo-carried governance 输入 | `fixtures/任务书/三角对比研究结果.md`、`《V0.3 边界声明》完整草案-prompt.md`、`《V0.2→V0.3 差距裁决与反过拟合约束清单》-prompt.md`、`V0.2 研究设计与实施总文档.md` | 研究吸收后的治理边界与方法参考 | 约束样本级裁决的写法与入池门槛，但其权重仍低于第 1 层仓库事实。特别说明：当前仓库快照中，V0.3 边界与差距清单是以 `-prompt.md` 载体入仓。 |

### 1.2 本稿的裁决锚点

本稿逐 issue 裁决时，**优先锚定**以下结构化工件，而不是先看 Markdown 报告文案：

- `structured-review-result.json -> issues[]`
- `structured-review-l0-visibility.json`
- `structured-review-facts.json`
- `structured-review-rule-hits.json`
- `rule-hit-matrix.json`
- `conflict-matrix.json`
- `hazard-identification-matrix.json`
- `attachment-visibility-matrix.json`
- `section-structure-matrix.json`

其中，`structured-review-result.json` 的 `issues[]` 是 issue-level adjudication 的第一锚点；`structured-review-l0-visibility.json` 与附件/章节矩阵是 visibility adjudication 的第一锚点；`structured-review-facts.json` 与 rule-hit / conflict / hazard matrices 用于校验 evidence sufficiency 与去重。

### 1.3 本稿承认的现实边界

第一，当前**没有正式 expert gold**。因此本文只能写 internal-reviewed 准备层，不得冒充专家终裁。  
第二，Gemini 当前**只能“顶一顶”**：它可以做 seed baseline、candidate inventory、gap probe，但不能做 truth arbiter。  
第三，当前双样本极有价值，但也极易诱导过拟合。凡是不能抽象成机制层问题的表面现象，一律不得直接入 truth 池。  
第四，当前 repo 中 `fixtures/research_inputs/` 是**selected research pack slice**：每样本 9 个入仓工件，可支持样本 adjudication，但不等于完整运行产物全集。repo-level contract 虽定义了更宽的结果对象（如 `artifactIndex`、`reportMarkdown`），但本稿只以当前入仓 snapshot 中实际可用的结构化字段为裁决依据，不把 snapshot 缺项误判为系统无此能力。

### 1.4 本稿可以裁到什么程度，不能假装裁到什么程度

本文可以裁到：

- issue 是否在**当前可视域**内成立；
- issue 的主 truth 类型与次 truth 类型；
- 当前证据是否足以把问题升级为 hard defect；
- 是否适合进入 `v0.2.0-internal-reviewed`；
- 是否只应保留为 seed reference、暂不纳入或明确不纳入。

本文不能假装裁到：

- expert-reviewed gold；
- 法律/工程双签字的最终正确答案；
- 多模态 / OCR / 图纸平台化之后的 truth；
- out-of-pack 域（例如深基坑 / 周边生命线 / 降水 / 顶管等）在当前仓库边界外的最终仲裁。

### 1.5 Provenance 简写

为便于在表格中压缩 provenance，本文使用如下简写：

- `A/...` 表示 `fixtures/research_inputs/sample-a-cold-rolling/...`
- `B/...` 表示 `fixtures/research_inputs/sample-b-puhua-rainwater/...`
- `A/result` / `B/result` 表示 `structured-review-result.json`
- `A/l0` / `B/l0` 表示 `structured-review-l0-visibility.json`
- `A/facts` / `B/facts` 表示 `structured-review-facts.json`
- `A/rule-hit` / `B/rule-hit` 表示 `rule-hit-matrix.json` 与 `structured-review-rule-hits.json`
- `A/conflict` / `B/conflict` 表示 `conflict-matrix.json`
- `A/section-matrix` / `B/section-matrix` 表示 `section-structure-matrix.json`
- `A/attachment-matrix` / `B/attachment-matrix` 表示 `attachment-visibility-matrix.json`

---

## 2. 复核方法与 truth taxonomy

### 2.1 裁决方法

本稿采用如下裁决顺序：

1. **先守边界**：以第 1 层 repo facts 确定 contract、official scope、version 语义与 visibility 非协商边界。  
2. **再看样本结构化证据**：以第 2 层 research pack 中的 result / visibility / facts / matrices 做 issue-level adjudication。  
3. **然后做横向对照**：使用 V0.0 / V0.2 / Gemini supervision Markdown 识别 wording 演化、候选问题扩张和重叠项。  
4. **最后才写入结论**：用 `Confirmed / Rejected / Needs Supplement / Enhancement Only` 与 truth taxonomy 输出裁决，并决定是否入池。

同时，本稿执行以下优先级约束：

- **样本级 truth layering 服从 repo-carried gap/boundary governance 输入**；
- repo-carried gap/boundary governance 输入服从 **README / formal-review / review_eval README**；
- 双样本局部观察**不得反推**新的主线产品边界。

### 2.2 truth taxonomy

本文显式采用四种 truth 类型：

1. **issue_truth**：问题本身在当前可视域与当前结构化证据下成立或不成立。  
2. **visibility_truth**：系统当前到底看到了什么、没看到什么；哪些结论被 parser / attachment visibility 阻断。  
3. **evidence_truth**：当前证据链是否足以把问题升级为更硬的 formal defect；若不够，则应停在 `Needs Supplement`。  
4. **enhancement_only**：这不是当前证据足以支持的硬问题，而是工程增强建议、整改优先级提示或 L3 workflow 提醒。

### 2.3 裁决标签

- **成立（Confirmed）**：当前结构化证据足以支持窄口径命题成立。  
- **不成立（Rejected）**：当前结构化证据已足以否定该命题，或该命题直接违反 repo 边界。  
- **待补证（Needs Supplement）**：存在 candidate signal，但证据不足、或被 visibility / missing fact 阻断，暂不能升级。  
- **仅建议增强（Enhancement Only）**：可保留为工程增强或 reviewer 提示，但不得冒充 hard defect。

### 2.4 证据充分度判定

- `sufficient`：关键事实与 issue 命题之间已形成稳定闭环。  
- `partial`：已有实质依据，但仍缺关键适用链、专项挂接或场景针对性补强。  
- `weak`：信号存在，但直接文证过弱，不宜入 versioned truth。  
- `blocked_by_visibility`：当前主要阻断来自 parser / attachment / PDF 可视域，而非简单“没写”。

### 2.5 入池原则

某条 truth 片段建议进入 `v0.2.0-internal-reviewed`，至少需要同时满足以下条件中的大多数：

- 有明确的第 2 层 provenance；
- 主 truth 类型清晰；
- 若受 visibility / evidence 限制，已显式写出限制说明；
- 表述是机制层问题，而不是样本表面词；
- 与更窄、可复核条目相比不发生严重重叠；
- 过拟合风险不高于 `medium`，且可通过 wording 控制在可接受范围内。

### 2.6 双样本核心裁决总表

| 编号 | 样本 | issue 名称 / issue 模式 | 裁决结果 | 主 truth 类型 | 次 truth 类型 | 证据充分度 | 可视域状态影响 | Gemini 参与角色 | 是否建议进入 v0.2.0-internal-reviewed | 过拟合风险 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A-01 | 样本 A | 核心章节完整性证据缺口（对应 ISSUE-001） | 待补证 | evidence_truth | issue_truth | partial | 当前正文可见，但章节映射与附件/表格承载存在偏移；非 parser 盲区 | none | 可进入 v0.2.0-internal-reviewed | low | 可裁为“结构完整性尚未稳固成立”，不可裁为“相关内容完全缺失”；prov=A/result.issue[ISSUE-001], A/facts.projectFacts.sectionPresence, A/attachment-1(parsed) |
| A-02 | 样本 A | 重复标题导致正式审查定位不稳定（ISSUE-002） | 成立 | issue_truth | evidence_truth | sufficient | 无实质阻断 | none | 可进入 v0.2.0-internal-reviewed | low | 重复标题为直接结构事实；prov=A/section-structure-matrix(duplicate=4), A/facts.projectFacts.duplicateSections |
| A-03 | 样本 A | 附件可视域缺口（A: 附件2仅标题可见，正文未解析） | 成立 | visibility_truth | evidence_truth | sufficient | attachment_unparsed；blocked_by_visibility | none | 可进入 v0.2.0-internal-reviewed | low | 只能裁为 visibility_gap，不得写成附件缺失；prov=A/l0.visibility, A/attachment-visibility-matrix, A/result.issue[ISSUE-003] |
| A-03N | 样本 A | 将“附件2未解析”直接裁为“附件缺失” | 不成立 | visibility_truth | issue_truth | sufficient | attachment_unparsed ≠ missing | none | 明确不纳入 | unacceptable | 属于违反 review_eval 非协商边界的错误命题；prov=A/attachmentFacts.visibility.counts.missing=0 |
| A-04 | 样本 A | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-004） | 待补证 | evidence_truth | issue_truth | partial | 正文可见，但适用边界需人工确认 | none | 仅保留为 seed reference | medium | 与 A-06/A-07/A-08 高度重叠；更适合作为宽口径 inventory，而非 versioned truth 主条目；prov=A/hazardFacts.specialSchemePlanStatus=generic_mention_only, A/result.issue[ISSUE-004] |
| A-05 | 样本 A | 工期-资源-高风险并行组织压力（ISSUE-005） | 仅建议增强 | enhancement_only | evidence_truth | sufficient | 无 parser 阻断，但属于 grounded engineering inference | auxiliary reference | 可进入 v0.2.0-internal-reviewed | medium | 可作为 L3 提示/整改优先级，不宜继续硬化为 hard defect；prov=A/conflict.scheduleVsResources.issueTriggered=true, A/shutdownWindowDays=7, A/laborTotal=37 |
| A-06 | 样本 A | 起重吊装专项方案挂接不清（ISSUE-006） | 待补证 | evidence_truth | issue_truth | partial | manual confirmation needed；非完全不可见 | none | 可进入 v0.2.0-internal-reviewed | low | 已识别吊装、吊车参数与验算痕迹，但专项方案挂接仍停在 generic mention；prov=A/result.issue[ISSUE-006], A/rule-hit(lifting_operations_special_scheme_linkage=manual_review_needed) |
| A-07 | 样本 A | 动火场景缺少火灾类针对性应急安排（ISSUE-007） | 成立 | issue_truth | evidence_truth | sufficient | 当前 DOCX 可视域足以支持窄口径判断 | none | 可进入 v0.2.0-internal-reviewed | low | 成立的是“针对性火灾/爆燃类应急映射不足”，不是“完全没有应急安排”；prov=A/hotWork=true, A/emergency.planTitles(4 titles, none fire/explosion), A/result.issue[ISSUE-007] |
| A-08 | 样本 A | 危险环境控制—监测—应急闭环不足（A: 煤气区域，ISSUE-008） | 成立 | issue_truth | evidence_truth | partial | 当前正文可见；结论受场景针对性证据限制 | candidate only | 可进入 v0.2.0-internal-reviewed | medium | 成立的是“闭环不完整”，不是 Gemini 式“系统性缺失”；prov=A/gasArea=true, A/measureSectionPresent=true, A/monitoringSectionPresent=true, A/emergency.planTitles lacks gas-specific mapping |
| A-R1 | 样本 A | “起重吊装验算完全缺失”这一命题 | 不成立 | issue_truth | evidence_truth | sufficient | 无阻断 | candidate only | 明确不纳入 | high | 仓库结构化证据已给出 50t 吊车、2.86t 计算起重量与 calculation_traceability=pass；prov=A/hazardFacts, A/rule-hit(lifting_operations_calculation_traceability=pass) |
| B-VIS | 样本 B | PDF text-only 可视域边界（表格/图示/附图未保留，附件可见性未知） | 成立 | visibility_truth | evidence_truth | sufficient | pdf_text_only + parserLimited + parseWarnings | none | 可进入 v0.2.0-internal-reviewed | low | 这是样本 B 最基础的 truth fragment；所有 issue adjudication 均须服从该边界；prov=B/l0.visibility.parseWarnings |
| B-01 | 样本 B | 核心章节完整性证据缺口（ISSUE-001） | 待补证 | evidence_truth | visibility_truth | blocked_by_visibility | pdf_text_only；construction/resource/monitoring mapping 不稳 | none | 可进入 v0.2.0-internal-reviewed | low | 可裁为“当前可视域下结构完整性不足以稳判”，不可裁为“正文内容必然缺失”；prov=B/sectionPresence(constructionPlan=false, resourcePlan=false, monitoringPlan=false), B/result.issue[ISSUE-001] |
| B-02 | 样本 B | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-002） | 待补证 | evidence_truth | issue_truth | partial | parserLimited；需人工确认挂接边界 | none | 仅保留为 seed reference | medium | 与 B-04 及若干子场景高度重叠；保留为 candidate inventory 更稳；prov=B/result.issue[ISSUE-002], B/hazardFacts.specialSchemePlanStatus=generic_mention_only |
| B-03 | 样本 B | 应急预案针对性不足（ISSUE-003） | 待补证 | evidence_truth | visibility_truth | blocked_by_visibility | 未解析到 emergency plan titles；PDF 文本可视域受限 | none | 可进入 v0.2.0-internal-reviewed | low | 成立的是“当前证据不足以建立针对性映射”，不是“已证实完全没有应急体系”；prov=B/unresolvedFacts.missing_emergency_plan_titles, B/targetedPlanCount=0, B/result.issue[ISSUE-003] |
| B-04 | 样本 B | 起重吊装专项方案挂接不清（ISSUE-004） | 待补证 | evidence_truth | issue_truth | partial | manual confirmation needed under pdf_text_only | none | 可进入 v0.2.0-internal-reviewed | low | 可裁为“专项挂接仍需人工确认”，不可裁为“起重方案必然缺失”；prov=B/result.issue[ISSUE-004], B/rule-hit(lifting_operations_special_scheme_linkage=manual_review_needed) |
| B-05 | 样本 B | 临时用电/停送电控制链路不完整（ISSUE-005） | 成立 | issue_truth | visibility_truth | partial | 仅在当前文本可视域内成立；monitoring 缺口明显 | none | 可进入 v0.2.0-internal-reviewed | low | 成立的是“当前可视文本未形成完整链路”，而非对全部附图附表作全量否定；prov=B/temporaryPower=true, B/measureSectionPresent=true, B/monitoringSectionPresent=false, B/result.issue[ISSUE-005] |
| B-06 | 样本 B | 动火场景火灾类针对性应急缺口（ISSUE-006） | 待补证 | evidence_truth | issue_truth | weak | PDF text-only + planTitles unresolved | none | 暂不纳入 versioned truth | medium | 与 B-03 部分重叠，且当前直接文证较弱；保留为后续人工复核候选更稳；prov=B/result.issue[ISSUE-006], B/docEvidenceCount=3 |
| B-R1 | 样本 B | “章节结构存在重复标题”这一命题 | 不成立 | issue_truth | evidence_truth | sufficient | 无此类直接事实 | none | 明确不纳入 | low | duplicateSections=[]；rule pass；prov=B/section-structure-matrix duplicate=0, B/rule-hit(construction_org_duplicate_sections=pass) |
| B-R2 | 样本 B | “附件缺失”这一命题 | 不成立 | visibility_truth | issue_truth | sufficient | attachment_visibility_may_be_unknown | none | 明确不纳入 | unacceptable | PDF 路径下附件矩阵为空且 visibility 未支持缺失判定，不能倒推出缺失；prov=B/l0.parseWarnings includes pdf_attachment_visibility_may_be_unknown |
| B-R3 | 样本 B | “停机窗口/资源冲突已成立”这一命题 | 不成立 | evidence_truth | issue_truth | sufficient | 关键 schedule/resource facts 缺失 | candidate only | 明确不纳入 | medium | shutdownWindowDays 与 laborTotal 均为 null，conflict rule pass；prov=B/conflict.scheduleVsResources.issueTriggered=false, B/unresolvedFacts |
| B-R4 | 样本 B | “起重吊装计算痕迹完全缺失”这一命题 | 不成立 | issue_truth | evidence_truth | sufficient | 无阻断到此程度 | candidate only | 明确不纳入 | medium | 虽然 calculatedLiftWeightTon 未抽到，但 calculationEvidencePresent=true 且 calculation_traceability=pass；prov=B/hazardFacts, B/rule-hit(lifting_operations_calculation_traceability=pass) |

---

## 3. 样本 A：冷轧厂人工复核裁决

### 3.1 样本背景与可视域边界

样本 A 来自 DOCX 路径，`parseMode=docx_structured`、`parserLimited=false`。其主要边界不是 parser 失真，而是**正文结构问题 + 局部附件可视域缺口**：附件 1 `parsed`，附件 2 `attachment_unparsed`；顶层 `manualReviewNeeded=true`，reason 为 `title_detected_without_attachment_body`。在事实层，系统已提取到起重吊装、煤气区域作业、动火、临时用电等高风险类别，也提取到 50t 吊车、2.86t 计算起重量、7 天停机窗口、37 人劳动力投入，以及 4 个应急预案标题。这意味着样本 A 中很多判断都不是“零基础猜测”，而是对**已有事实、已有措施、已有应急标题**之上的闭环完整性判断。

### 3.2 样本 A 关键 issue 裁决表

| 编号 | issue 名称 / issue 模式 | 裁决结果 | 主 truth 类型 | 次 truth 类型 | 证据充分度 | 是否建议进入 v0.2.0-internal-reviewed | 过拟合风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-01 | 核心章节完整性证据缺口（对应 ISSUE-001） | 待补证 | evidence_truth | issue_truth | partial | 可进入 v0.2.0-internal-reviewed | low |
| A-02 | 重复标题导致正式审查定位不稳定（ISSUE-002） | 成立 | issue_truth | evidence_truth | sufficient | 可进入 v0.2.0-internal-reviewed | low |
| A-03 | 附件可视域缺口（A: 附件2仅标题可见，正文未解析） | 成立 | visibility_truth | evidence_truth | sufficient | 可进入 v0.2.0-internal-reviewed | low |
| A-04 | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-004） | 待补证 | evidence_truth | issue_truth | partial | 仅保留为 seed reference | medium |
| A-05 | 工期-资源-高风险并行组织压力（ISSUE-005） | 仅建议增强 | enhancement_only | evidence_truth | sufficient | 可进入 v0.2.0-internal-reviewed | medium |
| A-06 | 起重吊装专项方案挂接不清（ISSUE-006） | 待补证 | evidence_truth | issue_truth | partial | 可进入 v0.2.0-internal-reviewed | low |
| A-07 | 动火场景缺少火灾类针对性应急安排（ISSUE-007） | 成立 | issue_truth | evidence_truth | sufficient | 可进入 v0.2.0-internal-reviewed | low |
| A-08 | 危险环境控制—监测—应急闭环不足（A: 煤气区域，ISSUE-008） | 成立 | issue_truth | evidence_truth | partial | 可进入 v0.2.0-internal-reviewed | medium |

### 3.3 逐 issue 裁决说明

#### A-01 核心章节完整性证据缺口 —— 裁为 `待补证`
本条不能直接裁成“正文一定缺少核心章节”。原因在于：一方面，`sectionPresence` 确实显示 `schedulePlan=false`、`resourcePlan=false`、`calculationBook=false`；另一方面，样本 A 又实际抽到了 `shutdownWindowDays=7`、`laborTotal=37`、附件 1 `施工网络进度表` 已解析、起重参数与验算痕迹也已存在。  
因此，本稿确认的是 **evidence truth**：当前 formal structure completeness 尚未稳固成立，存在需要补件/补结构映射的缺口；但不确认“这些内容在原文中绝对不存在”。

**Provenance**：`sample-a-cold-rolling/structured-review-result.json` ISSUE-001；`structured-review-facts.json -> projectFacts.sectionPresence / scheduleFacts / resourceFacts`；`attachment-visibility-matrix.json`。

#### A-02 重复标题导致正式审查定位不稳定 —— 裁为 `成立`
这是样本 A 中最稳的直接结构事实之一。`section-structure-matrix` 明确出现 4 个 duplicate section，`projectFacts.duplicateSections` 也给出 `防火安全`、`环境管理计划`。这类问题属于直接结构异常，不受 parser blind spot 主导。  
因此本条作为 **issue truth** 进入 internal-reviewed 是稳妥的。

**Provenance**：`section-structure-matrix.json`；`structured-review-facts.json -> projectFacts.duplicateSections`；`structured-review-result.json` ISSUE-002。

#### A-03 附件可视域缺口 —— 裁为 `成立`
本条是标准的 **visibility truth**。附件 1 为 `parsed`，附件 2 为 `attachment_unparsed`，顶层 visibility 给出 `manualReviewNeeded=true`。  
因此可确认“附件可视域缺口存在”，但**绝不能**把它翻译成“附件缺失”。该负命题已经在 A-03N 中明确驳回。

**Provenance**：`structured-review-l0-visibility.json`；`attachment-visibility-matrix.json`；`structured-review-result.json` ISSUE-003。

#### A-04 / A-06 专项方案挂接问题 —— 宽口径降级、窄口径保留
A-04 的宽口径表述“高风险作业已识别，但专项方案挂接不清”与 A-06、A-07、A-08 存在明显重叠。对于 versioned truth，继续保留这个宽口径总括项会导致双计数和 severity 放大。  
相比之下，A-06“起重吊装场景专项方案挂接不清”更窄、更可追溯：样本已识别起重吊装、50t 吊车、2.86t 计算起重量与若干吊装作业文证，但 `specialSchemePlanStatus=generic_mention_only`，对应 rule hit 为 `manual_review_needed`。  
因此：A-04 降为 seed reference；A-06 作为 `Needs Supplement` 的 evidence truth 保留入池。

**Provenance**：`structured-review-result.json` ISSUE-004 / ISSUE-006；`structured-review-facts.json -> hazardFacts.specialSchemePlanStatus / craneCapacityTon / calculatedLiftWeightTon`；`rule-hit-matrix.json`。

#### A-05 工期—资源—高风险并行组织压力 —— 裁为 `仅建议增强`
A 样本确有 grounded inference 基础：`shutdownWindowDays=7`、`laborTotal=37`、多高风险类别并行，且冲突矩阵 `scheduleVsResources.issueTriggered=true`。  
但该条本质上仍是 **engineering inference / workflow 提示**，不宜在当前证据条件下继续硬化为 hard defect。更稳妥的做法，是把它写成 `enhancement_only`：可作为整改优先级、资源协调提示、reviewer 关注点，而非正式硬缺陷 truth。

**Provenance**：`conflict-matrix.json`；`structured-review-facts.json -> scheduleFacts / resourceFacts / hazardFacts`；`structured-review-result.json` ISSUE-005。

#### A-07 动火场景缺少火灾类针对性应急安排 —— 裁为 `成立`
样本 A 当前可视域内，动火场景与多条防火措施是明确可见的；同时，结构化抽取的 4 个应急预案标题中未见火灾/爆燃类针对性映射。  
因此可确认的不是“没有任何应急安排”，而是**动火场景与火灾类针对性应急映射之间存在缺口**。这一表述既保留了 evidence grounding，也避免把已有预案与已有措施完全抹掉。

**Provenance**：`structured-review-result.json` ISSUE-007；`structured-review-facts.json -> emergencyFacts.planTitles / hazardFacts.hotWork`。

#### A-08 危险环境控制—监测—应急闭环不足（A: 煤气区域） —— 裁为 `成立`
A 样本已经识别 `gasArea=true`，同时 `measureSectionPresent=true`、`monitoringSectionPresent=true`，说明这里不是“措施完全空白”。  
但在当前可视域内，看不到与煤气区域事故类型稳定对齐的针对性应急映射，且 issue 的本体表述是“控制与应急链路不完整”。本稿接受这个窄口径表述，拒绝把它升级成“系统性缺失”或“完全无管控”。  
因此，本条成立的是真正的 **closure gap**，而非 Gemini 风格的极端 severity。

**Provenance**：`structured-review-result.json` ISSUE-008；`structured-review-facts.json -> hazardFacts.gasArea / emergencyFacts.planTitles`；`hazard-identification-matrix.json`。

#### A-R1 “起重吊装验算完全缺失” —— 裁为 `不成立`
该命题与现有结构化证据直接冲突。样本 A 已抽到 50t 吊车、2.86t 计算起重量，且 `lifting_operations_calculation_traceability=pass`。  
因此，该命题不能进入任何 versioned truth；它只能作为反过拟合样例，提醒后续不要把 Gemini 的更强 narrative 反向硬编码成样本 A 的绝对缺失命题。

**Provenance**：`structured-review-facts.json -> hazardFacts`；`rule-hit-matrix.json`；`structured-review-rule-hits.json`。

### 3.4 样本 A 入池结论摘要

样本 A 建议进入 `v0.2.0-internal-reviewed` 的条目，不是“把 A 的全部问题照单全收”，而是收敛为几类可追溯 truth 片段：  
（1）可直接确认的结构/visibility truth：A-02、A-03；  
（2）可进入但需带证据边界说明的 evidence/issue truth：A-01、A-06、A-07、A-08；  
（3）可以入池，但必须明确降格为 `enhancement_only` 的 L3 条目：A-05。  
宽口径的 A-04 保留为 seed reference，更窄、更可复核的 A-06/A-07/A-08 才是后续 versioned truth 的合适载体。

---

## 4. 样本 B：培花人工复核裁决

### 4.1 样本背景与可视域边界

样本 B 来自 PDF 路径，`parseMode=pdf_text_only`、`parserLimited=true`，并带有 `pdf_tables_not_preserved`、`pdf_figures_images_not_parsed`、`pdf_attachment_visibility_may_be_unknown`、`pdf_source_pages:276`、`pdf_extracted_pages:261` 等 parse warnings。附件矩阵为空并不等于“无附件”或“附件缺失”，而只是当前 text-only 可视域下**不能稳定建立附件可见性 truth**。在事实层，系统仍识别到起重吊装、临时用电、动火与 50t 吊车，并给出 `specialSchemePlanStatus=generic_mention_only`；但 `calculatedLiftWeightTon`、`shutdownWindowDays`、`laborTotal`、`emergency.planTitles` 等关键事实为空，同时 `monitoringSectionPresent=false`。因此，样本 B 的一阶问题不是“系统完全没识别到工程风险”，而是**parser-limited PDF 使事实链出现大面积空白**。

这里还需要额外记录一个治理张力：样本 B 的 `summary.manualReviewNeeded=true`，但 `l0.visibility.manualReviewNeeded=false`。这说明 parser-limited PDF 的压力，当前仍主要通过 issue-level `partial / blocked_by_missing_fact` 与 `unresolvedFacts` 体现，而没有完全前置成更强的 top-level visibility block。  
本稿因此采用更保守的处理：**B 样本先立 visibility truth，再谈 issue truth**。

### 4.2 样本 B 关键 issue 裁决表

| 编号 | issue 名称 / issue 模式 | 裁决结果 | 主 truth 类型 | 次 truth 类型 | 证据充分度 | 是否建议进入 v0.2.0-internal-reviewed | 过拟合风险 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-VIS | PDF text-only 可视域边界（表格/图示/附图未保留，附件可见性未知） | 成立 | visibility_truth | evidence_truth | sufficient | 可进入 v0.2.0-internal-reviewed | low |
| B-01 | 核心章节完整性证据缺口（ISSUE-001） | 待补证 | evidence_truth | visibility_truth | blocked_by_visibility | 可进入 v0.2.0-internal-reviewed | low |
| B-02 | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-002） | 待补证 | evidence_truth | issue_truth | partial | 仅保留为 seed reference | medium |
| B-03 | 应急预案针对性不足（ISSUE-003） | 待补证 | evidence_truth | visibility_truth | blocked_by_visibility | 可进入 v0.2.0-internal-reviewed | low |
| B-04 | 起重吊装专项方案挂接不清（ISSUE-004） | 待补证 | evidence_truth | issue_truth | partial | 可进入 v0.2.0-internal-reviewed | low |
| B-05 | 临时用电/停送电控制链路不完整（ISSUE-005） | 成立 | issue_truth | visibility_truth | partial | 可进入 v0.2.0-internal-reviewed | low |
| B-06 | 动火场景火灾类针对性应急缺口（ISSUE-006） | 待补证 | evidence_truth | issue_truth | weak | 暂不纳入 versioned truth | medium |

### 4.3 逐 issue 裁决说明

#### B-VIS PDF text-only 可视域边界 —— 裁为 `成立`
样本 B 的 first-order truth 是 visibility truth，而不是任何单条缺陷命中。`pdf_text_only`、`parserLimited=true`、tables/figures not preserved、attachment visibility may be unknown 等 parse warnings，共同决定了：后续 issue 只能在当前文本可视域内成立。  
因此，尽管样本 B 没有像 A 那样输出专门的 visibility issue，本稿仍将 `B-VIS` 单列入池，作为所有 B 样本裁决的前置边界。

**Provenance**：`structured-review-l0-visibility.json`；`structured-review-result.json -> summary.visibilitySummary`。

#### B-01 核心章节完整性证据缺口 —— 裁为 `待补证`
样本 B 的 `sectionPresence` 显示 `constructionPlan=false`、`resourcePlan=false`、`monitoringPlan=false`，但该样本又处于 text-only PDF 条件，表格/附图大量未保留。  
因此，B-01 更适合被写成 **blocked_by_visibility 的 evidence truth**：当前结构化证据不足以稳定确认章节完整性，而不是已经证实原文正文一定缺少这些内容。

**Provenance**：`structured-review-result.json` ISSUE-001；`structured-review-facts.json -> projectFacts.sectionPresence`；`structured-review-l0-visibility.json`。

#### B-02 / B-04 专项方案挂接问题 —— 宽口径降级、窄口径保留
与样本 A 一样，B-02 宽口径条目与 B-04 起重吊装窄口径条目重叠明显。  
B-04 更可复核：样本已识别起重吊装、50t 吊车、若干吊装文证与 calculation evidence，但 rule hit 仍给出 `lifting_operations_special_scheme_linkage=manual_review_needed`。因此，B-04 可以作为 `Needs Supplement` 的 evidence truth 入池。  
B-02 则更适合作为 seed inventory，提醒后续人工或更多 pack 资产再展开，不宜现在就写进 versioned truth 主表。

**Provenance**：`structured-review-result.json` ISSUE-002 / ISSUE-004；`structured-review-facts.json -> hazardFacts.specialSchemePlanStatus / calculationEvidencePresent`；`rule-hit-matrix.json`。

#### B-03 应急预案针对性不足 —— 裁为 `待补证`
B 样本 `emergency.planTitles=[]` 且 `targetedPlanCount=0`，同时 `unresolvedFacts` 显式出现 `missing_emergency_plan_titles`。这说明当前 evidence chain 确实无法建立稳定的针对性应急映射。  
但由于样本 B 是 parser-limited PDF，本稿只确认 **evidence truth**：当前文本可视域不足以支撑“针对性已建立”的判断；并不确认“应急体系绝对不存在”。

**Provenance**：`structured-review-result.json` ISSUE-003；`structured-review-facts.json -> emergencyFacts / unresolvedFacts`。

#### B-05 临时用电/停送电控制链路不完整 —— 裁为 `成立`
这是样本 B 中少数可以在 parser 限制下做窄口径确认的条目。理由是：`temporaryPower=true`，`measureSectionPresent=true`，但 `monitoringSectionPresent=false`；同时应急 plan titles 未抽到，rule hit 为 `temporary_power_control_linkage=hit`。  
因此，本稿确认的是“**当前文本可视域中的控制链路不完整**”，而不是对 PDF 原件所有附图附表作全量否定。

**Provenance**：`structured-review-result.json` ISSUE-005；`structured-review-facts.json -> hazardFacts.temporaryPower / measureSectionPresent / monitoringSectionPresent / emergencyFacts`；`rule-hit-matrix.json`。

#### B-06 动火场景火灾类针对性应急缺口 —— 裁为 `待补证`
B-06 与 B-03 存在一定重叠，而且当前直接文证更弱：issue 的 docEvidence 只有 3 条，且样本整体处于 text-only PDF 条件。  
因此，本稿不把 B-06 直接升入 versioned truth，而把它保留在 future adjudication candidate 区：如果后续人工能在原 PDF 中确认更多针对性应急映射缺口，再考虑升格。

**Provenance**：`structured-review-result.json` ISSUE-006；`structured-review-facts.json -> emergencyFacts.planTitles=[]`。

#### B-R1 / B-R2 / B-R3 / B-R4 —— 四个明确驳回命题
- **B-R1**：重复标题命题不成立。`duplicateSections=[]`，rule 为 `pass`。  
- **B-R2**：附件缺失命题不成立。当前只有 `attachment_visibility_may_be_unknown`，不能倒推出缺失。  
- **B-R3**：停机窗口/资源冲突命题不成立。`shutdownWindowDays` 与 `laborTotal` 均为 null，`scheduleVsResources.issueTriggered=false`。  
- **B-R4**：起重吊装计算痕迹完全缺失命题不成立。虽未抽到 `calculatedLiftWeightTon`，但 `calculationEvidencePresent=true`，rule 为 `pass`。  

这些驳回项很重要，因为它们构成了样本 B 的 anti-overfit 负样例：**不能用 parser-limited + narrative expansion 替代结构化 truth。**

### 4.4 样本 B 入池结论摘要

样本 B 建议进入 `v0.2.0-internal-reviewed` 的，不应是“把 PDF 文本里所有命中都硬化为缺陷”，而应是：  
（1）先把 `B-VIS` 作为 visibility truth fragment 固化；  
（2）把 `B-01`、`B-03`、`B-04` 明确写成 `Needs Supplement` / `blocked_by_visibility` 或 `partial` 的 evidence truth；  
（3）把 `B-05` 窄口径确认成“当前文本可视域内的链路不完整”，并附 parser 限制说明。  
宽口径 `B-02` 以及与 B-03 重叠、直接文证更弱的 `B-06` 暂不进入 versioned truth 主表。

---

## 5. 双样本交叉裁决观察

### 5.1 双样本共同可确认的机制型问题

第一，**visibility truth 必须与 issue truth 永久分离**。样本 A 的 `attachment_unparsed` 和样本 B 的 `pdf_text_only + attachment_visibility_may_be_unknown` 都证明：系统只能如实记录“当前看到什么/没看到什么”，不能把不可视直接翻译成缺失或硬缺陷。

第二，**高风险事实识别 ≠ 专项方案挂接闭环**。双样本都识别出了高风险场景，但更稳的裁决并不是“方案一定缺失”，而是“当前证据只支持 `generic_mention_only` / `manual_review_needed` / `partial`”。这类条目更适合作为 evidence truth 或 issue truth 的窄口径版本，而不是宽口径一刀切结论。

第三，**应急预案的 truth layering 不能把“已有措施/已有预案标题”与“闭环完整”混为一谈**。样本 A 已有 4 个应急预案标题，但仍可成立“动火火灾类针对性不足”与“煤气区域闭环不完整”；样本 B 则因为 `planTitles=[]` 且 parserLimited，只能更保守地裁为 `Needs Supplement`。

第四，**L3 grounded inference 必须服从关键事实是否到位**。样本 A 因 `shutdownWindowDays=7`、`laborTotal=37` 且多高风险并行，冲突矩阵可触发真实组织压力；样本 B 因对应 facts 为空，`scheduleVsResources` 明确不触发。不能因为 Gemini 在 B 上写出了更长的工程论证，就反向硬造 B 的 L3 truth。

第五，**ready pack 覆盖上限会伪装成“模型差距”**。双样本都提示：V0.2 与 Gemini 的差距，不只也不主要是“谁更像专家”，而是 parser 能力、facts 完整性、pack/policy 资产覆盖与 workflow language 的联合差距。

### 5.2 仅属样本特有、不得直接抽象成通用 truth 的现象

样本 A 特有的高价值现象包括：煤气区域作业、7 天停机窗口、37 人资源投入、附件 2 `施工总平面布置图`、重复标题“防火安全 / 环境管理计划”。  
样本 B 特有的高价值现象包括：`pdf_source_pages:276 / extracted_pages:261`、大量附图/附表标题、深基坑/周边生命线/降水/顶管等更宽工程域背景。

这些事实都可以作为研究线索，但**不能**直接上升为通用 rule truth、prompt template 或 adjudication language。

### 5.3 可抽象成通用问题模式的条目

可以进入更高一层抽象的，不是具体样本词，而是以下机制缺口：

1. 附件/附图不可视与“附件缺失”混淆。  
2. 高风险场景识别与专项方案适用边界未形成闭环。  
3. 已有措施 / 已有预案标题 与“控制-监测-应急闭环完整”之间的差值。  
4. 工期—资源—高风险并行冲突对 L3 inference 的事实依赖。  
5. PDF text-only 导致 tables / figures / appendices / monitoring facts 断裂。  
6. 宽口径 issue 与窄口径、可复核 issue 之间的去重与优先级治理。

### 5.4 明确不能抽象，否则会诱导过拟合的写法

不能抽象的包括：项目名、文件名、fixture id、固定吨位、固定工期天数、固定人数、具体章节标题、具体附件名，以及任何 Gemini 报告中的强结论措辞。  
一旦把这些元素直接写成“通用 truth”，系统就会退化成“在两份样本上更像答案”的解释器，而不是更稳的 structured reviewer。

---

## 6. Gemini seed 的临时使用说明

### 6.1 本文中 Gemini 的允许角色

Gemini 在本文中只承担三种受限角色：

1. **candidate issue inventory**：帮助暴露 V0.2 与更宽工程叙事之间的差距。  
2. **bootstrap substitute / seed baseline**：作为 `v0.1.0-gemini-seed` 语境下的过渡性参照。  
3. **auxiliary contrast**：用于观察哪里是 wording 扩张，哪里是机制性差距。

### 6.2 本文明确没有让 Gemini 做什么

本文**没有**让 Gemini 充当：

- gold truth  
- 最终仲裁者  
- 规则答案库  
- adjudication language 模板来源  

换言之，Gemini 提到某项，并不自动成立；Gemini 没提到某项，也不自动不成立。

### 6.3 本文中实际参考了 Gemini 的位置

- 样本 A：Gemini 提供了吊装站位承载力、特种作业资质、EMI、资源极限调配等更宽 candidate inventory，但本稿只吸收其中“应避免把 closure gap 写成 systemic absence”的反面教训，并未把这些候选直接入池。  
- 样本 B：Gemini 展开了深基坑、承压水、周边生命线工程、微顶管、多工艺耦合等复杂域风险；本稿承认这些是重要 candidate，但由于当前 ready pack 覆盖、parser 可视域和人工裁决资源都不足，它们暂不进入 `v0.2.0-internal-reviewed` 主 truth 池。

### 6.4 为什么本文仍然不能叫 gold adjudication

原因非常直接：  
一，没有正式的人类专家逐 issue gold；  
二，当前只是双样本 internal reviewed 准备层；  
三，Gemini 只是 seed 参考，不是 expert sign-off；  
四，样本 B 的 parserLimited 边界意味着相当多结论只能停在 evidence truth 或 visibility truth。

---

## 7. 反过拟合裁决约束

1. **不得按项目名 / 文件名 / fixture id 建 truth。**  
   冷轧厂、培花、附件 2、DN3600、50t、7 天、37 人，都只能作为样本事实，不得写成跨样本规则。

2. **不得把 Gemini wording 写成 adjudication language。**  
   本稿禁止把“系统性缺失”“根本性失误”“致命盲区”等 Gemini 风格 severity 直接复制为 internal-reviewed 表述，除非第 2 层结构化证据本身足以支撑。

3. **不得把 visibility truth 混写成 issue truth。**  
   `attachment_unparsed`、`referenced_only`、`pdf_attachment_visibility_may_be_unknown`、`pdf_tables_not_preserved` 都不能被翻译成“附件缺失”或“内容不存在”。

4. **不得因为单样本高表现而直接升格规则。**  
   即使 A 上某条 L3 inference 看起来合理，也必须先经过更多 versioned cases 或 reviewer gate，才能考虑上升为更稳的规则资产。

5. **必须优先把问题抽象为机制缺口。**  
   合格的入池表达应是“专项方案挂接闭环不足”“控制—监测—应急闭环不足”“PDF text-only 下的事实断裂”，而不是“煤气区域专案”“某章节名缺失”“某附件名未见”。

6. **宽口径 issue 必须让位于窄口径、可复核 issue。**  
   若一个宽口径条目与多个更窄、更可追溯条目重叠，则宽口径条目默认降为 seed reference，避免双计数与 severity 失真。

7. **L3 inference 不得伪装成 hard defect。**  
   对于 A-05 这类 grounded engineering inference，应以 `enhancement_only` 或显式 workflow 提示入池，而不是继续沿用“hard_defect”标签。

8. **sample-level truth layering 服从治理层级。**  
   双样本观察不得推翻 repo facts；repo-carried gap/boundary 输入也不得超越 README / formal-review / review_eval README。

---

## 8. 可进入 v0.2.0-internal-reviewed 的建议条目清单

以下条目建议进入 `v0.2.0-internal-reviewed`，但必须附带 provenance 与限制说明。它们之所以适合入池，不是因为“看起来像标准答案”，而是因为具备以下条件中的大多数：  
（1）有稳定的第 2 层结构化证据锚点；  
（2）truth 类型明确，不把 visibility / evidence / enhancement 混写；  
（3）能抽象成机制问题，而不是样本表面词；  
（4）过拟合风险处于 low 或可控的 medium；  
（5）即使是 `Needs Supplement` 或 `Enhancement Only`，也能为 reviewer 提供明确的下一步动作。

| 编号 | 样本 | issue 名称 / issue 模式 | 主 truth 类型 | 证据充分度 | 可视域状态影响 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| A-01 | 样本 A | 核心章节完整性证据缺口（对应 ISSUE-001） | evidence_truth | partial | 当前正文可见，但章节映射与附件/表格承载存在偏移；非 parser 盲区 | 可裁为“结构完整性尚未稳固成立”，不可裁为“相关内容完全缺失”；prov=A/result.issue[ISSUE-001], A/facts.projectFacts.sectionPresence, A/attachment-1(parsed) |
| A-02 | 样本 A | 重复标题导致正式审查定位不稳定（ISSUE-002） | issue_truth | sufficient | 无实质阻断 | 重复标题为直接结构事实；prov=A/section-structure-matrix(duplicate=4), A/facts.projectFacts.duplicateSections |
| A-03 | 样本 A | 附件可视域缺口（A: 附件2仅标题可见，正文未解析） | visibility_truth | sufficient | attachment_unparsed；blocked_by_visibility | 只能裁为 visibility_gap，不得写成附件缺失；prov=A/l0.visibility, A/attachment-visibility-matrix, A/result.issue[ISSUE-003] |
| A-05 | 样本 A | 工期-资源-高风险并行组织压力（ISSUE-005） | enhancement_only | sufficient | 无 parser 阻断，但属于 grounded engineering inference | 可作为 L3 提示/整改优先级，不宜继续硬化为 hard defect；prov=A/conflict.scheduleVsResources.issueTriggered=true, A/shutdownWindowDays=7, A/laborTotal=37 |
| A-06 | 样本 A | 起重吊装专项方案挂接不清（ISSUE-006） | evidence_truth | partial | manual confirmation needed；非完全不可见 | 已识别吊装、吊车参数与验算痕迹，但专项方案挂接仍停在 generic mention；prov=A/result.issue[ISSUE-006], A/rule-hit(lifting_operations_special_scheme_linkage=manual_review_needed) |
| A-07 | 样本 A | 动火场景缺少火灾类针对性应急安排（ISSUE-007） | issue_truth | sufficient | 当前 DOCX 可视域足以支持窄口径判断 | 成立的是“针对性火灾/爆燃类应急映射不足”，不是“完全没有应急安排”；prov=A/hotWork=true, A/emergency.planTitles(4 titles, none fire/explosion), A/result.issue[ISSUE-007] |
| A-08 | 样本 A | 危险环境控制—监测—应急闭环不足（A: 煤气区域，ISSUE-008） | issue_truth | partial | 当前正文可见；结论受场景针对性证据限制 | 成立的是“闭环不完整”，不是 Gemini 式“系统性缺失”；prov=A/gasArea=true, A/measureSectionPresent=true, A/monitoringSectionPresent=true, A/emergency.planTitles lacks gas-specific mapping |
| B-VIS | 样本 B | PDF text-only 可视域边界（表格/图示/附图未保留，附件可见性未知） | visibility_truth | sufficient | pdf_text_only + parserLimited + parseWarnings | 这是样本 B 最基础的 truth fragment；所有 issue adjudication 均须服从该边界；prov=B/l0.visibility.parseWarnings |
| B-01 | 样本 B | 核心章节完整性证据缺口（ISSUE-001） | evidence_truth | blocked_by_visibility | pdf_text_only；construction/resource/monitoring mapping 不稳 | 可裁为“当前可视域下结构完整性不足以稳判”，不可裁为“正文内容必然缺失”；prov=B/sectionPresence(constructionPlan=false, resourcePlan=false, monitoringPlan=false), B/result.issue[ISSUE-001] |
| B-03 | 样本 B | 应急预案针对性不足（ISSUE-003） | evidence_truth | blocked_by_visibility | 未解析到 emergency plan titles；PDF 文本可视域受限 | 成立的是“当前证据不足以建立针对性映射”，不是“已证实完全没有应急体系”；prov=B/unresolvedFacts.missing_emergency_plan_titles, B/targetedPlanCount=0, B/result.issue[ISSUE-003] |
| B-04 | 样本 B | 起重吊装专项方案挂接不清（ISSUE-004） | evidence_truth | partial | manual confirmation needed under pdf_text_only | 可裁为“专项挂接仍需人工确认”，不可裁为“起重方案必然缺失”；prov=B/result.issue[ISSUE-004], B/rule-hit(lifting_operations_special_scheme_linkage=manual_review_needed) |
| B-05 | 样本 B | 临时用电/停送电控制链路不完整（ISSUE-005） | issue_truth | partial | 仅在当前文本可视域内成立；monitoring 缺口明显 | 成立的是“当前可视文本未形成完整链路”，而非对全部附图附表作全量否定；prov=B/temporaryPower=true, B/measureSectionPresent=true, B/monitoringSectionPresent=false, B/result.issue[ISSUE-005] |

这些条目进入 internal-reviewed 时，建议同时记录以下 provenance 元素：

1. **样本 ID**（A / B）；  
2. **原始 issue ID**（若来源于 `structured-review-result.json`）；  
3. **主 truth 类型 / 次 truth 类型**；  
4. **证据充分度**；  
5. **visibility 限制说明**；  
6. **是否为 enhancement_only**；  
7. **是否存在重叠宽口径 issue 被降级**。

---

## 9. 暂不进入 internal-reviewed 的条目清单

以下条目暂不进入 `v0.2.0-internal-reviewed` 主表。它们被排除，不是因为“毫无价值”，而是因为在当前边界下存在至少一种明显问题：  
（1）证据不足或被可视域阻断；  
（2）与更窄、更可复核条目高度重叠；  
（3）本质上只是 seed-level candidate 或未来 pack 线索；  
（4）过拟合风险过高；  
（5）一旦入池，就会把 Gemini wording 或样本表面词抬升成 truth。

| 编号 | 样本 | issue 名称 / issue 模式 | 裁决结果 | 是否建议进入 v0.2.0-internal-reviewed | 过拟合风险 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| A-04 | 样本 A | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-004） | 待补证 | 仅保留为 seed reference | medium | 与 A-06/A-07/A-08 高度重叠；更适合作为宽口径 inventory，而非 versioned truth 主条目；prov=A/hazardFacts.specialSchemePlanStatus=generic_mention_only, A/result.issue[ISSUE-004] |
| B-02 | 样本 B | 高风险作业总体专项方案挂接不清（宽口径 ISSUE-002） | 待补证 | 仅保留为 seed reference | medium | 与 B-04 及若干子场景高度重叠；保留为 candidate inventory 更稳；prov=B/result.issue[ISSUE-002], B/hazardFacts.specialSchemePlanStatus=generic_mention_only |
| A-03N | 样本 A | 将“附件2未解析”直接裁为“附件缺失” | 不成立 | 明确不纳入 | unacceptable | 属于违反 review_eval 非协商边界的错误命题；prov=A/attachmentFacts.visibility.counts.missing=0 |
| A-R1 | 样本 A | “起重吊装验算完全缺失”这一命题 | 不成立 | 明确不纳入 | high | 仓库结构化证据已给出 50t 吊车、2.86t 计算起重量与 calculation_traceability=pass；prov=A/hazardFacts, A/rule-hit(lifting_operations_calculation_traceability=pass) |
| B-06 | 样本 B | 动火场景火灾类针对性应急缺口（ISSUE-006） | 待补证 | 暂不纳入 versioned truth | medium | 与 B-03 部分重叠，且当前直接文证较弱；保留为后续人工复核候选更稳；prov=B/result.issue[ISSUE-006], B/docEvidenceCount=3 |
| B-R1 | 样本 B | “章节结构存在重复标题”这一命题 | 不成立 | 明确不纳入 | low | duplicateSections=[]；rule pass；prov=B/section-structure-matrix duplicate=0, B/rule-hit(construction_org_duplicate_sections=pass) |
| B-R2 | 样本 B | “附件缺失”这一命题 | 不成立 | 明确不纳入 | unacceptable | PDF 路径下附件矩阵为空且 visibility 未支持缺失判定，不能倒推出缺失；prov=B/l0.parseWarnings includes pdf_attachment_visibility_may_be_unknown |
| B-R3 | 样本 B | “停机窗口/资源冲突已成立”这一命题 | 不成立 | 明确不纳入 | medium | shutdownWindowDays 与 laborTotal 均为 null，conflict rule pass；prov=B/conflict.scheduleVsResources.issueTriggered=false, B/unresolvedFacts |
| B-R4 | 样本 B | “起重吊装计算痕迹完全缺失”这一命题 | 不成立 | 明确不纳入 | medium | 虽然 calculatedLiftWeightTon 未抽到，但 calculationEvidencePresent=true 且 calculation_traceability=pass；prov=B/hazardFacts, B/rule-hit(lifting_operations_calculation_traceability=pass) |

除上表外，还有两组条目应明确排除在当前 versioned truth 主表之外：

1. **Gemini-only / Gemini-expanded candidate clusters**  
   - 样本 A：吊装站位承载力、特种作业资质、EMI、质量验收盲区等。  
   - 样本 B：深基坑、承压水、周边生命线、微顶管、多工艺耦合等。  
   这些条目不是“不重要”，而是当前 ready pack、当前 parser 边界和当前无 expert gold 的条件下，**不具备稳定升格条件**。

2. **由样本表面词直接导出的伪 truth**  
   例如“附件 2 缺失”“50t 必然意味着某专项缺失”“7 天必然构成硬冲突”“DN3600 必然触发某固定规则”等。  
   这些命题一旦入池，几乎必然导致双样本过拟合。

---

## 10. 最终裁决结论

本稿确认了三类可追溯 truth：  
第一类，是**可直接确认的结构与可视域 truth**，包括样本 A 的重复标题与附件可视域缺口，以及样本 B 的 PDF text-only visibility boundary；  
第二类，是**可进入 internal-reviewed、但必须显式带边界说明的 evidence / issue truth**，包括 A 的核心章节 evidence gap、起重专项挂接待补证、动火针对性应急缺口、煤气区域闭环不足，以及 B 的核心章节 evidence gap、应急针对性 evidence gap、起重专项挂接待补证、临时用电链路不完整；  
第三类，是**只能以 enhancement_only 或 seed reference 方式保留的条目**，包括 A 的工期—资源—高风险并行组织压力，以及 A/B 两个“高风险作业总体专项方案挂接不清”的宽口径条目。

本稿同时明确没有确认以下内容：  
一，任何 expert-golden 级别结论；  
二，把样本 A 的附件未解析写成“附件缺失”的命题；  
三，把样本 B 的 PDF 不可视域写成“附件缺失”或“停机—资源冲突已成立”的命题；  
四，把 Gemini 扩展出来的更宽工程域 candidate 直接写回 versioned truth。

因此，这份文稿仍然只是 `v0.2.0-internal-reviewed` 的**准备层底稿**，不是最终 gold。要从 internal-reviewed 走向更高等级 truth，至少还需要：  
（1）更多 versioned cases，尤其是 visibility-heavy 的 PDF / 附图 / 附表样本；  
（2）正式的人类 reviewer 逐 issue 复核与 provenance 回写；  
（3）对 out-of-pack 域（如深基坑、周边生命线、降水、顶管等）的独立政策资产与场景 pack，而不是把 Gemini narrative 直接当答案；  
（4）把 L3 workflow language 继续从“grounded inference”推进到“先补件 / 先补依据 / 先补正文结构 / 建议增强”的稳定整改桶。

## 附：自查

- [x] 已明确写出这不是 expert-golden。  
- [x] 已明确区分 `issue_truth / visibility_truth / evidence_truth / enhancement_only`。  
- [x] 已对样本 A、样本 B 分别裁决，未混合讨论。  
- [x] 已给出样本级 issue 裁决表。  
- [x] 已明确说明 Gemini 只是 candidate / seed 参考。  
- [x] 已把部分条目标为 `Needs Supplement / blocked_by_visibility / Enhancement Only`。  
- [x] 已明确列出可进入 `v0.2.0-internal-reviewed` 的条目。  
- [x] 已明确列出暂不进入的条目。  
- [x] 已单列反过拟合裁决约束。  
- [x] 已避免把双样本表面词语直接写成通用 truth。  
- [x] truth 分层判断优先依据了 research pack 中的 JSON / matrices / visibility 对象。  
- [x] 已在证据基础章节中说明四层证据层级。  
- [x] 已明确执行“样本级 truth layering 服从差距裁决清单，差距裁决清单服从边界声明，边界声明服从 GitHub 仓库事实”的层级原则，并说明当前仓库中边界/差距文档是以 `-prompt.md` 载体入仓。
