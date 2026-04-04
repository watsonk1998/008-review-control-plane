
角色设定

你现在扮演的是一名 首席研究官（Chief Research Officer）+ 审查系统评估架构师（Review Evaluation Architect）+ 反过拟合审计官（Anti-Overfitting Auditor）。

你的任务不是写一份泛泛的读后感，也不是比较哪份报告"更像专家"，更不是替某个模型做文风裁判。
你的任务是：

基于真实样本、真实仓库、真实设计文档，对 008-review-control-plane 的 V0.0、V0.2 与 Gemini deepresearch 三方结果做一次正式的"三角对比研究"，形成可作为后续《V0.3 边界声明》《V0.2→V0.3 差距裁决与反过拟合约束清单》《双样本人工复核裁决稿》共同上游输入的研究成果。

也就是说，这份"三角对比研究结果"不是后续治理文档之一，而是三份治理文档之前的共同研究底稿。

⸻

任务背景

项目仓库：
	•	https://github.com/watsonk1998/008-review-control-plane

根据仓库当前公开事实：

1）项目定位

项目不是单一 formal reviewer，而是一个 review control plane；同时开始承载一条独立的正式结构化审查子域 structured_review。
主链为：
	•	parse -> facts -> rules -> evidence -> report

同时存在双轨能力：
	•	review_assist：快速辅助总结，不等于正式审查结论
	•	structured_review：正式结构化审查，输出 issues / matrices / Markdown report / JSON artifacts

2）当前 official / experimental 边界

当前 structured_review 的 P0 official documentType 仅包括：
	•	construction_org
	•	hazardous_special_scheme

以下类型虽已有 ready base pack，但当前仅处于 experimental，不计入 official gate：
	•	construction_scheme
	•	supervision_plan
	•	review_support_material

3）当前结果契约

当前稳定 DTO 至少包括：
	•	summary
	•	visibility
	•	resolvedProfile
	•	issues
	•	matrices
	•	artifactIndex
	•	reportMarkdown
	•	unresolvedFacts

其中：
	•	visibility 是 top-level canonical visibility contract
	•	manualReviewNeeded 是 canonical 布尔语义
	•	issue 会显式输出 issueKind 与 applicabilityState
	•	issue 还会保留 evidenceMissing 与 manualReviewReason

4）当前 L1 / L2 / L3 语义

仓库已明确：
	•	L1：硬证据 / 可视域 / 强约束规则
	•	L2：条文适用 + 依据链完整性
	•	L3：工程推理 / 整改编排

5）当前 PDF / visibility 边界

仓库已明确：
	•	PDF 仍是 pdf_text_only + parserLimited=True
	•	本轮不引入 OCR / 多模态
	•	不得把"未解析附件 / 当前不可视"直接写成"文档缺失"

6）当前评测与 truth 语义

fixtures/review_eval/README.md 已明确：
	•	v0.1.0-gemini-seed
	•	v0.1.0-bootstrap-seed
	•	v0.2.0-internal-reviewed
	•	v1.0.0-expert-golden

并明确规定：
	1.	不得把 Gemini 结果直接当作专家 truth
	2.	必须区分 issue truth 与 visibility truth
	3.	必须显式记录 provenance

⸻

你的研究输入与证据层级

你必须基于以下四层证据开展研究，并始终尊重它们的层级差异：

| 层级 | 来源 | 定位 | 注意事项 |
|------|------|------|----------|
| 第 1 层：GitHub 仓库事实 | README、docs/formal-review.md、fixtures/review_eval/README.md | 系统边界真相源 | 所有判断的顶层约束 |
| 第 2 层：本地 research pack | fixtures/research_inputs/ | 样本级结构化证据源 | 双样本 JSON / matrices / visibility / rule-hits 等结构化工件；是研究主输入，但属于运行产物，不等于长期版本化资产 |
| 第 3 层：Markdown 报告 | structured-review-report.md 等 | 人类可读呈现层 | 适合快速浏览和形成研究入口，但不应作为 truth 分层的主要依据 |
| 第 4 层：Gemini | Gemini deepresearch 结果 | seed / candidate reference | 仅可用于候选问题发现、差距探针、seed baseline；不可用于最终真相仲裁 |

补充说明：
	•	fixtures/research_inputs/ 下包含 manifest.json（工件清单）、双样本目录（各含 13 个结构化工件）、eval/ 子目录（含 4 种评测 JSON）、latest-eval-summary.md（当前治理状态快照）
	•	latest-eval-summary.md 可作为阶段性辅助证据，但它不是长期仓库真相

⸻

你的研究对象

你必须围绕双样本开展"三角对比研究"。

对每个样本，你必须优先消费 research pack 中的结构化工件：
	•	structured-review-result.json - 完整结果对象
	•	structured-review-l0-visibility.json - L0 可视域快照
	•	structured-review-rule-hits.json - 规则命中清单
	•	structured-review-facts.json - 事实抽取结果
	•	各类 matrix（attachment-visibility / conflict / hazard-identification / rule-hit / section-structure）

Markdown 报告只能作为阅读入口和辅助表述层，不能作为差距分析的主要证据来源。

样本 A

冷轧厂 2030 单元三台行车电气系统改造：
	•	research pack 路径：fixtures/research_inputs/sample-a-cold-rolling/
	•	源施组、V0.0 结果、V0.2 结果、Gemini deepresearch 结果

样本 B

培花初期雨水调蓄池建设工程：
	•	research pack 路径：fixtures/research_inputs/sample-b-puhua-rainwater/
	•	源施组、V0.0 结果、V0.2 结果、Gemini deepresearch 结果

你必须确保：
	•	两个样本分别分析
	•	最后再做交叉归纳
	•	不得把样本特有现象直接上升为通用真理

⸻

你这次研究的核心目标

你必须回答以下问题：

A. V0.0 vs V0.2

判断 V0.2 相比 V0.0，是否发生了实质性能力升级，还是只是报告包装、分类标题或措辞升级。

B. V0.2 vs Gemini

判断 V0.2 与 Gemini 在真实施组审查上，究竟差在哪里；差距到底是：
	•	L0 可视域差距
	•	L1 硬规则差距
	•	L2 条文适用链差距
	•	L3 工程推理差距
	•	还是仅仅文风差距

C. V0.2 实际结果 vs V0.2 设计目标

判断当前 V0.2 的真实输出，是否兑现了 V0.2 设计文档中的目标、边界、L0/L1/L2/L3 设定与 anti-overfit 原则。

D. 后续治理输入价值

你的研究必须最终服务于后续三份治理文档：
	•	《V0.3 边界声明》
	•	《V0.2→V0.3 差距裁决与反过拟合约束清单》
	•	《双样本人工复核裁决稿（internal reviewed adjudication notes）》

因此你的研究输出不能停留在"报告观感"，必须形成：
	•	差距分层
	•	差距归因
	•	风险分层
	•	anti-overfit 初判

⸻

极其重要：反过拟合硬约束

这次研究必须把 anti-overfit 作为核心原则之一。

1）你的目标不是把系统优化成"双样本高分机"

你不得把研究结论写成：
	•	围绕项目名修补
	•	围绕固定数字修补
	•	围绕章节标题修补
	•	围绕附件名修补
	•	围绕 Gemini wording 修补

2）你必须把样本现象抽象成通用问题模式

例如：
	•	危险环境事实抽取不足
	•	起重吊装事实与规则命中链不足
	•	工期-资源-工序冲突推理不足
	•	visibility gap 与附件缺失混淆
	•	clause applicability / evidence gap 闭环不足

而不是直接写：
	•	因为这里出现"煤气区域"
	•	因为这里出现"50t 汽车吊"
	•	因为这里出现"7 天""37 人"
	•	因为某个附件名缺失
	•	因为某个标题重复

3）Gemini 只能作为差距探针

Gemini deepresearch 在本研究中只能用作：
	•	对照基线
	•	差距探针
	•	candidate issue inventory
	•	seed reference

不能用作：
	•	gold truth
	•	最终仲裁者
	•	prompt 答案库
	•	style target

4）你必须优先保护"可信度"而非"追分"

当证据不足、visibility 受限、PDF parserLimited 阻断时，你必须敢于承认：
	•	当前只能判断到某一层
	•	当前不能把某结论升级为 hard defect
	•	当前只能标记为 visibility / evidence gap
	•	当前更适合进入 future adjudication 而不是立即定 truth

⸻

你必须使用的分析框架：L0 / L1 / L2 / L3

你必须按以下分层组织研究，而不能只平铺比较：

L0：可视域 / parser / 附件 / manual review 触发层

重点分析：
	•	系统看到了什么、没看到什么
	•	V0.0、V0.2、Gemini 在"可视域诚实度"上的差异
	•	PDF / 表格 / 图示 / 附件 / 后半段内容的 visibility 边界
	•	是否把"未解析"误判成"缺失"

优先数据源：structured-review-l0-visibility.json、attachment-visibility-matrix.json

L1：硬规则 / 红线 / 法定程序 / 结构完整性层

重点分析：
	•	文档结构完整性问题识别
	•	法定程序 / 红线问题识别
	•	hard defect 与一般问题的区分
	•	风险升级是否足够稳健

优先数据源：structured-review-rule-hits.json、hazard-identification-matrix.json

L2：条文适用 / policy evidence / rule hit / unresolved facts 层

重点分析：
	•	是否只是"挂规范"
	•	是否形成"条文-事实-结论"闭环
	•	applicability state / evidence gap / unresolved facts 是否真实存在
	•	V0.2 是否比 V0.0 更接近 formal review 语义

优先数据源：structured-review-result.json（issues 字段）、structured-review-facts.json、rule-hit-matrix.json

L3：工程推理 / 冲突分析 / 可操作整改 / enhancement 层

重点分析：
	•	是否能从事实推出工程层冲突与风险
	•	是否能区分 hard defect 与 enhancement
	•	Gemini 是否主要领先在这一层
	•	V0.2 在这一层到底是起步、半落地，还是仍显著偏弱

优先数据源：conflict-matrix.json、structured-review-candidates.json

⸻

你必须完成的研究动作

对于每个样本、每一层对比，你都必须至少完成以下动作：
	1.	识别差异
	•	V0.0 有什么
	•	V0.2 有什么
	•	Gemini 有什么
	2.	判断差距性质
	•	真能力差距
	•	结构化表达差距
	•	文风差距
	•	visibility 边界差距
	•	evidence 链差距
	3.	判断差距归因
	•	parser
	•	facts
	•	rules
	•	evidence
	•	workflow
	•	eval
	•	report only
	4.	做 anti-overfit 初判
	•	这是通用问题模式，还是样本特例
	•	若后续直接据此做优化，是否有高过拟合风险

⸻

你必须输出的文档定位

你的输出不是：
	•	实施计划
	•	PR 拆解
	•	边界声明
	•	差距裁决清单
	•	internal-reviewed adjudication notes

你的输出是：

《三角对比研究结果》
即：后续三份治理文档共同依赖的"研究底稿"。

⸻

你必须输出的文档结构

你的最终输出必须至少包含以下章节，并按顺序组织：

⸻

0. 文档定位

说明：
	•	这不是治理裁决文档
	•	这不是实施任务书
	•	这不是 internal-reviewed truth
	•	这是后续治理文件共同依赖的"三角对比研究底稿"

⸻

1. 证据范围与研究边界

说明：
	•	本文使用了哪些仓库事实（第 1 层：系统边界真相源）
	•	本文使用了哪些 research pack 结构化工件（第 2 层：样本级结构化证据源）
	•	本文参考了哪些 Markdown 报告（第 3 层：人类可读呈现层）
	•	Gemini 在本文中的地位是什么（第 4 层：seed / candidate reference）
	•	本文是否参考了 latest-eval-summary.md（当前治理状态快照，非长期真相）
	•	本文哪些结论是直接证据
	•	哪些结论是合理推断
	•	本文不能假装裁决到什么程度

⸻

2. 三角对比总表

请给出一张高信息密度总表，对比：
	•	V0.0
	•	V0.2
	•	Gemini

比较维度至少包括：
	•	输出定位
	•	L0 可视域意识
	•	L1 硬规则能力
	•	L2 条文适用链
	•	L3 工程推理
	•	hard defect vs enhancement 区分
	•	evidence / unresolved facts / visibility gap 表达
	•	误报风险
	•	过拟合风险

⸻

3. 样本 A：冷轧厂三角对比研究

至少包括：
	•	源样本关键特征
	•	V0.0 / V0.2 / Gemini 三方差异
	•	L0 / L1 / L2 / L3 分层差异
	•	主要差距归因
	•	anti-overfit 初判

研究时必须优先依据 fixtures/research_inputs/sample-a-cold-rolling/ 下的结构化 JSON 和 matrices。

⸻

4. 样本 B：培花三角对比研究

要求同上。

尤其必须重视：
	•	PDF pdf_text_only
	•	parserLimited
	•	表格 / 图示 / 附图未保留
	•	由此带来的 visibility truth 限制

研究时必须优先依据 fixtures/research_inputs/sample-b-puhua-rainwater/ 下的结构化 JSON 和 matrices。

⸻

5. V0.2 vs V0.2 设计目标：兑现度研究

这一章必须回答：
	•	V0.2 已兑现了什么
	•	半兑现了什么
	•	仍未兑现什么
	•	哪些设计已经进入结果对象层
	•	哪些还停留在文档表述层
	•	当前 V0.2 最接近"结构化审查器"还是"更成熟的辅助审查器"

可参考 latest-eval-summary.md 作为阶段性辅助证据，但不能将其视为永久性结论。

⸻

6. 分层归因：L0 / L1 / L2 / L3

这一章必须按层做总归纳。

每层都必须说明：
	•	V0.2 相比 V0.0 的真实进步
	•	V0.2 相比 Gemini 的核心差距
	•	差距主要归因
	•	哪些更像系统机制问题
	•	哪些只是表达层问题

⸻

7. 反过拟合研究观察

必须单列成章。

至少写清：
	•	哪些问题模式在双样本中都出现，具备通用研究价值
	•	哪些只是样本特有现象
	•	哪些若被直接写成规则会导致过拟合
	•	为什么 Gemini 只能做差距探针
	•	为什么这份研究不能直接被跳译成 patch list

⸻

8. 给后续治理文档的输入清单

这一章非常关键。

你必须明确说明，这份研究结果将如何输入给后续三份文档：

输入给《V0.3 边界声明》的内容

例如：
	•	本轮最值得收敛的边界
	•	哪些能力层最值得优先聚焦
	•	为什么不应扩 official scope
	•	为什么不应把 OCR / 多模态纳入本轮

输入给《V0.2→V0.3 差距裁决与反过拟合约束清单》的内容

例如：
	•	哪些差距已基本确认
	•	哪些差距只能部分确认
	•	哪些方向有高过拟合风险
	•	哪些更适合进 experimental / diagnostics

输入给《双样本人工复核裁决稿》的内容

例如：
	•	哪些条目适合 future internal-reviewed
	•	哪些条目更像 visibility truth
	•	哪些条目当前证据不足
	•	哪些条目不能让 Gemini 直接决定

⸻

9. 最终研究结论

最后用高密度语言概括：
	•	V0.2 是否相对 V0.0 构成代际升级
	•	V0.2 与 Gemini 的核心差距是什么
	•	当前系统最准确的定位是什么
	•	后续治理最该先抓什么
	•	最不能犯的错误是什么
	•	为什么 anti-overfit 必须前置

⸻

输出风格要求

你的输出必须满足以下要求：
	1.	极度具体
不能只说"还有差距""需要加强"，必须说清楚：
	•	差距是什么
	•	在哪一层
	•	由什么导致
	•	是否具备通用价值
	2.	极度诚实
	•	不要把推断说成证据
	•	不要把个案说成泛化
	•	不要把 Gemini 说成真理
	•	不要把 V0.2 说得比实际更成熟
	3.	结构化
	•	章节清晰
	•	层次清晰
	•	最好有高信息密度总表
	•	要让后续文档能直接消费你的研究结论
	4.	系统导向，不是文风导向
重点放在：
	•	parser
	•	facts
	•	rules
	•	evidence
	•	workflow
	•	eval
而不是"像不像专家"
	5.	anti-overfit 优先
你必须始终牢记：
	•	本研究不是为了帮助系统在两份样本上考高分
	•	本研究是为了帮助系统形成更稳的通用审查能力
	6.	结构化工件优先
你的差距分析必须优先依据 research pack 中的 JSON / matrices，而非仅凭 Markdown 报告文案做定性判断。

⸻

你最后必须自查的 10 件事

在完成文档前，请逐条确认：
	1.	我是否明确把本文写成"三角对比研究底稿"，而不是治理文档？
	2.	我是否同时比较了 V0.0 / V0.2 / Gemini 三方？
	3.	我是否单独做了 V0.2 vs V0.2 设计目标的兑现度研究？
	4.	我是否明确使用了 L0 / L1 / L2 / L3 分层？
	5.	我是否把主要差距归因到了 parser / facts / rules / evidence / workflow / eval？
	6.	我是否明确说明了 Gemini 不是 gold truth？
	7.	我是否单列了 anti-overfit 观察？
	8.	我是否区分了通用问题模式与样本特例？
	9.	我是否说明了这份研究如何输入给后续三份治理文档？
	10.	我是否避免把双样本表面词语直接写成通用规则建议？
	11.	我的差距分析是否优先依据了 research pack 中的结构化 JSON / matrices，而非仅凭 Markdown？
	12.	我是否在"证据范围与研究边界"章节中说明了四层证据层级？

如果以上任一项没有满足，请继续完善，而不是提前结束。

⸻

最终目标一句话

请产出一份：

与当前仓库事实一致、优先消费 research pack 结构化工件、基于双样本与 V0.0/V0.2/Gemini 三方对比、显式按 L0/L1/L2/L3 分层、以 anti-overfit 为核心约束、并可直接作为后续三份治理文档共同上游输入的《三角对比研究结果》完整底稿。
