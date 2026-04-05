# 《产品思路与路线图》

以下文本按仓库当前 `README`、`docs/architecture.md`、`docs/formal-review.md`、`fixtures/review_eval/README.md`、`fixtures/research_inputs/README.md`、`latest-eval-summary`，以及 `fixtures/任务书/` 中的上游研究、边界、差距裁决与双样本监督材料综合起草。仓库当前在 `fixtures/任务书/` 下同时存在成文稿与 prompt 形态文件；本文只吸收其中已经稳定的产品边界、治理约束与路线判断，不把这些材料混写成实施任务书。 ([GitHub][1])

## 0. 文档定位

本文不是 README 改写版，不是《V0.3 边界声明》，不是《V0.2→V0.3 差距裁决与反过拟合约束清单》，也不是《双样本人工复核裁决稿》。它的角色，是把这些上游材料已经收敛出的事实与约束，整理成一份面向产品思路收口的总纲文件，为后续《V0.3 实施设计 / 执行任务书》提供稳定的上位约束。 ([GitHub][2])

它要回答的不是“这一轮具体怎么拆任务”，而是“008-review-control-plane 到底是什么、当前阶段在哪里、V0.3 为什么这样收边界、哪些能力属于当前主线、哪些只能进入未来路线”。换句话说，它服务的是产品身份澄清、路线分层和治理稳定，而不是一次性实施展开。 ([GitHub][2])

## 1. 产品一句话定义

**产品当前一句话：**`008-review-control-plane` 当前是一个以 **review control plane** 为总控壳、在 **official scope** 内承载 `structured_review` 正式结构化审查主链的系统。 ([GitHub][3])

**V0.3 一句话目标：****V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本。目标是在 official scope 内，把 structured_review 做成：可审前置、可视域诚实、证据可追溯、规则可命中、结果可复核、评测可闭环的 formal-review spine。** ([GitHub][4])

## 2. 当前阶段的产品定位

当前产品的最准确说法，不是“大而全的工程 AI 平台”，也不是“单一对话式审查模型”，而是一个 review control plane：前端统一任务入口与链路展示，后端负责任务 API、状态存储与 artifacts，运行时负责能力路由与编排；在这个总控壳之内，`structured_review` 是正式结构化审查子域，主链已经被定义为 `parse -> facts -> rules -> evidence -> report`。 ([GitHub][3])

它当前不是什么，同样需要写清楚：它不是万能工程 AI，不是全自动替代人工签发系统，不是“更像 Gemini 的写作器”，也不是当前阶段就去做平台级 OCR、多模态、图纸平台或多文档联合审查的大系统。仓库现有边界已经明确：`review_assist` 只是快速辅助总结，不等于正式审查结论；`structured_review` 目前也仍受限于单文档、`pdf_text_only + parserLimited=True` 的保守路径。 ([GitHub][5])

之所以当前应称为 **review control plane + formal-review spine**，是因为产品的重心已经不再是“做一个更会写报告的审查器”，而是“在统一总控之内，把正式审查所需的可视域、事实、规则、证据、报告、评测与复核机制收成一条可信主链”。上游三角对比研究也给出的判断是：它已经超过了“更成熟的 assist reviewer”，更接近“early structured reviewer”，但还不是成熟的 formal reviewer。 ([GitHub][6])

`review_assist` 与 `structured_review` 的关系，也必须持续双轨区分：前者承担辅助性、快速性、总结型能力，解决“先看一眼、先归纳一下”的问题；后者承担正式结构化审查能力，解决“是否形成可追溯、可复核、可评测的正式审查结果”的问题。前者可以帮助用户更快进入问题域，后者才是 V0.3 的产品主线。 ([GitHub][3])


### 产品结构图

以下是当前仓库的产品结构与 formal-review spine 主链示意：

```
008-review-control-plane
|
|-- review_assist                          <-- 快速辅助 / 总结 / 预览（非正式审查）
|
+-- structured_review                      <-- 正式结构化审查主链
    |
    |   +----------- formal-review spine -----------+
    |   |                                           |
    |-- parse ........... 文档解析 + parseMode/Warnings
    |-- facts ........... 事实抽取 + unresolvedFacts
    |-- rules ........... 规则/条文适用 + applicabilityState
    |-- evidence ........ 证据链闭合 + evidence gap
    |-- report .......... 报告 + artifacts + artifactIndex
    |   |                                           |
    |   +-------------------------------------------+
    |
    |-- reviewer gate ... 人工复核分流（manualReviewNeeded）
    +-- eval gate ....... 版本化评测拦截（versioned cases + layered metrics）

支撑层：前端界面 / runtime 编排 / 外部能力适配器
未来层：OCR / 多模态 / 图纸平台化 / 多文档联合 / ontology / graph-first / workflow 产品化
```

## 3. 为什么 V0.3 要“收边界、硬内核、补证据、强评测”

V0.3 的中心定义必须明确写死，而不是作为附注：**V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本。目标是在 official scope 内，把 structured_review 做成：可审前置、可视域诚实、证据可追溯、规则可命中、结果可复核、评测可闭环的 formal-review spine。**这不是一句口号，而是对当前仓库最短板的直接响应。 ([GitHub][4])

当前最重要的问题，不在平台壳不够大，也不在报告文案不够像专家，而在 **L0 可视域与 parser 诚实性、L1/L2 规则与证据闭环、reviewer gate 与 eval gate 的硬度**。最新阶段性评测虽然显示 official stage gate 已通过，但同一份摘要也同时给出：`attachment_visibility_accuracy` 仅 0.5833、`hard_evidence_accuracy` 仅 0.6945，而 L3 的 `suggestion_defect_separation` 仍只是 diagnostic 维度。这恰恰说明“能跑通”不等于“内核已硬”，更不能据此放松边界。 ([GitHub][7])

因此，V0.3 不是扩范围版本。当前 official `documentType` 仍只有 `construction_org` 与 `hazardous_special_scheme`；`construction_scheme`、`supervision_plan`、`review_support_material` 虽已有 ready base pack，但仍处于 experimental。formal-review 文档和差距裁决都明确要求保留“ready pack ≠ official documentType”的晋升治理：只有测试、versioned cases、policy evidence、rule coverage 达标，才允许晋升。现在贸然扩范围，只会在尚未做硬的主链上叠加更多不稳定性，并放大双样本过拟合风险。 ([GitHub][3])

V0.3 也不是“追报告效果”的版本。上游三角对比研究已经反复指出：V0.2 相比 V0.0 的代际升级，真正成立的地方在于 **结构化 contract、visibility honesty、issue/rule/evidence 语义和 pack 边界纪律**，而不是“写出更像专家的话术”。研究型 AI 使用说明与双样本监督材料同样强调：最大的错误，不是少写一点漂亮结论，而是把产品带成“围绕 Gemini wording 和双样本表面答案优化”的特化系统。 ([GitHub][8])

之所以是 **L0 + L2 主攻**，不是因为 L1 不重要，而是因为当前真正的脆弱点在两端：一端是 L0 的可视域、parser warnings、manual review 语义还没有完全前置成独立 gate；另一端是 L2 的 clause applicability、unresolved facts、evidence gap closure 虽然在对象语义上已出现，但还没有稳定闭环。相比之下，L1 已有规则命中与问题对象的骨架，L3 则在当前阶段被明确定义为可增强但不应成为主战场。 ([GitHub][8])

所以，V0.3 必须让 **evidence / visibility / gate** 成为主线。仓库当前已经把 `visibility` 定为 top-level canonical object，把 `manualReviewNeeded` 定为唯一 canonical 布尔语义，把 `artifactIndex` 定为 authoritative source，并把 official versioned cases 设为正式 stage gate。产品真正要做的，是把这些“可信审查的锚点”从已有语义升级成硬约束，而不是在它们之上继续铺更大的叙事壳。 ([GitHub][3])

## 4. V0.3 的目标与非目标

### 4.1 V0.3 目标

V0.3 的目标，首先是在 **official scope 内收口**。这意味着产品主线只围绕 `construction_org` 与 `hazardous_special_scheme` 展开，不借 ready pack 的存在偷偷把更多文档类型抬成默认主线，也不把 experimental 结果包装成 official 成熟度。V0.3 的成功标准，不是覆盖面，而是这两类 official 输入下的 formal-review spine 是否已经足够硬。 ([GitHub][3])

其次，V0.3 要把 formal-review spine 做到“像一条正式主链”，而不是“像一组看起来很像的输出对象”。这条主链至少要完成六件事：审查前先判断可不可审；用 `visibility` 诚实表达看到了什么和没看到什么；把 facts、rules、policy refs、issues、artifacts 串成可追溯证据链；把 `unresolvedFacts` 与 `applicabilityState` 纳入判断；在结果层支持人工复核；在评测层支持 versioned replay 与 stage gate。 ([GitHub][9])

再次，V0.3 中的 reviewer、eval 与 artifacts 不是配角，而是正式主线的一部分。reviewer gate 的作用，是把“需要人工判断的边界情况”从系统结果里显式分流出来，而不是让模型继续在盲区里硬判；eval gate 的作用，是让 official mainline 的质量靠 versioned cases 和 layered metrics 被持续拦截；artifacts 的作用，则是把每次审查的可视域、事实、规则命中、证据与报告都落成可回放、可核对、可比较的对象，而不是只留下一个 Markdown 结论。 ([GitHub][10])

### 4.2 V0.3 非目标

V0.3 不以“全文档类型覆盖”为目标。当前治理已经明确：official 只有两个 doc type，其余 ready base pack 仍然是 experimental；是否晋升，取决于测试、versioned cases、policy evidence 与 rule coverage，而不是“已经做出来了一个 pack”。因此，本轮不做“把更多入口一口气拉成主线”的工作。 ([GitHub][3])

V0.3 不做 OCR、多模态或图纸平台化。仓库当前对 PDF 的正式边界仍然是 `pdf_text_only + parserLimited=True`，并明确不引入 OCR / multimodal / drawing platformized chain。这个约束不是保守拖延，而是为了避免在可视域尚未诚实、evidence semantics 尚未稳定之前，先把输入复杂度抬高。 ([GitHub][5])

V0.3 不做多文档联合审查。当前 `structured_review` 仍是最小单文件输入路径，只支持 `fixtureId` 或单个 `sourceDocumentRef`，尚不支持多文档 batch、对象存储级联或联合证据求解。在这种状态下，先把单文档 spine 做硬，比提前堆联合审查框架更符合产品主线。 ([GitHub][5])

V0.3 不做 ontology / graph-first 重构。像 AEC3PO 这样的对象模型与术语关系体系，对长期知识建模很有价值，但当前主问题不是“图谱还不够漂亮”，而是“可视域、证据与规则闭环还不够硬”。在这个时点做 graph-first，只会把主线从 formal-review spine 的可信收口，扭向知识工程先行。 ([GitHub][11])

V0.3 也不做企业级大 workflow 壳。008 当然已经有 control plane 雏形，但当前仓库与上游研究都表明，最短板并不在队列编排、并发控制或 SaaS 化外壳，而在 formal-review spine 本身。如果现在把重点切到 RAPID 式的工作流产品化，会过早地把产品带成“流程很完整、审查内核却仍发软”的系统。 ([GitHub][6])

## 5. 从 V0.0 到 V0.3：产品演进主线

从产品视角看，V0.0 解决的不是“正式审查是否已经成立”，而是“系统能不能产出审查相关对象和原型输出”。三角对比研究显示，V0.0 已经有 issue、rule-hit、matrix 等雏形，但整体仍偏向试验性的审查辅助：它证明了这条路可走，却还没有把哪些对象是 canonical、哪些语义必须稳定下来。 ([GitHub][8])

V0.2 带来的变化则是代际性的。它把 `structured_review` 从“会产出一些像结构化的东西”，推进到“开始拥有正式结构化 contract”：`visibility` 成为 top-level canonical object，`manualReviewNeeded` 成为 canonical 语义，issues、matrices、`artifactIndex`、`unresolvedFacts` 等结果对象被正式化，pack readiness 和 official/experimental 边界也被纳入治理，而不再只是运行时现象。 ([GitHub][8])

V0.3 之所以不是继续“大扩张”，是因为上游研究已经证明：V0.2 的升级是实的，但仍未完成。L0 仍然受 parser-limited PDF 路径影响，L2 的 applicability 与 evidence-gap closure 还不够硬，L3 仍主要停留在诊断性增强；与此同时，latest-eval-summary 也表明“阶段性过关”不等于“边界可放松”。所以，V0.3 的合理方向不是继续拓宽，而是治理收口。 ([GitHub][8])

因此，V0.0 到 V0.3 的真正产品演进主线，不是“从小工具一路长成大平台”，而是“从审查相关原型输出，走向带稳定 contract 的 early structured reviewer，再继续收成 official scope 内可信、可复核、可评测的 formal-review spine”。这条主线一旦说清楚，V0.3 的所有边界与路线判断就都有了稳定坐标。 ([GitHub][8])

## 6. 核心能力地图

产品的核心能力，不应理解为散点功能，而应理解为一张围绕 formal-review spine 组织起来的能力地图。当前这张地图的中心，不是“更多模型能力”，而是“更可靠的 formal-review contract”。 ([GitHub][6])

**文档可视域层。**这是当前正式主线的第一层。它负责回答“系统到底看到了什么、没看到什么、为什么没看到、是否需要人工介入”。`visibility`、`parseMode`、`parseWarnings`、`manualReviewReason`、`manualReviewNeeded` 都属于这一层。对 V0.3 来说，它不是外围元信息，而是 formal-review 是否成立的前置条件。 ([GitHub][3])

**事实抽取层。**这一层负责把输入文档转成可用于规则判断的 facts，并明确哪些 facts 已解析、哪些 facts 仍 unresolved。它是从 parse 走向 rule applicability 的中间骨架。当前它已经是正式主线的一部分，但还需要进一步和 `unresolvedFacts`、visibility 状态、evidence 缺口联动。 ([GitHub][12])

**规则 / 条文适用层。**这一层负责把 facts 对接 policy packs、clause applicability 与 rule hits，并形成 issue-level 的判断语义。仓库已经稳定输出 `issueKind`、`applicabilityState` 等字段，这说明这层不是未来想象，而是当前 formal spine 的核心中段。V0.3 的任务不是发明它，而是把它做硬。 ([GitHub][3])

**证据与 unresolved facts 层。**这是 V0.3 必须补硬的一层。它负责把 source、fact、clause、policy ref、rule hit、issue 与 evidence gap 串成一条可以追溯的证据链；同时，它也负责诚实承认“当前 blocked 于 visibility”或“blocked 于 missing fact”，而不是把证据缺口伪装成硬缺陷结论。这个层级直接决定 formal-review spine 是否可信。 ([GitHub][12])

**报告与 artifact 层。**报告层不是“把话说好听”，而是把上游对象与证据组织成 reviewer 可读、eval 可回放的外显载体。`reportMarkdown`、各类 matrices、以及 `artifactIndex` 共同构成这一层。对当前产品而言，它是正式主线的输出层，但它的价值在于承载事实与证据，不在于替代主链本身。 ([GitHub][3])

**reviewer gate 层。**这一层负责把“系统可以正式给出判断”的部分，与“必须由人进一步复核”的部分分开。双样本监督材料和 V0.2 设计文档都强调：L0 gate 不能长期缺席，manual review 不能只是 issue 末端的附带字段，而应该逐步成为 formal-review 的前置或并行治理机制。V0.3 中它已经属于正式主线，但目前仍偏弱。 ([GitHub][13])

**eval gate 层。**这一层负责把产品能力从“看起来不错”变成“被 versioned cases 和 layered metrics 稳定约束”。当前仓库已经建立 legacy stable baseline、official versioned stage gate、experimental diagnostics、`internal-reviewed` 与 `expert-golden` 的版本层次；因此，eval gate 不是补充件，而是 formal-review spine 的治理闭环。 ([GitHub][10])

综合来看，**文档可视域层、事实抽取层、规则 / 条文适用层、证据与 unresolved facts 层、报告与 artifact 层、reviewer gate 层、eval gate 层**，共同构成当前正式主线；前端界面、runtime 编排、外部能力适配器属于支撑层；OCR、多模态、图纸平台化、多文档联合审查、ontology / graph-first 与企业级 workflow 壳，则都属于未来层。 ([GitHub][6])

## 7. 外部参考项目与借鉴边界

以下五个外部项目在研究过程中被系统性参考。本节不是征引它们的先进性，而是为后续实施设计划定"借什么、不借什么、为什么不借更多"的明确边界，防止实施层跑偏。

| 项目 | 可借鉴 | V0.3 适用性 | 明确不借 | 借过头会偏向 |
|---|---|---|---|---|
| OpenContracts | 证据对象模型 / annotation / relationship / provenance | **当前可用**：强化 evidence traceability | 整体协作壳、annotation-first 工作方式、技术栈迁移 | 文档标注与语料管理平台 |
| AEC-Bench | 评测任务设计 / scope taxonomy / replay 方法论 | **当前可用**：让 eval 更像可诊断基准系统 | multimodal benchmark 壳、agent sandbox、评测平台产品路线 | 面向多模态 agent 的 benchmark 平台 |
| claude-legal-skill | pre-review checklist / 审查前置纪律 / 输出桶方法 | **当前可用**：加强 reviewer gate 和 pre-review gate | 法律 redline、市场基准、法律文书输出壳、法律域内容本体 | 文档审阅写作 copilot |
| AEC3PO | schema discipline / 术语关系命名 / 概念边界 | **中长期储备**：为 facts/rules/evidence 命名一致性做准备 | ontology-first 重构路线、整套知识本体工程化 | 先做知识本体、后谈审查主链的知识工程项目 |
| AWS RAPID | 人在回路工作流 / 队列编排 / 产品化参考 | **长期参考**：008 当前短板不在壳层 | 作为当前主借鉴对象、企业工作流产品化整套实现 | 流程很完整的工作流 SaaS，审查内核仍发软 |


### OpenContracts

对 008 最有价值的，不是 OpenContracts 的整套产品壳，而是它对 **annotation、relationship、version history、human-anchored provenance** 的对象模型意识。OpenContracts 明确把人工标注、关系建模和版本追踪作为基础，这正好对应 008 当前最该补硬的 evidence traceability。V0.3 借它，是为了让 artifacts、issue、rule、evidence 的关系更清楚，而不是把 008 重做成合同语料协作平台。明确不借的是它的整体协作壳、annotation-first 工作方式和整仓迁移方向；如果现在借过头，008 会被带向“文档标注与语料管理平台”，而不是“official scope 内的 formal-review spine”。 ([GitHub][14])

### AEC-Bench

AEC-Bench 对 008 的主要帮助，在于 **task / scope taxonomy、benchmark / replay / diagnostics** 的方法论。它把 AEC 任务拆成清晰的 scope 与 task type，并提供可重复 trial 的运行方式，这和 008 当前正在建立的 versioned cases、layered metrics、replay-based eval 非常契合。V0.3 借它，是为了让评测设计更像“可诊断的基准系统”，而不是更像“偶发通过的样例演示”。明确不借的是它的 multimodal benchmark 壳、agent sandbox 运行体系和“先以评测平台为中心”的产品路线；如果现在借过头，008 会被带向“面向多模态 agent 的 benchmark 平台”，而不是先把 formal-review spine 做硬。 ([GitHub][15])

### claude-legal-skill

claude-legal-skill 对 008 的价值，不在法律结论本身，而在 **pre-review checklist、position-aware review、输出桶纪律**。它强调先做 red flags、关键条款、缺失项和一致性检查，这对 008 当前要补的 pre-review gate 很有启发：审查不应一上来就生成结论，而应先过一个“我正在审什么、按什么框架审、哪些部分需要人工介入”的前置门。V0.3 借它，是为了加强 reviewer gate 和审查前置纪律。明确不借的是法律 redline、市场基准、法律文书输出壳；如果现在借过头，008 会被带向“文档审阅写作 copilot”，而不是 formal-review spine。 ([GitHub][16])

### AEC3PO

AEC3PO 对 008 的价值，主要在 **schema discipline、术语与关系命名、长期知识建模储备**。它把合规检查中的概念、关系、检查方法和 competency questions 组织成结构化本体，这对 008 未来把 facts、rules、policy refs、evidence objects 做得更一致很有帮助。V0.3 可以借它的命名纪律与概念边界，但不应把它变成当前主线实施对象。明确不借的是 ontology-first 重构路线；如果现在借过头，008 会被带向“先做知识本体、后谈审查主链”的知识工程项目。 ([GitHub][11])

### AWS RAPID

RAPID 对 008 的帮助，主要在 **未来的人在回路工作流、队列编排、产品化执行节奏**。它强调 AI review + human in the loop，并在产品实现上处理 checklist、review queue、并发与调度，这些都可以为 008 的中长期 workflow 产品化提供参考。V0.3 之所以只把它当未来参考，是因为 008 当前的短板不在这些壳层。明确不借的是它当前作为主借鉴对象的地位，以及面向企业工作流产品化的整套实现重心；如果现在借过头，008 会过早变成“流程很完整的工作流 SaaS”，却没有先把审查内核做硬。 ([GitHub][17])

## 8. 中期与长期路线图

路线可以写，但必须分层，而且每一层都必须有进入前提。任何未来能力都不能伪装成 V0.3 的当下任务。进入后续路线的共同前提只有一个：official scope 内的 formal-review spine 必须先足够硬，尤其是 L0 可视域诚实、L2 适用性与证据闭环、reviewer gate 和 eval gate 稳定成立。 ([GitHub][4])

### 路线分层总览

```
时间层        主要目标                                          进入前提
────────────────────────────────────────────────────────────────────────────────
当前 V0.3     收边界 · 硬内核 · 补证据 · 强评测                  <-- 当前主线
              |-- official scope 内 formal-review spine 做硬
              |-- 主攻 L0（可视域 / parser 诚实）+ L2（证据闭环）
              +-- reviewer gate + eval gate 成为正式制度
────────────────────────────────────────────────────────────────────────────────
中期          扩边界 · 补承接 · 强治理                          V0.3 主链足够硬
              |-- 更多 ready packs 通过治理晋升为 official        |-- L0 visibility
              |-- 补 internal-reviewed / gold 承接层             |   contract 稳定
              +-- 加强 reviewer workflow / adjudication          |-- L2 evidence
                                                                |   闭环可信
                                                                +-- eval gate
                                                                    stage gate 成立
────────────────────────────────────────────────────────────────────────────────
中远期        扩输入 · 扩文档                                    中期治理成熟
              |-- OCR / 多模态 / 图纸平台化                      |-- visibility
              +-- 多文档联合审查                                 |   contract 可吸收
                                                                |   复杂输入
                                                                +-- 单文档 spine
                                                                    已可信
────────────────────────────────────────────────────────────────────────────────
长期          扩模型 · 扩平台                                    中远期能力稳定
              |-- ontology / graph-first                        |-- 证据对象模型
              |-- 完整 workflow / 产品化                         |   已稳定
              +-- 审查控制平台级能力                             +-- pack / doc type
                                                                    覆盖足以支撑
                                                                    抽象建模
────────────────────────────────────────────────────────────────────────────────
```

**关键原则**：每一层路线的进入必须以上一层主链"足够硬"为前提，不允许以"技术上做得到"替代"产品上接得住"。


### 8.1 中期路线

中期路线首先是 **扩更多 ready packs、扩更多 documentType，但只通过治理晋升，不通过叙事偷渡**。也就是说，`construction_scheme`、`supervision_plan`、`review_support_material` 以及更多 scenario packs 可以进入后续晋升池，但进入 official 的前提仍然是 tests、versioned cases、policy evidence、rule coverage 达标，而不是“已经有了 base pack”。这条路线是“在同一 formal spine 上扩边界”，不是“先扩边界再回头补 spine”。 ([GitHub][12])

中期路线还包括 **补 internal-reviewed / gold 承接层、加强 reviewer workflow**。双样本监督材料已经明确：当前没有正式 expert gold，`internal-reviewed` 只能是受边界约束、显式记录 provenance 的中间层。因此，中期产品建设应把 reviewer decision、人工复核痕迹、样本级 adjudication 和 versioned truth 之间的承接关系做得更清楚，让系统逐步具备从 seed、diagnostics 走向 reviewed、再走向 gold-ready 的能力。 ([GitHub][13])

### 8.2 中远期路线

中远期路线可以进入 **OCR、多模态、图纸平台化**，但前提不是“技术上做得到”，而是“产品上接得住”。只有当 L0 visibility contract、manual review 语义、artifact traceability 和 eval gate 已经足以吸收更复杂输入时，多模态能力才不会把当前盲区放大成系统性失真。否则，它只会制造更多“看似能读、实际不可复核”的假确定性。 ([GitHub][5])

中远期路线还可以进入 **多文档联合审查**。但它的进入前提同样严格：单文档 structured_review 必须先有稳定的事实层、规则层、证据层与 reviewer/eval 治理；否则，多文档不会带来更强能力，只会把来源、适用性与责任边界进一步搅乱。多文档应该建立在“单文档 formal spine 已经可信”的基础上，而不是反过来期待多文档来弥补单文档主链的不成熟。 ([GitHub][5])

### 8.3 长期路线

长期路线可以考虑 **ontology / graph-first、更加完整的 workflow / 产品化能力、以及更完整的审查控制平台**。这条路线并非不存在，但它的前提是：证据对象模型已经稳定、pack 与 doc type 的覆盖已扩展到足以支撑抽象建模、reviewer/eval 治理已经成熟到可以承受更高层次的系统化重构。换言之，graph-first 不是当前真相源，而是未来在规模和复杂度足够高之后，才值得启用的结构升级。 ([GitHub][11])

长期路线中的 workflow / 产品化，也应建立在同样前提之上。届时可以吸收 RAPID 式的人在回路流程编排、任务队列、执行治理，甚至进一步把 review control plane 做成更完整的审查控制平台；但那必须发生在 formal-review spine 已经足够硬之后，而不是拿更大的平台壳去掩盖当前 spine 仍未收口的事实。 ([GitHub][17])

## 9. 产品路线的治理原则

第一，**anti-overfit 不是 V0.3 的临时提醒，而是长期治理原则**。双样本监督材料、研究型 AI 使用说明和差距裁决都一致强调：当前只有两份高价值真实样本，Gemini 只能是 seed / candidate reference，不能变成 gold truth、规则答案库或 prompt 模板目标。任何围绕项目名、固定数字、章节标题、附件名或 Gemini wording 的特判式优化，都必须被视为产品治理层面的违规，而不是聪明修补。 ([GitHub][13])

第二，**official / experimental / diagnostics / internal-reviewed / gold 的分层治理必须长期保留**。这是 008 能够避免“把阶段性运行结果误当长期真相”的关键制度。`research_inputs` 已明确自身只是 curated sample-level evidence，不是 gold truth；`latest-eval-summary` 也只是阶段性 snapshot；review_eval 则把 `gemini-seed`、`bootstrap-seed`、`internal-reviewed`、`expert-golden` 的语义层级写得很清楚。未来扩范围时，这套分层不能被抹平。 ([GitHub][18])

第三，**任何扩范围都必须在已有主线足够硬之后发生**。这意味着产品治理必须承认一个顺序：先做硬 official scope 内的 formal-review spine，再谈更多 doc type、更多 pack、更多模态、更多工作流。如果当前主线仍在 L0 可视域、L2 适用性与证据闭环上发软，那么扩范围本身就应被视为治理风险，而不是增长成果。 ([GitHub][4])

第四，**研究、边界、裁决、实施四层文档关系应长期维护**。研究文档负责发现问题与形成输入；边界文档负责收口“做什么 / 不做什么”；差距裁决负责把问题分流到 official mainline、experimental、diagnostics、internal-reviewed preparation 或 out of scope；实施文档只负责在既定边界内拆设计、拆任务、拆验证。实施层不应反向重写研究层、边界层与裁决层。 ([GitHub][2])

## 10. V0.3 的成功判据

### 什么叫 V0.3 在产品层面成功

V0.3 成功的判断标准不是"产出更多"，而是"主链更硬"。具体而言：

- **可审前置成立**：L0 visibility / parser warnings / manual review 语义已前置成独立 gate，系统在审查开始前就诚实表达"看到了什么、没看到什么、为什么没看到"
- **可视域诚实可验证**：`attachment_visibility_accuracy` 有系统性提升，且提升来自 contract 硬度增强而非样本特判
- **证据可追溯**：facts → rules → policy refs → issues → evidence 的关系链可以在 artifacts 中被完整回溯，而非仅存在于 reportMarkdown 叙述中
- **规则可命中**：`applicabilityState`、clause applicability 与 rule coverage 在 official scope 内可被 versioned cases 稳定复现
- **结果可复核**：reviewer gate 能把"系统可判"与"需人工复核"的边界显式分流，而非让模型在盲区里硬判
- **评测可闭环**：eval gate 通过 versioned cases + layered metrics 实现 stage gate 拦截，而非依赖单次快照

### 什么不算成功

以下情形即使出现，也不应被误读为 V0.3 产品层面的成功：

- 报告文风更像 Gemini 或更像"专家话术"，但证据链未变硬
- 某次样本 A/B 对比得分更高，但提升来自 wording 优化而非 contract 加固
- 多了更多 experimental 方向或 ready base pack，但 official scope 主链硬度未提升
- 讲了更多远期愿景，但 L0 / L2 的具体短板仍未闭合
- diagnostics 层某项指标提升，但被误解为 official readiness 提升

### 哪些指标只是辅助，不应被误读

- **某次 eval 快照**不是长期真相——它是阶段性 snapshot，不代表主线已成熟
- **某次样本表现提升**不代表 formal-review spine 已可信——必须区分是 contract 硬度提升还是 prompt / wording 调优
- **diagnostics 层提升**不等于 official readiness——L3 维度在当前阶段明确定义为可增强但不应成为主战场
- **`hard_evidence_accuracy` 等单项改善**不代表证据链闭环已成立——必须看整条 facts → rules → evidence → artifacts 链路的系统性

V0.3 成功判据的核心是 **anti-overfit**：不追样本追分，不追文风追像，不追指标追高；而是追可视域诚实、追证据可追溯、追规则可命中、追 gate 可拦截、追评测可闭环。


## 11. 对后续《V0.3 实施设计 / 执行任务书》的输入要求

这份《产品思路与路线图》对后续实施任务书的首要约束，是：**后续文档不应再重新讨论产品身份**。实施层不应再争论“008 到底是不是 review control plane”“structured_review 到底是不是正式主链”“V0.3 到底要不要扩范围”。这些问题在本文件及上游边界材料中已经定性完成。 ([GitHub][2])

因此，后续实施任务书不应再重新讨论以下事项：official scope 的定义；`ready pack ≠ official` 的治理；Gemini 不是 gold truth；`research_inputs` 和本地 eval snapshot 不是长期真相；OCR、多模态、图纸平台化、多文档联合审查、ontology / graph-first、企业级大 workflow 壳不是 V0.3 主线。这些都应被视为实施层的既定约束，而不是可再次协商的选项。 ([GitHub][12])

后续实施任务书应重点展开的，是 **如何把当前主线做硬**：L0 visibility / parser / manual review gate 的 contract 与 artifact；L1/L2 的 facts、rule hit、applicabilityState、unresolvedFacts、policy ref 和 evidence gap closure；reviewer decision 与 artifacts 的承接；official stage gate、diagnostics、versioned cases 和 layered metrics 的实现；以及 doc type / pack 的晋升标准如何落到测试、样本池与回放链路上。 ([GitHub][9])

外部借鉴里，**可以进入实施层** 的，只应是方法和局部对象：例如 OpenContracts 的 annotation / provenance 对象意识，AEC-Bench 的 task/scope taxonomy 与 replay 纪律，claude-legal-skill 的 pre-review checklist 与输出桶方法。**只能保留在产品思路层** 的，则包括 AEC3PO 式 ontology-first 重构、RAPID 式 workflow / queue / 并发产品壳，以及任何“整体迁移其技术栈或产品壳”的想法。 ([GitHub][14])

## 12. 最终结论

`008-review-control-plane` 当前不是万能工程 AI，不是自动签发机，也不是更像 Gemini 的写作器。它当前是一个 **review control plane**，而它在 V0.3 这一阶段的唯一正确主线，是在 official scope 内把 `structured_review` 收成一条真正可信的 **formal-review spine**：先把可视域讲清楚，再把事实与规则连起来，再把证据与 unresolved facts 落实到 artifacts，再把 reviewer gate 与 eval gate 做成可复核、可拦截、可回放的制度化能力。 ([GitHub][3])

所以，V0.3 到底做什么，答案不是“做更大”，而是“做更硬”；不是“扩更多能力壳”，而是“补证据、补可视域、补 gate、补评测闭环”；不是“追更像专家的文风”，而是“追更像正式审查系统的可信性”。未来路线当然存在，但它们必须被分层留白：中期扩 pack、扩 doc type、补 reviewed 承接与 reviewer workflow；中远期再进 OCR、多模态、图纸平台化、多文档联合审查；长期才考虑 ontology / graph-first 与更完整的平台化工作流。最不能做错的，是在当前主线还未做硬时，就被双样本表象、Gemini 话术或平台宏大叙事带偏方向。 ([GitHub][13])

[1]: https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6 "https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6"
[2]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/V0.3%20%E5%89%8D%E7%BD%AE%E5%B7%A5%E4%BD%9C%E6%B5%81%E7%A8%8B%E6%8C%87%E5%8D%97%E2%80%94%E2%80%94%E6%96%87%E6%A1%A3%E7%94%9F%E6%88%90%E9%A1%BA%E5%BA%8F%E4%B8%8E%E4%BE%9D%E8%B5%96%E5%85%B3%E7%B3%BB.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/V0.3%20%E5%89%8D%E7%BD%AE%E5%B7%A5%E4%BD%9C%E6%B5%81%E7%A8%8B%E6%8C%87%E5%8D%97%E2%80%94%E2%80%94%E6%96%87%E6%A1%A3%E7%94%9F%E6%88%90%E9%A1%BA%E5%BA%8F%E4%B8%8E%E4%BE%9D%E8%B5%96%E5%85%B3%E7%B3%BB.md"
[3]: https://github.com/watsonk1998/008-review-control-plane "https://github.com/watsonk1998/008-review-control-plane"
[4]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E3%80%8AV0.3%20%E8%BE%B9%E7%95%8C%E5%A3%B0%E6%98%8E%E3%80%8B%E5%AE%8C%E6%95%B4%E8%8D%89%E6%A1%88-prompt.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E3%80%8AV0.3%20%E8%BE%B9%E7%95%8C%E5%A3%B0%E6%98%8E%E3%80%8B%E5%AE%8C%E6%95%B4%E8%8D%89%E6%A1%88-prompt.md"
[5]: https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/known-limitations.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/known-limitations.md"
[6]: https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/architecture.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/architecture.md"
[7]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/research_inputs/latest-eval-summary.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/research_inputs/latest-eval-summary.md"
[8]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E4%B8%89%E8%A7%92%E5%AF%B9%E6%AF%94%E7%A0%94%E7%A9%B6%E7%BB%93%E6%9E%9C.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E4%B8%89%E8%A7%92%E5%AF%B9%E6%AF%94%E7%A0%94%E7%A9%B6%E7%BB%93%E6%9E%9C.md"
[9]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/V0.2%20%E7%A0%94%E7%A9%B6%E8%AE%BE%E8%AE%A1%E4%B8%8E%E5%AE%9E%E6%96%BD%E6%80%BB%E6%96%87%E6%A1%A3.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/V0.2%20%E7%A0%94%E7%A9%B6%E8%AE%BE%E8%AE%A1%E4%B8%8E%E5%AE%9E%E6%96%BD%E6%80%BB%E6%96%87%E6%A1%A3.md"
[10]: https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/review_eval "https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/review_eval"
[11]: https://github.com/Accord-Project/aec3po "https://github.com/Accord-Project/aec3po"
[12]: https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/formal-review.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/docs/formal-review.md"
[13]: https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E3%80%8A%E5%8F%8C%E6%A0%B7%E6%9C%AC%E4%BA%BA%E5%B7%A5%E5%A4%8D%E6%A0%B8%E8%A3%81%E5%86%B3%E7%A8%BF%EF%BC%88internal%20reviewed%20adjudication%20notes%EF%BC%89%E3%80%8B-prompt.md "https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/%E4%BB%BB%E5%8A%A1%E4%B9%A6/%E3%80%8A%E5%8F%8C%E6%A0%B7%E6%9C%AC%E4%BA%BA%E5%B7%A5%E5%A4%8D%E6%A0%B8%E8%A3%81%E5%86%B3%E7%A8%BF%EF%BC%88internal%20reviewed%20adjudication%20notes%EF%BC%89%E3%80%8B-prompt.md"
[14]: https://github.com/Open-Source-Legal/OpenContracts "https://github.com/Open-Source-Legal/OpenContracts"
[15]: https://github.com/nomic-ai/aec-bench "https://github.com/nomic-ai/aec-bench"
[16]: https://github.com/evolsb/claude-legal-skill "https://github.com/evolsb/claude-legal-skill"
[17]: https://github.com/aws-samples/review-and-assessment-powered-by-intelligent-documentation "https://github.com/aws-samples/review-and-assessment-powered-by-intelligent-documentation"
[18]: https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/research_inputs "https://github.com/watsonk1998/008-review-control-plane/tree/main/fixtures/research_inputs"
