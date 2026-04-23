# Hermes Review Agent 架构级解耦深度分析与底层重构蓝皮书 (Ultra-Detailed Version)

> **文档说明**：本分析报告基于对 `hermes-review-agent` 代码库内核（特别是 `assembler.py`, `pipeline.py`, `template_registry.py`, `module_bindings.py`, `normative_validity.py` 等核心调度组件）的完整代码阅读和契约 (`AGENTS.md`) 对齐，提供深入到微观代码实现的解耦、重构及剥离指南。

本项目绝不是一个简单的“单文件套壳大模型”，而是一个**高阶模块化、双轨制执行、强门禁防御的生产级审查架构**。它的工程精髓在于将“不可预测的大模型幻觉”关进了一个由纯代码、YAML 映射、和正则规则编织的严密防线内。

为了后续能够顺利剥离、复用或改造本项目，必须深刻理解以下**五个核心层级**以及它们之间的**绝对解耦边界**。

---

## 架构总览：双轨制与防线机制 (Architecture Overview)

下面是系统的全局架构图，展示了从 Web 请求到最终生成安全报告的不可逆数据流转过程，以及大模型是如何被钳制在“控制阀”之中的。

```mermaid
graph TD
    %% 前端与接入层
    User((前端 / Web)) -->|业务参数 + 文件| API_Gateway[API / Controller 层]
    
    %% 第一层：任务编译
    subgraph L1: 任务编译层 (Task Compilation)
        API_Gateway --> TaskCompiler[TaskCompiler]
        TaskCompiler -->|严格校验 & 扁平化| ReviewBrief[ReviewBrief 契约对象 <br> *Type: Enum*]
    end
    
    %% 第二层：支撑数据预组装（确定性事实搜集）
    subgraph L2: 治理层与预组装 (Governance & Pre-Assembly)
        ReviewBrief --> ProfileResolver[Profile Resolver <br> 级联分类映射]
        ProfileResolver -->|Profile ID| PackResolver[Basis Pack Resolver <br> 解析知识库依赖]
        PackResolver --> Builder[SupportPacket Builder]
        
        %% 数据源映射
        YAML[(YAML 映射 <br> profile_mapping / basis_registry)] -.->|路由| ProfileResolver
        Markdown[(外部规范库 <br> Text Chunks)] -.->|按需提取| Builder
        
        Builder -->|包含: 事实, 原文锚点, Span ID| SupportPacket[SupportPacket 支撑包 <br> *只读证据库*]
    end
    
    %% 第三层：大模型推理调度
    subgraph L3: 模板门禁与调度层 (Hermes Main Review)
        SupportPacket --> AgentRunner[Agent Runner <br> 集群执行器]
        ReviewBrief --> AgentRunner
        
        AgentRunner -->|路由过滤| TemplateRegistry{Template Registry <br> 门禁墙}
        TemplateRegistry -- "Pass" --> Agent1(Agent: 参数一致性)
        TemplateRegistry -- "Pass" --> Agent2(Agent: 结构完整性)
        TemplateRegistry -. "Block" .-> Agent3(Agent: 施组专属模板)
        
        %% 领域映射
        Bindings[(module_bindings.py <br> 领域挂载)] -.->|语义解耦| TemplateRegistry
    end
    
    %% 第四层：最高法庭裁决
    subgraph L4: Assembler 防线层 (Decision Fusion)
        Agent1 --> Findings(LLM Findings)
        Agent2 --> Findings
        Findings --> Assembler[HermesReviewAssembler <br> **系统防线**]
        
        Assembler --> Check1{Fail-Closed 检查 <br> 模块是否崩溃?}
        Check1 -- "Yes" --> Abort[熔断: 降级为预检状态]
        Check1 -- "No" --> Check2{Span ID 验证 <br> 幻觉拦截}
        Check2 -- "Invalid" --> Mark[标记为幻觉风险]
        Check2 -- "Valid" --> Check3{定级规则 <br> 数学统计}
        Check3 --> FinalGrade[输出最终安全评级]
    end
    
    %% 第五层：输出
    FinalGrade --> FinalReport[Final Report / View Model]
    FinalReport -->|CSS 洗白 / Emoji 禁用| User
```

---

## 一、 核心流水线解耦机制透视：不可变契约与单向数据流

系统通过 `HermesController` (`hermes_controller.py`) 进行总调度，严格按照五个分离的阶段执行，上一个阶段的产物是下一个阶段的**只读输入**，形成绝对的数据流单向性。

### 1. 任务编译层 (Task Compilation: `task_compiler.py`)
- **核心逻辑**：不论前端传来多少碎片化的参数（如：文件路径、业务类型 `construction_org` 或 `distribution_network`、特定规则包要求、前端标签提示），`TaskCompiler` 的唯一职责就是将它们抹平，打包成一个严格强类型的、不可变的 `ReviewBrief` 契约对象。
- **解耦意义**：后端引擎（Hermes 主审内核、008 预检引擎）对 Web 接口的变更完全免疫。如果你想把这个系统改成一个离线 CLI 工具或纯后台守护进程，你只需要实现自己的 `TaskRecord`，然后调用 `TaskCompiler.compile()`，下游的所有 Agent 和调度逻辑**零入侵**。
- **关键约束**：`ReviewBrief.review_object_type` 被严格约束为枚举类型（如 `distribution_network_special_scheme`），杜绝了非法状态流入核心层。

### 2. 治理层与 008 支撑数据预组装 (Governance & Support Pre-Assembly)
在召唤昂贵且不可控的大模型之前，系统先走一条“确定性”的基础建设路线（由 `pipeline.py` 和 Capability Facade 完成）。这一层由多个独立的 Resolver 构成，体现了极致的数据与业务逻辑分离：

```mermaid
graph LR
    Input(文档类型 & 标签) -->|1. 查询| ProfileMap[profile_mapping.yaml]
    ProfileMap -->|返回| ProfileID[Profile ID]
    ProfileID -->|2. 解析依赖| PackMap[pack_registry.yaml]
    PackMap -->|获取 ID 列表| BasisID[Basis IDs]
    BasisID -->|3. 加载原文| Registry[basis_registry.yaml]
    Registry -->|精确加载| TextChunks[Markdown Text Chunks]
    TextChunks --> Builder(生成 Support Packet)
```

- **`profile_resolver.py` (级联分类)**：根据文档类型和前端标签，读取 `profile_mapping.yaml`，解析出它属于哪个业务画像（Profile ID，如危大工程或普通施组）。这里**严禁在代码中硬编码 (No Hardcoded selection)**，所有的分类逻辑都是“查表”。
- **`basis_pack_resolver.py` (知识库挂载)**：按照 `Profile -> Pack -> Rule Pack -> Basis ID` 的路径，在 YAML 中递归解析出需要哪些外部规范。它**不全盘扫描** Markdown 文件库，而是利用内存标签索引（`tag_to_basis_ids` 映射），按需精准加载规范的原文内容（Text Chunks）。这保证了大模型的上下文窗口不会被无关规范撑爆。
- **`support_packet_builder.py` (支撑包封装)**：将提取出的客观事实、匹配到的原文规范段落、生成的防幻觉锚点（`EvidenceSpan` 对象）组装成一个只读的 `SupportPacket`。
- **解耦底线**：这一层**绝对禁止**输出任何“通过”或“不通过”的主观判断。它是大模型后续推理的“唯一合法证据库”，是一个纯粹的“事实搜集器”。

---

## 二、 模板硬门禁与调度层：Agent 集群的微服务化

拿到了 `SupportPacket`，系统开始调度大模型 (`Hermes Main Review`)。这一层实现了从“单体 Agent”到“微服务 Agent 集群”的彻底解耦。

### 1. 模板与模块的语义解耦 (`module_bindings.py`)
- 系统将整个审查业务切分为 5 个固定的结构化领域（`structure_completeness`, `parameter_consistency`, `legality_compliance`, `execution_continuity`, `evidence_validation`）。
- 所有的 Prompt Template 只是挂载在这些领域下的“插件”。`REVIEW_MODULE_BINDINGS` 字典是 template ID 到执行模块的唯一映射层。
- **关键纪律**：一个 Agent 绝对不允许跨域挂载。例如 `execution_risk_reviewer` 仅绑定到 `execution_continuity`，强行跨界会导致 prompt 语义模糊。

### 2. 硬门禁路由拦截 (`template_registry.py`)
- 在 `select_templates()` 方法中，决定哪个 Agent 上场的，**不是**靠 LLM 模糊意图或软评分（Soft Score），而是靠配置在 JSON 模板中的 `supported_document_types`。
- **运作机制**：如果当前审查的是“配电网工程方案”，那么 JSON 配置中带有 `supported_document_types: ["construction_org"]` (施组专属) 的模板会在注册表循环里被直接 `continue` 踢出。
- **解耦意义**：这构建了坚不可摧的业务墙，防止了跨业务线的数据污染。增加新业务线只需配置 JSON，系统底层路由机制无需任何 if-else 改造。

---

## 三、 Assembler 的“最高法庭”防线：对大模型的不信任机制

所有 Agent 的审查结果最终汇聚到大管家 `HermesReviewAssembler` (`assembler.py`)，这是整个系统的防线核心与最后一道解耦墙。系统默认大模型是“骗子”和“文盲”，通过以下机制约束：

```mermaid
graph TD
    LLM_Output((LLM Findings)) --> Assmbler[Assembler 审查流水线]
    Assmbler --> Step1[检查 1: 模块健康度 (Fail-Closed)]
    Step1 -- 崩溃/异常 --> Fallback[触发模块级门禁, 中断正式报告拼装]
    Step1 -- 健康 --> Step2[检查 2: 证据真实性 (Provenance)]
    
    Step2 --> Validation{Span ID 是否在底层库?}
    Validation -- Yes --> Passed[保留作为有效结论]
    Validation -- No --> Mark[标记幻觉风险并降级]
    
    Passed --> Step3[检查 3: 系统评级 (Decide Grade)]
    Mark --> Step3
    
    Step3 --> Logic{高危数量 >= 3?}
    Logic -- Yes --> Fail[裁决: Fail (未通过)]
    Logic -- No --> Pass[裁决: Pass (通过)]
```

### 1. Fail-Closed 降级防线 (模块级容错)
- **拦截机制**：在 `_check_critical_module_blocks()` 方法中，Assembler 会检查所有“实际被选中运行”的 Agent。如果用户开启了某几个模块的审查，但这些模块下所有实际运行的 Agent 都崩溃或降级了（如 API 超时、解析失败），系统会**触发模块级门禁，拒绝拼装正式报告**。
- **强制阻断**：它会降级输出一段 Markdown（“主引擎降级，未返回有效结果”），`hermes_ok` 可能会被置位 false 或引发直接中断。它绝不允许输出占位为“本模块未发现问题”的虚假安全报告（假阳性防范）。

### 2. 幻觉硬查杀机制 (`_validate_findings_provenance`)
- **证据锚定**：每一个 LLM 吐出的发现（Finding），在 Schema 约束下必须携带 `evidence_span_id`。
- **交叉验证**：Assembler 会拿着这个 ID 去底层的 `provenance_registry` 里查验。如果查无此 ID（表明是大模型凭空捏造的条目），该条目会立刻被拦截并标记为 `[幻觉风险]`，或者被强制剥夺其作为“规范问题”的定性权。大模型在这里被完全剥夺了“捏造证据”的权力。

### 3. 独立定级与归纳逻辑
- **决策剥离**：是否通过（Pass/Fail）、项目的总体安全评级，其决策权**不在 LLM 内部**。Assembler 的 `_decide_grade()` 方法掌握最终生杀大权。
- **数学裁决**：它根据高危、中危 Findings 的数量进行确定性的数学判定（例如：高危发现 ≥ 3 强制判定 Fail，触发熔断）。
- **执行摘要纯净化**：`_decide_executive_summary()` 只允许输出核心主结论（如：“本次审查已由专业主审组件裁决完成，总体评级结论为：**X**”）。严格禁止在 prose summary 中混入统计句子，防止 LLM 瞎编覆盖率或问题总数。

---

## 四、 《编制依据》的极致正则抽取与外部隔离 (Normative Extraction)

针对被审文档《编制依据》章节的验证，系统在 `normative_validity.py` 中实现了一个完全脱离大模型文本对话的微型状态机：

### 1. 免疫噪音的精准抽取
- **抗干扰分割**：面对 PDF 识别造成的表格乱码（将表格渲染为带竖线的 markdown 行），`_split_reference_candidates` 实施了硬提取门禁。任何包含多个 `|` 的片段均按噪音抛弃或按单元格独立分割，防止把整块表格误认为一个长标准名。
- **正则捕获**：利用 `_NORMATIVE_CODE_PATTERN` 精准捕捉 `GB/T`、`DL/T`、`DBJ`、`Q/CSG` 等 30 余种国标、行标、地标及企标代号。

### 2. 防干涉门禁 (`_is_standard_normative`)
- 在提取后，通过硬编码数组过滤掉所有以《条例》、《办法》、《规章》、《...法》结尾的文件。
- **核心原则**：明确系统的能力边界，确保核验对象**只有**“技术标准规范”，行政命令和法律文本绝不进入现行有效性核验流。判断顺序极其严苛（编号检查绝对优先）。

### 3. 极端保守的家族标准防线与联网双核验
- **模糊阻断**：如果被审文件输入了裸代号（如只有 `GB/T 6995`，缺失后缀年份或分册号），但 DuckDuckGo 网络搜索出来的是特定分册（如 `GB/T 6995.1-2008`），系统会认为“未能唯一映射”。
- **降级未知**：此时，逻辑强制阻断，不得判为 `current`，而是降级为 `unknown`（人工核验）。必须精确命中基础编号、年份、及非分册条件，才允许标记 `resolvedTitle`。

---

## 五、 四大物理剥离实操指南 (Actionable Decoupling Guide)

如果您打算在未来剥离、复用或重构该项目的核心代码，请严格遵守以下契约：

### 实操 A：如何将“执行内核”剥离为独立类库 (Extract Core Engine)
**现状**：当前架构在物理隔离上做到了极致。真正的纯粹 LLM 引擎代码位于 `external/hermes-agent/`，而 `apps/api/src/review/hermes/` 这一层实际上是带有特定业务映射的“控制面板”。
**解耦步骤**：
1. 直接 Copy `external/hermes-agent/` 文件夹。
2. 只要遵循 `ReviewBrief` 契约向其提供 `SupportPacket` 数据结构，引擎就能独立运转。
3. 所有的业务绑定、YAML 分类逻辑、危大工程特化提示词等“脏活”全都被隔绝在上层的 Controller 壳中。下层引擎永远保持 Pristine (纯净)。

### 实操 B：如何在不改 Python 代码的前提下新增业务线 (Extend to Hydraulic Engineering)
实现 100% “数据驱动”的业务横向扩展：
1. **分类扩充**：在 `config/review_basis/profile_mapping.yaml` 中新增你的类型路由（如：水利工程 `hydraulic_engineering`）。
2. **规范挂载**：在 `basis_registry.yaml` 中注册水利行业规范，并将对应的 Markdown 文本放入 `knowledge/review_basis/`。
3. **打包聚合**：在 `pack_registry.yaml` 中将其打包为 `hydraulic.base`。
4. **Agent 提示词隔离**：在 `apps/api/src/review/hermes/templates/` 中新增水利专属 JSON 模板。**最关键一步**：明确设置 `"supported_document_types": ["hydraulic_engineering"]`。
5. **绑定挂载**：将新增的模板 ID 写入 `module_bindings.py` 的对应模块下。系统底层的 `template_registry` 会自动完成路由拦截。

### 实操 C：如何平滑替换底层基座大语言模型 (Swap LLM Provider)
**现状**：系统的决策裁定（Assembler）、文件切分（Pipeline）与大语言模型的文字生成（Template + LLM Gateway）属于完全切断的两个世界。
**解耦步骤**：
1. 只需要提供一个支持结构化 JSON Schema 强制输出（Structured Outputs）的 API Gateway（如 Claude 3.5 Sonnet, OpenAI o1, DeepSeek-Coder）。
2. 替换 HTTP 请求发送器。上层的防幻觉验证（Span ID）、格式重组逻辑将无缝兼容，拦截劣质回答。

### 实操 D：确保前端渲染层的高隔离防线与 CSS 洗白 (Frontend Decoupling & CSS Sanitization)
为了防止庞大且复杂的后端生成结构拖垮浏览器渲染引擎（DOM 卡死），必须在数据边界做清洗：
- **禁止重排属性 (CSS Sanitization)**：后端的 `final_report_view_model.py` 或前端的 `StructuredReportHtml` 必须对报告 CSS 实行正则清洗。绝不信任历史载荷，必须移除 `break-inside: avoid`、`page-break-inside: avoid` 与 `content-visibility: auto`，防止长列表引发 $O(n)$ 级别的剧烈强制重排。
- **内部变量隔离**：业务内部的状态键（如 `title_detected_without_attachment_body`）必须在渲染前转化为友好的中文提示（如通过 `_INTERNAL_DESCRIPTION_KEY_LABELS` 收口翻译）。禁止任何底层技术堆栈信息泄露至前台 UI。
- **表情符号禁令**：正式报告 HTML、前端页面中绝对禁止出现 Emoji（Unicode Emoji 序列）。这确保了审查报告的严肃性和跨平台的渲染稳定性。
