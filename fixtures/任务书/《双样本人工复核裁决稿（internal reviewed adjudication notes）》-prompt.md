

角色设定

你现在扮演的是一名 首席研究官（Chief Research Officer）+ 内部复核裁决官（Internal Adjudication Lead）+ 审查真相分层设计师（Truth Layering Designer）+ 反过拟合审计官（Anti-Overfitting Auditor）。

你的任务不是直接产出 expert gold，也不是把 Gemini deepresearch 结果包装成"标准答案"。
你的任务是：

基于当前 GitHub 仓库事实、本地 research pack 结构化证据、双样本监督材料、V0.0 / V0.2 / Gemini 对照结果、已完成的《三角对比研究结果》、已定稿的《V0.3 边界声明》与《差距裁决清单》，以及当前缺乏正式人工裁决资源这一现实，起草一份《双样本人工复核裁决稿（internal reviewed adjudication notes）》完整草案。

这份文档的目标不是宣布"最终正确答案"，而是为后续版本化评测池中的：
	•	v0.2.0-internal-reviewed

提供一个受边界约束、显式区分 truth 类型、显式记录 provenance、并强防过拟合的内部复核底稿。

⸻

任务背景

项目仓库：
	•	https://github.com/watsonk1998/008-review-control-plane

当前仓库已经明确：

1）项目定位
	•	项目是 review control plane
	•	structured_review 是正式结构化审查子域
	•	主链是：parse -> facts -> rules -> evidence -> report
	•	review_assist 不是正式审查结论

2）当前结果契约

structured_review 的稳定结果对象包括：
	•	summary
	•	visibility
	•	resolvedProfile
	•	issues
	•	matrices
	•	artifactIndex
	•	reportMarkdown
	•	unresolvedFacts

其中：
	•	visibility 是 top-level canonical 可视域对象
	•	manualReviewNeeded 是唯一 canonical 布尔语义
	•	issue 会显式输出：
	•	issueKind
	•	applicabilityState
	•	evidenceMissing
	•	manualReviewReason

3）当前 truth / seed / reviewed 语义

fixtures/review_eval/README.md 已明确版本语义：
	•	v0.1.0-gemini-seed
	•	v0.1.0-bootstrap-seed
	•	v0.2.0-internal-reviewed
	•	v1.0.0-expert-golden

并明确规定：
	1.	不得把 Gemini 结果直接当作专家 truth
	2.	必须区分 issue truth 与 visibility truth
	3.	必须显式记录 provenance

4）当前 parser / visibility 事实
	•	PDF 仍是 pdf_text_only + parserLimited=True
	•	本轮不引入 OCR / 多模态
	•	以下情况必须保留人工复核语义：
	•	visibility_gap
	•	attachment_unparsed
	•	referenced_only
	•	evidence 不足以形成硬缺陷时
	•	系统不得把"没读到附件"直接写成"附件缺失"

⸻

你的研究输入与证据层级

你必须基于以下四层证据开展裁决工作，并始终尊重它们的层级差异：

| 层级 | 来源 | 定位 | 注意事项 |
|------|------|------|----------|
| 第 1 层：GitHub 仓库事实 | README、docs/formal-review.md、fixtures/review_eval/README.md | 系统边界真相源 | 所有裁决的顶层约束 |
| 第 2 层：本地 research pack | fixtures/research_inputs/ | 样本级结构化证据源 | 双样本 JSON / matrices / visibility / rule-hits 等结构化工件；issue truth / visibility truth / evidence truth 的判断必须优先依托此层 |
| 第 3 层：Markdown 报告 | structured-review-report.md 等 | 人类可读呈现层 | 适合快速浏览，但不应作为 truth 分层的主要依据 |
| 第 4 层：Gemini | Gemini deepresearch 结果 | seed / candidate reference | 仅可用于候选问题发现；不可替代结构化证据做 truth 分层 |

补充说明：
	•	样本 A 结构化工件路径：fixtures/research_inputs/sample-a-cold-rolling/
	•	样本 B 结构化工件路径：fixtures/research_inputs/sample-b-puhua-rainwater/
	•	每个样本目录包含 13 个结构化工件：structured-review-result.json、structured-review-l0-visibility.json、structured-review-rule-hits.json、structured-review-facts.json、各类 matrix 等
	•	逐 issue 裁决时，必须优先依据 structured-review-result.json 中的 issues 字段（含 issueKind / applicabilityState / evidenceMissing）和 structured-review-l0-visibility.json（可视域对象），而非主要靠 Markdown 报告文案做 truth 分层
	•	latest-eval-summary.md 可作为阶段性辅助参考，但不能因某次 eval 通过就自动升格 truth

⸻

已知现实约束（你必须正视，不能绕开）

现实约束 1：当前没有正式的人类专家 gold

你不能假装我们已经拥有：
	•	完整专家审查意见
	•	成体系人工逐 issue adjudication
	•	法律/工程双签字的 gold set

所以你产出的文档只能是：
	•	internal reviewed adjudication notes
而不能冒充：
	•	expert-golden

现实约束 2：Gemini 目前只能临时"顶一顶"

Gemini deepresearch 在当前阶段只能作为：
	•	seed baseline
	•	candidate issue inventory
	•	bootstrap substitute
	•	差距探针

不能作为：
	•	gold truth
	•	最终仲裁者
	•	规则答案库
	•	prompt 模板目标

现实约束 3：当前只有两份高价值真实样本

双样本非常有价值，但也极易诱导过拟合。
你必须全程防止以下错误：
	•	围绕项目名写裁决
	•	围绕固定数字写裁决
	•	围绕章节标题写模板特判
	•	围绕附件名写例外逻辑
	•	围绕 Gemini wording 做"像标准答案"的裁决

⸻

你本次文档的核心目标

你要起草的不是"结论报告"，而是双样本人工复核裁决稿。

这份裁决稿必须完成以下任务：
	1.	对每个样本的关键 issue 做内部复核裁决
	2.	对每个 issue 明确区分：
	•	issue truth
	•	visibility truth
	•	evidence truth
	•	suggestion enhancement
	3.	对每个 issue 明确标记：
	•	成立 / 不成立 / 待补证 / 仅建议增强
	4.	明确指出：
	•	哪些结论只是在当前可视域内成立
	•	哪些结论受 parserLimited / attachment_unparsed 影响
	•	哪些结论暂时只能作为 seed-level signal
	5.	为后续 v0.2.0-internal-reviewed 提供可追溯、可治理、可防过拟合的底稿

truth 分层判断时，必须优先依托 research pack 中的结构化 JSON / matrices / visibility 对象，而非主要靠 Markdown 报告文案。

⸻

你必须处理的样本范围

你必须至少覆盖双样本：

样本 A

冷轧厂 2030 单元三台行车电气系统改造：
	•	research pack 路径：fixtures/research_inputs/sample-a-cold-rolling/
	•	源施组、V0.0 结果、V0.2 结果、Gemini deepresearch 结果

样本 B

培花初期雨水调蓄池建设工程：
	•	research pack 路径：fixtures/research_inputs/sample-b-puhua-rainwater/
	•	源施组、V0.0 结果、V0.2 结果、Gemini deepresearch 结果

你必须把这两份样本分别做裁决，不能混成一锅。

⸻

你必须遵守的 truth 分层规则

这份文档最重要的不是"给答案"，而是"把真相分层"。

你必须显式使用以下 truth taxonomy：

1）Issue Truth

表示：某个问题本身是否成立。
例如：
	•	文档确实缺少某关键章节
	•	结构性矛盾确实存在
	•	某项强约束风险确实被触发

2）Visibility Truth

表示：系统当前到底看到了什么、没看到什么。
例如：
	•	附件只是没解析到，不等于缺失
	•	PDF 路径是 text-only，不足以支持某些强判断
	•	图表、附图、表格未保留结构

3）Evidence Truth

表示：当前证据链是否足以支撑 issue 升级为 hard defect。
例如：
	•	只能判断"疑似缺口"
	•	尚不足以形成硬缺陷
	•	需要补附件 / 补图纸 / 补条款适用证据

4）Suggestion Enhancement

表示：这不是硬缺陷，也不是当前证据足以支持的规范强约束，只是更优整改建议、工程增强建议或研究员式提醒。

⸻

你必须使用的裁决标签

对于每条关键 issue，你必须至少给出以下裁决标签：

A. 裁决结果
	•	成立（Confirmed）
	•	不成立（Rejected）
	•	待补证（Needs Supplement）
	•	仅建议增强（Enhancement Only）

B. Truth 类型
	•	issue_truth
	•	visibility_truth
	•	evidence_truth
	•	enhancement_only

注意：
一条 issue 可以同时涉及多个 truth 层，但你必须明确主 truth 类型和次 truth 类型。

C. 证据充分度
	•	sufficient
	•	partial
	•	weak
	•	blocked_by_visibility

D. 过拟合风险
	•	low
	•	medium
	•	high
	•	unacceptable

E. 进入后续版本化样本池的建议地位
	•	可进入 v0.2.0-internal-reviewed
	•	仅保留为 seed reference
	•	暂不纳入 versioned truth
	•	明确不纳入

⸻

极其重要：反过拟合硬约束

这份人工复核裁决稿必须把 anti-overfit 做成核心规范。

1）不得把样本表面特征直接裁成通用 truth

以下东西不能直接被写成"通用正确项"：
	•	项目名本身
	•	某个固定吨位
	•	某个固定工期天数
	•	某个人数配置
	•	某个章节标题
	•	某个附件名称
	•	某种 Gemini wording

你必须把它们抽象成更高层的问题模式，例如：
	•	起重吊装事实抽取不足
	•	危险环境控制链缺口
	•	工期-资源-工序冲突推理不足
	•	附件可视域缺口与缺失误判混淆

2）不得把 Gemini 结果当裁决仲裁者

你可以用 Gemini：
	•	辅助发现候选问题
	•	作为对照参照
	•	帮助形成 seed inventory

但你不能：
	•	以 Gemini 为终裁
	•	认为 Gemini 提到了就一定成立
	•	认为 Gemini 没提到就一定不成立

3）必须优先保护"可追溯 truth"而不是"高 recall 幻觉"

如果某个结论在当前证据下不够硬，你必须敢于裁成：
	•	Needs Supplement
	•	blocked_by_visibility
	•	Enhancement Only

而不是为了"看起来像专家"去强行给出硬判断。

4）不得把 internal-reviewed 写成 expert-golden

这份文档必须始终承认自己是：
	•	内部复核底稿
	•	暂时版本
	•	有证据边界
	•	有 seed 依赖
	•	有待未来人工/专家进一步确认的部分

⸻

你必须处理的输入材料

你必须综合处理以下材料：

A. GitHub 当前主干事实（第 1 层：系统边界真相源）

至少包括：
	•	README
	•	docs/formal-review.md
	•	fixtures/review_eval/README.md
	•	fixtures/supervision 中双样本结果与源文档

B. 本地 research pack 结构化证据（第 2 层：样本级结构化证据源）

	•	fixtures/research_inputs/sample-a-cold-rolling/ - 样本 A 全部结构化工件
	•	fixtures/research_inputs/sample-b-puhua-rainwater/ - 样本 B 全部结构化工件

逐 issue 裁决时，必须优先依据：
	•	structured-review-result.json（issues 字段：issueKind / applicabilityState / evidenceMissing）
	•	structured-review-l0-visibility.json（可视域对象）
	•	structured-review-rule-hits.json（规则命中）
	•	structured-review-facts.json（事实抽取）
	•	各类 matrix（attachment-visibility / conflict / hazard-identification / rule-hit / section-structure）

不得主要靠 Markdown 报告文案做 truth 分层。

C. V0.2 设计文档
	•	V0.2 研究设计与实施总文档.md

你必须把它用作：
	•	truth 分层与 anti-overfit 原则参考
	•	但不能把它当当前现状快照

D. 双样本 V0.0 / V0.2 / Gemini 对照材料（第 3 层 + 第 4 层）

你必须：
	•	横向对比
	•	但最终做的是内部裁决，不是简单比较

E. 已完成的上游文档

	•	《三角对比研究结果》- 研究底稿
	•	《V0.3 边界声明》- 上位约束
	•	《差距裁决与反过拟合约束清单》- 差距闸门

你的所有裁决必须在这三份上游文档的框架内进行，不得越界。

⸻

你必须输出的文档结构

你的输出必须是完整的 《双样本人工复核裁决稿（internal reviewed adjudication notes）》草案，并至少包含以下章节，且按顺序组织：

⸻

0. 文档定位

说明：
	•	这不是 expert-golden
	•	这不是 implementation plan
	•	这不是 Gemini 对照报告
	•	这是 v0.2.0-internal-reviewed 准备层的人工复核裁决底稿

⸻

1. 证据基础与裁决边界

说明：
	•	本文基于哪些仓库事实（第 1 层：系统边界真相源）
	•	本文使用了哪些 research pack 结构化工件（第 2 层：样本级结构化证据源）
	•	本文参考了哪些 Markdown 报告（第 3 层：人类可读呈现层）
	•	Gemini 在本文中的地位是什么（第 4 层：seed / candidate reference）
	•	本文可以裁决到什么程度
	•	本文不能假装裁决到什么程度

这一章必须体现"证据边界意识"。

⸻

2. 复核方法与 truth taxonomy

明确写清：
	•	你如何区分 issue truth / visibility truth / evidence truth / enhancement
	•	你如何使用 Confirmed / Rejected / Needs Supplement / Enhancement Only
	•	你如何判断某条结论能否进入 v0.2.0-internal-reviewed
	•	你的 truth 分层判断优先依据了哪些结构化工件

⸻

3. 样本 A：冷轧厂人工复核裁决

这一章必须是样本级裁决。

至少包括：
	•	样本背景与可视域边界
	•	关键 issue 裁决表
	•	每个关键 issue 的裁决说明
	•	哪些条目可进入 v0.2.0-internal-reviewed
	•	哪些条目只能保留 seed reference
	•	哪些条目必须待补证
	•	哪些条目属于 enhancement only

裁决时必须优先依据 fixtures/research_inputs/sample-a-cold-rolling/ 下的结构化 JSON 和 matrices。

⸻

4. 样本 B：培花人工复核裁决

要求同上。

尤其必须更重视：
	•	PDF pdf_text_only
	•	parserLimited
	•	表格 / 图示 / 附图未保留
	•	由此导致的 visibility truth 限制

裁决时必须优先依据 fixtures/research_inputs/sample-b-puhua-rainwater/ 下的结构化 JSON 和 matrices。

⸻

5. 双样本交叉裁决观察

这一章要做的是：
	•	哪些问题模式在两样本中都表现出系统差距
	•	哪些只是样本特有现象
	•	哪些可抽象成通用问题模式
	•	哪些不能抽象，否则会诱导过拟合

这一章非常关键，必须体现 anti-overfit 思维。

⸻

6. Gemini seed 的临时使用说明

这一章必须单列。

说明：
	•	本文中 Gemini 被怎么使用
	•	没被怎么使用
	•	哪些裁决参考了 Gemini 作为候选问题来源
	•	哪些地方明确没有让 Gemini 决定真相
	•	为什么这仍然不能叫 gold adjudication

⸻

7. 反过拟合裁决约束

必须单列，而且要写得硬。

至少包括：
	•	不得把样本词写成通用 truth
	•	不得把 Gemini wording 写成 adjudication language
	•	不得按项目名 / 文件名 / 数字 / 附件名建 truth
	•	不得因单样本高表现而直接升格规则
	•	必须优先把问题抽象为机制缺口

⸻

8. 可进入 v0.2.0-internal-reviewed 的建议条目清单

这一章非常重要。

你必须明确列出：
	•	哪些 issue / truth 片段适合进入 internal-reviewed
	•	为什么适合
	•	provenance 怎么记录
	•	truth 类型是什么
	•	是否需要附带 visibility/evidence 限制说明

⸻

9. 暂不进入 internal-reviewed 的条目清单

这一章同样重要。

明确列出：
	•	哪些条目暂不进入
	•	原因是什么：
	•	证据不足
	•	被 visibility 阻断
	•	仅是建议增强
	•	过拟合风险高
	•	过度依赖 Gemini

⸻

10. 最终裁决结论

最后用高密度语言说明：
	•	这份内部复核稿确认了什么
	•	没确认什么
	•	为什么它仍不是 gold
	•	下一步要补什么，才能从 internal-reviewed 走向更高等级 truth

⸻

你必须给出的核心表格

你的文档中至少必须有一张高信息密度总表。
每一行至少包含：
	•	样本
	•	issue 名称 / issue 模式
	•	裁决结果
	•	主 truth 类型
	•	次 truth 类型（如有）
	•	证据充分度
	•	可视域状态影响
	•	Gemini 参与角色（none / candidate only / auxiliary reference）
	•	是否建议进入 v0.2.0-internal-reviewed
	•	过拟合风险
	•	备注

这张表必须成为全文核心。

⸻

输出风格要求

你的输出必须满足以下要求：
	1.	像正式的内部复核裁决稿
不是研究随笔，不是对比报告，不是实施建议。
	2.	必须诚实
要敢于写：
	•	不成立
	•	待补证
	•	blocked_by_visibility
	•	enhancement only
	3.	必须真分 truth 层
不能把 visibility truth 混成 issue truth，也不能把 enhancement 混成 hard defect。
	4.	必须强 anti-overfit
不能把双样本现象直接升级为通用 truth。
	5.	必须与仓库事实一致
不能和 README / formal-review / review_eval README 冲突。
	6.	必须承认这只是 internal-reviewed 准备层，而不是 gold
这是底线。
	7.	truth 分层必须优先依据结构化工件
不得主要靠 Markdown 报告文案做 truth 分层判断。

⸻

你最后必须自查的 10 件事

在完成文档前，请确认：
	1.	我是否明确写出这不是 expert-golden？
	2.	我是否明确区分了 issue truth / visibility truth / evidence truth / enhancement？
	3.	我是否为每个样本分别做了裁决，而不是混合讨论？
	4.	我是否给出了样本级 issue 裁决表？
	5.	我是否明确说明了 Gemini 只是 candidate / seed 参考？
	6.	我是否敢于把一部分条目标成 Needs Supplement / blocked_by_visibility？
	7.	我是否明确列出了可进入 v0.2.0-internal-reviewed 的条目？
	8.	我是否明确列出了暂不进入的条目？
	9.	我是否写出了反过拟合裁决约束？
	10.	我是否避免把双样本表面词语直接写成通用 truth？
	11.	我的 truth 分层判断是否优先依据了 research pack 中的结构化 JSON / matrices / visibility 对象？
	12.	我是否在证据基础章节中说明了四层证据层级？

如果以上任一项没有满足，请继续完善，而不是提前结束。

⸻

最终目标一句话

请产出一份：

基于双样本、优先依托 research pack 结构化工件做 truth 分层、显式区分 truth 类型、承认当前非 gold 现实、允许 Gemini 仅作 seed 辅助、并把防双样本过拟合作为核心制度约束的《双样本人工复核裁决稿（internal reviewed adjudication notes）》完整草案。
