````markdown
你现在的角色不是“评论者”或“方案顾问”，而是 **资深技术负责人 + Staff Engineer + 架构师 + 交付经理 + 评测负责人**。  
你的任务不是继续比较 Gemini 与 008-review-control-plane 谁更强，也不是写一篇泛泛的分析报告，而是输出一份 **可以直接指导 Codex 分阶段改造仓库的完整工程任务书**。

---

# 任务目标

请基于我提供的全部材料，输出一份：

# 008-review-control-plane 结构化施组审查能力改造任务书（Codex 执行版）

这份任务书必须达到以下目标：

- **完整**
  - 覆盖背景、现状、目标架构、分阶段路线、文件级改造、测试评测、风险边界、Definition of Done
- **详尽**
  - 不能只讲方向，必须落到模块、文件、对象、接口、流程、评测、验收
- **可执行**
  - Codex 看完后，应能按任务书拆成 PR 并逐步改造仓库
- **增量演进**
  - 不推翻当前 control plane 架构，而是在现有项目之上新增 formal review 的结构化能力
- **可验证**
  - 必须定义测试、评测、回归与验收标准
- **防过拟合**
  - 不能为了这一个冷轧厂样本做 case-specific patch

---

# 你将获得的输入材料

我会提供给你以下内容，请你全部吸收后再输出任务书：

1. `008-review-control-plane` 仓库分支与代码
2. 被审查的原始施组文档
3. Gemini 生成的深度审查结果
4. 当前 008 项目生成的审查结果
5. 一份人类分析结论与改造建议（指出当前 008 更像 review control plane / 审查辅助总结器，而不是 formal reviewer）

你必须在输出中**绑定这些实际材料**，优先引用真实文件路径、真实模块、真实代码职责，不要凭空虚构一个完全不同的系统。

---

# 你必须遵守的核心原则（非协商）

## 1）不要把 008 粗暴改造成“另一个新系统”
- 008 当前是 control plane / orchestration 项目
- 改造必须优先采用 **增量演进**
- 必须保留现有平台价值：
  - 任务入口
  - 编排能力
  - adapter 边界
  - artifact 机制
  - runtime / planner / router 等基础设施
- 可以新增 review 子域与 formal review 能力，但不要推倒重来

## 2）保留 `review_assist`，新增真正的 `structured_review`
- 不要继续让 `review_assist` 承担正式审查期待
- 必须建议新增 `structured_review` task type
- `review_assist` 继续做辅助总结 / 审查辅助
- `structured_review` 承担正式结构化审查能力

## 3）不能把“系统没看到”误判成“文档没有”
必须显式区分：
- 文档真实缺失
- 当前解析链路未读到
- 图片 / 图纸 / 附件存在但未解析
- 需要人工复核

任务书中必须引入并使用类似概念：
- `visibility_gap`
- `attachment_unparsed`
- `evidence_missing`
- `manual_review_needed`

## 4）不能靠伪改进假装解决问题
必须明确反对以下做法：
- 只换更大模型
- 只加更长 prompt
- 只把输出文风改成 L1/L2/L3
- 只增加上下文长度
- 为当前案例硬编码若干特征
- 把建议性工程优化伪装成强制性缺陷

## 5）正式审查能力必须建立在结构化流水线之上
不要把“正式审查”写成一个大 prompt。  
必须围绕以下流水线设计：

**文档解析层 → 事实抽取层 → 规则命中层 → 证据归档层 → LLM 解释层 → 报告组装层**

## 6）P0 不是“换模型”或“优化检索”
真正的 P0 必须是：
- 结构化抽取
- 规则命中
- 证据归档
- 可视域管理
- 最小可用的 formal review 路径

## 7）必须显式防止单案例过拟合
任务书必须专门写一节：
- 哪些做法会导致对冷轧厂样本过拟合
- 哪些规则应抽象成可复用 pack
- 哪些建议属于工程增强建议，不能伪装成硬缺陷

---

# 你必须吸收并转译的核心判断

你在输出任务书时，必须吸收并转译以下判断，不要只是复述，要把它们转化成工程方案：

1. 当前 008 的定位更接近 **review control plane**，不是 formal reviewer
2. 当前 `review_assist` 更像 **辅助审查总结**
3. 差距主要不在“模型强弱”，而在：
   - 输入可视域
   - 文档解析降维
   - 真正参与推理的上下文太少
   - 缺乏字段抽取
   - 缺乏规则命中
   - 缺乏 issue schema / evidence schema
   - 缺乏正式评测体系
4. 当前系统能抓到一些显性缺陷，但不足以稳定覆盖：
   - L1 法定程序问题
   - L2 规范适用深度
   - L3 工程推理与现场闭环
5. 改造目标不是“复制 Gemini”，而是把 008 升级成：
   - **可扩展的结构化审查底座**
   - **支持 formal review pack 的运行时平台**
   - **可解释、可评测、可回归的工程审查系统**

---

# 必须逐项落地的约束清单（不得泛化带过）

## 一、正式审查流水线必须明确写成以下六层
- 文档解析层
- 事实抽取层
- 规则命中层
- 证据归档层
- LLM 解释层
- 报告组装层

并且对每一层都必须说明：
- 输入是什么
- 输出是什么
- 与上下游如何衔接
- 哪些判断由确定性逻辑完成
- 哪些判断才允许交给 LLM

## 二、标准化评测样本池，至少覆盖以下文档/专业类型
- 施工组织设计
- 一般施工方案
- 危大专项方案
- 监理规划 / 审查辅助材料
- 机电安装类
- 土建类
- 钢结构类
- 临电类
- 起重吊装类

任务书必须把上述样本池覆盖目标写成明确建设要求，不得只写一句“建立评测集”。

## 三、评测指标至少包括以下项目，并逐项解释含义
- 问题召回率：是否找到标注问题
- 重大问题命中率：尤其是 L1 / 重大事故隐患
- 危大识别命中率：是否识别危大工程、是否要求专项方案
- 依据引用准确率：条文是否适用、引用是否正确
- 硬证据准确率：直接可证问题的误报 / 漏报
- 工程推断率与过度推断率：推断是否合理、是否越界
- 严重度校准准确性：L1/L2/L3 或 high/medium/low 是否合适
- 建议可执行性：整改建议是否能落地
- 可解释性评分：问题—证据—依据—建议链是否完整
- 附件可视域正确率：“缺失”与“未解析”是否区分正确

## 四、评测方法至少包括以下维度
- 端到端评测
- 模块级消融（parser / retriever / rule engine / LLM / report builder）
- 跨模型对照
- 跨 pack 对照

## 五、分阶段路线图必须至少包含以下内容

### P0：必须先做
#### P0-1：把“辅助审查”与“正式审查”分开
- 新增 `structured_review`
- 不要继续让 `review_assist` 承担正式审查期待

#### P0-2：升级输入解析与可视域管理，至少解决
- 章节 / 表格保留
- 附件 / 图纸可见性标记
- 重复内容清洗
- 不再只靠 4000 / 24000 / 15000 截断后的文本前缀

#### P0-3：建立最小可用的规则核，优先覆盖
- 施组结构完整性
- 危大识别
- 重大隐患初筛
- 附件可视域
- 应急预案针对性
- 工期 / 资源基础冲突

### P1：很重要
- P1-1：引入 policy pack / evidence pack / issue schema，把规则、依据、输出解耦
- P1-2：实现 L1/L2/L3 分层审查流程（L1 硬规则优先，L2 规范适用，L3 工程推理补强）
- P1-3：建立标准化评测集，不再只看单一样本
- P1-4：做 report builder 和中间矩阵，让输出从 Markdown 升级成可复核产物

### P2：优化项
- P2-1：增强工程推理能力（资源-工序仿真、风险升级、交叉作业冲突分析）
- P2-2：增强多模态文档理解（图纸、总平面图、进度网络图、示意图）
- P2-3：做平台化运营能力（pack 管理、人工复核闭环、规则回归、误报库、标注回流）

## 六、防止过拟合的禁止事项必须单列成节，逐项写清楚
- 不得硬编码本案例特征
  - 例如看到“煤气区域”就固定报缺空气呼吸器
  - 看到“汽车吊”就固定报承载力验算缺失
  - 看到“防火安全”重复就加一个正则专项
- 不得只模仿 Gemini 的文风
- 不得只换更大模型
- 不得把“系统没读到附件”当成“文档缺附件”
- 不得为单一行业场景做专门 patch
- 不得把建议性工程优化伪装成强制性缺陷
- 必须明确区分“必须 / 应当 / 建议”

## 七、核心对象必须明确写入任务书，并给出字段级设计建议
至少包括：
- `PolicyPack`
- `EvidencePack`
- `ExtractedFacts`
- `RuleHit`
- `IssueCandidate`
- `FinalIssue`

其中：
- `PolicyPack`：按文档类型和专业场景装载规则
- `EvidencePack`：法规全文、条款适用条件、强制 / 建议级别、严重度映射
- `ExtractedFacts`：如起重量、起重设备型号、危险区域、临电方案状态、动火区域、停机窗口、劳动力、附件状态、预案列表等
- `RuleHit / IssueCandidate`：必须区分 `direct_hit / inferred_risk / visibility_gap`
- `FinalIssue`：必须包含 `layer(L1/L2/L3)`、`severity`、`finding_type`、`doc_evidence`、`policy_evidence`、`recommendation`、`confidence`

## 八、必须明确采用双轨制
- 保留 `review_assist`
- 新增 `structured_review`
- `review_assist` 做辅助总结
- `structured_review` 承担正式审查
- 必须说明这与当前 control plane 定位一致，是增量演进，不是推倒重来

---

# 必须逐项体现的代码改造与审查流程设计（不得泛化带过）

## 6.2 代码改进要求

任务书必须明确建议新增一个专门的 `review` 子域，而不是继续把正式审查逻辑堆在 `deepresearch_runtime.py` 中。  
请至少按如下方向给出目标目录结构、模块职责与落地建议：

```text
apps/api/src/review/
  schema.py
  parser/
    docx_parser.py
    normalizer.py
    attachment_indexer.py
  extractors/
    project_facts.py
    hazard_facts.py
    schedule_resource_facts.py
  rules/
    engine.py
    packs/
      construction_org/
      construction_scheme/
      hazardous_work/
      supervision/
  evidence/
    clause_store.py
    evidence_builder.py
  report/
    issue_builder.py
    report_builder.py
    matrices.py
  evaluation/
    dataset.py
    metrics.py
    harness.py
````

你必须解释：

* 为什么要新增 `review/` 子域
* 上述目录分别负责什么
* 与现有 `orchestrator / adapters / domain` 的边界如何划分
* 哪些模块是新增
* 哪些模块是从旧链路中拆出或下沉

### 关键文件必须逐项说明改造方向

#### 1. `document_loader.py`

必须明确建议升级为返回 `DocumentParseResult`，至少保留：

* heading 层级
* table 结构
* figure / image / attachment 占位
* appendix 状态
* 页眉页脚 / 重复内容清洗
* “不可读附件”状态标记

必须解释：

* 为什么纯文本拼接不够
* 为什么需要 parse result 而不是 plain text
* 如何避免把“未解析附件”误判为“文档缺失”

#### 2. `deepresearch_runtime.py`

必须明确建议：

* 不要再把 `review_assist` 或正式审查的最终输入做成一个被截断的 JSON 大包
* 正式审查应改为多阶段执行：

1. parse
2. extract facts
3. run rules
4. ask LLM only for ambiguous reasoning and wording
5. build report

必须说明：

* 现有截断式综合为什么会导致“更像总结器”
* 哪些职责应从 runtime 中拆走
* 哪些职责继续保留在 runtime 编排层

#### 3. `router.py`

必须明确建议：

* 从“按 query 关键词推数据集”升级为“按文档类型 + 专业标签 + policy pack 选择”
* 必须指出粗粒度默认路由不适合正式审查

必须说明：

* 新路由输入是什么
* pack 选择如何发生
* 如何兼容现有 `review_assist`

#### 4. `llm_gateway.py`

必须明确建议：

* 不再让它承担“从碎片里拼一个审查结论”的主职责
* 它应接受 `IssueCandidate[]` 和 `Evidence[]`
* 职责集中在：解释、归并、去重、润色
* 不应让它承担第一性审查判断

#### 5. `gpt_researcher_adapter.py`

如果继续保留，必须明确建议：

* 从“直接吃前若干字符”改为“按 section graph 和目标问题分段研究”
* 解释它在新体系中究竟是辅助检索器、研究器，还是可被替代的增强模块

#### 6. `domain/models.py`

必须明确建议新增或扩展以下对象：

* `ReviewIssue`
* `RuleHit`
* `EvidenceSpan`
* `ReviewLayer`
* `FindingType`
* `AttachmentVisibility`

必须解释：

* 没有这些对象，为什么评测、回归、人工复核会很痛苦
* 它们分别是 domain model、runtime artifact，还是 report DTO

---

## 6.3 审查流程改进要求

任务书必须把正式审查流程明确拆成以下四层，而不是一个大 prompt：

### L0：可视域检查

系统先判断：

* 哪些内容读到了
* 哪些没读到
* 哪些是图片 / 图纸 / 附件但未解析

必须明确指出：

* 这一步的目标是避免把“系统没看见”误判成“文档没有”
* 这一层应尽量采用确定性逻辑，不依赖 LLM 自由发挥

### L1：硬证据与强约束规则

这一层至少应举例覆盖：

* 重复章节
* 专项方案计划为空
* 起重吊装是否触发危大规则
* 特种作业人员证照要求是否出现
* 平面图是否可见
* 关键附件是否可见

必须明确：

* L1 尽量使用确定性规则
* L1 不应主要依赖 LLM 判断

### L2：条文适用与规范差距

必须明确：

* 用规则筛出的事实去检索适用条文
* 形成“事实—条文—缺口”链条
* 这一层的重点是规范适用与差距论证，而不是简单摘要

### L3：工程推理与整改编排

必须明确：

* 只在这一层使用 LLM 进行现场可操作性、资源-工序冲突、风险升级、整改排序的推理
* 同时强制模型标记这条意见属于：

  * 硬证据
  * 工程推断
  * 建议性增强

---

## 必须增加 4 类专门的 artifact builder

任务书必须明确建议至少新增以下 4 类中间产物：

* 章节结构图
* 危大识别矩阵
* 规则命中矩阵
* 冲突矩阵（工期-资源、危险源-措施、附件-审查项）

并明确说明：

* 这四类 artifact 为什么能显著提升可解释性
* 为什么它们有利于回归测试和人工复核
* 它们分别由哪个模块生成
* 最终如何进入 report builder 或 evaluation harness

---

# 你输出的任务书必须包含以下章节（不得省略）

## A. 执行摘要（Executive Summary）

要求：

* 用 300~600 字总结现状、核心差距、目标状态、分阶段路线
* 明确指出目标不是“更像 Gemini”，而是“让 Codex 能把 008 改造成一套结构化施组审查能力底座”

## B. 背景与问题定义

要求：

* 结合输入材料定义当前问题到底是什么
* 说明“为什么现在不够”
* 按以下维度拆解问题：

  * 输入层
  * 检索层
  * 审查方法层
  * 架构层
  * 数据模型层
  * 测试评测层

## C. 现状盘点（As-Is）

要求：

* 基于当前仓库真实文件路径梳理现有系统如何工作
* 至少覆盖：

  * `apps/api/src/services/document_loader.py`
  * `apps/api/src/orchestrator/planner.py`
  * `apps/api/src/orchestrator/router.py`
  * `apps/api/src/orchestrator/deepresearch_runtime.py`
  * `apps/api/src/adapters/llm_gateway.py`
  * `apps/api/src/adapters/gpt_researcher_adapter.py`
  * `apps/api/src/adapters/fastgpt_adapter.py`
  * `apps/api/src/domain/models.py`
  * `docs/architecture.md`
  * `docs/testing.md`
* 对每个关键文件说明：

  * 当前职责
  * 当前限制
  * 为什么会导致“更像总结器而不是审查器”

## D. 目标状态（To-Be）

要求：

* 给出目标架构图的文字版描述
* 明确哪些能力要保留、哪些能力要新增、哪些能力要重构
* 必须体现双轨制：

  * `review_assist`
  * `structured_review`

## E. 设计原则与非目标（Principles / Non-goals）

要求：

* 明确列出这次改造“不做什么”
* 例如：

  * 不为单案例打补丁
  * 不只优化 prompt
  * 不直接依赖单一大模型完成正式审查
  * 不把系统没看见当成文档缺失
  * 不先做一个庞大多模态平台再说

## F. 目标架构设计

要求：

* 以工程实现视角给出目标模块划分
* 覆盖：

  * review 子域
  * parser
  * extractors
  * rules
  * evidence
  * report
  * evaluation
* 给出建议目录结构
* 说明每个目录的职责、输入输出、与现有 orchestrator 的关系

## G. 领域模型与数据结构设计

要求：
必须给出建议新增的核心对象，并说明字段设计、用途、生命周期、序列化形式。至少包括：

* `StructuredReviewTask`
* `PolicyPack`
* `EvidencePack`
* `DocumentParseResult`
* `AttachmentVisibility`
* `ExtractedFacts`
* `RuleHit`
* `IssueCandidate`
* `FinalIssue`
* `EvidenceSpan`
* `ReviewLayer`
* `FindingType`
* `ConfidenceLevel`

对每个对象至少说明：

* 为什么需要它
* 关键字段
* 与其他对象的关系
* 建议放在哪个文件
* 是 domain model、runtime artifact，还是 report DTO

如合适，请给出 JSON Schema / Pydantic Model 级别的结构草图。

## H. 正式审查流水线设计

要求：
必须详细说明 `structured_review` 的运行流程，建议至少分为：

### H1. 可视域检查（Visibility Check）

* 哪些内容读到了
* 哪些没读到
* 哪些是附件 / 图纸 / 图片但未解析
* 如何避免误报

### H2. 事实抽取（Fact Extraction）

* 抽取哪些事实
* 如何按专业抽取
* 如何做 section-aware / table-aware 抽取
* 如何区分硬事实和模糊事实

### H3. 规则命中（Rule Matching）

* 规则如何组织
* 如何区分强制性规则、建议性规则
* 如何按 pack 加载

### H4. 证据分层（Evidence Layering）

* 文档证据
* 规范证据
* 工程推断
* 待补充证据

### H5. LLM 解释（LLM Explanation）

* 只在何处使用 LLM
* 哪些地方不能让 LLM 做第一性判定
* 如何控制 hallucination

### H6. 报告组装（Report Builder）

* 如何输出正式审查报告
* 如何输出中间矩阵
* 如何支持人工复核

### H7. L0 / L1 / L2 / L3 层级与六层流水线的映射关系

* 说明 L0/L1/L2/L3 与 parse / extract / rules / evidence / LLM / report 的对应关系
* 避免术语混乱

## I. Policy Pack / Rule Pack 设计

要求：

* 说明为什么要 pack 化
* 至少给出三层抽象：

  * 文档类型 pack
  * 专业场景 pack
  * 法规依据 pack
* 结合当前施组场景举例：

  * 施工组织设计 pack
  * 危大专项方案 pack
  * 起重吊装子 pack
  * 煤气区域子 pack
  * 临时用电子 pack
  * 动火子 pack
  * 特种设备子 pack
* 但必须强调：这些只是抽象示例，不得为当前案例硬编码

## J. 文件级改造清单（必须非常具体）

要求：
做一个“文件级改造矩阵”，至少包含列：

* 优先级（P0 / P1 / P2）
* 模块
* 当前文件
* 新增文件
* 修改目的
* 具体改动点
* 依赖关系
* 风险
* 验收标准

对关键文件要写到“可以直接分配给 Codex”的粒度。必须明确包括：

* `document_loader.py` 要改成什么返回结构
* `router.py` 如何新增 `structured_review`
* `deepresearch_runtime.py` 哪些逻辑拆掉，哪些保留
* `llm_gateway.py` 如何降级为解释 / 归并 / 润色层
* `domain/models.py` 如何扩展
* `docs/testing.md` 如何重写测试目标
* 是否需要新增 `review/` 子域与哪些文件

## K. 分阶段实施路线图（P0 / P1 / P2）

要求：
每阶段至少包含：

* 目标
* 具体任务
* 输出产物
* 风险
* 依赖
* 验收标准

建议至少按以下组织：

### P0：最小可用结构化审查内核

* `structured_review` task type
* `DocumentParseResult`
* `ExtractedFacts`
* 最小规则集
* `visibility_gap` 机制
* 最小 issue schema

### P1：规则体系、报告体系、评测体系

* policy packs
* evidence packs
* report builder
* evaluation harness
* golden fixtures

### P2：工程推理增强与多模态扩展

* 更复杂的工程逻辑
* 图纸 / 图片附件增强
* 人工复核闭环
* pack registry / 平台化能力

## L. 给 Codex 的执行拆分（PR / Commit 级别）

要求：
输出建议的 Codex 执行顺序，例如：

* PR1：新增 domain schema 与 task type
* PR2：重构 document parse pipeline
* PR3：引入 fact extraction
* PR4：引入 minimal rule engine
* PR5：重构 report builder
* PR6：测试与评测框架
* PR7：兼容层与文档更新

对每个 PR 说明：

* 改哪些文件
* 不改哪些文件
* 为什么这个顺序最安全
* 回滚边界在哪里

## M. 测试、评测与回归方案

要求：
不能只写“补测试”，必须分层写：

* 单元测试
* 集成测试
* 端到端测试
* 评测集
* 回归基线
* 模块级消融

必须明确：

* 现有 `make test / make smoke / make verify-connectivity` 如何延续
* 需要新增哪些测试命令或 fixture
* 如何建立 golden cases
* 如何衡量：

  * 问题召回率
  * 重大问题命中率
  * 危大识别命中率
  * 依据引用准确率
  * 硬证据准确率
  * 工程推断率与过度推断率
  * 严重度校准准确性
  * 附件可视域正确率
  * 建议可执行性
  * 可解释性评分

## N. 报告输出格式设计

要求：
给出正式审查输出的目标结构，至少包括：

* 总体结论
* L1 / L2 / L3 分层问题
* 每条问题的：

  * 问题标题
  * layer
  * severity
  * finding_type
  * doc_evidence
  * policy_evidence
  * recommendation
  * confidence
  * whether_manual_review_needed

还必须包括中间矩阵：

* 危大识别矩阵
* 规则命中矩阵
* 冲突矩阵
* 附件可视域矩阵
* 章节结构图

## O. 风险、边界与开放问题

要求：
列出至少三类：

1. 现在就能定的
2. 需要工程试做后再定的
3. 必须人工拍板的

例如：

* 规范 pack 的组织粒度
* 是否在第一阶段引入多模态
* 是否立刻重写现有 `review_assist` 结果格式
* 是否需要单独 rule authoring 机制
* 证据库如何长期维护

## P. 明确的 Definition of Done

要求：
给出“完成改造”的判定标准，而不是模糊表述。至少包括：

* `structured_review` 能运行
* 现有 `review_assist` 不回归损坏
* 至少支持一类施组正式结构化审查
* 能区分 `missing` 与 `visibility_gap`
* 能输出结构化 `FinalIssue[]`
* 有最小 golden dataset 与回归命令
* 文档和测试同步更新
* 中间 artifacts 可供人工复核
* 可以在不依赖“模仿 Gemini 文风”的前提下输出正式审查结果

## Q. 附录：接口草图 / 伪代码 / 数据流草图

要求：

* 可以给骨架
* 不要给无法维护的大段完整代码
* 重点帮助 Codex 理解模块边界与接口

---

# 输出质量要求

请严格遵守：

## 1）不要空话

禁止输出：

* “建议优化”
* “建议增强”
* “建议完善”
* “后续可进一步研究”
  这类没有动作对象和实施边界的话。

每个建议都必须落实到：

* 模块
* 文件
* 数据对象
* 运行流程
* 测试
* 验收

## 2）不要只讲战略

这不是管理层汇报稿，也不是 PRD 概述。
这是 **Codex 可执行的工程任务书**。

## 3）必须绑定真实仓库

优先引用当前仓库中的真实文件路径和目录结构。
不要虚构一个完全不同的工程组织方式。

## 4）必须显式区分三类内容

请在任务书中明确区分：

* **已确认事实**
* **合理推断**
* **建议新增设计**

不要把推断写成既成事实。

## 5）必须可供 Codex 执行

内容必须具体到：

* 能切成 PR
* 能写出新增文件
* 能定义模型与对象
* 能写测试
* 能逐步验收

## 6）必须写出避免过拟合的措施

必须专门写一节“不要做什么”，并逐项解释为什么不能那么做。

## 7）必须兼容现有能力

不能给出“删掉 review_assist / 全量替换 runtime / 全系统重写”这种粗暴方案。
优先增量演进。

## 8）必须体现正式审查与审查辅助的边界

要清楚说明：

* 什么由 `review_assist` 做
* 什么由 `structured_review` 做
* 两者如何共存
* 哪些 artifact 可复用
* 哪些 schema 共用，哪些分开

---

# 输出格式要求

请输出为一个完整 Markdown 文档，标题固定为：

# 008-review-control-plane 结构化施组审查能力改造任务书（Codex 执行版）

并满足：

* 使用清晰标题层级
* 适当使用表格
* 适当使用编号
* 语言专业、明确、克制
* 不是宣传稿
* 不是空泛咨询报告
* 不省略实施细节

---

# 最后要求

你的任务不是继续比较 Gemini 与 008，而是把这些差距、限制和目标状态，**转译成一个工程团队与 Codex 都能执行的改造任务书**。

因此：

* 任何空泛、模糊、不可落地的内容都不合格
* 任何只停留在“优化 prompt / 换模型 / 模仿文风”的内容都不合格
* 任何忽略评测、验收、回归、过拟合风险的内容都不合格

现在开始。请直接输出完整任务书正文。

```
```
