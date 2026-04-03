下面这版可以直接交给研究型 AI。
我按“越复杂越好、越能拉高回答质量”的思路写成了**完整版主 Prompt**，重点是：

* 只以**当前仓库**为事实源
* 把**已删除的旧仓库**彻底排除
* 要它先做 **As-Is 真实盘点**
* 再做 **Gap Analysis**
* 最后输出 **完整产品架构设计书 / 演进设计书**
* 强制绑定你已有的 round1 材料、改进建议、golden pool 指导书
* 强制落到模块、文件、对象、评测、路线图、DoD 粒度

你可以直接复制下面全文。

---

# 可直接投喂研究型 AI 的完整版 Prompt

你现在的角色不是“泛泛的方案顾问”或“评论者”，而是：

**资深技术负责人 + Staff Engineer + 平台架构师 + 产品架构师 + 交付经理 + 评测负责人 + 审查系统方法论设计者**

你的任务不是再写一篇普通分析，也不是再比较某个模型和某个系统谁更强。
你要做的是：**基于当前真实存在的仓库和我提供的材料，输出一份完整、详尽、面向下一阶段持续演进的产品架构设计书。**

---

# 一、最重要的事实前提（必须严格遵守）

## 1）旧仓库已经删除，视为不存在

下面这个仓库：

`https://github.com/watsonk1998/watson-agent-squad/tree/pr-monorepo-migration/008-review-control-plane`

**已经删除，请完全当它不存在。**

禁止行为：

* 不要引用它
* 不要假设它还存在
* 不要把它当作事实源
* 不要把它的代码结构、文件路径、实现状态当成当前事实
* 不要写“旧仓库里如何如何”来支撑当前判断

如果我之前提供过基于旧仓库写的材料，那些材料也只能作为：

* 历史需求背景
* 设计约束
* 对系统目标的表达
* 过往判断的参考

**不能作为当前代码事实。**

---

## 2）当前唯一仓库事实源

你必须以这个仓库为唯一代码事实源：

`https://github.com/watsonk1998/008-review-control-plane`

你所有关于代码、架构、模块、目录、对象、状态、实现程度的判断，都必须优先来自：

* 当前仓库代码
* 当前仓库 README
* 当前仓库 docs
* 当前仓库测试与 fixtures
* 当前仓库前后端真实实现

---

## 3）你将同时获得一批背景材料

我会同时提供你一些材料，可能包括但不限于：

1. 原始施组文档 / 施工组织设计文档
2. Gemini deepresearch 生成的审查结果
3. 当前 008 项目生成的审查结果
4. 我之前写的 round1 prompt
5. 修复任务书
6. 改进建议
7. golden pool / mini golden cases 指导书
8. 其他与 structured review、formal review、评测样本池相关的说明文档

这些材料的用途是：

* 让你理解项目真实业务目标
* 让你理解我对 formal review 的预期
* 让你做 gap analysis
* 让你判断哪些旧建议已经被当前 repo 吸收，哪些还没落地

但再次强调：

> **这些材料不是当前 repo 代码事实源。**
> 你必须先看当前 repo，再把这些材料作为约束和对照输入。

---

# 二、你的最终输出目标

请输出一份完整 Markdown 文档，标题固定为：

# 008-review-control-plane 产品架构设计书（当前态盘点 + 下一阶段演进版）

这份设计书必须同时完成以下三件事：

---

## A. 真实盘点当前仓库（As-Is）

你必须基于当前仓库真实代码和 docs，回答：

* 这个项目现在到底是什么定位？
* 它到底是 review control plane、formal reviewer、还是二者之间的某种过渡形态？
* 当前有哪些能力已经实现？
* 哪些能力只是骨架 / scaffold？
* 哪些能力只是接口、DTO、README、docs 层面出现，但仍未真正做实？
* 当前 `review_assist` 的边界是什么？
* 当前 `structured_review` 的边界是什么？
* 当前“正式结构化审查能力”到底是：

  * 概念占位
  * 初始骨架
  * 最小可用路径
  * 半成型系统
  * 还是已具备稳定正式审查能力

你必须给出清晰判断，而不是模糊表述。

---

## B. 做 Gap Analysis（当前仓库 vs 历史材料/目标预期）

你必须对照我提供的这些背景材料，判断：

* 哪些诉求在当前 repo 已经落地
* 哪些只落地了一半
* 哪些仍明显缺失
* 哪些旧版 round1 结论已经过时
* 哪些旧版建议仍然成立
* 哪些东西原本只是“设计目标”，现在已经进入真实代码
* 哪些东西在 README 里有，但在代码里没有
* 哪些东西在测试口径里有，但运行时还不够实

你必须专门写一节分析：

# 当前 repo 与旧版 round1 任务书 / 改进建议之间的关系

至少回答：

* round1 里哪些判断今天仍成立
* 哪些判断现在需要修正
* 哪些建议已经被吸收到当前 repo
* 哪些建议只是“名义上吸收”，实现仍偏浅
* 下一阶段不应该再重复哪些“已经做了的事”
* 下一阶段真正该做的重点是什么

---

## C. 给出下一阶段的 To-Be 设计

你的目标不是从 0 发明一个新系统，而是：

> **基于当前已经存在的 repo，设计下一阶段的产品架构演进方案。**

也就是说，你要回答：

* 当前这套系统下一阶段应该演进成什么？
* 产品定位如何表述更准确？
* `review_assist` 与 `structured_review` 的关系如何稳定下来？
* formal review 到底应该由哪些层组成？
* 当前哪些薄弱点最值得优先补强？
* 哪些部分要保留，哪些部分要重构，哪些部分要新增？
* 哪些改造适合 P0，哪些适合 P1，哪些适合 P2？
* 如何避免为单案例打补丁？
* 如何让系统变得可解释、可评测、可回归，而不是只会生成更长的报告？

---

# 三、你必须遵守的核心原则（非协商）

## 原则 1：不要把当前仓库写成“从零开始”

你必须承认并处理这个现实：

* 当前 repo 已经不是最早的空白 control plane
* 当前 repo 里很可能已经有 `structured_review`、review schema、review pipeline、testing、fixtures、DTO、artifact 之类内容
* 因此这次设计书不能按“仓库里完全没有这些能力”的方式来写

也就是说：

> 你不能再输出一份“新增 structured_review、引入 review 子域、加 TaskType”的老版从 0 到 1 任务书，除非你已经核实当前 repo 里真的没有这些东西。

---

## 原则 2：必须区分“已实现 / 已声明 / 已部分实现 / 未落地”

你对每项能力都必须显式判定状态，例如：

* 已实现（working implementation）
* 已有骨架（scaffold only）
* 文档已声明但实现不完整
* 测试口径存在但未稳定
* 仅 DTO / 接口存在
* 尚未落地

至少覆盖以下能力：

* `review_assist`
* `structured_review`
* task/request/result DTO
* `DocumentLoader`
* parse / extract / rules / evidence / report
* policy pack
* evidence pack
* artifacts
* frontend task entry / detail rendering
* evaluation harness
* golden pool / mini golden cases
* 模块级消融
* 跨模型评测
* 跨 pack 评测
* visibility / attachment / manual review 机制

---

## 原则 3：坚持双轨制，但不要假装当前仓库还没开始双轨

你必须显式分析：

* `review_assist` 是否仍然是辅助审查总结
* `structured_review` 是否已经开始承担正式结构化审查
* 当前双轨制是“概念已明确”还是“代码已初步成立”
* 下一阶段核心问题，不是“要不要双轨”，而是“如何把这条双轨做稳、做深、做清晰”

---

## 原则 4：正式审查不能被写成一个大 prompt

你必须围绕以下六层流水线来分析和设计，并对每一层分别判断当前状态与下一阶段建议：

* 文档解析层
* 事实抽取层
* 规则命中层
* 证据归档层
* LLM 解释层
* 报告组装层

你必须回答：

* 当前 repo 里哪些层已经真实存在
* 哪些层只是名字存在
* 哪些层仍严重依赖 LLM 粗综合
* 哪些层已经开始结构化
* 下一阶段最该加强哪几层

---

## 原则 5：不能把“换更强模型”当核心方案

你必须明确反对以下伪改进：

* 只换更大模型
* 只加更长 prompt
* 只增加上下文
* 只模仿 Gemini 文风
* 只把输出改成 L1/L2/L3 样式
* 为单一案例硬编码若干特征
* 把工程增强建议伪装成强制性缺陷
* 把“系统没看到”当成“文档没有”

---

## 原则 6：必须继续强化 visibility / attachment / manual review

你必须专门分析以下概念在当前 repo 中的真实落地情况：

* `visibility_gap`
* `attachment_unparsed`
* `evidence_missing`
* `manual_review_needed`

并判断：

* 当前 repo 是否已经有这些概念或其等价物
* 是只存在 schema / DTO 里，还是已经进入运行时逻辑
* 哪些地方仍然可能把“未解析”误判成“缺失”
* 哪些地方需要继续补齐

---

## 原则 7：golden pool 不是附录，而是主设计的一部分

你必须结合我提供的 golden pool / mini golden cases 指导材料，分析：

* 当前 repo 是否已经有 `fixtures/review_eval/`、seed cases、schema、evaluation harness 等基础设施
* 当前评测资产到底是 bootstrap、seed、内部回归集、还是稳定 golden pool
* 当前评测设计能否真正支撑 formal review 的持续演进
* 下一阶段如何从 mini golden cases 走向稳定 golden pool
* 如何把 facts / rule hits / visibility / final issues 全部纳入评测

---

# 四、你必须重点检查的真实文件 / 模块

你必须优先检查并绑定真实路径。至少覆盖：

## 仓库顶层 / 文档

* `README.md`
* `docs/architecture.md`
* `docs/testing.md`
* 其他与 review / structured_review / evaluation / fixtures 有关的 docs

## 后端 API / Domain / Runtime

* `apps/api/src/domain/models.py`
* `apps/api/src/routes/tasks.py`
* `apps/api/src/repositories/sqlite_store.py`
* `apps/api/src/services/document_loader.py`
* `apps/api/src/orchestrator/planner.py`
* `apps/api/src/orchestrator/router.py`
* `apps/api/src/orchestrator/deepresearch_runtime.py`

## Adapters

* `apps/api/src/adapters/llm_gateway.py`
* `apps/api/src/adapters/gpt_researcher_adapter.py`
* `apps/api/src/adapters/fastgpt_adapter.py`
* 其他与 review 输出直接相关的 adapter（如存在）

## Review 子域（如存在）

* `apps/api/src/review/`
* 其下的 parser / extractors / rules / evidence / report / evaluation
* 其 schema / pipeline / result builder / artifacts

## 前端

* `apps/web/src/types/control-plane.ts`
* `apps/web/src/components/home-dashboard.tsx`
* `apps/web/src/components/task-detail.tsx`
* 其他与 task type、structured review 展示、artifact 渲染相关的文件

## Fixtures / Evaluation / Tests

* `fixtures/review_eval/`（如存在）
* `fixtures/copied/` 中与审查相关的样本（如存在）
* review/evaluation 相关脚本、schema、测试
* 其他能体现当前评测体系的目录

---

# 五、你必须回答的核心问题

请在文中逐项明确回答以下问题，不得遗漏：

## 1）当前项目真实定位是什么？

不是口号，要结合 README、架构文档、planner/router/runtime 边界、review 子域和 UI 来判断。

---

## 2）当前 `structured_review` 到什么成熟度？

你必须清晰判断它更像：

* 名义存在
* DTO 存在
* 流程骨架存在
* 最小可用路径
* 半成型系统
* 还是可以稳定承担正式审查

并且必须说明判断依据。

---

## 3）当前 repo 与我历史 round1 材料有哪些关键不一致？

必须专门列一节，逐项指出：

* 旧版假设
* 当前 repo 真实状态
* 哪些旧结论已经不适用
* 这会如何改变下一阶段设计书的写法

---

## 4）当前最大的真实短板在哪里？

你必须区分并分别分析：

* 输入对象定义问题
* parser 深度问题
* facts 抽取覆盖不足
* rules / packs 不足
* evidence linking 不足
* issue schema / result contract 不足
* report builder 不足
* UI 展示和人工复核链路不足
* golden pool / eval 不足
* runtime 职责边界不清
* legacy `review_assist` 对整体认知的干扰

---

## 5）下一阶段最值得做的 P0 / P1 / P2 是什么？

这里的路线图必须是：

> **基于当前仓库已有实现继续演进**

不是再写一份老版“从 0 加 structured_review”的计划。

你必须避免重复提出那些已经在当前 repo 里做了的事情，除非你的判断是：

* 它虽然出现了，但实现过浅
* 仍然不能满足下一阶段目标
* 所以要“做实”而不是“新增”

---

# 六、你必须输出的章节结构（不得省略）

你的最终文档必须包含以下章节，并按此顺序组织：

---

## A. 执行摘要（Executive Summary）

要求：

* 300~600 字
* 明确说明：这份文档是基于**当前真实存在的 main 仓库**做的下一阶段演进设计
* 明确指出：已删除旧仓库不再作为事实源
* 明确总结当前状态、核心差距、下一阶段方向

---

## B. 当前仓库真实现状（As-Is）

要求：

* 逐模块、逐关键文件盘点
* 给出“当前职责 / 当前状态 / 当前限制 / 对 formal review 的意义”
* 不能泛泛而谈，必须绑定真实路径和真实实现

---

## C. 与历史材料的差异对照（Gap Analysis Against Historical Materials）

要求：

* 专门分析我给你的历史材料与当前 repo 的关系
* 明确指出：

  * 哪些已吸收
  * 哪些只吸收了一半
  * 哪些尚未落地
  * 哪些旧版判断已过时
* 这一章必须非常清晰，因为它决定你后续设计书不能再沿用旧前提

---

## D. 当前能力边界（Capability Boundary）

要求：

必须清晰区分：

* `review_assist`
* `structured_review`
* orchestrator / runtime
* adapters
* review domain
* frontend
* evaluation

并回答：

* 谁负责辅助总结
* 谁负责正式结构化审查
* 谁负责证据
* 谁负责结果组装
* 谁负责评测
* 哪些边界仍然混淆

---

## E. 关键问题与真实风险

要求：

* 不是抽象风险清单
* 必须基于当前实现写
* 要覆盖：

  * 输入解析
  * visibility
  * facts
  * rules
  * evidence
  * report
  * UI
  * eval
  * regression
  * pack overfitting
  * legacy chain interference

---

## F. 目标产品定位（To-Be Product Positioning）

要求：

* 回答下一阶段这个产品到底应如何定义
* 不要只是重复 README
* 要从“产品能力边界”和“用户预期管理”两个角度来写
* 必须体现双轨制

---

## G. 目标架构设计（To-Be Architecture）

要求：

* 仍围绕 review pipeline 来组织
* 但必须基于当前 repo 的真实现状来提出增强设计
* 必须说明：

  * 哪些层保留
  * 哪些层做实
  * 哪些层新增
  * 哪些层解耦
  * 哪些职责应该继续留在 runtime
  * 哪些职责必须下沉到 review 子域

---

## H. 核心对象与结果契约设计（Core Models & Result Contract）

要求：

至少覆盖这些对象及其状态判断：

* `TaskType`
* `StructuredReviewTask`
* `DocumentParseResult`
* `AttachmentVisibility`
* `ExtractedFacts`
* `RuleHit`
* `IssueCandidate`
* `FinalIssue`
* `ReviewLayer`
* `FindingType`
* `EvidenceSpan`
* `artifactIndex`
* `reportMarkdown`
* `manualReviewNeeded`
* `visibilityGap`
* 其他你认为已存在或应补强的关键对象

对每个对象至少回答：

* 当前 repo 是否已经有
* 若有，是在哪个文件
* 是完整实现、部分实现、还是仅 DTO
* 下一阶段建议如何调整

---

## I. 下一阶段分期路线图（P0 / P1 / P2）

要求：

* 必须基于当前状态继续演进
* 不能重复“新增早已存在的概念”
* 每阶段都要明确：

  * 目标
  * 范围
  * 文件/模块
  * 交付产物
  * 风险
  * 验收标准

建议你用下面这种思路：

* **P0：把当前已有骨架做实，形成稳定最小可用 formal review 路径**
* **P1：补齐 pack / evidence / matrices / UI / eval / regression**
* **P2：增强复杂工程推理、多模态、运营化与闭环能力**

但不要机械照搬，必须以当前 repo 真实状态为准。

---

## J. 文件级改造矩阵（File-level Engineering Plan）

要求：

必须细到可以分配给工程师 / Codex 的粒度。

至少包含列：

* 优先级（P0/P1/P2）
* 模块
* 当前文件
* 新增文件
* 修改目的
* 具体改动点
* 依赖关系
* 风险
* 验收标准

必须尽量覆盖：

* `document_loader.py`
* `planner.py`
* `router.py`
* `deepresearch_runtime.py`
* `llm_gateway.py`
* `gpt_researcher_adapter.py`
* `domain/models.py`
* `routes/tasks.py`
* `sqlite_store.py`
* `apps/web/src/types/control-plane.ts`
* `home-dashboard.tsx`
* `task-detail.tsx`
* `review/` 子域相关文件
* `fixtures/review_eval/`、schema、evaluation harness
* 其他关键文件

---

## K. 评测与 golden pool 演进方案（Evaluation & Golden Pool Roadmap）

要求：

必须写清楚：

### 1）当前状态是什么

* 是 seed cases？
* bootstrap？
* mini golden cases？
* 还是稳定 golden pool？

### 2）当前问题是什么

* facts 没纳入评测？
* visibility 没纳入评测？
* 只看最终报告？
* 缺乏模块级回归？
* 缺乏跨 pack / 跨模型对照？

### 3）下一阶段怎么演进

至少覆盖：

* 端到端评测
* parser / extractors / rules / evidence / report 模块消融
* 跨模型对照
* 跨 pack 对照
* facts / rule hits / visibility / final issues 分层评测
* regression baseline
* stable golden pool 的版本化机制

### 4）样本池覆盖要求

至少要求覆盖：

* 施工组织设计
* 一般施工方案
* 危大专项方案
* 监理规划 / 审查辅助材料
* 机电安装类
* 土建类
* 钢结构类
* 临电类
* 起重吊装类

---

## L. 非目标与禁止事项（Non-goals & Anti-patterns）

要求：

必须单列并写透，至少包括：

* 不为单案例硬编码
* 不只靠 prompt
* 不只靠更强模型
* 不把系统没读到当成文档缺失
* 不只模仿 Gemini 文风
* 不把建议性工程增强伪装成强制性缺陷
* 不先做一个庞大而空泛的多模态平台
* 不把 `review_assist` 强行包装成 formal review

---

## M. Definition of Done

要求：

必须明确写出下一阶段完成的判断标准。
至少包含：

* 功能 DoD
* 数据契约 DoD
* 评测 DoD
* 回归 DoD
* UI / artifact DoD
* 文档 DoD
* 风险边界 DoD

---

# 七、分析方法要求（你必须这样做）

你不能只浏览 README 然后写方案。
你必须采用下面的方法：

## 第一步：先做真实代码与 docs 盘点

先识别当前仓库的真实结构和关键模块职责。

## 第二步：给每项能力判定成熟度

不是只说“有/没有”，而要说：

* 完整
* 初步
* 骨架
* 名义存在
* 尚未落地

## 第三步：再对照历史材料

判断哪些历史判断已被当前 repo 吸收，哪些还没吸收。

## 第四步：最后再输出 To-Be 设计

不能跳过 As-Is 和 Gap Analysis，直接空想下一阶段。

---

# 八、写作要求

你的文风必须：

* 专业
* 克制
* 工程化
* 可执行
* 结构化
* 不宣传
* 不口号化
* 不写成论文腔空谈

你必须做到：

* 明确区分“已确认事实 / 合理推断 / 建议新增设计”
* 优先引用真实文件路径、真实模块、真实职责
* 不得凭空虚构系统
* 不得使用已删除旧仓库作为事实依据
* 不得把历史材料里的说法直接当成当前代码事实

---

# 九、特别提醒：你输出的不是哪三种东西

你输出的**不是**：

1. 一篇 Gemini vs 008 的优劣评论
2. 一份旧版 round1 修复任务书的改写版
3. 一份空泛的 AI 审查平台白皮书

你输出的必须是：

> **基于当前 `https://github.com/watsonk1998/008-review-control-plane` 真实状态的产品架构设计书 / 下一阶段演进设计书。**

现在开始。

---

如果你愿意，我还能继续帮你补一版：

**“给研究型 AI 的附加要求清单”**
专门强制它输出更狠一点，比如：

* 先列出“已实现 / 骨架 / 未落地”总表
* 必须给出 1 张文件级改造矩阵总表
* 必须给出 1 张 P0/P1/P2 路线表
* 必须给出 1 张当前 repo vs 历史 round1 的差异表

这样通常会让回答更稳。
