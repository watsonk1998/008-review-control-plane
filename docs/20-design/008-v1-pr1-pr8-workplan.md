> [!NOTE]
> **本文档职责**
> - 负责：
>   - 将 V1 实施骨架拆分为 PR1–PR8 的执行序列与任务边界
> - 不负责：
>   - 不替代产品定义、能力边界、验收标准
>   - 不直接构成最终发布说明
> - 主适用读者：
>   - 架构负责人、研发负责人、实施执行者
> - 冲突处理：
>   - 若与 `docs/20-design/008-v1-implementation-skeleton.md` 冲突，以后者为上位设计依据
> - 文档状态：
>   - 执行拆分骨架

---


⸻

第 25 章展开版：PR1–PR8 任务书骨架

总原则

25.0.1 拆分原则

PR 拆分按“能力脊柱”进行，不按文件堆砌进行。
每个 PR 必须同时回答 5 个问题：
	1.	改了哪一段产品主链
	2.	锁了哪一类 contract
	3.	新增了哪类可测行为
	4.	避免了哪种越界风险
	5.	为后续哪个 PR 提供前置条件

25.0.2 PR 顺序原则

推荐顺序固定为：
	•	PR1：contract spine
	•	PR2：visibility / preflight spine
	•	PR3：facts / basis / applicability spine
	•	PR4：issue assembly spine
	•	PR5：severity / blocked / major-hazard spine
	•	PR6：report / artifact / reviewer workflow spine
	•	PR7：eval / gold / expert scoring spine
	•	PR8：support-scope / promotion / governance spine

25.0.3 每个 PR 的统一交付结构

每个 PR 必须包含：
	•	目标
	•	范围
	•	非目标
	•	核心改造点
	•	数据契约
	•	流程变化
	•	测试要求
	•	验收口径
	•	风险与回滚点
	•	后续依赖

⸻

PR1 — Contract Spine

25.1.1 目标

建立 V1 的最小正式 contract 脊柱，把后续所有实现统一到同一套产品对象上，避免“实现先行、语义漂移”。

25.1.2 本 PR 解决的问题

当前系统已经有 structured_review 输出，但 V1 需要把以下对象收敛为稳定 contract：
	•	structured_review task input
	•	structured_review task output
	•	issue 三分法
	•	evidence / basis / visibility / unresolvedFacts
	•	reviewer decision 最小结构
	•	governance signal 占位

25.1.3 本 PR 范围

应至少定义并统一：
	•	task input DTO
	•	task output DTO
	•	issue 顶层结构
	•	formal / candidate / blocked 三类 issue 状态
	•	evidenceRefs / basisRefs / applicabilityState / blockingReasons
	•	unresolvedFacts 顶层结构
	•	visibility 顶层结构占位
	•	reviewer decision 顶层结构占位

25.1.4 非目标

本 PR 不负责：
	•	复杂规则命中
	•	parser 行为优化
	•	工艺问题生成质量
	•	详细 UI
	•	promotion 自动化

25.1.5 核心改造点
	•	统一 domain model / schema
	•	清理语义重复字段
	•	明确 canonical 字段名
	•	明确哪些字段必须有，哪些允许为空
	•	给后续 PR 留稳定扩展点

25.1.6 必须锁定的 contract

A. Issue Contract
	•	issueId
	•	issueType
	•	issueStatus
	•	issueSeverity
	•	title
	•	judgment
	•	recommendation
	•	evidenceRefs
	•	basisRefs
	•	applicabilityState
	•	blockingReasons
	•	reviewerHints

B. Visibility Contract
	•	parseMode
	•	parserLimited
	•	parseWarnings
	•	preflightStatus
	•	manualReviewReason

C. Unresolved Facts Contract
	•	factKey
	•	description
	•	whyNeeded
	•	howToVerify
	•	affectedIssueIds

25.1.7 测试要求
	•	contract serialization / validation tests
	•	backward compatibility policy tests（如保留兼容层）
	•	status enum 合法性测试
	•	缺字段时的 fail-fast 或 graceful behavior 测试

25.1.8 验收口径

通过标准：
	•	所有 structured_review 输出都能落到统一 contract
	•	formal / candidate / blocked 语义清晰
	•	visibility 是 top-level canonical 对象
	•	unresolvedFacts 是 top-level canonical 对象

25.1.9 风险
	•	字段名反复改动导致后续 PR 全线返工
	•	status / severity 混写
	•	contract 过重，阻碍落地

25.1.10 后续依赖

PR2–PR8 全部依赖 PR1 的 contract 脊柱。

⸻

PR2 — Visibility / Preflight Spine

25.2.1 目标

把“系统看到了什么、没看到什么、这些缺口如何影响判断”变成 formal-review 主链的前置显式环节。

25.2.2 本 PR 解决的问题
	•	parser 受限信息未被产品化表达
	•	“不可见”容易被误写成“缺失”
	•	preflight gate 不够显式
	•	manual review trigger 缺统一语义

25.2.3 本 PR 范围
	•	parse & preflight runtime
	•	visibility object 填充
	•	parser warnings 分类
	•	attachment / table / image visibility 占位
	•	blocking hint 初步下传
	•	manualReviewReason 触发规则

25.2.4 非目标
	•	不解决高质量表格解析
	•	不引入 OCR/多模态
	•	不做复杂 issue 生成

25.2.5 核心改造点
	•	先看清再下判
	•	将 parse limitations 变成产品对象
	•	parser-limited 场景强制可见化
	•	为 blocked issue 提供前置信号

25.2.6 流程变化

新增或强化：
	1.	input normalization 后
	2.	parse visibility scan
	3.	preflight assessment
	4.	manual review trigger
	5.	downstream blocking hints

25.2.7 测试要求
	•	parser-limited sample tests
	•	attachment not visible tests
	•	table/image not visible tests
	•	“不可见 ≠ 缺失” regression tests
	•	preflightStatus 决策测试

25.2.8 验收口径

通过标准：
	•	受限场景下 visibility 信息稳定输出
	•	manualReviewReason 与 parseWarnings 不再散落
	•	下游可依赖 visibility 做 blocked/candidate 降级

25.2.9 风险
	•	visibility 只停留在日志层
	•	下游模块无视 preflight 信号
	•	parser 警告表达过粗

25.2.10 后续依赖

PR3、PR5、PR6、PR7 强依赖本 PR。

⸻

PR3 — Facts / Basis / Applicability Spine

25.3.1 目标

建立 formal-review 的中间语义层：
把“文本内容”转成“事实对象”，把“规范候选”转成“适用状态”。

25.3.2 本 PR 解决的问题
	•	facts 抽取零散
	•	basis 只是引用，不是适用判断
	•	applicability 缺统一状态机
	•	A 类 / B 类问题未在中间层分流

25.3.3 本 PR 范围
	•	facts extraction 最小骨架
	•	basis candidate binding
	•	applicability state machine
	•	blocked_by_missing_fact 形成
	•	A 类 / B 类问题的中间层差异表达

25.3.4 非目标
	•	不做最终 issue 文案
	•	不做复杂合并去重
	•	不做最终严重度裁决

25.3.5 核心改造点
	•	facts 成为一等对象
	•	basis 与 issue 之间增加 applicability bridge
	•	缺关键事实时，不进入正式成立

25.3.6 建议输出对象
	•	fact records
	•	basis candidate records
	•	applicability decisions
	•	missingFactKeys
	•	blockedByFact state

25.3.7 测试要求
	•	fact extraction schema tests
	•	basis mapping tests
	•	applicability enum tests
	•	blocked_by_missing_fact tests
	•	A 类 / B 类路径差异测试

25.3.8 验收口径

通过标准：
	•	对 formal-review 主链而言，facts / basis / applicability 不再是隐式文本
	•	能稳定表达“候选适用”“已适用”“被事实阻塞”“需人工复核”

25.3.9 风险
	•	applicability 粒度过细导致难用
	•	facts schema 过宽导致后续混乱
	•	B 类问题被强行规则化

25.3.10 后续依赖

PR4、PR5、PR7 依赖本 PR。

⸻

PR4 — Issue Assembly Spine

25.4.1 目标

把 facts / basis / applicability / evidence 装配成 V1 的核心产品对象：issue。

25.4.2 本 PR 解决的问题
	•	输出仍接近散点评论
	•	formal / candidate / blocked 未被产品化
	•	A 类 / B 类结果混流
	•	去重/归并缺统一策略

25.4.3 本 PR 范围
	•	deterministic issue assembly
	•	heuristic candidate assembly
	•	blocked issue assembly
	•	merge / dedupe 最小机制
	•	issue-level reviewer hints 生成

25.4.4 非目标
	•	不做最终严重度升级规则
	•	不做完整报告格式
	•	不做专家操作界面

25.4.5 核心改造点
	•	issue 成为正式初稿的核心单位
	•	审查意见级粒度落地
	•	candidate 与 formal 不再共用同一语义层

25.4.6 模型边界

允许模型参与：
	•	title 清洗
	•	recommendation 组织
	•	candidate merge
不允许模型参与：
	•	直接把 candidate 升为 formal
	•	在 basis/evidence 不足时补全结论

25.4.7 测试要求
	•	issue assembly tests
	•	formal / candidate / blocked separation tests
	•	merge / dedupe tests
	•	no-evidence formalization prevention tests

25.4.8 验收口径

通过标准：
	•	输出已明显从“评论列表”转为“问题项系统”
	•	每个 formal issue 满足最小合同前四项
	•	blocked issue 与 candidate issue 区分清楚

25.4.9 风险
	•	issue 粒度过碎
	•	merge 过度导致问题被吞
	•	candidate 写成正式措辞

25.4.10 后续依赖

PR5、PR6、PR7 依赖本 PR。

⸻

PR5 — Severity / Blocked / Major-Hazard Spine

25.5.1 目标

建立问题状态与严重度的正式判定脊柱，特别是把“重大隐患双命中”落成系统约束。

25.5.2 本 PR 解决的问题
	•	severity 与 status 易混
	•	major hazard 容易被模型越权升级
	•	evidence 不足时缺统一降级逻辑
	•	parser-limited 场景降级策略未制度化

25.5.3 本 PR 范围
	•	severity enum
	•	status enum
	•	major hazard eligibility gate
	•	blocked / candidate downgrade logic
	•	manual review escalation rules

25.5.4 非目标
	•	不负责更好写报告
	•	不负责新增场景覆盖
	•	不负责完整 reviewer UI

25.5.5 核心改造点
	•	重大隐患必须双命中
	•	证据不足优先降级 status
	•	blocked/candidate 成为正式系统行为，不是写作修饰

25.5.6 关键规则

A. 重大隐患成立

必须同时具备：
	•	rule hit
	•	visible evidence
	•	closed critical facts

B. 不满足时

只能输出：
	•	candidate-high
	•	suspected major hazard
	•	blocked
	•	manual_review_required

25.5.7 测试要求
	•	major hazard gating tests
	•	severity/status combination tests
	•	downgrade tests
	•	parser-limited escalation prevention tests

25.5.8 验收口径

通过标准：
	•	系统不能再轻易把高风险推断写成重大隐患成立
	•	blocked / candidate / formal 与 severity 协同一致
	•	major hazard 双命中成为真实 gate

25.5.9 风险
	•	severity 设计过于复杂
	•	状态机分支过多
	•	manual review 触发泛化过度

25.5.10 后续依赖

PR6、PR7、PR8 依赖本 PR。

⸻

PR6 — Report / Artifact / Reviewer Workflow Spine

25.6.1 目标

把 formal-review 的核心结果变成“可复核初稿”和“可操作 artifact”，并打通专家最小闭环。

25.6.2 本 PR 解决的问题
	•	输出还停留在技术结构，不利于专家复核
	•	issue 与 evidence / blocked / unresolvedFacts 的阅读路径不够清楚
	•	reviewer 动作缺稳定落点

25.6.3 本 PR 范围
	•	reportMarkdown 模板
	•	artifactIndex 组织
	•	evidence matrix 占位
	•	unresolved facts list
	•	reviewerPreparation 生成
	•	reviewer decision persistence 最小闭环

25.6.4 非目标
	•	不做完整前端重构
	•	不做复杂协同工作流
	•	不做官方 promotion 决策

25.6.5 核心改造点
	•	报告服务复核，不服务炫技
	•	结构优先于文风
	•	reviewer action 最小闭环可追溯

25.6.6 主要产物
	•	structured report markdown
	•	issue list artifact
	•	visibility summary
	•	unresolved facts artifact
	•	reviewer preparation artifact

25.6.7 reviewer 最小动作
	•	confirm / reject
	•	severity adjust
	•	basis/evidence supplement
	•	mark blocked / manual review

25.6.8 测试要求
	•	report artifact generation tests
	•	reviewer action persistence tests
	•	issue-to-report consistency tests
	•	blocked/candidate/report visibility tests

25.6.9 验收口径

通过标准：
	•	专家能看懂正式问题、候选问题、阻塞问题
	•	报告不再掩盖不确定性
	•	reviewer action 有留痕对象

25.6.10 风险
	•	过度追求报告美观
	•	artifact 与 issue contract 脱节
	•	reviewer action 只写回文本，不写回结构

25.6.11 后续依赖

PR7、PR8 依赖本 PR。

⸻

PR7 — Eval / Gold / Expert Scoring Spine

25.7.1 目标

建立 V1 的正式评测主链，让系统改造与验收口径、gold 样本、专家打分表接上。

25.7.2 本 PR 解决的问题
	•	改造缺统一可测出口
	•	expert adoptability 无系统记录
	•	redline errors 无稳定判定
	•	ready / official 晋升缺证据基础

25.7.3 本 PR 范围
	•	eval case schema
	•	gold schema
	•	redline error schema
	•	metric aggregation
	•	expert scoring form integration
	•	versioned cases / baseline reports

25.7.4 非目标
	•	不做最终 governance 审批流
	•	不自动决定 official
	•	不解决所有评测阈值争议

25.7.5 核心改造点
	•	product metrics 接线
	•	expert adoptability 正式入表
	•	hard defects / wrong citation / parser dishonesty 成为硬指标

25.7.6 必测指标
	•	hard defect stable hit rate
	•	expert adoptability
	•	wrong citation rate
	•	evidence closure rate
	•	blocked issue detection accuracy
	•	parser-limited false-formal rate

25.7.7 必测红线
	•	系统性错引规范
	•	系统性把不可见写成确定
	•	parser-limited 强出正式结论
	•	模型单独决定重大隐患
	•	formal/candidate/blocked 混写

25.7.8 测试要求
	•	gold-driven eval tests
	•	regression suite
	•	expert scoring data capture tests
	•	redline detection tests

25.7.9 验收口径

通过标准：
	•	每个关键模块都有明确可测项
	•	case / gold / metric / expert review 形成闭环
	•	ready/official 讨论有证据，不再只是主观印象

25.7.10 风险
	•	gold 粒度过粗
	•	专家评分过度主观
	•	metric 过多难维护

25.7.11 后续依赖

PR8 强依赖本 PR。

⸻

PR8 — Support-Scope / Promotion / Governance Spine

25.8.1 目标

把 V1 的能力边界、成熟度分层与晋升治理正式落到系统和文档口径中。

25.8.2 本 PR 解决的问题
	•	ready / official / experimental 容易被口头使用
	•	promotionCriteria 缺统一生成逻辑
	•	对外口径与内部真实能力可能脱节

25.8.3 本 PR 范围
	•	support-scope 数据结构
	•	official / ready / experimental / candidate 状态管理
	•	promotionCriteria 产物汇总
	•	governance evidence snapshot
	•	capability state change 留痕
	•	docs / API / artifacts 的能力声明接线

25.8.4 非目标
	•	不做组织审批系统全集成
	•	不取代人工治理判断
	•	不做销售侧流程系统

25.8.5 核心改造点
	•	ready ≠ official 真正制度化
	•	promotion 需要证据快照
	•	边界声明与系统状态一致

25.8.6 必备治理产物
	•	capability maturity state
	•	promotion evidence pack
	•	redline error summary
	•	expert review summary
	•	approval status placeholder

25.8.7 测试要求
	•	support-scope output tests
	•	promotion evidence generation tests
	•	capability state transition tests
	•	docs/api consistency tests

25.8.8 验收口径

通过标准：
	•	系统能清晰表达什么是 official、什么只是 ready
	•	promotionCriteria 不再只是说明文，而是系统产物
	•	内外口径一致，减少伪成熟风险

25.8.9 风险
	•	governance 字段有名无实
	•	证据快照不能追溯
	•	ready 继续被误包装

25.8.10 完成标志

PR8 完成后，V1 才算具备“可治理的正式能力边界”，而不只是“能跑的主链”。

⸻

跨 PR 约束

25.9.1 全程红线

所有 PR 都必须遵守：
	•	不允许模型凭经验补齐不可见事实
	•	不允许模型单独决定重大隐患成立
	•	不允许模型在证据不足时生成看似完整的正式结论
	•	不允许把 parser 受限写成文档缺失
	•	不允许把 ready 包装成 official

25.9.2 每个 PR 的文档义务

每个 PR 都必须同步更新：
	•	变更摘要
	•	contract 变化说明
	•	测试与评测影响
	•	是否触及边界声明
	•	是否影响 promotion 口径

25.9.3 每个 PR 的验证义务

每个 PR 必须附带：
	•	unit tests
	•	integration tests
	•	至少一个相关 eval case 触点
	•	回归风险说明

⸻

推荐执行顺序说明

25.10.1 为什么先 PR1 再 PR2

没有 contract，就没有 visibility 的稳定落点。

25.10.2 为什么 PR3 在 PR4 前

没有 facts / basis / applicability，中间层不成立，issue assembly 只能继续拼文案。

25.10.3 为什么 PR5 在 PR6 前

不先锁状态与严重度，报告层一定会偷渡伪确定性。

25.10.4 为什么 PR7 在 PR8 前

没有评测与 gold，治理只能靠口头判断，无法支撑 official 晋升。

⸻

最终交付判断

25.11.1 PR1–PR4 完成代表什么

系统已具备 formal-review 对象脊柱，但还不一定具备正式治理能力。

25.11.2 PR5–PR6 完成代表什么

系统已具备 可复核初稿主链，专家可以在结构化结果上工作。

25.11.3 PR7–PR8 完成代表什么

系统已具备 可测、可审、可晋升 的产品级能力闭环。

⸻
