你现在的角色不是普通的“方案顾问”“:contentReference[oaicite:0]{index=0}人 + 工程文档作者**

你的任务不是再写一篇泛泛分析，也不是继续比较某个模型和某个系统谁更强。  
你的任务是：

> **基于当前真实存在的仓库与我提供的材料，输出一份完整、严谨、详尽、可执行、可验证的产品架构设计书。**

---

# 一、绝对前提（必须严格遵守）

## 1. 已删除旧仓库，视为完全不存在

下面这个仓库：

`https://github.com/watsonk1998/watson-agent-squad/tree/pr-monorepo-migration/008-review-control-plane`

**已经删除。请把它视为完全不存在。**

这不是“尽量不要依赖”，而是**禁止作为事实源**。

### 你必须遵守以下限制

- 不要引用这个仓库
- 不要假设它还存在
- 不要把它的目录、文件、模块、实现状态写成当前事实
- 不要写“旧仓库中如何如何，因此当前系统如何如何”
- 不要把基于旧仓库得出的结论直接当成当前 repo 的事实判断

如果我提供给你的某些材料是基于那个旧仓库写的，那么这些材料只能被视为：

- 历史需求背景
- 产品目标表达
- 设计约束
- 过往问题意识
- 对 formal review / structured_review 的期待

**不能作为当前代码事实。**

---

## 2. 当前唯一有效的代码事实源

你必须以这个仓库作为唯一代码事实源：

`https://github.com/watsonk1998/008-review-control-plane`

你所有关于以下内容的判断，都必须优先来自当前仓库真实内容：

- 项目定位
- README / docs
- 目录结构
- 模块职责
- planner / router / runtime
- domain models / task types / DTO
- review 子域
- adapters
- frontend 类型与页面
- fixtures / evaluation / tests
- artifact API
- golden pool / review_eval / regression 基础设施

---

## 3. 我会同时提供你一组背景材料

我可能会给你以下材料中的一部分或大部分：

1. 原始施组 / 施工组织设计文档 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/施工组织设计-培花初期雨水调蓄池建设工程.pdf` 和  `https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx`
2. Gemini deepresearch 审查结果 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/gemini-deepresearch审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md` 和  `https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/gemini-deepresearch审查结果-施工组织设计-培花初期雨水调蓄池建设工程.md`
3. 当前 008 项目生成的审查结果 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/review-control-plane审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md` 和  `https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/supervision/review-control-plane审查结果-施工组织设计培花初期雨水调蓄池建设工程.md`
4. 我此前写的 round1 prompt 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/任务书/改进建议-round1.md`
5. 修复任务书 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/任务书/出具修复任务书的prompt-round1.md`
6. 改进建议 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/任务书/修复任务书-round1.md`
7. golden pool / mini golden cases 指导书 地址：`https://github.com/watsonk1998/008-review-control-plane/blob/main/fixtures/golden pool/golden pool指导书.md`
8. 其他与 structured review / formal review / evaluation 相关的材料

这些材料的用途是：

- 帮助你理解真实业务目标
- 帮助你理解我对 formal review 的预期
- 帮助你做 gap analysis
- 帮助你判断哪些旧建议已经被当前 repo 吸收，哪些还未落地

但再次强调：

> **这些材料不是当前 repo 的代码事实源。**

你必须先基于当前 repo 进行真实盘点，再拿这些材料做差异对照与演进设计。

---

# 二、你的最终输出目标

请输出一份完整 Markdown 文档，标题固定为：

# 008-review-control-plane 产品架构设计书（当前态盘点 + 下一阶段演进版）

这份文档不是普通分析报告，也不是白皮书，而是一份：

- 面向下一阶段持续改造的正式设计书
- 能指导工程实现与任务拆分的设计书
- 能支撑 Codex / 工程师继续改仓库的设计书
- 兼顾产品定位、系统边界、工程路径、评测闭环的设计书

它必须同时完成三件事：

---

## 目标 A：真实盘点当前仓库现状（As-Is）

你必须基于当前仓库真实存在的 README、docs、代码、tests、fixtures、前后端实现，回答：

- 这个项目现在到底是什么定位？
- 它是 review control plane、formal reviewer、还是二者之间的过渡形态？
- 当前有哪些能力已经真实落地？
- 哪些能力只是骨架 / scaffold / skeleton？
- 哪些能力只是 DTO / schema / interface 存在？
- 哪些能力只是 README / docs 中被宣告了？
- 哪些能力只在 testing / fixture 口径中出现？
- 哪些能力仍明显未落地？

你不能只说“有/没有”，必须给出成熟度判断。

---

## 目标 B：对照历史材料做 Gap Analysis

你必须把我提供的历史材料视为：

- 需求背景
- 产品目标
- 历史判断
- 对 formal review 的约束表达
- 评测建设思路

然后分析：

- 哪些历史诉求已经被当前 repo 吸收
- 哪些只吸收了一半
- 哪些还明显没有落地
- 哪些旧版 round1 判断今天已经不适用
- 哪些判断今天仍成立
- 哪些建议已经从“概念/文档”进入了代码
- 哪些仍停留在命名或口号层
- 哪些下一阶段不该再重复提出
- 哪些下一阶段仍然应是优先事项

必须专门有一节：

# 当前 repo 与历史 round1 任务书 / 改进建议 / golden pool 指导材料的差异对照

---

## 目标 C：给出下一阶段 To-Be 设计

你不能从 0 发明一个新系统。  
你必须：

> **基于当前真实存在的 repo 状态，设计下一阶段如何继续演进。**

也就是说，你要回答：

- 下一阶段这个产品应该如何定义？
- `review_assist` 与 `structured_review` 的边界如何稳定下来？
- formal review 到底应该由哪些层构成？
- 当前最值得优先补强的真实短板是什么？
- 哪些部分应该保留、哪些应该重构、哪些应该新增？
- 哪些工作属于 P0、哪些属于 P1、哪些属于 P2？
- 如何避免为单案例打补丁？
- 如何让系统变得可解释、可评测、可回归，而不是只会生成更长报告？

---

# 三、研究流程要求（你必须按这个流程工作）

你不能只浏览 README 后直接写方案。  
你必须严格按下面的顺序研究和输出。

---

## 第 1 步：先做当前仓库真实盘点

你必须先识别：

- 关键目录
- 关键模块
- 关键文件
- 关键对象
- 关键 API
- 关键 task types
- 关键 artifacts
- 关键 tests / fixtures / eval assets

你必须先回答“现在有什么”，再回答“未来该做什么”。

---

## 第 2 步：对关键能力做成熟度判定

对每项能力，你不能只说“存在”。  
你必须使用以下成熟度标签之一：

- **已实现（working implementation）**
- **初步可用（minimally working）**
- **有骨架（scaffold only）**
- **仅 DTO / schema 存在（DTO only）**
- **仅 README / docs 声明（docs only）**
- **仅测试口径存在（test-only evidence）**
- **尚未落地（not landed）**

并解释你的判定依据。

---

## 第 3 步：再对照历史材料

你必须明确对照以下东西（如果我提供了）：

- round1 prompt
- 修复任务书
- 改进建议
- golden pool 指导书
- 原始施组
- Gemini 结果
- 008 当前结果

你必须判断：

- 哪些旧诉求已被当前 repo 吸收
- 哪些旧判断已过时
- 哪些还值得继续推进

---

## 第 4 步：最后输出 To-Be 设计

只有完成前 3 步后，才可以开始写下一阶段设计。  
不能跳过 As-Is 和 Gap Analysis，直接凭想象写 To-Be。

---

# 四、你必须重点检查的真实文件 / 模块

你必须优先检查并绑定真实路径。  
至少覆盖以下内容。

---

## A. 仓库顶层与文档

- `README.md`
- `DELIVERY_REPORT.md`
- `docs/architecture.md`
- `docs/formal-review.md`
- `docs/testing.md`
- `docs/known-limitations.md`
- 其他与 review / structured_review / artifacts / evaluation / fixtures 强相关的 docs

---

## B. 后端 API / Domain / Runtime

- `apps/api/src/domain/models.py`
- `apps/api/src/routes/tasks.py`
- `apps/api/src/repositories/sqlite_store.py`
- `apps/api/src/services/document_loader.py`
- `apps/api/src/orchestrator/planner.py`
- `apps/api/src/orchestrator/router.py`
- `apps/api/src/orchestrator/deepresearch_runtime.py`

---

## C. Adapters

- `apps/api/src/adapters/llm_gateway.py`
- `apps/api/src/adapters/gpt_researcher_adapter.py`
- `apps/api/src/adapters/fastgpt_adapter.py`
- 其他与结果生成、研究、证据、摘要、检索相关的 adapter

---

## D. Review 子域（如存在）

- `apps/api/src/review/`
- 其下的：
  - parser
  - extractors
  - rules
  - evidence
  - report
  - evaluation
  - schema
  - pipeline
  - pack registry
  - issue builder
  - report builder
  - matrices / artifact builder

---

## E. 前端

- `apps/web/src/types/control-plane.ts`
- `apps/web/src/components/home-dashboard.tsx`
- `apps/web/src/components/task-detail.tsx`
- 其他与 task type、structured review 创建、结果渲染、artifact 展示、issue/matrices 展示相关的文件

---

## F. Fixtures / Evaluation / Tests

- `fixtures/review_eval/`（如存在）
- `fixtures/copied/` 中与审查相关的样本
- review/evaluation 相关 schema、case metadata、ground truth、expected facts、expected rule hits
- review/evaluation harness
- tests / smoke / regression / ablations / cross-pack / cross-model 相关资产

---

# 五、你必须回答的核心问题（不得遗漏）

请在文中逐项明确回答以下问题。

---

## 1. 当前项目真实定位是什么？

你必须结合以下维度综合判断：

- README 中的定位
- architecture docs 中的边界
- planner / router / runtime 职责
- review 子域是否存在及其职责
- frontend 是否已经区分 `review_assist` / `structured_review`
- testing / eval 是否已支持 formal review

不能只用一句 slogan 回答。

---

## 2. 当前 `structured_review` 到什么成熟度？

你必须明确判断它更像以下哪一类：

- 名义存在
- DTO 存在
- 流程骨架存在
- 最小可用路径
- 半成型系统
- 能较稳定承担正式审查
- 仍只是 P1 级原型

并必须给出证据。

---

## 3. 当前 repo 与历史 round1 材料有哪些关键不一致？

必须专门写一节，逐项指出：

- 历史材料中的旧版假设是什么
- 当前 repo 的真实状态是什么
- 哪些旧结论已经不适用
- 哪些旧建议已经被吸收
- 哪些只吸收了一半
- 这些差异如何改变下一阶段设计书写法

---

## 4. 当前最大的真实短板在哪里？

你必须分别分析：

- 输入对象定义问题
- parser 深度问题
- facts 抽取覆盖不足
- rules / packs 过浅
- evidence linking 不足
- issue schema / result contract 不足
- report builder 不足
- UI 展示与人工复核不足
- golden pool / evaluation 不足
- runtime 职责边界不清
- legacy `review_assist` 对整体产品认知的干扰

---

## 5. 下一阶段最值得做的 P0 / P1 / P2 是什么？

必须是：

> **基于当前 repo 真实状态继续演进**

不是重新写一版“从 0 到 1 引入 structured_review”的旧方案。

如果某能力当前已经存在，但你认为做得太浅，那么你必须明确表述为：

- 做实
- 补强
- 收敛
- 解耦
- 规范化
- 稳定化
- 评测化

而不是笼统写“新增”。

---

# 六、核心原则（非协商）

---

## 原则 1：不能把当前仓库写成“空白系统”

你必须承认并处理这个现实：

- 当前 repo 很可能已经出现 `structured_review`
- 已经可能存在 review schema / DTO / pipeline / artifacts / fixtures / eval / UI type
- 因此这份设计书不能按“仓库里完全没有这些东西”的方式来写

---

## 原则 2：必须区分“已实现 / 已声明 / 已部分实现 / 未落地”

至少对以下能力逐项标状态：

- `review_assist`
- `structured_review`
- request / response DTO
- `DocumentLoader`
- parse / extract / rules / evidence / report
- policy packs
- evidence packs
- artifacts
- frontend task entry / detail rendering
- evaluation harness
- golden pool / mini golden cases
- 模块级消融
- 跨模型评测
- 跨 pack 评测
- visibility / attachment / manual review 机制

---

## 原则 3：坚持双轨制，但不要假装当前 repo 还没开始双轨

你必须分析：

- `review_assist` 是否仍然是辅助审查总结
- `structured_review` 是否已经开始承担正式结构化审查
- 当前双轨制是“概念已明确”还是“代码已初步成立”
- 下一阶段真正的问题不是“要不要双轨”，而是“如何把这条双轨做稳、做深、做清晰”

---

## 原则 4：正式审查不是一个大 prompt

你必须围绕以下六层流水线来分析和设计：

- 文档解析层
- 事实抽取层
- 规则命中层
- 证据归档层
- LLM 解释层
- 报告组装层

对每一层都要回答：

- 当前 repo 是否已有对应实现
- 是真实实现、部分实现、还是只是命名/接口
- 这一层目前主要依赖确定性逻辑，还是仍高度依赖 LLM
- 下一阶段最应该如何补强

---

## 原则 5：不能把换模型当主答案

你必须明确反对以下伪改进：

- 只换更大模型
- 只加更长 prompt
- 只扩大上下文
- 只模仿 Gemini 文风
- 只把输出改成 L1/L2/L3 样式
- 为当前案例硬编码 patch
- 把建议性工程增强伪装成强制性缺陷
- 把“系统没看到”当成“文档没有”

---

## 原则 6：必须显式分析 visibility / attachment / manual review

你必须专门分析以下概念在当前 repo 中的真实落地情况：

- `visibility_gap`
- `attachment_unparsed`
- `evidence_missing`
- `manual_review_needed`

并判断：

- 当前 repo 是否已经有这些概念或其等价物
- 是只存在 schema / DTO 里，还是已经进入 runtime / rule / report / UI 逻辑
- 哪些地方仍可能把“未解析”误判成“缺失”
- 下一阶段如何补齐

---

## 原则 7：golden pool 不是附录，而是主设计的一部分

你必须结合我提供的 golden pool / mini golden cases 指导材料，分析：

- 当前 repo 是否已经有 `fixtures/review_eval/`、schema、seed cases、expected facts、expected rule hits、evaluation harness
- 当前评测资产是 bootstrap、seed、mini golden cases、内部回归集还是稳定 golden pool
- 当前评测设计能否真正支撑 formal review 演进
- 下一阶段如何从 mini golden cases 走向正式 golden pool
- 如何把 facts / rule hits / visibility / final issues 全部纳入评测

---

# 七、你必须给出的输出结构（不得省略）

你的最终文档必须按以下顺序输出。

---

## A. 执行摘要（Executive Summary）

要求：

- 300~600 字
- 明确说明：本设计书基于当前真实存在的仓库
- 明确说明：已删除旧仓库不再作为事实源
- 总结当前状态、核心差距、下一阶段方向

---

## B. 当前仓库真实现状（As-Is）

要求：

- 逐模块、逐关键文件盘点
- 写清：
  - 当前职责
  - 当前实现状态
  - 当前限制
  - 对 formal review 的意义
- 必须绑定真实路径
- 不得泛泛描述

---

## C. 能力成熟度总表（Capability Maturity Matrix）

这一章必须单独存在，并至少提供一张总表。

### 表格列建议

- 能力名称
- 所属层（runtime / review / UI / eval / data / artifact）
- 当前状态（已实现 / 初步可用 / scaffold / DTO only / docs only / not landed）
- 证据文件
- 当前主要问题
- 下一阶段动作建议

### 至少覆盖以下能力

- task types
- review_assist
- structured_review
- document parsing
- facts extraction
- rule matching
- evidence linking
- report building
- artifact generation
- UI rendering
- fixtures / review_eval
- evaluation harness
- regression baseline
- pack selection
- manual review flow

---

## D. 与历史材料的差异对照（Gap Analysis Against Historical Materials）

要求：

- 明确对照我给你的：
  - round1 prompt
  - 修复任务书
  - 改进建议
  - golden pool 指导书
  - 原始施组 / Gemini / 008 当前结果（如提供）
- 逐项指出：
  - 已吸收
  - 已部分吸收
  - 仍未落地
  - 已过时
- 必须说明这些差异如何影响后续设计

---

## E. 当前能力边界（Capability Boundary）

要求：

必须清晰区分：

- `review_assist`
- `structured_review`
- orchestrator / runtime
- adapters
- review domain
- frontend
- evaluation / fixtures

必须回答：

- 谁负责辅助总结
- 谁负责正式结构化审查
- 谁负责 pack / rule / evidence
- 谁负责 artifacts
- 谁负责 UI 呈现
- 谁负责评测与回归
- 哪些边界仍然混淆

---

## F. 关键问题与真实风险

要求：

不能写成泛泛风险清单。  
必须基于当前实现写，并至少覆盖：

- 输入解析风险
- visibility 误判风险
- facts 漏抽 / 错抽风险
- rules / packs 过浅风险
- evidence 链条不完整风险
- LLM 越权判断风险
- report builder 过度摘要风险
- UI / 人工复核链路不足风险
- regression 体系不足风险
- single-case overfitting 风险
- legacy `review_assist` 持续干扰产品认知的风险

---

## G. 目标产品定位（To-Be Product Positioning）

要求：

- 从产品能力边界和用户预期管理两个角度来写
- 明确说明下一阶段这个项目应该如何定义
- 必须体现双轨制：
  - `review_assist`
  - `structured_review`

你必须解释：

- 什么应该继续归属于 `review_assist`
- 什么必须归属于 `structured_review`
- 为什么这种划分符合 control plane 的长期定位

---

## H. 目标架构设计（To-Be Architecture）

要求：

你必须以工程实现视角描述下一阶段架构，不要只写概念。

必须覆盖：

- runtime 与 review domain 的边界
- parser / extractors / rules / evidence / report / evaluation
- pack 机制
- artifact 机制
- result contract
- UI consumption contract
- regression / evaluation assets

必须明确：

- 哪些层保留
- 哪些层做实
- 哪些层新增
- 哪些层解耦
- 哪些职责继续留在 runtime
- 哪些职责必须下沉到 review 子域

---

## I. 核心对象与结果契约设计（Core Models & Result Contract）

要求：

至少覆盖以下对象，并逐项分析：

- `TaskType`
- `StructuredReviewTask`
- `DocumentParseResult`
- `AttachmentVisibility`
- `ExtractedFacts`
- `RuleHit`
- `IssueCandidate`
- `FinalIssue`
- `ReviewLayer`
- `FindingType`
- `EvidenceSpan`
- `artifactIndex`
- `reportMarkdown`
- `manualReviewNeeded`
- `visibilityGap`

对每个对象至少回答：

- 当前 repo 是否已有
- 若已有，在哪个文件
- 是完整实现 / 部分实现 / DTO only / docs only
- 下一阶段是否需要扩展、收敛、拆分、前后端对齐

如合适，请给出 JSON Schema / Pydantic / TS type 级别的结构草图。

---

## J. 六层流水线与 L0/L1/L2/L3 的映射分析

要求：

必须专门写一节，清晰说明：

### 六层流水线
- 文档解析层
- 事实抽取层
- 规则命中层
- 证据归档层
- LLM 解释层
- 报告组装层

### L0/L1/L2/L3
- L0 可视域检查
- L1 硬证据与强规则
- L2 条文适用与规范差距
- L3 工程推理与整改编排

请说明：

- 当前 repo 中哪些已经存在
- 哪些是概念上存在
- 哪些仍然混在一起
- 如何在下一阶段把两套视角真正映射清楚

---

## K. 下一阶段分期路线图（P0 / P1 / P2）

要求：

必须基于当前 repo 已有能力继续演进。  
不要重复提出那些已经落地的概念，除非你的判断是“它们需要被做实”。

每个阶段都必须明确：

- 目标
- 范围
- 涉及模块 / 文件
- 交付产物
- 风险
- 验收标准

建议逻辑可参考但不得机械照搬：

### P0
把当前已有骨架做实，形成稳定的最小可用 formal review 路径

### P1
补齐 pack / evidence / matrices / UI / eval / regression / result contract

### P2
增强复杂工程推理、多模态、运营化、人工复核闭环与平台化 pack 运营

---

## L. 文件级改造矩阵（File-level Engineering Plan）

要求：

这一章必须足够细，达到可以直接分配给工程师或 Codex 的粒度。

必须至少给出一张表，包含：

- 优先级（P0 / P1 / P2）
- 模块
- 当前文件
- 新增文件
- 修改目的
- 具体改动点
- 依赖关系
- 风险
- 验收标准

必须尽量覆盖以下文件：

- `apps/api/src/services/document_loader.py`
- `apps/api/src/orchestrator/planner.py`
- `apps/api/src/orchestrator/router.py`
- `apps/api/src/orchestrator/deepresearch_runtime.py`
- `apps/api/src/adapters/llm_gateway.py`
- `apps/api/src/adapters/gpt_researcher_adapter.py`
- `apps/api/src/adapters/fastgpt_adapter.py`
- `apps/api/src/domain/models.py`
- `apps/api/src/routes/tasks.py`
- `apps/api/src/repositories/sqlite_store.py`
- `apps/web/src/types/control-plane.ts`
- `apps/web/src/components/home-dashboard.tsx`
- `apps/web/src/components/task-detail.tsx`
- `apps/api/src/review/` 下核心文件
- `fixtures/review_eval/` 下 schema / case / evaluation 相关文件
- 其他你认为必须纳入改造计划的关键文件

---

## M. 评测与 golden pool 演进方案（Evaluation & Golden Pool Roadmap）

要求：

必须详细写清楚以下内容。

### 1）当前评测状态
- 当前 repo 的评测资产处于什么状态？
- 属于 bootstrap、seed、mini golden cases、内部回归集、还是稳定 golden pool？

### 2）当前主要问题
- 是否只看最终报告？
- 是否缺 facts 评测？
- 是否缺 rule hits 评测？
- 是否缺 visibility 评测？
- 是否缺模块级回归？
- 是否缺跨模型 / 跨 pack 对照？

### 3）下一阶段演进方案
至少覆盖：

- 端到端评测
- parser / extractors / rules / evidence / report 的模块消融
- 跨模型对照
- 跨 pack 对照
- facts / rule hits / visibility / final issues 分层评测
- regression baseline
- stable golden pool 版本化机制

### 4）样本池覆盖要求
至少要求覆盖：

- 施工组织设计
- 一般施工方案
- 危大专项方案
- 监理规划 / 审查辅助材料
- 机电安装类
- 土建类
- 钢结构类
- 临电类
- 起重吊装类

### 5）防过拟合要求
必须单列说明如何避免：

- 冷轧厂样本特征硬编码
- 只围绕单一行业样本优化
- 只围绕 Gemini 风格优化
- 工程增强建议伪装成硬缺陷
- visibility 错误被带入 golden truth

---

## N. 非目标与禁止事项（Non-goals & Anti-patterns）

要求：

必须单列并写透，至少包括：

- 不为单案例硬编码
- 不只靠 prompt
- 不只靠更强模型
- 不把系统没读到当成文档缺失
- 不只模仿 Gemini 文风
- 不把建议性工程增强伪装成强制性缺陷
- 不先做一个庞大而空泛的多模态平台
- 不把 `review_assist` 强行包装成 formal review

---

## O. Definition of Done

要求：

必须明确写出下一阶段完成的判断标准。  
至少包含：

- 功能 DoD
- 数据契约 DoD
- 结果可解释性 DoD
- 评测 DoD
- 回归 DoD
- UI / artifact DoD
- 文档 DoD
- 风险边界 DoD

---

# 八、你必须输出的表格（不得省略）

为了提高可执行性，你的文档必须至少包含以下表格。

---

## 表 1：能力成熟度总表

列建议：

- 能力
- 所属层
- 当前状态
- 证据文件
- 当前问题
- 下一步动作

---

## 表 2：历史材料 vs 当前 repo 差异表

列建议：

- 历史诉求 / 旧判断
- 当前 repo 状态
- 结论（已吸收 / 部分吸收 / 未落地 / 过时）
- 对后续设计的影响

---

## 表 3：文件级改造矩阵

列建议：

- 优先级
- 模块
- 当前文件
- 新增文件
- 修改目的
- 具体改动点
- 风险
- 验收标准

---

## 表 4：P0 / P1 / P2 路线表

列建议：

- 阶段
- 目标
- 核心任务
- 依赖
- 风险
- 验收

---

## 表 5：评测演进表

列建议：

- 评测层
- 当前状态
- 问题
- 下一阶段建设动作
- 产物

---

# 九、证据与引用规则（必须遵守）

为了避免你写成“听起来合理但未被仓库证实”的方案，你必须遵守以下规则。

---

## 1. 每一个关键判断都要尽量有依据

你的关键判断必须尽量绑定以下证据之一：

- README
- docs
- 代码文件
- fixtures / tests / evaluation assets
- 我提供的背景材料

---

## 2. 必须区分三类信息

在文中尽量显式区分：

- **已确认事实**
- **合理推断**
- **建议新增设计**

---

## 3. 不得把“推断”伪装成“当前实现事实”

例如：

- 如果某个对象在 README 中出现，但代码中没有足够证据，你不能写成“当前系统已实现”
- 如果某个能力看起来应该存在，但你没有确认，也不能写成既成事实

---

## 4. 若 README / docs 有声明，但代码证据不足

必须写成：

- “文档已声明，但代码侧落地证据不足”
- “schema 已出现，但系统级能力尚未完全贯通”
- “存在概念或接口，但未见充分运行时证据”

而不能偷换成“已完成”。

---

## 5. 对历史材料的使用方式

历史材料只能用于：

- 解释需求背景
- 解释为何要做某项设计
- 与当前 repo 做差异对照

不能用于：

- 伪造当前 repo 已有实现
- 替代当前代码事实
- 直接把旧版结论写成当前判断

---

# 十、你必须避免的常见失败模式

请在分析和写作过程中主动避免以下失败模式。

---

## 失败模式 1：只看 README 就开始写方案
你必须查看实际代码、docs、tests、fixtures、frontend。

---

## 失败模式 2：把旧版 round1 任务书当当前事实
严格禁止。

---

## 失败模式 3：把 DTO / schema 存在误判为能力已落地
你必须区分：

- DTO 已有
- runtime 已消费
- report 已生成
- UI 已渲染
- eval 已纳入
- regression 已覆盖

---

## 失败模式 4：把 `review_assist` 的能力误当成 `structured_review` 的成熟度
你必须严格区分这两条链路。

---

## 失败模式 5：只讨论未来想要什么，不讨论现在已经有什么
这份文档必须是：

- As-Is
- Gap Analysis
- To-Be

三部分都强。

---

## 失败模式 6：把“文本风格像 formal review”误当成“系统已经是 formal review”
你必须关注：

- 输入对象
- facts
- rules
- evidence
- matrices
- artifacts
- eval
- regression
- manual review

而不是只看最终文本长相。

---

# 十一、你必须给出的结论形式

在文档最后，你必须明确给出一段总结性结论，回答以下问题：

1. 当前 repo 到底处于什么阶段？
2. 当前 repo 最真实的优势是什么？
3. 当前 repo 最真实的短板是什么？
4. 下一阶段最值得投入的 3～5 件事是什么？
5. 这 3～5 件事中，哪些属于：
   - 做实已有骨架
   - 解耦现有职责
   - 新增能力
   - 评测补齐
6. 如果只能优先做一个阶段，你最建议先做哪个阶段，为什么？

---

# 十二、你的文风要求

你的文风必须：

- 专业
- 克制
- 工程化
- 结构化
- 可执行
- 可验证
- 不宣传
- 不口号化
- 不写成泛泛论文
- 不写成产品宣传稿

你必须做到：

- 优先引用真实路径、真实模块、真实职责
- 清晰区分“事实 / 推断 / 建议”
- 不凭空虚构系统
- 不把已删除旧仓库作为事实依据
- 不把历史材料里的说法直接当成当前代码事实
- 不偷换概念，不把“名义存在”写成“稳定落地”

---

# 十三、最终提醒：你输出的不是以下三种东西

你输出的**不是**：

1. 一篇 Gemini vs 008 的优劣评论
2. 一份旧版 round1 修复任务书的改写版
3. 一份空泛的 AI 审查平台白皮书

你输出的必须是：

> **一份真正基于当前 `https://github.com/watsonk1998/008-review-control-plane` 真实状态的产品架构设计书 / 下一阶段演进设计书。**

现在开始。

附加硬约束：

1. 不得少于以下结构化输出量：
   - 至少 1 张能力成熟度总表
   - 至少 1 张历史材料差异表
   - 至少 1 张文件级改造矩阵
   - 至少 1 张 P0/P1/P2 路线表
   - 至少 1 张评测演进表

2. 对每个“当前已实现”的判断，必须尽量给出代码或文档证据。
   若证据不足，必须降级为：
   - 初步可用
   - scaffold only
   - DTO only
   - docs only
   之一。

3. 对每个“下一阶段建议”，尽量说明它属于：
   - 做实已有骨架
   - 解耦职责
   - 新增能力
   - 评测补齐
   - UI / contract 对齐
   中的哪一类。

4. 对每个关键模块，尽量回答：
   - 当前职责
   - 当前成熟度
   - 当前问题
   - 下一阶段动作
   - 为什么它优先级是 P0/P1/P2

5. 若你发现某项能力在 README 中出现，但代码未见充分实现证据：
   你必须显式指出“文档存在领先于实现”的情况。

6. 若你发现某个 DTO / schema 已出现，但 runtime、UI、eval 没有形成闭环：
   你必须显式指出“契约存在，但系统级能力未完全贯通”。

7. 若你对某一部分无法确认：
   必须诚实写出不确定性来源，而不是补全想象。