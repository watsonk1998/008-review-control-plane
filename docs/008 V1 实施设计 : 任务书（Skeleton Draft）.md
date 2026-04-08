
⸻

《008 V1 实施设计 / 任务书（Skeleton Draft / PRD Pending Lock）》

0. 文档信息

0.1 文档名称

《008 V1 实施设计 / 任务书（Skeleton Draft / PRD Pending Lock）》

0.2 文档目标

将《008 Validate PRD v1》中的已锁定产品裁决，翻译为可实施的系统骨架、数据契约、流程改造面、评测接线与治理任务拆分。

0.3 文档状态

Skeleton Draft
	•	允许作为实施起点
	•	不等于最终锁定设计
	•	不得将“待锁定项”视为既定事实

0.4 适用范围

适用于 008 V1 的：
	•	formal-review 主链改造
	•	issue contract 落地
	•	visibility / evidence / blocking spine 落地
	•	reviewer workflow 落地
	•	eval / promotion / governance 接线

0.5 不包含内容

本文档不直接锁定：
	•	最终 UI 交互细节
	•	最终量化阈值
	•	最终问题族优先级排序
	•	V1.x 路线图节奏
	•	全量 PR 文本

⸻

1. 输入前提与上位文档

1.1 上位产品前提

引用并承接：
	•	《008 Validate PRD v1》
	•	《008 V1 能力边界声明》
	•	《008 V1 评测与验收口径》

1.2 本文档默认已锁定前提
	•	008 是面向审查专家的正式结构化审查初稿生产系统
	•	首要用户为审查专家
	•	A 类 / B 类审查对象二分法
	•	正式问题 / 候选问题 / 阻塞问题三分法
	•	重大隐患双命中
	•	parser-limited 降级输出
	•	ready ≠ official
	•	模型三条硬边界

1.3 本文档待锁定前提
	•	首批主战场的最终命名
	•	首批问题族最终优先级
	•	official 晋升的具体阈值
	•	专家可采用率目标值
	•	各映射场景的最终切分方式

⸻

2. 实施总目标

2.1 V1 落地总目标

把 PRD 中“正式结构化审查初稿生产系统”的产品定义，落成一个可运行、可测试、可复核、可晋升的 formal-review 主链。

2.2 六条实施主轴
	•	contract spine
	•	structured issue pipeline
	•	evidence / visibility spine
	•	reviewer workflow
	•	evaluation & gold
	•	governance & promotion

2.3 本轮不追求目标
	•	全行业全面覆盖
	•	大规模多模态联审
	•	复杂前端体验先行
	•	以更像专家文风为主目标
	•	未锁定主战场前的过度场景扩展

⸻

3. 范围定义

3.1 已锁定实施范围
	•	formal-review 主链
	•	issue schema 最小合同
	•	evidence / visibility / blocking 结构
	•	parser 受限降级逻辑
	•	reviewer action 最小闭环
	•	eval case / gold / promotion spine

3.2 暂定实施范围
	•	首批工作单元与问题族的具体映射
	•	场景 pack 的优先级
	•	报告呈现层格式优化
	•	特定 issue 类别的细粒度层级

3.3 明确不在本轮范围
	•	全量图纸审查
	•	OCR-first 多模态方案
	•	多文档联审主流程
	•	全量行业规范自动化适配
	•	广泛的 doc type 扩张

⸻

4. 当前现状与差距总览

4.1 仓库当前能力现状摘要
	•	review control plane 已成型
	•	structured_review 已存在正式结构化结果主链
	•	review_assist 仍并存
	•	official documentType 收敛
	•	scenario pack 存在 ready / placeholder 分层
	•	support-scope / promotionCriteria 已具备基础治理信号

4.2 当前主要差距
	•	issue contract 仍需统一收敛
	•	facts / rules / evidence / applicability 的桥接需更硬
	•	parser 受限与“文档缺失”的边界需更严
	•	reviewer workflow 仍需从“可用”升级为“产品主闭环”
	•	评测集、gold、专家打分表尚需系统化

4.3 本轮改造总判断

V1 应以“contract spine + issue pipeline + eval governance”做主脊柱，禁止走“加更多场景再说”的扩张路径。

⸻

5. 总体架构实施视图

5.1 实施总图（章节占位）
	•	Input Layer
	•	Parse / Visibility Layer
	•	Facts Layer
	•	Rules / Applicability Layer
	•	Issue Assembly Layer
	•	Severity / Status Layer
	•	Report / Artifact Layer
	•	Reviewer Workflow Layer
	•	Eval / Governance Layer

5.2 模块边界
	•	domain models
	•	review runtime
	•	parser / loader
	•	policy pack / rule pack
	•	issue synthesis
	•	report generation
	•	reviewer decision
	•	eval harness
	•	promotion support

5.3 待补：ASCII 总图

（占位，待后续锁定）

⸻

6. 数据契约设计总览

6.1 设计原则
	•	最小合同优先
	•	产品字段优先于实现便利
	•	候选 / 正式 / 阻塞状态不可混写
	•	可视域是一等对象
	•	reviewer action 可留痕
	•	promotion evidence 可落地

6.2 契约分层
	•	task input contract
	•	task output contract
	•	issue contract
	•	evidence contract
	•	visibility contract
	•	unresolved facts contract
	•	reviewer decision contract
	•	eval case contract
	•	promotion contract

6.3 契约状态说明格式

每个契约都按三栏表达：
	•	已锁定
	•	暂定
	•	待 PRD 最终锁定

⸻

7. Task 输入 / 输出契约

7.1 输入契约
	•	document reference
	•	document type
	•	review mode
	•	pack / scenario selection
	•	context metadata
	•	review intent

7.2 输出契约
	•	summary
	•	visibility
	•	issues
	•	matrices
	•	artifactIndex
	•	reportMarkdown
	•	unresolvedFacts
	•	reviewerPreparation
	•	governanceSignals

7.3 待锁项
	•	输出字段命名最终版
	•	matrices 的 V1 最小保留范围
	•	governanceSignals 的最终字段集

⸻

8. Issue Contract 设计

8.1 Issue 顶层结构
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

8.2 三类 issue
	•	formal issue
	•	heuristic candidate
	•	blocked issue

8.3 正式问题项最小合同
	•	facts
	•	basis
	•	judgment
	•	severity/status
	•	review/remediation hint

8.4 候选问题项最小合同
	•	candidate observation
	•	trigger reason
	•	missing facts
	•	review direction

8.5 阻塞问题项最小合同
	•	possible basis
	•	missing critical facts
	•	blocking reason
	•	supplement path

8.6 待锁项
	•	issueType 枚举边界
	•	severity 枚举细粒度
	•	recommendation 的 mandatory 程度

⸻

9. Evidence / Basis / Applicability 契约

9.1 Evidence Contract
	•	source
	•	span / locator
	•	visibility state
	•	evidence type
	•	confidence / certainty（若保留）

9.2 Basis Contract
	•	regulation / standard id
	•	clause locator
	•	applicability note
	•	support role

9.3 Applicability Contract
	•	applicable
	•	candidate_applicable
	•	blocked_by_missing_fact
	•	not_applicable
	•	needs_manual_review

9.4 桥接逻辑
	•	basis 如何支撑 judgment
	•	evidence 如何支撑 facts
	•	applicability 如何影响 severity 与 status

9.5 待锁项
	•	clause 粒度标准
	•	applicabilityState 的最终枚举
	•	confidence 是否进入外显 DTO

⸻

10. Visibility / Blocking / Unresolved Facts 契约

10.1 Visibility Contract
	•	parseMode
	•	parseWarnings
	•	parserLimited
	•	attachmentVisible
	•	tableVisible
	•	imageVisible
	•	preflightStatus
	•	manualReviewReason

10.2 Blocking Contract
	•	blockingReason code
	•	impacted issue ids
	•	missing fact keys
	•	recommended supplement action

10.3 Unresolved Facts Contract
	•	factKey
	•	description
	•	why_needed
	•	how_to_verify
	•	affected judgments

10.4 待锁项
	•	visibility 子字段最终清单
	•	parseWarnings 的分类体系
	•	unresolvedFacts 是否区分系统级/issue级

⸻

11. Reviewer Decision 契约

11.1 Reviewer Action 类型
	•	confirm
	•	reject
	•	downgrade
	•	upgrade
	•	reclassify
	•	add_evidence
	•	add_basis
	•	mark_blocked
	•	mark_manual_review

11.2 Reviewer Decision 记录结构
	•	action
	•	target issue
	•	operator
	•	rationale
	•	evidence additions
	•	basis additions
	•	timestamp

11.3 Reviewer Workflow 最小闭环
	•	issue review
	•	severity adjustment
	•	evidence supplement
	•	decision persistence

11.4 待锁项
	•	reviewer 身份模型
	•	前端交互粒度
	•	多轮 review 的合并策略

⸻

12. Eval Case / Gold / Promotion 契约

12.1 Eval Case Contract
	•	caseId
	•	document type
	•	work unit
	•	issue families
	•	visibility conditions
	•	scenario mapping
	•	gold references

12.2 Gold 标注 Contract
	•	hard defects gold
	•	candidate issue gold hints
	•	visibility limitations
	•	allowed basis range
	•	major hazard allowed/disallowed
	•	expected downgrade behavior

12.3 Promotion Evidence Contract
	•	test pass summary
	•	eval metrics snapshot
	•	redline errors
	•	expert review summary
	•	official recommendation status

12.4 待锁项
	•	gold 标注粒度
	•	major hazard gold 口径细节
	•	promotion evidence 的系统落盘方式

⸻

13. Formal Review 主流程设计

13.1 流程总览
	1.	input normalization
	2.	parse & visibility preflight
	3.	facts extraction
	4.	rule / basis applicability
	5.	issue assembly
	6.	severity / status decision
	7.	report + artifacts generation
	8.	reviewer workflow handoff
	9.	eval / governance trace

13.2 每一步的输入输出

（占位，后续展开）

13.3 每一步的失败降级逻辑

（占位，后续展开）

13.4 每一步的可测项

（占位，后续展开）

⸻

14. Parse & Visibility Preflight 设计

14.1 目标

先判断能不能“正式看”，而不是先急着“正式判”。

14.2 关键任务
	•	parse mode 识别
	•	parser limitations 暴露
	•	attachment/table/image visibility 判断
	•	preflight gate 形成
	•	manual review trigger 预判

14.3 输出要求
	•	top-level visibility
	•	parser warnings
	•	preflight status
	•	downstream blocking hints

14.4 禁止事项
	•	把不可视内容默认为不存在
	•	把 parser 失败伪装成 author omission

⸻

15. Facts Extraction 设计

15.1 目标

形成结构化 fact layer，为后续 rule / evidence / issue 装配提供可追溯输入。

15.2 事实类型
	•	project facts
	•	work-condition facts
	•	process facts
	•	control-measure facts
	•	schedule/resource facts
	•	document-structure facts

15.3 A 类 / B 类事实差异
	•	A 类：尽量结构化、可枚举
	•	B 类：允许开放抽取，但必须留证与待核

15.4 待锁项
	•	fact schema 最终枚举
	•	process facts 的标准化粒度

⸻

16. Rules / Basis / Applicability 设计

16.1 目标

把“可能相关的规范”变成“可审计的适用判断”。

16.2 输入
	•	facts
	•	document type
	•	scenario/work-unit hints
	•	rule pack / policy pack

16.3 输出
	•	rule hit
	•	candidate basis
	•	applicability state
	•	blocking by missing fact
	•	major hazard eligibility

16.4 重大隐患双命中接线
	•	rule hit
	•	visible evidence
	•	closed facts
	•	escalation allowed / denied

16.5 待锁项
	•	rule pack 组织方式
	•	clause matching 的最终策略
	•	major hazard escalation policy 细则

⸻

17. Issue Assembly 设计

17.1 目标

把 facts / basis / applicability / evidence 收敛成 issue-level product object。

17.2 装配逻辑
	•	deterministic issue assembly
	•	candidate issue assembly
	•	blocked issue assembly

17.3 去重与归并
	•	same judgment merge
	•	overlapping basis merge
	•	candidate to formal promotion path

17.4 模型参与边界
	•	可参与 title / recommendation / merge
	•	不可单独决定 final formalization

17.5 待锁项
	•	merge 策略细则
	•	issue clustering 的阈值

⸻

18. Severity / Status Decision 设计

18.1 状态枚举
	•	formal
	•	candidate
	•	blocked
	•	manual_review_required

18.2 严重度枚举
	•	major hazard
	•	high
	•	medium
	•	low
	•	candidate-high
	•	blocked

18.3 决策原则
	•	major hazard 需双命中
	•	evidence 缺失优先降级 status，而不是硬保 severity
	•	parser-limited 优先触发 blocked / candidate

18.4 待锁项
	•	severity 细节命名
	•	status 与 severity 的最终组合规则

⸻

19. Report / Artifact Generation 设计

19.1 目标

生成“可复核初稿”，不是生成“看似权威的长文”。

19.2 主要产物
	•	structured report markdown
	•	issue list artifact
	•	evidence matrix
	•	visibility summary
	•	unresolved facts list
	•	reviewer preparation artifact

19.3 报告内容原则
	•	先问题结构，后叙述
	•	先事实/依据，后建议
	•	明示 blocked / candidate / manual review

19.4 待锁项
	•	artifact 文件命名规则
	•	report markdown 模板最终结构

⸻

20. Reviewer Workflow 设计

20.1 目标

让专家“复核生产线化”，而不是“重写一遍”。

20.2 核心动作
	•	confirm / reject
	•	severity adjust
	•	basis adjust
	•	evidence supplement
	•	manual review flagging

20.3 reviewerPreparation 设计
	•	key blocked issues
	•	likely high-risk candidates
	•	supplement checklist
	•	review priorities

20.4 待锁项
	•	UI workflow 粒度
	•	batch actions 设计
	•	review comments 的保留策略

⸻

21. A 类 / B 类双引擎落地设计

21.1 A 类主链
	•	structure/facts extraction
	•	deterministic rules
	•	formal issue preferred
	•	strict evidence closure

21.2 B 类主链
	•	heuristic observation
	•	candidate issue generation
	•	evidence gap explicit
	•	promotion by reviewer / supplement

21.3 两条主链交点
	•	shared facts layer
	•	shared visibility layer
	•	shared issue contract
	•	shared reviewer workflow

21.4 待锁项
	•	B 类 candidate promotion 策略
	•	A/B 混合问题的归类标准

⸻

22. 首批主战场映射设计（占位章）

22.1 工作单元层
	•	高风险工艺完整性审查
	•	高风险工艺冲突审查
	•	高风险工艺可实施性审查

22.2 问题族层
	•	程序触发与边界识别
	•	工艺链条缺口
	•	控制措施缺口
	•	资源与时间窗冲突
	•	空间与作业面冲突
	•	现场落地性不足

22.3 场景映射层
	•	吊装
	•	动火
	•	煤气区域
	•	临时用电
	•	候选：特种设备 / 高处作业

22.4 待锁项
	•	场景最终优先级
	•	首批 official / ready 映射清单
	•	场景 pack 归属边界

⸻

23. Eval / Gold / Acceptance 接线设计

23.1 模块到指标映射
	•	parse 模块对应 visibility/honesty 指标
	•	rule 模块对应 hard defect hit 指标
	•	issue assembly 对应 issue contract 指标
	•	severity 模块对应 major hazard misuse 指标
	•	reviewer workflow 对应 expert adoptability 指标

23.2 必测红线
	•	错引规范
	•	把不可见写成确定
	•	parser-limited 强出正式结论
	•	模型单独决定重大隐患
	•	issue 状态混写

23.3 versioned cases 设计入口

（占位）

23.4 待锁项
	•	各指标阈值
	•	样本规模要求
	•	专家可采用率的目标值

⸻

24. Governance / Promotion 实现设计

24.1 support-scope 接线
	•	official
	•	ready
	•	experimental
	•	candidate

24.2 promotionCriteria 产物
	•	tests
	•	eval metrics
	•	gold coverage
	•	expert review
	•	redline error report

24.3 审批链路
	•	PM
	•	tech lead
	•	expert lead
	•	final approver

24.4 留痕要求
	•	capability state change log
	•	promotion evidence snapshot
	•	boundary statement reference

24.5 待锁项
	•	promotion UI / API 呈现方式
	•	审批状态机细节

⸻

25. 实施拆分策略

25.1 拆分原则
	•	按能力脊柱拆
	•	按 contract-first 拆
	•	按可测性拆
	•	禁止只按文件分散小改

25.2 推荐拆分维度
	•	PR1: contract spine
	•	PR2: visibility / preflight spine
	•	PR3: facts & applicability spine
	•	PR4: issue assembly spine
	•	PR5: severity / blocking / major hazard spine
	•	PR6: report / artifact / reviewer workflow
	•	PR7: eval / gold / expert scoring
	•	PR8: support-scope / promotion / governance

25.3 每个 PR 的最小交付格式
	•	changed contracts
	•	changed runtime behavior
	•	tests
	•	eval touchpoints
	•	docs update

⸻

26. 测试与回归计划

26.1 单元测试
	•	contract validation
	•	rule applicability
	•	status transitions
	•	downgrade paths

26.2 集成测试
	•	end-to-end structured_review
	•	parser-limited downgrade
	•	reviewer action persistence
	•	promotion signals generation

26.3 回归测试
	•	official sample set
	•	ready sample set
	•	negative / redline cases

26.4 待锁项
	•	覆盖率阈值
	•	gold case 数量
	•	回归频率

⸻

27. 交付物清单

27.1 代码交付
	•	updated contracts
	•	runtime modules
	•	tests
	•	eval harness changes

27.2 文档交付
	•	PRD references updated
	•	boundary statement references updated
	•	acceptance spec links updated
	•	support-scope docs updated

27.3 评测交付
	•	case definitions
	•	metric report
	•	redline errors report
	•	expert review summary

27.4 治理交付
	•	promotion recommendation
	•	official/ready state snapshot
	•	unresolved pending items

⸻

28. 风险与反模式

28.1 主要风险
	•	先做场景，后补 contract
	•	用模型润色掩盖证据不足
	•	parser 受限时强出正式结论
	•	ready 被误讲为 official
	•	候选 / 正式 / 阻塞边界失真
	•	过早扩 pack / doc type

28.2 明确反模式
	•	“先把 demo 跑出来再补治理”
	•	“先把所有高风险作业都列出来”
	•	“先放大模型，后补规则”
	•	“先扩文档类型，后补主链”
	•	“先做报告好看，后补 evidence spine”

⸻

29. 待锁定事项清单

29.1 待锁定事项表（模板）
	•	项目
	•	当前状态
	•	候选方案
	•	依赖的 PRD 决策
	•	风险
	•	锁定后动作

29.2 当前待锁重点
	•	工作单元最终命名
	•	问题族优先级
	•	severity 枚举细节
	•	official 晋升阈值
	•	专家可采用率目标
	•	pack 映射最终边界
	•	report 模板最终样式

⸻

30. 启动顺序建议

30.1 可立即启动
	•	contract spine
	•	visibility / preflight spine
	•	issue contract spine
	•	reviewer decision 最小闭环
	•	eval case / gold contract 骨架

30.2 PRD 锁定后再启动
	•	主战场最终 pack 优先级
	•	指标阈值硬编码
	•	official 晋升自动化逻辑
	•	完整报告模板定稿
	•	场景扩展计划

30.3 启动门槛

任何实施动作都不得违反：
	•	三条模型硬边界
	•	重大隐患双命中
	•	parser-limited 降级输出
	•	ready ≠ official

⸻

31. 附录（占位）

31.1 术语表

31.2 schema 示例

31.3 状态机草图

31.4 ASCII 架构图

31.5 PR 拆分草案

31.6 样本 / gold 示例

31.7 reviewer decision 示例

⸻

