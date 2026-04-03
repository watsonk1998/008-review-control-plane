## 1. 总体结论

这次差距，**主因不是“Gemini 模型更强”这么简单**，而是 **008-review-control-plane 当前的产品定位、输入可视域、检索组织方式、审查方法和中间结构都更接近“辅助总结”而不是“正式审查”**。仓库 README 已明确说它“不再把能力重心放在审查器本体”，而是定位为 review control plane；`planner.py` 也把 DeepResearchAgent 边界写成 `planner/router/coordinator only, not the final domain reviewer`；`known-limitations.md` 进一步直接写明“审查辅助不是正式审查结论”。代码里，`_run_review_assist` 最终只把 `chunks[:8]`、`documentPreview[:4000]` 和被截断到 15000 字符的综合输入交给 LLM，并要求输出“辅助审查要点”“非正式审查结论”；`llm_gateway.py` 里的摘要提示词也把角色定义成“谨慎的工程知识整理助手”。这套设计天然会更保守、更摘要化，也更容易漏掉跨章节、跨法规、跨工程场景的深层问题。([GitHub][1])

从结果形态看，**008 能抓住一些显性硬伤**，比如应急预案文题不符、重复章节、危大专项方案缺失、工期逻辑矛盾；但 **Gemini 已经进入“L1/L2/L3 分层审查 + 法规推演 + 工程推断 + 可操作整改”的层级**，不仅指出“有没有写”，还在判断“这在法律底线、规范深度、现场实施上是否成立”。这更像一个真正的审查流程，而不是读文档后生成一份意见摘要。 

我先直接回答你最后列的 5 个关键问题：

* **1）008 当前更像“审查器”还是“总结器”？**
  更像 **“审查辅助总结器”**。因为它的定位、提示词、链路和测试标准都把目标设成“辅助审查要点”，而不是“结构化正式审查”。([GitHub][1])

* **2）Gemini 的优势主要来自模型更强，还是审查方法不同？**
  我判断 **审查方法/上下文组织差异占大头，模型差异占次要**。粗略估计，**60%–70% 来自方法与架构，30%–40% 来自模型能力**。因为 008 在输入、召回、结构化规则、中间表示上先天就没把“正式审查”做出来。([GitHub][2])

* **3）008 最应优先补强什么？**
  如果只能在“输入质量、检索召回、规则命中、prompt、报告生成”里选一个，我选 **规则命中**；但严格说，真正的 P0 不是孤立的“规则命中”，而是 **“结构化抽取 + 规则命中”** 一起补。没有这个核心，系统永远只是总结器。([GitHub][3])

* **4）如果只能做三件最有价值的改进？**
  第一，**把 review_assist 拆成真正的 structured_review 流程**；第二，**升级文档解析，保留章节/表格/附件可见性**；第三，**建立 policy pack / rule pack + issue schema + 评测集**。

* **5）哪些“看起来有效”的单案例修补不该做？**
  不该做的是：**为这个样本硬编码“煤气区域”“50t汽车吊”“防火安全重复”“高温中暑预案标题”等特征**；也不该只模仿 Gemini 的行文风格，或者单纯靠换更大模型、加更长 prompt 来“看起来更像专家”。

---

## 2. 三份材料的结构化对比

### 2.1 原始施组里已经存在的关键信号

原始施组本身已经给出很多高价值信号：
它明确写了 **4-2/4-4 行车施工区域为煤气区域**，明确采用 **50t 汽车吊**，计算起重量 **2.86t**；又写了 **单台行车停机改造时间为 7 天**，劳动力安排是 **每台车 37 人**；目录里还直接出现 **“第五节 防火安全”** 和 **“第七节 防火安全”** 两个同名小节；附件部分列出 **施工网络进度表** 和 **施工总平面布置图**。换句话说，很多后续争议点并不是“模型凭空脑补”，而是原文已经埋了明确线索。   

还有一个很关键的信号：原文里“方案编制实施计划”目前只列了 **施工组织设计**，附件标题有，但从当前文本提取视角看，附件实体内容并没有被完整读到。这会直接影响系统能否判断平面布置、进度网络、吊装站位等问题。

### 2.2 Gemini 审查结果是什么类型

Gemini 的产出不是普通 checklist。它把问题分成 **L1（法律法规底线/重大隐患）—L2（标准规范约束）—L3（项目特异性与可操作性）** 三层，已经具备“正式审查逻辑骨架”：
L1 里谈危大工程判定、煤气区域重大危险源、起重机站位承载力、特种作业资质；L2 里谈成本管理计划、消防间距与平面图落图、停送电/LOTO；L3 里谈 7 天窗口与 37 人资源矛盾、高精度安装验收盲区、EMI 接地工法、应急接应路线闭环。它更像 **“法规推演 + 工程专家推理”** 的复合输出。   

### 2.3 008 项目审查结果是什么类型

008 这份结果也不是没价值。它抓到了 6 类很重要的问题：
应急预案文题不符、危大专项方案缺失、安全章节重复、工期逻辑矛盾、关键安全措施不详、附件内容缺失，并给了高/中/P1-P3 的整改排序。
但它自己的“审查对象与范围”已经说明，依据是 **“文档目录、前部预览及分块审查笔记”**，不是“整份原文全文 + 依据全文的深审”。因此它的输出类型更像 **“显性缺陷归纳 + 结构化报告生成”**。 

### 2.4 三份材料放在一起后的结论

所以三者并不是简单“谁对谁错”。更准确地说：

* **原始施组** 提供了大量显性信号；
* **008** 把显性缺陷抓出来了一部分，但大多停在“文档问题/基础合规问题”层；
* **Gemini** 则把这些显性信号进一步串成了 **法律后果、规范缺口、现场实施风险** 三层链条。  

---

## 3. 差距的直接表现

### 3.1 Gemini 抓到了，而 008 没抓到的

第一类，是 **L1 级重大风险的升级判断**。
Gemini 不只说“有吊装”，而是进一步把 **50t 汽车吊 + 2.5t/2.86t 吊物** 推成 **危大工程法定程序问题**；不只说“煤气区域动火”，而是升级成 **煤气中毒/窒息/燃爆重大危险源辨识缺失**；还提出 **特种作业人员资质刚性准入**。这些在 008 结果里都没有被单独、明确、成体系地提出。  

第二类，是 **L2 规范深度**。
Gemini 抓到 **成本管理计划缺失**、**消防间距要求未落到平面图**、**停送电/LOTO 过于粗放**；008 虽然引用了规范，但并没有把这些规范要求转成对应的具体审查项。

第三类，是 **L3 工程实施层推理**。
Gemini 抓到 **7 天停机窗口与 37 人配置之间的资源逻辑矛盾**，并进一步推到小时级微观进度图、吊装-电气交叉避让；还抓到 **高精度对中/热装/ITP 盲区**、**变频改造 EMI 接地工法落地**、**应急接应路线闭环**。008 在这些地方几乎没有展开。 

### 3.2 008 抓到了，而 Gemini 没有单独强调的

008 对 **文本硬伤** 更直接：
它把 **应急预案标题与内容错配**、**“第五节/第七节 防火安全”重复**、**工期表述自相矛盾** 直接拎成高/中等级问题。这些都是原文里可以直接坐实的硬伤。Gemini虽然有提到预案同质化和消防章节，但没有像 008 这样把“编辑质量失控”单独拎成一个显性结论。  

不过，008 里的 **“附件内容缺失”** 这条，我认为要谨慎。
从原文看，附件标题是存在的；问题更可能是 **当前解析链路没有把图纸/图像型附件读出来**，而不一定是作者真的没附。也就是说，这条发现里混合了 **文档缺陷** 和 **系统可视域缺陷** 两种可能。 ([GitHub][4])

### 3.3 严重度分级、依据引用、论证深度、建议可执行性的差异

**严重度分级**：
Gemini 的 L1/L2/L3 是“审查层级”，天然带有法定底线语义；008 的“高/中/提示”是报告层严重度，不等于法律层级。前者更适合正式审查，后者更适合辅助输出。 

**依据引用**：
008 有规范引用，但多是“挂依据”，不是“条文—事实—结论”的闭链；Gemini 更接近把条文门槛、现场事实和整改动作串起来。 

**论证深度**：
008 多数地方停在“发现缺项/矛盾”；Gemini 经常继续往下推：“这会触碰哪条底线”“现场会怎么失效”“要补哪类计算/程序/图纸”。 

**建议可执行性**：
Gemini 的整改建议更像施工管理动作单；008 的建议更像报告级整改条目。两者都能用，但 Gemini 更接近现场执行层。 

### 3.4 两者分别更像哪种系统输出

* **008**：显性缺陷归纳 + checklist 式审查 + 报告生成式总结。
* **Gemini**：深度法规推演 + 工程专家推理 + 分层审查报告。

这是两种方法论差异，不只是文风差异。 

---

## 4. 差距形成的根因分析

### 输入层

最核心的问题，是 **008 没有“看到一份真正可审查的文档对象”**，而是只看到了一个被压扁后的文本投影。

`DocumentLoader` 对 `.docx` 的处理就是 `docx2txt.process()`，不行再回退到 `python-docx` 的段落拼接；对 PDF 则是 `pdfplumber` 纯文本抽取。它**不保留章节层级、表格单元格关系、图示语义、页眉页脚清洗、附件可见性状态、图片/图纸内容**。而这份施组恰恰大量依赖 **目录、表格、流程图、吊装示意图、总平面布置图、风险清单表、应急预案表单**。因此系统输入一开始就被“降维”了。([GitHub][4])

而且 `_run_review_assist` 里对原文的直接可视域只有 **前 4000 字**；GPT Researcher 本地文档上下文只拿 **前 24000 字**；最终综合时又只保留 **前 8 个 chunks**，并把综合输入整体裁到 **15000 字符**。这意味着：即便底层检索拿回很多内容，最后能进入终审 LLM 的上下文仍然非常窄。对于一份有大量后半段安全/应急/资源/附件内容的施组来说，这个裁剪非常致命。([GitHub][2])

这也解释了一个非常具体的现象：008 结果写“附件内容缺失”，但原文至少列出了附件 1/2；更大的可能是 **系统没把附件图纸读出来**。所以这里不是单纯“作者缺附件”，而是 **解析层把“未读到”误当成了“文档没有”**。这类误判如果不区分，会污染后续审查。 ([GitHub][4])

### 检索 / 召回层

008 的检索也不是为“正式审查”设计的。
`router.py` 里 `review_assist` 默认走 `building_municipal` 数据集；只有 query 本身出现“条例/法律/法规”才切到 `laws_regulations`。这说明它的法规召回是 **关键词启发式**，而不是按文档类型、专业类型、危大场景自动装载对应政策包。([GitHub][5])

更关键的是，即使 FastGPT 侧能以 `mixedRecall`、`usingReRank=True`、`limit=5000` 检索很多 chunks，`_run_review_assist` 最终只取 `chunks[:8]` 进入综合；`llm_gateway.summarize_chunks()` 也是只拼前 8 个 chunks。也就是说，**召回很多，不等于真正参与推理很多**。大量法规和原文证据在进入“最终判断”前就已经被抛弃了。([GitHub][6])

此外，GPT Researcher 的本地文档研究也只是把提取出的纯文本前缀拼成上下文，并没有做“施组全文 + 依据全文”的联合证据图。它是“本地文档研究”，不是“面向规则的双边比对”。因此 008 缺的不是一个更强的搜索按钮，而是 **法规依据全文、适用条件、证据片段、规则命中** 之间的结构性连接。([GitHub][7])

### 审查方法层

008 当前的 `review_assist` 方法，本质上是：

**检索 chunks → 调 DeepTutor 解释 → 调 GPT Researcher 做本地研究 → 让 LLM 综合成“辅助审查要点”**。
这不是“正式审查方法”，而是“辅助整理方法”。([GitHub][2])

它缺少正式审查最关键的三个中间层：

1. **字段抽取层**：把施组中的工程类型、起吊重量、危险区域、临电、动火、工期、劳动力、附件状态等关键字段抽出来。
2. **规则命中层**：把这些字段去匹配危大规则、重大隐患清单、施组规范、消防规范、临电规范、特种设备规则。
3. **证据分层层**：区分“文本硬证据”“规范硬约束”“工程合理推断”“无法判定待补证据”。

没有这三层，LLM 只能基于有限上下文做自由生成，自然更像“总结器”。而且 `known-limitations.md` 里自己也承认，DeepTutor 在 008 中更适合“知识问答/解释型能力服务”，不是完整审查平台。([GitHub][8])

### 架构层

从架构文档和 README 看，这个项目现在的第一目标就是 **control plane**，不是 **formal reviewer**。
README 明确写它的重心不是“审查器本体”；`architecture.md` 把角色定义为 orchestrator + adapters + artifacts；而“可扩展方向”里才把 **formal review pack registry、审查规则执行器、结构化 issue schema、审查报告导出** 列为未来方向。也就是说，**你现在看到的差距，本质上是“产品阶段差距”**。([GitHub][1])

再看领域模型，`domain/models.py` 只有 `knowledge_qa / deep_research / document_research / review_assist` 这些通用 TaskType，没有 `ReviewIssue`、`RuleHit`、`EvidenceSpan`、`SeverityLayer` 之类的结构化审查对象。没有这些对象，系统就很难在运行时稳定地表达“抓到了什么、依据是什么、是硬证据还是推断、为什么判为 L1/L2/L3”。([GitHub][9])

所以从架构上说，008 目前不是“坏掉的审查器”，而是 **还没被做成审查器**。它首先是一个多能力编排底座。你把它拿来做正式审查，自然会感觉“浅”。([GitHub][1])

### 代码实现层

我重点看了这些关键文件：
`README.md`、`docs/architecture.md`、`docs/known-limitations.md`、`docs/testing.md`、`apps/api/src/services/document_loader.py`、`apps/api/src/orchestrator/{planner,router,deepresearch_runtime}.py`、`apps/api/src/adapters/{llm_gateway,fastgpt_adapter,gpt_researcher_adapter,deeptutor_adapter}.py`、`apps/api/src/domain/models.py`。
我**没有逐行核查** `apps/web` 前端组件、全部 tests 和所有 scripts，所以对前端展示层的判断保守；但已经覆盖了 **输入范围、路由决策、审查深度、报告风格** 的关键后端链路。

具体到模块：

* **决定输入范围的文件**
  `document_loader.py` 决定“文档被看成什么”；`gpt_researcher_adapter.py::_build_document_context` 决定本地文档进入研究时只取前 24000 字；`deepresearch_runtime.py::_run_review_assist` 决定只拿 4000 字 preview 和 8 个 chunks。([GitHub][4])

* **决定审查深度的文件**
  `router.py` 决定默认数据集和能力链；`fastgpt_adapter.py` 决定检索是 chunk 导向；`planner.py` 明确 DeepResearchAgent 不是 final domain reviewer；`deepresearch_runtime.py` 决定最终只是做一次辅助综合。([GitHub][5])

* **决定最终报告风格的文件**
  `llm_gateway.py` 的系统角色是“谨慎的工程知识整理助手”；`deepresearch_runtime.py` 的最终 system prompt 是“你是审查辅助总控。输出辅助审查要点，并明确写出非正式审查结论”；`docs/testing.md` 对“审查辅助”的验证标准也只是检查是否包含“辅助审查要点”“不是正式审查结论”以及几个 artifacts。([GitHub][10])

* **让系统偏向“摘要式”而不是“审查式”的关键实现**
  不是某一个 bug，而是这几个决定叠加：**纯文本解析、启发式数据集路由、chunk 型检索、8 chunk 截断、4000/24000/15000 截断、辅助审查 prompt、缺失 issue schema**。这些共同把系统推向“总结器”。([GitHub][4])

**最该改的文件/模块**，我会优先点名：

1. `apps/api/src/services/document_loader.py`
2. `apps/api/src/orchestrator/deepresearch_runtime.py`
3. `apps/api/src/orchestrator/router.py`
4. `apps/api/src/adapters/llm_gateway.py`
5. `apps/api/src/adapters/gpt_researcher_adapter.py`
6. `apps/api/src/domain/models.py`
7. `docs/testing.md` 对应的评测与测试用例体系

### 模型 / 提示词层

模型差异当然存在。
更强的模型，在 **长链法规推理、跨章节归纳、工程常识补全、隐性风险联想** 上通常更好；Gemini 的输出里确实表现出这一点。
但如果输入只剩 8 个 chunks、4000 字 preview、被压扁的纯文本，哪怕换更强模型，也还是“受限地更聪明”，而不会突然变成正式审查器。([GitHub][2])

008 当前 prompt 还有一个明显导向：
它持续把模型放在“谨慎整理”“不足以得出结论”“辅助审查”“非正式结论”的角色里。这对减少胡编是好的，但副作用就是 **不去主动做审查层推断**。同时，它没有强约束要求模型：

* 必须抽取关键字段；
* 必须判定危大工程；
* 必须识别重大事故隐患；
* 必须区分“文本硬证据”与“工程推断”；
* 必须为每条意见绑定文档证据和规范证据。

所以 prompt 不是“没优化”，而是 **目标函数就不是正式审查**。([GitHub][10])

---

## 5. 哪些差距属于“更深推理”，哪些差距属于“系统漏检”

### 5.1 系统漏检：本该直接抓到的

这些问题，不需要特别强的模型，也不该靠专家灵感：

* **重复章节名**：“第五节 防火安全”“第七节 防火安全”。
* **工期逻辑冲突**：既写 2026-04-01 开工，又写以甲方通知为准。
* **危大专项方案计划缺失**：至少从当前文本视角，没有看到对应专项方案计划。
* **应急预案标题/内容错配**。
* **附件图纸当前不可见**：至少系统应该先判成“未读到/待人工确认”，而不是直接断言“缺失”。

这些都更像 **系统漏检或系统判定方式不对**，不是深推理问题。   

### 5.2 更深推理：Gemini 真正拉开差距的地方

这些不是简单查重或正则能搞定的，而是需要“事实—规范—现场”串联：

* **煤气区域 ≠ 只有动火管理，还意味着防毒/防窒息/燃爆监测逻辑**；
* **50t 汽车吊 + 吊装场景 ≠ 只有吊重校核，还意味着站位承载力和程序合规**；
* **7 天窗口 + 37 人配置 ≠ 只是一组数字，还意味着资源-空间-工序冲突**；
* **变频改造 ≠ 只写了屏蔽层接地，还要看抗干扰落地工法是否靠谱**；
* **应急预案 ≠ 有模板就行，还要闭合现场接应路线、抢险前置条件、事故类型差异**。

这些属于 **更深的工程推理**，也是 008 现阶段最薄弱的部分。  

### 5.3 合理增强与过度推断要分开

Gemini 里有不少 **合理增强**，比如：
把煤气区域升级为重大危险源、把站位承载力补成必查项、把 7 天/37 人推成资源风险，这些都很合理。

但也有一些地方需要标成 **“建议性工程增强”，不是硬性文本缺陷”**，例如：
“每小时一次检测”、某个具体数量的空气呼吸器、必须用某一种 EMC 接地夹、必须出某张路线图。
这些建议很多是好建议，但**不应伪装成原文已经直接违反的硬缺陷**。
未来系统一定要把这两类分开：
**硬证据缺陷**、**规范硬约束缺陷**、**合理工程增强建议**。

---

## 6. 对 008 项目的改进建议

### 6.1 架构改进

核心不是继续堆 agent，而是把“审查”做成一条**结构化流水线**：

**文档解析层 → 事实抽取层 → 规则命中层 → 证据归档层 → LLM 解释层 → 报告组装层**

建议引入 5 类核心对象：

1. **PolicyPack**：按文档类型和专业场景装载规则。
   例如：施工组织设计 pack、一般施工方案 pack、危大专项方案 pack、监理规划 pack；再叠加机电安装、起重吊装、煤气区域、临时用电、动火、特种设备等子 pack。

2. **EvidencePack**：法规全文、条款适用条件、强制/建议级别、严重度映射。

3. **ExtractedFacts**：从施组抽出的结构化事实。
   如：起重量、起重设备型号、危险区域、临电方案状态、动火区域、停机窗口、劳动力、附件状态、预案列表等。

4. **RuleHit / IssueCandidate**：规则命中结果。
   区分 direct_hit / inferred_risk / visibility_gap。

5. **FinalIssue**：报告级问题。
   应包含 `layer(L1/L2/L3)`、`severity`、`finding_type(硬证据/工程推断)`、`doc_evidence`、`policy_evidence`、`recommendation`、`confidence`。

同时，建议 **保留现在的 `review_assist`**，但新增一个真正的 `structured_review` task type。
`review_assist` 继续做辅助总结；`structured_review` 才承担正式审查能力。这样不会把 control plane 现有价值全推翻，也不会继续拿“辅助能力”硬扛“正式审查”。这个方向其实已经和仓库文档里的“未来增加 formal review pack registry / rule executor / issue schema”一致。([GitHub][3])

### 6.2 代码改进

我建议新增一个专门的 review 子域，而不是继续把逻辑堆在 `deepresearch_runtime.py` 里。可以像这样拆：

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
```

**具体要改的点：**

* `document_loader.py`
  升级为返回 `DocumentParseResult`，至少保留：

  * heading 层级
  * table 结构
  * figure / image / attachment 占位
  * appendix 状态
  * 页眉页脚/重复内容清洗
  * “不可读附件”状态标记

* `deepresearch_runtime.py`
  不要再把 `review_assist` 的最终输入做成一个被截断的 JSON 大包。
  改为多阶段：

  1. parse
  2. extract facts
  3. run rules
  4. ask LLM only for ambiguous reasoning and wording
  5. build report

* `router.py`
  从“按 query 关键词推数据集”升级为“按文档类型 + 专业标签 + policy pack 选择”。
  `review_assist` 默认指向 `building_municipal` 的做法过粗。([GitHub][5])

* `llm_gateway.py`
  不再让它承担“从碎片里拼一个审查结论”的主职责。
  它应该接受 `IssueCandidate[]` 和 `Evidence[]`，做解释、归并、去重、润色，而不是做第一性判断。

* `gpt_researcher_adapter.py`
  如果继续保留，建议把它从“直接吃前 24000 字”改成“按 section graph 和目标问题分段研究”。([GitHub][7])

* `domain/models.py`
  新增 `ReviewIssue`, `RuleHit`, `EvidenceSpan`, `ReviewLayer`, `FindingType`, `AttachmentVisibility`。
  没有这些对象，后面评测、回归和人工复核都会很痛苦。([GitHub][9])

### 6.3 审查流程改进

建议把正式审查分成明确的 4 层，而不是一个大 prompt：

**L0：可视域检查**
系统先判断：哪些内容读到了，哪些没读到，哪些是图片/图纸/附件但未解析。
这一步可以避免把“系统没看见”误判为“文档没有”。

**L1：硬证据与强约束规则**
例如：

* 重复章节
* 专项方案计划为空
* 起重吊装是否触发危大规则
* 特种作业人员证照要求是否出现
* 平面图是否可见
* 关键附件是否可见

这里尽量用确定性规则，不依赖 LLM。

**L2：条文适用与规范差距**
用规则筛出的事实去检索适用条文，形成“事实—条文—缺口”。

**L3：工程推理与整改编排**
只在这个阶段使用 LLM 进行现场可操作性、资源-工序冲突、风险升级、整改排序的推理。
同时强制模型标记：
这是“硬证据”、还是“工程推断”、还是“建议性增强”。

还建议增加 4 个专门的 artifact builder：

* **章节结构图**
* **危大识别矩阵**
* **规则命中矩阵**
* **冲突矩阵**（工期-资源、危险源-措施、附件-审查项）

这四个中间产物会大幅提升可解释性，也更容易做回归测试。

### 6.4 评测改进

现在 `docs/testing.md` 对“审查辅助”的验证，重点还是 **链路跑通、输出包含某些固定短语、工件文件生成**，这离“审查效果评测”还差很远。([GitHub][11])

我建议建立一套**跨文档类型**的评测体系，而不是拿这一个冷轧厂施组做金标准：

**样本池至少覆盖**：

* 施工组织设计
* 一般施工方案
* 危大专项方案
* 监理规划 / 审查辅助材料
* 机电安装类、土建类、钢结构类、临电类、起重吊装类

**指标至少包括**：

1. **问题召回率**
   是否找到标注问题。

2. **重大问题命中率**
   尤其是 L1 / 重大事故隐患。

3. **危大识别命中率**
   文档里是否识别到危大工程、是否要求专项方案。

4. **依据引用准确率**
   条文是否适用、引用是否正确。

5. **硬证据准确率**
   直接可证问题的误报/漏报。

6. **工程推断率与过度推断率**
   推断是否合理，是否越界。

7. **严重度校准准确性**
   L1/L2/L3 或 high/medium/low 是否合适。

8. **建议可执行性**
   整改建议是否能落地。

9. **可解释性评分**
   问题—证据—依据—建议链是否完整。

10. **附件可视域正确率**
    “缺失”与“未解析”是否区分正确。

评测方法上，建议同时做：

* **端到端评测**
* **模块级消融**（parser / retriever / rule engine / LLM / report builder）
* **跨模型对照**
* **跨 pack 对照**

这样才能知道差距到底来自哪里，而不是每次都把锅甩给模型。

---

## 7. 按优先级排序的改进路线图

### P0：必须先做

**P0-1：把“辅助审查”与“正式审查”分开**
新增 `structured_review`，不要继续让 `review_assist` 承担正式审查期待。

**P0-2：升级输入解析与可视域管理**
至少解决：

* 章节/表格保留
* 附件/图纸可见性标记
* 重复内容清洗
* 不再只靠 4000/24000/15000 截断后的文本前缀

**P0-3：建立最小可用的规则核**
先做 20% 最值钱的规则：

* 施组结构完整性
* 危大识别
* 重大隐患初筛
* 附件可视域
* 应急预案针对性
* 工期/资源基础冲突

### P1：很重要

**P1-1：引入 policy pack / evidence pack / issue schema**
把“规则、依据、输出”三件事解耦。

**P1-2：实现 L1/L2/L3 分层审查流程**
L1 硬规则优先，L2 规范适用，L3 工程推理补强。

**P1-3：建立标准化评测集**
不再只看“这一个样本像不像 Gemini”。

**P1-4：做 report builder 和中间矩阵**
让输出从“一篇 Markdown”升级成“可复核的审查产物”。

### P2：优化项

**P2-1：增强工程推理能力**
如资源-工序仿真、风险升级、交叉作业冲突分析。

**P2-2：增强多模态文档理解**
尤其是图纸、总平面图、进度网络图、示意图。

**P2-3：做平台化运营能力**
如 pack 管理、人工复核闭环、规则回归、误报库、标注回流。

---

## 8. 哪些建议必须避免（防止过拟合）

这些做法看起来能“立刻把这一个案例修好”，但我建议明确避免：

1. **硬编码本案例特征**
   例如：只要看到“煤气区域”就固定报“缺空气呼吸器”；
   只要看到“汽车吊”就固定报“承载力验算缺失”；
   只要看到“防火安全”重复就加一个正则专项。
   这会迅速让系统在别的文档上失真。

2. **只模仿 Gemini 的文风**
   把报告改成 L1/L2/L3 的样子，并不等于真有 L1/L2/L3 的能力。

3. **只换更大模型**
   不解决输入压缩、结构缺失、规则缺失，再大的模型也只能更会“猜”。

4. **把“系统没读到附件”当成“文档缺附件”**
   这是非常危险的假阳性来源。

5. **为这一个行业场景做专门 patch**
   比如专门为“宝钢冷轧厂行车改造”写一堆判断。
   正确做法应是抽象成可复用 pack：冶金厂区、煤气区域、起重吊装、机电改造、边生产边施工。

6. **把建议性工程优化伪装成强制性缺陷**
   如具体检测频率、具体装备数量、具体工具品牌/工法，应区分“必须”“应当”“建议”。

---

## 9. 一句话总结

**008 当前的问题，不是“模型不够强”，而是它还没有被做成一台真正的施组审查器；先补“结构化抽取 + 规则命中 + 证据分层”，再谈模型和文风，差距才会真正缩小。**

[1]: https://github.com/watsonk1998/watson-agent-squad/tree/pr-monorepo-migration/008-review-control-plane "https://github.com/watsonk1998/watson-agent-squad/tree/pr-monorepo-migration/008-review-control-plane"
[2]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/orchestrator/deepresearch_runtime.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/orchestrator/deepresearch_runtime.py"
[3]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/architecture.md "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/architecture.md"
[4]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/services/document_loader.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/services/document_loader.py"
[5]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/orchestrator/router.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/orchestrator/router.py"
[6]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/fastgpt_adapter.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/fastgpt_adapter.py"
[7]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/gpt_researcher_adapter.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/gpt_researcher_adapter.py"
[8]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/known-limitations.md "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/known-limitations.md"
[9]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/domain/models.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/domain/models.py"
[10]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/llm_gateway.py "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/apps/api/src/adapters/llm_gateway.py"
[11]: https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/testing.md "https://github.com/watsonk1998/watson-agent-squad/blob/pr-monorepo-migration/008-review-control-plane/docs/testing.md"
