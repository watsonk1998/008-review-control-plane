

角色设定

你现在扮演的是一名 首席产品战略官（Chief Product Strategist）+ 审查系统架构研究员（Formal Review System Architect）+ 路线图设计师（Roadmap Designer）。

你的任务不是继续输出某一轮实施任务书，也不是重复已有的边界声明、差距裁决或样本裁决稿。
你的任务是：

基于当前 GitHub 仓库事实、V0.2/V0.3 已完成文档、双样本监督材料与现有研究输入，起草一份《产品思路与路线图》完整文档。

这份文档的目标是：
把 008-review-control-plane 这个产品“到底是什么、当前阶段在哪里、V0.3 为什么这样收边界、未来可能往哪里演进”讲清楚。

⸻

任务背景

项目仓库：
	•	https://github.com/watsonk1998/008-review-control-plane

当前已知事实包括：

1）项目定位

项目不是一个“大而全的工程 AI 平台”，也不是单一对话式模型产品。
它当前的准确定位是：
	•	一个 review control plane
	•	其中承载一条正式结构化审查主链：structured_review
	•	主链基本形态为：
	•	parse -> facts -> rules -> evidence -> report

同时存在双轨能力：
	•	review_assist：辅助性、快速性、总结型能力
	•	structured_review：正式结构化审查能力

2）当前 official / experimental 边界

当前 official documentType 仅包括：
	•	construction_org
	•	hazardous_special_scheme

以下虽已有 ready base pack，但当前仍是 experimental：
	•	construction_scheme
	•	supervision_plan
	•	review_support_material

3）当前系统边界

当前仍明确：
	•	PDF 路径是 pdf_text_only + parserLimited=True
	•	不引入 OCR / 多模态 / 图纸平台化
	•	Gemini 只是 seed，不是 gold truth
	•	研究型 AI 可以读取 GitHub，但本地运行产物不是默认长期真相

4）当前已完成的前置文档

你必须参考并吸收以下文档，但不能混淆它们的角色：

上游研究与治理文档
	•	fixtures/任务书/三角对比研究结果.md
	•	fixtures/任务书/《V0.3 边界声明》.md
	•	fixtures/任务书/《V0.2→V0.3 差距裁决与反过拟合约束清单》.md
	•	fixtures/任务书/《双样本人工复核裁决稿（internal reviewed adjudication notes）》.md

设计 / 输入 / 流程文档
	•	fixtures/任务书/V0.2 研究设计与实施总文档.md
	•	fixtures/任务书/使用说明（给研究型 AI）.md
	•	fixtures/任务书/V0.3 前置工作流程指南——文档生成顺序与依赖关系.md

结构化研究输入
	•	fixtures/research_inputs/
	•	fixtures/supervision/

⸻

这份文档的定位

你要写的《产品思路与路线图》不是：
	•	不是 README 改写版
	•	不是 V0.3 实施任务书
	•	不是边界声明
	•	不是差距裁决清单
	•	不是 internal-reviewed truth 文档
	•	不是外部项目评测报告

它是：

面向产品思路收口的总纲文档。

它要回答的核心问题是：
	1.	这个产品究竟想成为什么？
	2.	它现在实际上是什么？
	3.	为什么 V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本？
	4.	哪些能力属于当前主线，哪些能力属于中远期路线？
	5.	外部项目可以借鉴什么、不能借鉴什么？
	6.	后续《V0.3 实施设计 / 执行任务书》应该建立在怎样的产品思路之上？

⸻

你必须坚持的产品目标口径（已确认，不允许跑偏）

请以以下口径作为全文中心定义：

V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本。
目标是在 official scope 内，把 structured_review 做成：
	•	可审前置
	•	可视域诚实
	•	证据可追溯
	•	规则可命中
	•	结果可复核
	•	评测可闭环
的 formal-review spine。

这句话必须在文档中占据核心地位，而不是作为边角说明。

⸻

你必须明确区分的几类东西

全文必须持续区分以下概念，不得混淆：

1）产品当前定位 vs 长期愿景
	•	当前定位：review control plane + formal-review spine
	•	长期愿景：可能扩展到更多文档、更多模态、更复杂的工作流

2）V0.3 主线 vs 远期规划

V0.3 主线不应包含：
	•	全文档类型覆盖
	•	OCR / 多模态 / 图纸平台化
	•	多文档联合审查
	•	ontology / graph-first 重构
	•	企业级大 workflow SaaS 化

但这些内容可以作为：
	•	中期路线
	•	长期路线
	•	战略储备方向

3）研究文档 vs 实施文档

前面三份治理文档和双样本裁决稿，不是实施任务书；
本次文档也不是实施任务书。
它只是为后续实施任务书提供产品思路总纲。

4）借鉴外部项目 vs 引入外部项目

你必须严格区分：
	•	借它的方法
	•	借它的对象模型
	•	借它的评测方式
	•	借它的流程纪律

与：
	•	整体引入其技术栈
	•	整体迁移其产品壳
	•	用它替代当前产品目标

⸻

你必须处理的外部参考项目

请把以下项目作为“外部参考输入”，但要严格控制使用方式：
	•	OpenContracts
	•	AWS RAPID
	•	AEC3PO
	•	AEC-Bench
	•	claude-legal-skill

你必须做的不是“夸谁先进”，而是回答：
	1.	这些项目分别能给 008 什么帮助？
	2.	哪些帮助是当前 V0.3 阶段就能吸收的？
	3.	哪些帮助只适合中长期？
	4.	哪些如果现在借得太多，会把产品带偏？

⸻

你必须坚持的外部借鉴结论方向

除非仓库事实强烈反驳，否则你应基本沿用以下判断逻辑：

OpenContracts

更适合作为：
	•	证据对象模型参考
	•	annotation / relationship / versioning 参考

不适合作为：
	•	当前整仓迁移目标
	•	当前产品壳模板

AEC-Bench

更适合作为：
	•	评测任务设计参考
	•	task / scope taxonomy 参考
	•	benchmark / replay / diagnostics 参考

claude-legal-skill

更适合作为：
	•	pre-review checklist
	•	审查前置 gate 的方法参考

AEC3PO

更适合作为：
	•	schema discipline
	•	术语与关系命名参考
	•	长期知识建模参考

不适合作为：
	•	V0.3 主线实施对象

RAPID

更适合作为：
	•	未来工作流 / 产品化 / 队列编排参考

不适合作为：
	•	当前 V0.3 主借鉴对象

⸻

你必须输出的核心结论方向

文档必须最终清楚表达：

1）产品不是什么
	•	不是万能工程 AI
	•	不是全自动替代人工签发系统
	•	不是“更像 Gemini 的写作器”
	•	不是当前阶段就做平台级 OCR / 多模态 / 图纸平台 / 多文档联合审查的大系统

2）产品当前是什么
	•	是 review control plane
	•	是在 official scope 内收口 formal-review spine 的系统
	•	是通过 artifacts / evidence / visibility / reviewer gate / eval gate 来建立可信审查能力的系统

3）V0.3 为什么这样定义
	•	因为当前最短板不在平台壳，而在证据、可视域、规则、评测闭环
	•	因为前期治理文档已明确：先收边界，再硬内核
	•	因为扩范围会破坏 anti-overfit 与治理稳定性

4）远期路线应该怎么写

远期路线可以有，但必须分层：
	•	中期：扩 pack / 扩 doc type / 补 internal-reviewed / reviewer workflow
	•	中远期：OCR / 图纸 / 多模态 / 多文档联合审查
	•	长期：ontology / graph-first / 更强产品化工作流

⸻

你必须输出的文档结构

你的最终输出必须至少包含以下章节，并按顺序组织：

⸻

0. 文档定位

说明：
	•	这不是实施任务书
	•	这不是边界声明
	•	这不是差距裁决
	•	这是产品思路与路线图总纲

⸻

1. 产品一句话定义

必须明确写出：
	•	产品当前一句话是什么
	•	V0.3 一句话目标是什么

这一章必须高度凝练。

⸻

2. 当前阶段的产品定位

回答：
	•	当前产品是什么
	•	当前产品不是什么
	•	为什么当前最准确的说法是 review control plane + formal-review spine
	•	review_assist 与 structured_review 的关系是什么

⸻

3. 为什么 V0.3 要“收边界、硬内核、补证据、强评测”

这一章必须成为全文中心之一。

至少说明：
	•	V0.3 当前最重要的问题是什么
	•	为什么不是扩范围
	•	为什么不是追报告效果
	•	为什么是 L0 + L2 主攻
	•	为什么要让 evidence / visibility / gate 成为主线

⸻

4. V0.3 的目标与非目标

拆成两部分：

4.1 V0.3 目标

必须写清：
	•	official scope 内要做什么
	•	formal-review spine 要做到什么程度
	•	reviewer / eval / artifacts 要达到什么作用

4.2 V0.3 非目标

明确列出并解释为什么本轮不做：
	•	全文档类型覆盖
	•	OCR / 多模态 / 图纸平台化
	•	多文档联合审查
	•	ontology / graph-first 重构
	•	企业级大 workflow 壳

⸻

5. 从 V0.0 到 V0.3：产品演进主线

用产品视角而不是纯技术视角，解释：
	•	V0.0 解决了什么
	•	V0.2 带来了什么变化
	•	V0.3 为什么不是继续“大扩张”，而是治理收口
	•	当前演进主线到底是什么

⸻

6. 核心能力地图

请把产品能力拆成地图，而不是散点建议。

建议至少包括：
	•	文档可视域层
	•	事实抽取层
	•	规则 / 条文适用层
	•	证据与 unresolved facts 层
	•	报告与 artifact 层
	•	reviewer gate 层
	•	eval gate 层

并说明：
	•	哪些是当前正式主线
	•	哪些只是支撑层
	•	哪些还处于未来阶段

⸻

7. 外部参考项目的借鉴边界

这是全文关键章节之一。

请逐项说明：
	•	OpenContracts
	•	AEC-Bench
	•	claude-legal-skill
	•	AEC3PO
	•	AWS RAPID

对每个项目都要写：
	1.	可借鉴什么
	2.	当前 V0.3 阶段为什么借这些
	3.	明确不借什么
	4.	如果现在借过头，会把产品带向哪里

⸻

8. 中期与长期路线图

请明确分层：

8.1 中期路线

可以包含：
	•	扩更多 ready packs
	•	扩更多 documentType
	•	补 internal-reviewed / gold 承接层
	•	更强 reviewer workflow

8.2 中远期路线

可以包含：
	•	OCR / 多模态
	•	图纸平台化
	•	多文档联合审查

8.3 长期路线

可以包含：
	•	ontology / graph-first
	•	更大范围的 workflow / 产品化能力
	•	更完整的审查控制平台

关键要求：
	•	必须说明这些是未来路线，不得冒充 V0.3 主线
	•	必须说明进入这些路线的前提条件

⸻

9. 产品路线的治理原则

这一章必须明确：
	•	anti-overfit 是长期原则，不只是 V0.3 临时原则
	•	official / experimental / diagnostics / internal-reviewed / gold 的分层治理要长期保留
	•	任何扩范围都必须在已有主线足够硬之后发生
	•	研究、边界、裁决、实施四层文档关系应如何长期维护

⸻

10. 对后续《V0.3 实施设计 / 执行任务书》的输入要求

这一章要回答：
	•	这份《产品思路与路线图》将如何约束后续实施任务书
	•	后续实施任务书不应再重新讨论什么
	•	后续实施任务书应重点展开什么
	•	哪些外部借鉴可以进入实施层，哪些只能保留在产品思路层

⸻

11. 最终结论

最后用高密度语言概括：
	•	产品到底是什么
	•	V0.3 到底做什么
	•	为什么这么定义
	•	未来路线怎么留白
	•	最不能做错的是什么

⸻

输出风格要求

你的输出必须满足以下要求：
	1.	产品总纲感
不是边界声明，不是研究报告，不是技术实施书，而是产品思路总纲。
	2.	克制
不要把所有远期能力都写成当前要做的事。
	3.	强分层
要把当前 / 中期 / 远期清楚分开。
	4.	与既有文档不冲突
必须服从：
	•	《V0.3 边界声明》
	•	《V0.2→V0.3 差距裁决与反过拟合约束清单》
	•	《双样本人工复核裁决稿》
	•	GitHub 仓库事实
	5.	外部参考项目要写成“借鉴边界”
不能写成“引入路线”。
	6.	必须能为后续《V0.3 实施设计 / 执行任务书》提供稳定上位约束
这是这份文档最核心的价值。

⸻

你最后必须自查的 10 件事

在完成文档前，请确认：
	1.	我是否清楚定义了产品当前是什么、不是什​​么？
	2.	我是否明确把 V0.3 定义成“收边界、硬内核、补证据、强评测”的版本？
	3.	我是否把远期能力与 V0.3 主线清楚分开？
	4.	我是否没有把 OCR / 多模态 / 多文档联合审查写成当前主线？
	5.	我是否没有把外部项目写成“直接引入对象”？
	6.	我是否把 OpenContracts / AEC-Bench / claude-legal-skill / AEC3PO / RAPID 的借鉴边界讲清楚了？
	7.	我是否持续服从已有边界声明与差距裁决？
	8.	我是否把 anti-overfit 写成长期治理原则而不是临时提醒？
	9.	我是否让这份文档能约束后续实施任务书？
	10.	我是否避免把它写成新的宏大愿景空话？

如果以上任一项没有满足，请继续完善，而不是提前结束。

⸻

最终目标一句话

请产出一份：

与当前仓库事实和既有治理文档一致、明确产品当前定位与 V0.3 主线、清晰区分中短期与远期路线、并能作为后续《V0.3 实施设计 / 执行任务书》上位约束的《产品思路与路线图》完整文档。
:::

如果你愿意，我下一条可以继续给你一版更适合实施型 AI 落库到 docs/product-strategy.md 的版本。
角色设定

你现在扮演的是一名 首席产品战略官（Chief Product Strategist）+ 审查系统架构研究员（Formal Review System Architect）+ 路线图设计师（Roadmap Designer）。

你的任务不是继续输出某一轮实施任务书，也不是重复已有的边界声明、差距裁决或样本裁决稿。
你的任务是：

基于当前 GitHub 仓库事实、V0.2/V0.3 已完成文档、双样本监督材料与现有研究输入，起草一份《产品思路与路线图》完整文档。

这份文档的目标是：
把 008-review-control-plane 这个产品“到底是什么、当前阶段在哪里、V0.3 为什么这样收边界、未来可能往哪里演进”讲清楚。

⸻

任务背景

项目仓库：
	•	https://github.com/watsonk1998/008-review-control-plane

当前已知事实包括：

1）项目定位

项目不是一个“大而全的工程 AI 平台”，也不是单一对话式模型产品。
它当前的准确定位是：
	•	一个 review control plane
	•	其中承载一条正式结构化审查主链：structured_review
	•	主链基本形态为：
	•	parse -> facts -> rules -> evidence -> report

同时存在双轨能力：
	•	review_assist：辅助性、快速性、总结型能力
	•	structured_review：正式结构化审查能力

2）当前 official / experimental 边界

当前 official documentType 仅包括：
	•	construction_org
	•	hazardous_special_scheme

以下虽已有 ready base pack，但当前仍是 experimental：
	•	construction_scheme
	•	supervision_plan
	•	review_support_material

3）当前系统边界

当前仍明确：
	•	PDF 路径是 pdf_text_only + parserLimited=True
	•	不引入 OCR / 多模态 / 图纸平台化
	•	Gemini 只是 seed，不是 gold truth
	•	研究型 AI 可以读取 GitHub，但本地运行产物不是默认长期真相

4）当前已完成的前置文档

你必须参考并吸收以下文档，但不能混淆它们的角色：

上游研究与治理文档
	•	fixtures/任务书/三角对比研究结果.md
	•	fixtures/任务书/《V0.3 边界声明》.md
	•	fixtures/任务书/《V0.2→V0.3 差距裁决与反过拟合约束清单》.md
	•	fixtures/任务书/《双样本人工复核裁决稿（internal reviewed adjudication notes）》.md

设计 / 输入 / 流程文档
	•	fixtures/任务书/V0.2 研究设计与实施总文档.md
	•	fixtures/任务书/使用说明（给研究型 AI）.md
	•	fixtures/任务书/V0.3 前置工作流程指南——文档生成顺序与依赖关系.md

结构化研究输入
	•	fixtures/research_inputs/
	•	fixtures/supervision/

⸻

这份文档的定位

你要写的《产品思路与路线图》不是：
	•	不是 README 改写版
	•	不是 V0.3 实施任务书
	•	不是边界声明
	•	不是差距裁决清单
	•	不是 internal-reviewed truth 文档
	•	不是外部项目评测报告

它是：

面向产品思路收口的总纲文档。

它要回答的核心问题是：
	1.	这个产品究竟想成为什么？
	2.	它现在实际上是什么？
	3.	为什么 V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本？
	4.	哪些能力属于当前主线，哪些能力属于中远期路线？
	5.	外部项目可以借鉴什么、不能借鉴什么？
	6.	后续《V0.3 实施设计 / 执行任务书》应该建立在怎样的产品思路之上？

⸻

你必须坚持的产品目标口径（已确认，不允许跑偏）

请以以下口径作为全文中心定义：

V0.3 不是扩范围版本，而是收边界、硬内核、补证据、强评测的版本。
目标是在 official scope 内，把 structured_review 做成：
	•	可审前置
	•	可视域诚实
	•	证据可追溯
	•	规则可命中
	•	结果可复核
	•	评测可闭环
的 formal-review spine。

这句话必须在文档中占据核心地位，而不是作为边角说明。

⸻

你必须明确区分的几类东西

全文必须持续区分以下概念，不得混淆：

1）产品当前定位 vs 长期愿景
	•	当前定位：review control plane + formal-review spine
	•	长期愿景：可能扩展到更多文档、更多模态、更复杂的工作流

2）V0.3 主线 vs 远期规划

V0.3 主线不应包含：
	•	全文档类型覆盖
	•	OCR / 多模态 / 图纸平台化
	•	多文档联合审查
	•	ontology / graph-first 重构
	•	企业级大 workflow SaaS 化

但这些内容可以作为：
	•	中期路线
	•	长期路线
	•	战略储备方向

3）研究文档 vs 实施文档

前面三份治理文档和双样本裁决稿，不是实施任务书；
本次文档也不是实施任务书。
它只是为后续实施任务书提供产品思路总纲。

4）借鉴外部项目 vs 引入外部项目

你必须严格区分：
	•	借它的方法
	•	借它的对象模型
	•	借它的评测方式
	•	借它的流程纪律

与：
	•	整体引入其技术栈
	•	整体迁移其产品壳
	•	用它替代当前产品目标

⸻

你必须处理的外部参考项目

请把以下项目作为“外部参考输入”，但要严格控制使用方式：
	•	OpenContracts
	•	AWS RAPID
	•	AEC3PO
	•	AEC-Bench
	•	claude-legal-skill

你必须做的不是“夸谁先进”，而是回答：
	1.	这些项目分别能给 008 什么帮助？
	2.	哪些帮助是当前 V0.3 阶段就能吸收的？
	3.	哪些帮助只适合中长期？
	4.	哪些如果现在借得太多，会把产品带偏？

⸻

你必须坚持的外部借鉴结论方向

除非仓库事实强烈反驳，否则你应基本沿用以下判断逻辑：

OpenContracts

更适合作为：
	•	证据对象模型参考
	•	annotation / relationship / versioning 参考

不适合作为：
	•	当前整仓迁移目标
	•	当前产品壳模板

AEC-Bench

更适合作为：
	•	评测任务设计参考
	•	task / scope taxonomy 参考
	•	benchmark / replay / diagnostics 参考

claude-legal-skill

更适合作为：
	•	pre-review checklist
	•	审查前置 gate 的方法参考

AEC3PO

更适合作为：
	•	schema discipline
	•	术语与关系命名参考
	•	长期知识建模参考

不适合作为：
	•	V0.3 主线实施对象

RAPID

更适合作为：
	•	未来工作流 / 产品化 / 队列编排参考

不适合作为：
	•	当前 V0.3 主借鉴对象

⸻

你必须输出的核心结论方向

文档必须最终清楚表达：

1）产品不是什么
	•	不是万能工程 AI
	•	不是全自动替代人工签发系统
	•	不是“更像 Gemini 的写作器”
	•	不是当前阶段就做平台级 OCR / 多模态 / 图纸平台 / 多文档联合审查的大系统

2）产品当前是什么
	•	是 review control plane
	•	是在 official scope 内收口 formal-review spine 的系统
	•	是通过 artifacts / evidence / visibility / reviewer gate / eval gate 来建立可信审查能力的系统

3）V0.3 为什么这样定义
	•	因为当前最短板不在平台壳，而在证据、可视域、规则、评测闭环
	•	因为前期治理文档已明确：先收边界，再硬内核
	•	因为扩范围会破坏 anti-overfit 与治理稳定性

4）远期路线应该怎么写

远期路线可以有，但必须分层：
	•	中期：扩 pack / 扩 doc type / 补 internal-reviewed / reviewer workflow
	•	中远期：OCR / 图纸 / 多模态 / 多文档联合审查
	•	长期：ontology / graph-first / 更强产品化工作流

⸻

你必须输出的文档结构

你的最终输出必须至少包含以下章节，并按顺序组织：

⸻

0. 文档定位

说明：
	•	这不是实施任务书
	•	这不是边界声明
	•	这不是差距裁决
	•	这是产品思路与路线图总纲

⸻

1. 产品一句话定义

必须明确写出：
	•	产品当前一句话是什么
	•	V0.3 一句话目标是什么

这一章必须高度凝练。

⸻

2. 当前阶段的产品定位

回答：
	•	当前产品是什么
	•	当前产品不是什么
	•	为什么当前最准确的说法是 review control plane + formal-review spine
	•	review_assist 与 structured_review 的关系是什么

⸻

3. 为什么 V0.3 要“收边界、硬内核、补证据、强评测”

这一章必须成为全文中心之一。

至少说明：
	•	V0.3 当前最重要的问题是什么
	•	为什么不是扩范围
	•	为什么不是追报告效果
	•	为什么是 L0 + L2 主攻
	•	为什么要让 evidence / visibility / gate 成为主线

⸻

4. V0.3 的目标与非目标

拆成两部分：

4.1 V0.3 目标

必须写清：
	•	official scope 内要做什么
	•	formal-review spine 要做到什么程度
	•	reviewer / eval / artifacts 要达到什么作用

4.2 V0.3 非目标

明确列出并解释为什么本轮不做：
	•	全文档类型覆盖
	•	OCR / 多模态 / 图纸平台化
	•	多文档联合审查
	•	ontology / graph-first 重构
	•	企业级大 workflow 壳

⸻

5. 从 V0.0 到 V0.3：产品演进主线

用产品视角而不是纯技术视角，解释：
	•	V0.0 解决了什么
	•	V0.2 带来了什么变化
	•	V0.3 为什么不是继续“大扩张”，而是治理收口
	•	当前演进主线到底是什么

⸻

6. 核心能力地图

请把产品能力拆成地图，而不是散点建议。

建议至少包括：
	•	文档可视域层
	•	事实抽取层
	•	规则 / 条文适用层
	•	证据与 unresolved facts 层
	•	报告与 artifact 层
	•	reviewer gate 层
	•	eval gate 层

并说明：
	•	哪些是当前正式主线
	•	哪些只是支撑层
	•	哪些还处于未来阶段

⸻

7. 外部参考项目的借鉴边界

这是全文关键章节之一。

请逐项说明：
	•	OpenContracts
	•	AEC-Bench
	•	claude-legal-skill
	•	AEC3PO
	•	AWS RAPID

对每个项目都要写：
	1.	可借鉴什么
	2.	当前 V0.3 阶段为什么借这些
	3.	明确不借什么
	4.	如果现在借过头，会把产品带向哪里

⸻

8. 中期与长期路线图

请明确分层：

8.1 中期路线

可以包含：
	•	扩更多 ready packs
	•	扩更多 documentType
	•	补 internal-reviewed / gold 承接层
	•	更强 reviewer workflow

8.2 中远期路线

可以包含：
	•	OCR / 多模态
	•	图纸平台化
	•	多文档联合审查

8.3 长期路线

可以包含：
	•	ontology / graph-first
	•	更大范围的 workflow / 产品化能力
	•	更完整的审查控制平台

关键要求：
	•	必须说明这些是未来路线，不得冒充 V0.3 主线
	•	必须说明进入这些路线的前提条件

⸻

9. 产品路线的治理原则

这一章必须明确：
	•	anti-overfit 是长期原则，不只是 V0.3 临时原则
	•	official / experimental / diagnostics / internal-reviewed / gold 的分层治理要长期保留
	•	任何扩范围都必须在已有主线足够硬之后发生
	•	研究、边界、裁决、实施四层文档关系应如何长期维护

⸻

10. 对后续《V0.3 实施设计 / 执行任务书》的输入要求

这一章要回答：
	•	这份《产品思路与路线图》将如何约束后续实施任务书
	•	后续实施任务书不应再重新讨论什么
	•	后续实施任务书应重点展开什么
	•	哪些外部借鉴可以进入实施层，哪些只能保留在产品思路层

⸻

11. 最终结论

最后用高密度语言概括：
	•	产品到底是什么
	•	V0.3 到底做什么
	•	为什么这么定义
	•	未来路线怎么留白
	•	最不能做错的是什么

⸻

输出风格要求

你的输出必须满足以下要求：
	1.	产品总纲感
不是边界声明，不是研究报告，不是技术实施书，而是产品思路总纲。
	2.	克制
不要把所有远期能力都写成当前要做的事。
	3.	强分层
要把当前 / 中期 / 远期清楚分开。
	4.	与既有文档不冲突
必须服从：
	•	《V0.3 边界声明》
	•	《V0.2→V0.3 差距裁决与反过拟合约束清单》
	•	《双样本人工复核裁决稿》
	•	GitHub 仓库事实
	5.	外部参考项目要写成“借鉴边界”
不能写成“引入路线”。
	6.	必须能为后续《V0.3 实施设计 / 执行任务书》提供稳定上位约束
这是这份文档最核心的价值。

⸻

你最后必须自查的 10 件事

在完成文档前，请确认：
	1.	我是否清楚定义了产品当前是什么、不是什​​么？
	2.	我是否明确把 V0.3 定义成“收边界、硬内核、补证据、强评测”的版本？
	3.	我是否把远期能力与 V0.3 主线清楚分开？
	4.	我是否没有把 OCR / 多模态 / 多文档联合审查写成当前主线？
	5.	我是否没有把外部项目写成“直接引入对象”？
	6.	我是否把 OpenContracts / AEC-Bench / claude-legal-skill / AEC3PO / RAPID 的借鉴边界讲清楚了？
	7.	我是否持续服从已有边界声明与差距裁决？
	8.	我是否把 anti-overfit 写成长期治理原则而不是临时提醒？
	9.	我是否让这份文档能约束后续实施任务书？
	10.	我是否避免把它写成新的宏大愿景空话？

如果以上任一项没有满足，请继续完善，而不是提前结束。

⸻

最终目标一句话

请产出一份：

与当前仓库事实和既有治理文档一致、明确产品当前定位与 V0.3 主线、清晰区分中短期与远期路线、并能作为后续《V0.3 实施设计 / 执行任务书》上位约束的《产品思路与路线图》完整文档。
:::
