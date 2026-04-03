
## 先说结论

**golden pool**
指的是一组**经过人工确认、可长期复用、可做回归基线**的高质量评测样本集合。你可以把它理解成：

> “这套系统以后每次改代码、换规则、换模型、调 parser，都要拿来复测的一池标准题。”

**mini golden cases**
指的是 golden pool 的**最小起步版**，通常是 P0/P1 阶段先做出来的 5～10 个代表性样本，用来先把评测链路跑起来，而不是一上来就建几十上百个完整基准库。

所以关系是：

> **mini golden cases = golden pool 的起始子集**
> **golden pool = 完整、持续扩充、可版本化维护的金标准样本池**

---

## 为什么这个项目一定要有 golden pool

因为你现在这个仓库，不是简单在做“生成一篇报告”，而是要把 008 从“辅助总结”升级成“结构化正式审查”。
只要开始引入：

* parser
* facts extraction
* rule engine
* evidence builder
* report builder

你就一定会遇到一个问题：

> 改动看起来更合理，但到底是“真的变好了”，还是“换了一种说法”？

没有 golden pool，你只能靠“看一两个案例感觉不错”。
有了 golden pool，才能回答：

* 危大识别命中率是不是上升了
* 附件“未解析”有没有被误报成“缺失”
* L1 问题有没有漏掉
* 规则改造后有没有把旧能力打坏
* `review_assist` 有没有被误伤

---

## 用你这个冷轧厂案例举例，golden case 里到底存什么

这个案例很适合做 **mini golden cases** 里的 1 个样本，但**不能让它等于整个 golden pool**。

因为这份原始施组里本身就有一些非常好的“基准标签素材”：

* 目录里同时出现“第五节 防火安全”和“第七节 防火安全”，属于可直接证实的重复章节问题。
* 附件 1“施工网络进度表”、附件 2“施工总平面布置图”在目录里明确列出，所以如果系统没解析到，优先应标成 `referenced_only` 或 `attachment_unparsed`，而不是直接判成“文档缺附件”。
* 文本里有 50t 汽车吊、起重量计算 2.86t、专项施工方案计划写“无”，这正适合做“危大识别 / 专项方案缺失”类规则样本。
* 工期写了“2026年4月1日开工”“实际开工日期以甲方批准为准”“单台行车停机改造时间为7天”，适合做逻辑冲突与资源约束类样本。

而 Gemini 的结果正好展示了另一类标签来源：
不是只看“文本硬伤”，而是把这些事实提升成 L1/L2/L3 的结构化问题，例如危大工程判定、煤气区域风险、地基承载力、7 天窗口与资源调配矛盾等。它可以作为**人工标注时的参考材料之一**，但不能直接等于 ground truth。

008 当前结果则适合作为**回归对照基线**：
它已经抓到应急预案文题不符、危大方案缺失、防火安全重复、工期逻辑矛盾、附件内容缺失等问题。未来 structured_review 上线后，可以直接比较“新链路相对旧链路到底提升了什么”。

---

## golden pool 里，一条 case 不是“只有一个文档”

一个真正能拿来做回归的 golden case，至少应该包含 5 类东西：

### 1. 原始输入

就是源文件本身：

* `.docx`
* 或 `.pdf`
* 或它的附件包

### 2. 元数据

告诉系统“这是什么文档”：

* `docType`
* `disciplineTags`
* `expectedPacks`
* 是否有附件
* 是否允许人工复核项

### 3. ground truth issues

也就是人工确认的问题标签。

不是写一篇散文，而是结构化数据，比如：

```json
[
  {
    "id": "ISSUE-001",
    "title": "安全章节重复",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "hard_evidence",
    "doc_evidence": ["目录-第六章-第五节防火安全", "目录-第六章-第七节防火安全"],
    "manual_review_needed": false
  }
]
```

### 4. visibility labels

专门标注“系统看见了什么 / 没看见什么”，这是这次任务书里很关键的一点。

比如这个冷轧厂案例里：

```json
{
  "attachments": [
    {
      "name": "附件1：施工网络进度表",
      "expected_visibility": "referenced_only"
    },
    {
      "name": "附件2：施工总平面布置图",
      "expected_visibility": "referenced_only"
    }
  ]
}
```

如果后续多模态 parser 能读到附件内容，再升级为 `parsed`；
但在当前阶段，绝不能一上来标成 `missing`。

### 5. 评测断言

不是所有东西都要精确字符串比对，很多时候你只需要断言：

* 必须命中某条 issue
* 不得把附件判成 missing
* 危大识别必须触发
* 至少给出 1 条 L1 问题
* `review_assist` 结果 shape 不得变化

---

## mini golden cases 怎么构建

我建议你把它理解成：

> “先做一个小而硬的种子集，先把评测系统跑起来。”

### 推荐起步规模

P0 阶段先做 **5～10 个 mini golden cases**，不要一开始追求大而全。

### 推荐起步覆盖

至少这样配：

1. **施工组织设计** 2 个

   * 一个机电安装类
   * 一个土建或钢结构类

2. **一般施工方案** 1～2 个

3. **危大专项方案** 1～2 个

4. **监理规划 / 审查辅助材料** 1 个

### 推荐起步原则

每个样本都要“带一个明确考点”，不要全选那种信息极其杂乱、什么都能测但什么都测不准的文件。

比如 mini golden cases 最适合选这种：

* 章节重复明显
* 附件引用明确但正文不可见
* 危大工程触发条件明显
* 工期和资源逻辑矛盾明显
* 应急预案标题与正文错配明显

这类样本最适合先把：

* parser
* visibility
* rule engine
* issue schema

四条链路打稳。

---

## golden pool 应该怎么一步一步构建

### 第一步：先定“评什么”，再收样本

不要先收一堆文档再想怎么评。
先定义评测轴：

#### 按文档类型

* 施工组织设计
* 一般施工方案
* 危大专项方案
* 监理规划 / 审查辅助材料

#### 按专业场景

* 机电安装
* 土建
* 钢结构
* 临电
* 起重吊装

#### 按问题类型

* 硬证据缺陷
* 危大识别
* 规范适用
* 工程推断
* 附件可视域
* 手工复核项

这样你收样本时才不会全堆在一个行业、一个问题模式里。

---

### 第二步：为每个 case 设计统一目录结构

建议直接按任务书里的思路落库：

```text
fixtures/review_eval/
  construction_org/
    electromech/
      case_001/
        source.docx
        metadata.json
        ground_truth_issues.json
        ground_truth_visibility.json
        notes.md
```

我建议你再加两个文件：

```text
        expected_facts.json
        expected_rule_hits.json
```

为什么加这两个？
因为你这个项目后面要做的不只是端到端报告，还要做模块消融。
如果只有最终 issues，没有 facts 和 rule hits，你会很难定位到底是：

* parser 坏了
* facts 没抽出来
* 规则没命中
* 还是 LLM 解释层写偏了

---

### 第三步：先写“标注规范”，再标数据

这是最容易被忽略、也是最关键的一步。

至少要先定这几条：

#### A. 什么叫一个 issue

比如：

* “重复章节”算 1 条 issue
* “危大专项方案缺失”算 1 条 issue
* “附件1、附件2不可见”是 1 条 issue，还是 2 条 visibility record

#### B. layer 怎么标

* L1：法定底线 / 重大隐患 / 程序硬约束
* L2：规范适用与编制深度差距
* L3：工程推理与现场闭环问题

#### C. finding_type 怎么标

* `hard_evidence`
* `engineering_inference`
* `visibility_gap`
* `suggestion_enhancement`

#### D. 什么时候必须打 `manual_review_needed`

例如：

* 图纸正文引用了，但系统未解析到
* 需要看示意图才能判断站位
* OCR/图片内容不完整
* 条文适用存在争议

#### E. 必须 / 应当 / 建议 怎么分

这个一定要先写清楚，否则后期很容易把工程建议标成强制缺陷。

---

### 第四步：采用“双人标注 + 一人裁决”

不要让一个人独立拍脑袋定 golden truth。

推荐流程：

1. **标注员 A**
   先标 issues / visibility / facts

2. **标注员 B**
   独立复核并指出分歧

3. **裁决人 / 资深工程师**
   对分歧项拍板，形成最终 golden version

这样做的好处是：

* 减少单人偏见
* 避免直接把 Gemini 输出当答案
* 能把“合理推断”和“过度推断”分开

---

### 第五步：给每个 case 打“版本号”

golden case 不是一劳永逸的。
随着你：

* pack 变多
* parser 变强
* 多模态能力上线
* 条文映射调整

ground truth 也可能迭代。

所以每个 case 都要有版本：

```json
{
  "caseId": "construction_org_electromech_001",
  "version": "v1.0",
  "docType": "construction_org",
  "disciplineTags": ["electromechanical", "lifting"],
  "expectedPacks": ["construction_org.base", "lifting_operations.base"]
}
```

这样你以后改标签不会把历史结果搞乱。

---

## 我建议你在这个项目里怎么落第一版

### P0：先做 5 个 mini golden cases

建议：

1. 冷轧厂这份施组
   用来测：

   * 章节重复
   * 危大识别
   * 附件可视域
   * 工期逻辑冲突
   * 应急预案错配

2. 一个一般施工方案
   用来测结构完整性与基础规范项

3. 一个危大专项方案
   用来测“应识别为专项方案且专项内容完整”

4. 一个监理规划或审查辅助材料
   用来防止 pack 误配

5. 一个“附件很多但正文不全”的样本
   专门测 visibility / manual review

### P1：扩到 20～30 个 golden pool

按照文档类型和专业标签补齐覆盖。

### P2：再往里加

* 图片型附件
* 图纸
* 扫描件
* 多模态 case
* 高争议工程推断 case

---

## 构建时最容易犯的 6 个错误

### 1. 直接把 Gemini 结果当 ground truth

不行。
Gemini 可以当参考，但不能直接当金标准。它里面也有工程增强建议和推断，必须人工裁决。

### 2. 直接把 008 当前输出当基准答案

也不行。
它适合当“旧系统基线”，不适合直接当 ground truth。

### 3. 只存最终报告，不存结构化标签

这样以后只能比“像不像”，不能比“到底哪层退化了”。

### 4. 不单独标 visibility

这是这个项目最容易误报的地方。
附件 1/2 明明在目录里有引用，如果 parser 没读到，不应直接判 missing。

### 5. 全拿同一行业场景做样本

这样会把系统训成“冷轧厂专家”，不是“通用施组审查器”。

### 6. 没有版本和裁决流程

后面谁都能改标签，评测就失去公信力。

---

## 你可以直接照着做的最小模板

### `metadata.json`

```json
{
  "caseId": "construction_org_electromech_001",
  "version": "v1.0",
  "docType": "construction_org",
  "disciplineTags": ["electromechanical", "lifting", "gas_area"],
  "expectedPacks": [
    "construction_org.base",
    "lifting_operations.base",
    "gas_area_ops.base"
  ],
  "sourceFile": "source.docx"
}
```

### `ground_truth_visibility.json`

```json
{
  "attachments": [
    {
      "name": "附件1：施工网络进度表",
      "expectedVisibility": "referenced_only",
      "manualReviewNeeded": true
    },
    {
      "name": "附件2：施工总平面布置图",
      "expectedVisibility": "referenced_only",
      "manualReviewNeeded": true
    }
  ]
}
```

### `ground_truth_issues.json`

```json
[
  {
    "id": "ISSUE-001",
    "title": "安全章节标题重复",
    "layer": "L2",
    "severity": "medium",
    "findingType": "hard_evidence",
    "manualReviewNeeded": false
  },
  {
    "id": "ISSUE-002",
    "title": "危大工程专项方案计划缺失",
    "layer": "L1",
    "severity": "high",
    "findingType": "hard_evidence",
    "manualReviewNeeded": false
  },
  {
    "id": "ISSUE-003",
    "title": "附件仅被引用但当前不可见",
    "layer": "L0",
    "severity": "info",
    "findingType": "visibility_gap",
    "manualReviewNeeded": true
  }
]
```

---

## 一句话区分

* **golden pool**：整套长期维护的金标准评测样本池
* **mini golden cases**：先用 5～10 个代表性样本把这套评测机制跑起来的种子集

如果你愿意，我下一条可以直接给你一份 **适配 008-review-control-plane 的 `fixtures/review_eval/` 目录模板 + 3 个 JSON 样例文件**。



# 008-review-control-plane mini golden cases / golden pool 构建任务书（Codex 执行版）

> 本任务书用于指导 Codex 在 `008-review-control-plane` 仓库内，先从**施工组织设计**开始，构建一套**可版本化、可回归、可扩展**的 mini golden cases / golden pool 基础设施。
> 当前仓库 README 已把 `008-review-control-plane` 明确定位为 **review control plane**，而不是把能力重心放在“审查器本体”；已实现能力中包含 `review_assist`，而不是 formal reviewer。([GitHub][1])
> 本次数据建设绑定两份真实施组及两份 Gemini deepresearch 审查结果：
> 冷轧厂施组目录中明确出现重复“防火安全”章节、附件1/附件2、施工单台行车停机改造时间为7天、施工区域为煤气区域、共22台电动机等信号；培花施组目录和正文中明确出现危大工程清单、施工方案编制计划、调蓄池开挖深度 20.05m（局部 22.05m）、微顶管长度约 37m 等强结构化信息。   
> Gemini deepresearch 结果可作为本阶段**seed labels / bootstrap labels** 的来源，但**不能冒充专家确认 gold truth**。Gemini 对冷轧厂已提出危大工程专项方案缺失、煤气区域风险辨识不足、吊车站位承载力校核缺失等深度问题；对培花已提出成本管理计划缺失、临建防火材质约束不够硬、第三方监测主体表述模糊等高价值 seed issues。 

---

## 1. 执行摘要

本阶段不做专家标注闭环，不做正式 gold truth 定版，不做多文档大规模扩池。先完成一件事：

> 在仓库里建立一套**可落地的 golden pool 目录结构 + 统一 schema + case 版本号体系 + 2 个施工组织设计 mini golden cases**。

这 2 个 case 分别是：

1. `施工组织设计-冷轧厂2030单元三台行车电气系统改造`
2. `施工组织设计-培花初期雨水调蓄池建设工程`

这一步的目标不是“证明系统已经有最终评测集”，而是把后续 `structured_review` 需要的评测基础设施搭起来，包括：

* case 元数据
* 源文件引用
* Gemini seed source 引用
* seed issues
* visibility labels
* expected facts
* expected rule hits
* evaluation notes
* 版本号与升级路径

必须明确：

* **允许**用 Gemini deepresearch 审查结果启动 seed labeling；
* **禁止**把 Gemini 结果直接写成“专家确认 gold”；
* **必须**把所有 case 版本初始命名为 `v0.1.0-gemini-seed`；
* **必须**区分 `doc_fact`、`gemini_inference`、`visibility_assumption`；
* **必须**单独保存 visibility 标签，尤其不能把“附件未解析/仅引用”直接写成 `missing`。冷轧厂施组目录明确列有“附件1：施工网络进度表”“附件2：施工总平面布置图”，因此 P0 只能标为 `referenced_only` 或 `attachment_unparsed + manual_review_needed`，不能直接标成文档缺失。

---

## 2. 任务范围与边界

### 2.1 本次要做的事情

Codex 必须完成以下事项：

1. 在仓库内创建 `fixtures/review_eval/` 及其完整子目录。
2. 为两个施工组织设计 case 建立统一的版本化目录。
3. 写出统一 schema 文件。
4. 为每个 case 生成完整的 JSON / Markdown 文件集合。
5. 将 Gemini 结果转成 seed labels。
6. 为每个 case 写出最小可用的 `expected_facts` 与 `expected_rule_hits`。
7. 为后续升级路径预留版本位。

### 2.2 本次不做的事情

本阶段**不要**做下面这些事：

1. 不把 seed case 命名为 `v1.0.0`。
2. 不把 Gemini 结果直接视为专家 truth。
3. 不补写实际 `structured_review` 代码。
4. 不建设大规模 20+ case pool。
5. 不引入复杂数据库、标注平台、DSL。
6. 不为单案例打硬编码补丁。
7. 不创建重复拷贝的大文档副本；优先保留源文件引用，而不是复制源文件。

---

## 3. 术语定义

### 3.1 golden pool

一组可长期维护、可回归测试、可版本升级的标准评测样本池。

### 3.2 mini golden cases

golden pool 的起步子集。本阶段就是做 2 个 mini golden cases。

### 3.3 seed labels

来自非专家但高质量来源的初始标注。本次来源为 Gemini deepresearch 审查结果。

### 3.4 bootstrap truth

用于先把评测链路跑起来的“启动 truth”，不是最终专家 gold。

### 3.5 visibility label

专门标记系统对附件/图纸/附表“看见了什么、没看见什么、是不是未解析”的标签层。

---

## 4. 核心原则（非协商）

1. **可用 Gemini 结果做 seed labels，但必须降级命名**
   每个 case 必须写：

   * `label_source = "gemini_deepresearch"`
   * `label_status = "seeded_unreviewed"`
   * `truth_level = "bootstrap"`
   * `review_status = "not_final"`

2. **不能把 seed case 伪装成专家 gold**
   初始版本统一为：

   * `v0.1.0-gemini-seed`

3. **必须分离 issue truth 与 visibility truth**
   issue 与附件可视域必须分成两个独立文件。

4. **必须保留 provenance**
   每条 issue 都要标明：

   * 是否来自原文直接证据
   * 是否来自 Gemini 推断
   * 是否需要人工复核

5. **不能把系统没看见当成文档没有**
   冷轧厂附件 1/2 只能先标为 `referenced_only` 或 `attachment_unparsed`，不能直接标 `missing`。

6. **必须有 case 版本号**
   版本目录必须物理存在，不只写在 metadata 里。

---

## 5. 输入材料绑定

Codex 必须以仓库内真实文件为准，优先使用以下路径：

### 5.1 冷轧厂 case

* `fixtures/copied/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx`
* `fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md`

### 5.2 培花 case

* `fixtures/copied/supervision/施工组织设计-培花初期雨水调蓄池建设工程.pdf`
* `fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-培花初期雨水调蓄池建设工程.md`

若本地真实文件名与 conversation 上传名略有差异，**以仓库实际存在路径为准**，但必须在 `source_ref.json` 中显式记录最终采用的绝对路径和相对路径。

---

## 6. 目标目录结构

Codex 必须创建以下目录树：

```text
fixtures/
  review_eval/
    README.md
    schemas/
      case_metadata.schema.json
      ground_truth_issues.schema.json
      ground_truth_visibility.schema.json
      expected_facts.schema.json
      expected_rule_hits.schema.json
      evaluation_notes.schema.json
    construction_org/
      electromechanical/
        cn_baosteel_coldrolling_crane_230235/
          v0.1.0-gemini-seed/
            case_metadata.json
            source_ref.json
            seed_sources/
              gemini_review_ref.json
            ground_truth_issues.json
            ground_truth_visibility.json
            expected_facts.json
            expected_rule_hits.json
            evaluation_notes.md
            README.md
      municipal/
        cn_puhua_rainwater_storage_pool/
          v0.1.0-gemini-seed/
            case_metadata.json
            source_ref.json
            seed_sources/
              gemini_review_ref.json
            ground_truth_issues.json
            ground_truth_visibility.json
            expected_facts.json
            expected_rule_hits.json
            evaluation_notes.md
            README.md
```

---

## 7. 为什么采用这套结构

### 7.1 `fixtures/review_eval/`

与 `fixtures/copied/` 分离：

* `fixtures/copied/` 保持源材料；
* `fixtures/review_eval/` 保存结构化评测资产。

### 7.2 `schemas/`

防止每个 case 各写一套 JSON 结构，后期不好统一消费。

### 7.3 按 `doc_type / domain / case_id / version` 分层

这能兼容未来扩展：

* 施工组织设计
* 一般施工方案
* 危大专项方案
* 监理规划

### 7.4 `source_ref.json`

不复制原始大文件，只引用源文件路径，减少冗余和版本混乱。

### 7.5 `seed_sources/gemini_review_ref.json`

明确写清 seed label 来源，后续如果换成内部复核或专家标注，可以再新增来源链。

### 7.6 `expected_facts.json`

让未来 parser / extractor 可做模块级回归。

### 7.7 `expected_rule_hits.json`

让未来 rule engine 可做模块级回归。

---

## 8. 版本号策略

### 8.1 版本格式

采用语义化版本 + 来源后缀：

* `v0.1.0-gemini-seed`
* `v0.2.0-internal-reviewed`
* `v1.0.0-expert-golden`

### 8.2 本阶段统一版本

两个 case 都必须用：

* `v0.1.0-gemini-seed`

### 8.3 版本升级规则

* 只改 README / 注释 / 文档说明：patch
* 调整 issue truth / visibility truth / facts truth：minor
* 专家重标、结构性重构：major

---

## 9. 标注来源与标签规范

## 9.1 每条 issue 的来源标签

每条 issue 都必须包含：

* `label_source_type`
* `doc_supported`
* `gemini_supported`
* `manual_review_needed`

枚举如下：

* `doc_fact`
* `gemini_inference`
* `visibility_assumption`

### 9.2 推荐判断规则

#### `doc_fact`

原文直接可以证实。
例如冷轧厂目录中“第五节 防火安全”和“第七节 防火安全”重复出现，这属于原文直接可证。

#### `gemini_inference`

Gemini 基于原文和规范推理出来，但原文不是一句话直接写明。
例如冷轧厂“危大工程专项方案缺失”“煤气区域风险辨识不足”“吊车支腿站位承载力未校核”，都可先标为 Gemini inference。

#### `visibility_assumption`

来源于文档目录、引用关系和当前解析可视域之间的差异。
例如冷轧厂附件1、附件2。原文目录明确引用了两份附件，但当前正文不可见，这应先归入 visibility，而不是 issue hard missing。

---

## 10. Case A：冷轧厂2030单元三台行车电气系统改造

## 10.1 case 基本信息

* `case_id`: `cn_baosteel_coldrolling_crane_230235`
* `doc_type`: `construction_org`
* `discipline_tags`:

  * `electromechanical`
  * `lifting`
  * `gas_area`
  * `temporary_power`
  * `hot_work`
  * `special_equipment`

## 10.2 原文中已确认的强信号

冷轧厂施组原文至少包含以下直接信号：

* 目录中重复出现“第五节 防火安全 / 第七节 防火安全”；
* 目录中有“附件1：施工网络进度表”“附件2：施工总平面布置图”；
* 工程特点里明确写“施工区域为煤气区域”；
* 共 22 台电动机需要更新；
* 施工单台行车停机改造时间为 7 天；
* 进度表述同时出现“2026年4月1日开工”和“实际开工日期以甲方批准为准”；
* 当前 008 的审查结果也已把应急预案文题不符、危大方案缺失、安全章节重复、工期逻辑矛盾、附件内容缺失列为主要问题。

## 10.3 冷轧厂 case 必须落地的 seed issues

至少写入以下 8 条：

1. 安全章节标题重复
2. 危大工程专项方案计划缺失
3. 煤气区域风险辨识不足
4. 吊车站位承载力验算缺失
5. 应急预案标题与正文错配
6. 附件被引用但当前正文不可见
7. 工期逻辑存在双重基准
8. 成本管理计划缺失

说明：

* 1、5、6、7 可以标 `doc_fact` 或 `doc_fact + gemini_supported`。  
* 2、3、4、8 先标 `gemini_inference`，并 `manual_review_needed = true`。

---

## 11. Case B：培花初期雨水调蓄池建设工程

## 11.1 case 基本信息

* `case_id`: `cn_puhua_rainwater_storage_pool`
* `doc_type`: `construction_org`
* `discipline_tags`:

  * `municipal`
  * `deep_excavation`
  * `foundation_pit`
  * `support_system`
  * `dewatering`
  * `pipe_jacking`

## 11.2 原文中已确认的强信号

培花施组原文至少包含以下强结构化事实：

* 目录中有“4.5 施工方案编制计划”“7.7 危大工程清单及安全管理措施”“11.附图附表”；
* 调蓄池规模 10400 立方米；
* 调蓄池开挖深度 20.05m，局部 22.05m；
* 微顶管长度约 37m；
* 危大工程清单章节明确写出“本工程最大开挖深度达 22.05m”“模板支撑工程最大搭设高度约 11.5m”；
* 工程方案编制计划中已经列出深基坑方案、降水施工方案等专项方案。
* Gemini 对培花给出的 seed 问题主要是：成本管理计划缺失、临建防火材质约束不够硬、第三方监测主体表述模糊。

## 11.3 培花 case 的定位

培花 case 不是纯“问题 case”，还要承担：

> **正向 rule hit case / 正样本 case**

因为它在危大识别、专项方案计划、深基坑识别上比冷轧厂完整得多，适合后续回归时验证：

* 规则能否正确命中
* 系统是否不过度误报
* positive findings 能否被保留

## 11.4 培花 case 必须落地的 seed issues

至少写入以下 4 条：

1. 成本管理计划缺失
2. 临建防火材质约束未明确到 A 级不燃材料
3. 第三方监测主体表述不够刚性
4. 危大工程识别完整（这条作为正向 rule hit 的 evaluation note，不必写成 negative issue）

---

## 12. Codex 必须创建的 schema 文件

下面这些 schema 必须创建为实际 JSON Schema 文件。
不要求做到非常复杂，但必须能约束后续 case 文件。

## 12.1 `case_metadata.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CaseMetadata",
  "type": "object",
  "required": [
    "case_id",
    "case_version",
    "schema_version",
    "title",
    "doc_type",
    "discipline_tags",
    "expected_packs",
    "label_source",
    "label_status",
    "truth_level",
    "review_status",
    "source_files",
    "seed_review_files"
  ],
  "properties": {
    "case_id": { "type": "string" },
    "case_version": { "type": "string" },
    "schema_version": { "type": "string" },
    "title": { "type": "string" },
    "doc_type": { "type": "string" },
    "discipline_tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "expected_packs": {
      "type": "array",
      "items": { "type": "string" }
    },
    "label_source": { "type": "string" },
    "label_status": { "type": "string" },
    "truth_level": { "type": "string" },
    "review_status": { "type": "string" },
    "source_files": {
      "type": "array",
      "items": { "type": "string" }
    },
    "seed_review_files": {
      "type": "array",
      "items": { "type": "string" }
    },
    "notes": { "type": "string" }
  }
}
```

## 12.2 `ground_truth_issues.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "GroundTruthIssues",
  "type": "array",
  "items": {
    "type": "object",
    "required": [
      "id",
      "title",
      "layer",
      "severity",
      "finding_type",
      "label_source_type",
      "doc_supported",
      "gemini_supported",
      "manual_review_needed",
      "status"
    ],
    "properties": {
      "id": { "type": "string" },
      "title": { "type": "string" },
      "layer": {
        "type": "string",
        "enum": ["L0", "L1", "L2", "L3"]
      },
      "severity": {
        "type": "string",
        "enum": ["high", "medium", "low", "info"]
      },
      "finding_type": {
        "type": "string",
        "enum": [
          "hard_evidence",
          "engineering_inference",
          "visibility_gap",
          "suggestion_enhancement"
        ]
      },
      "label_source_type": {
        "type": "string",
        "enum": [
          "doc_fact",
          "gemini_inference",
          "visibility_assumption"
        ]
      },
      "doc_supported": { "type": "boolean" },
      "gemini_supported": { "type": "boolean" },
      "manual_review_needed": { "type": "boolean" },
      "status": {
        "type": "string",
        "enum": ["seeded_unreviewed", "reviewed", "deprecated"]
      },
      "notes": { "type": "string" }
    }
  }
}
```

## 12.3 `ground_truth_visibility.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "GroundTruthVisibility",
  "type": "object",
  "required": ["attachments"],
  "properties": {
    "attachments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "expected_visibility",
          "manual_review_needed"
        ],
        "properties": {
          "name": { "type": "string" },
          "expected_visibility": {
            "type": "string",
            "enum": [
              "parsed",
              "attachment_unparsed",
              "referenced_only",
              "missing",
              "unknown"
            ]
          },
          "manual_review_needed": { "type": "boolean" },
          "notes": { "type": "string" }
        }
      }
    }
  }
}
```

## 12.4 `expected_facts.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ExpectedFacts",
  "type": "object",
  "required": ["facts"],
  "properties": {
    "facts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "key",
          "value",
          "value_type",
          "support_type"
        ],
        "properties": {
          "key": { "type": "string" },
          "value": {},
          "value_type": { "type": "string" },
          "support_type": {
            "type": "string",
            "enum": ["doc_fact", "gemini_inference", "derived"]
          },
          "notes": { "type": "string" }
        }
      }
    }
  }
}
```

## 12.5 `expected_rule_hits.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ExpectedRuleHits",
  "type": "array",
  "items": {
    "type": "object",
    "required": [
      "rule_id",
      "expected_status",
      "expected_match_type"
    ],
    "properties": {
      "rule_id": { "type": "string" },
      "expected_status": {
        "type": "string",
        "enum": ["hit", "pass", "manual_review_needed"]
      },
      "expected_match_type": {
        "type": "string",
        "enum": ["direct_hit", "inferred_risk", "visibility_gap"]
      },
      "notes": { "type": "string" }
    }
  }
}
```

## 12.6 `evaluation_notes.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluationNotesMeta",
  "type": "object",
  "required": ["purpose", "primary_checks", "known_limitations"],
  "properties": {
    "purpose": {
      "type": "array",
      "items": { "type": "string" }
    },
    "primary_checks": {
      "type": "array",
      "items": { "type": "string" }
    },
    "known_limitations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "next_review_actions": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

---

## 13. 每个 case 必须创建的文件

每个 case 都必须实际生成以下文件，不允许只建空目录：

1. `case_metadata.json`
2. `source_ref.json`
3. `seed_sources/gemini_review_ref.json`
4. `ground_truth_issues.json`
5. `ground_truth_visibility.json`
6. `expected_facts.json`
7. `expected_rule_hits.json`
8. `evaluation_notes.md`
9. `README.md`

---

## 14. Codex 可执行的文件内容模板包

下面这些内容必须一并写入仓库，作为初始化模板与 starter data。

---

## 14.1 `fixtures/review_eval/README.md`

```markdown
# review_eval

本目录存放 `008-review-control-plane` 的结构化评测样本池（golden pool）。

## 当前状态
当前样本均为 bootstrap 数据，不是最终专家确认 gold truth。

## 版本语义
- `v0.1.0-gemini-seed`：基于 Gemini deepresearch 结果构建的 seed labels
- `v0.2.0-internal-reviewed`：内部人工复核后的版本
- `v1.0.0-expert-golden`：专家确认后的正式 gold 版本

## 非协商原则
1. 不得把 Gemini 结果直接当作专家 truth
2. 必须区分 issue truth 与 visibility truth
3. 必须显式记录 provenance
4. 不得把“未解析附件”直接标成“缺失”

## 当前已初始化 case
- construction_org / electromechanical / cn_baosteel_coldrolling_crane_230235 / v0.1.0-gemini-seed
- construction_org / municipal / cn_puhua_rainwater_storage_pool / v0.1.0-gemini-seed
```

---

## 14.2 冷轧厂 `case_metadata.json`

```json
{
  "case_id": "cn_baosteel_coldrolling_crane_230235",
  "case_version": "v0.1.0-gemini-seed",
  "schema_version": "v1",
  "title": "施工组织设计-冷轧厂2030单元三台行车电气系统改造",
  "doc_type": "construction_org",
  "discipline_tags": [
    "electromechanical",
    "lifting",
    "gas_area",
    "temporary_power",
    "hot_work",
    "special_equipment"
  ],
  "expected_packs": [
    "construction_org.base",
    "electromech_installation.base",
    "lifting_operations.base",
    "gas_area_ops.base"
  ],
  "label_source": "gemini_deepresearch",
  "label_status": "seeded_unreviewed",
  "truth_level": "bootstrap",
  "review_status": "not_final",
  "source_files": [
    "fixtures/copied/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx"
  ],
  "seed_review_files": [
    "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md"
  ],
  "notes": "本版本基于原始施组与 Gemini deepresearch 结果生成，不等同于专家确认 gold truth。"
}
```

---

## 14.3 冷轧厂 `source_ref.json`

```json
{
  "source_document": {
    "relative_path": "fixtures/copied/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx",
    "doc_type": "construction_org",
    "file_kind": "docx"
  },
  "review_seed_documents": [
    {
      "relative_path": "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md",
      "source_type": "gemini_deepresearch_markdown"
    }
  ]
}
```

---

## 14.4 冷轧厂 `seed_sources/gemini_review_ref.json`

```json
{
  "seed_source": "gemini_deepresearch",
  "relative_path": "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md",
  "status": "used_as_seed_only",
  "notes": "仅作为 bootstrap labels 来源，不能视作最终专家金标准。"
}
```

---

## 14.5 冷轧厂 `ground_truth_visibility.json`

```json
{
  "attachments": [
    {
      "name": "附件1：施工网络进度表",
      "expected_visibility": "referenced_only",
      "manual_review_needed": true,
      "notes": "原文目录已引用，但当前 seed case 不包含附件正文内容。"
    },
    {
      "name": "附件2：施工总平面布置图",
      "expected_visibility": "referenced_only",
      "manual_review_needed": true,
      "notes": "原文目录已引用，但当前 seed case 不包含附件正文内容。"
    }
  ]
}
```

---

## 14.6 冷轧厂 `expected_facts.json`

```json
{
  "facts": [
    {
      "key": "project_id",
      "value": "230235",
      "value_type": "string",
      "support_type": "doc_fact",
      "notes": "项目编号"
    },
    {
      "key": "contains_gas_area",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "工程特点中明确写有煤气区域。"
    },
    {
      "key": "major_equipment_motor_count",
      "value": 22,
      "value_type": "integer",
      "support_type": "doc_fact",
      "notes": "原文写明共有22台电动机。"
    },
    {
      "key": "single_crane_shutdown_days",
      "value": 7,
      "value_type": "integer",
      "support_type": "doc_fact",
      "notes": "单台行车停机改造时间为7天。"
    },
    {
      "key": "has_attachment_1",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "目录中有附件1。"
    },
    {
      "key": "has_attachment_2",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "目录中有附件2。"
    },
    {
      "key": "duplicate_section_title",
      "value": "防火安全",
      "value_type": "string",
      "support_type": "doc_fact",
      "notes": "目录中第五节与第七节标题重复。"
    },
    {
      "key": "construction_dates_have_dual_basis",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "既写固定开工日期，又写以甲方批准为准。"
    },
    {
      "key": "dangerous_work_special_plan_missing",
      "value": true,
      "value_type": "boolean",
      "support_type": "gemini_inference",
      "notes": "Gemini 明确指出危大工程专项方案缺失。"
    },
    {
      "key": "gas_area_risk_identification_insufficient",
      "value": true,
      "value_type": "boolean",
      "support_type": "gemini_inference",
      "notes": "Gemini 指出煤气区域重大风险辨识不足。"
    }
  ]
}
```

---

## 14.7 冷轧厂 `expected_rule_hits.json`

```json
[
  {
    "rule_id": "construction_org.section_duplicate_title",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "重复章节标题。"
  },
  {
    "rule_id": "construction_org.attachment_reference_visible",
    "expected_status": "manual_review_needed",
    "expected_match_type": "visibility_gap",
    "notes": "附件被引用但未纳入当前 seed case 正文。"
  },
  {
    "rule_id": "construction_org.progress_baseline_conflict",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "固定日期与甲方批准并存。"
  },
  {
    "rule_id": "lifting_operations.special_plan_required",
    "expected_status": "manual_review_needed",
    "expected_match_type": "inferred_risk",
    "notes": "起重吊装专项方案缺失由 Gemini seed 指出。"
  },
  {
    "rule_id": "gas_area_ops.risk_identification_complete",
    "expected_status": "manual_review_needed",
    "expected_match_type": "inferred_risk",
    "notes": "煤气区域防毒/防窒息辨识需要后续人工复核。"
  }
]
```

---

## 14.8 冷轧厂 `ground_truth_issues.json`

```json
[
  {
    "id": "CRANE-ISSUE-001",
    "title": "安全章节标题重复（防火安全重复出现）",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "hard_evidence",
    "label_source_type": "doc_fact",
    "doc_supported": true,
    "gemini_supported": false,
    "manual_review_needed": false,
    "status": "seeded_unreviewed",
    "notes": "目录中第五节与第七节均为防火安全。"
  },
  {
    "id": "CRANE-ISSUE-002",
    "title": "危大工程专项方案计划缺失",
    "layer": "L1",
    "severity": "high",
    "finding_type": "engineering_inference",
    "label_source_type": "gemini_inference",
    "doc_supported": true,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "Gemini 明确指出起重吊装专项方案缺失；后续需结合规则引擎复核。"
  },
  {
    "id": "CRANE-ISSUE-003",
    "title": "煤气区域风险辨识不足",
    "layer": "L1",
    "severity": "high",
    "finding_type": "engineering_inference",
    "label_source_type": "gemini_inference",
    "doc_supported": true,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "原文确认煤气区域，Gemini 指出防毒/防窒息层面存在缺口。"
  },
  {
    "id": "CRANE-ISSUE-004",
    "title": "吊车站位承载力验算缺失",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "engineering_inference",
    "label_source_type": "gemini_inference",
    "doc_supported": false,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "后续需结合专项方案及平面布置图进一步核验。"
  },
  {
    "id": "CRANE-ISSUE-005",
    "title": "应急预案标题与正文用途存在错配",
    "layer": "L1",
    "severity": "high",
    "finding_type": "hard_evidence",
    "label_source_type": "doc_fact",
    "doc_supported": true,
    "gemini_supported": true,
    "manual_review_needed": false,
    "status": "seeded_unreviewed",
    "notes": "当前文档中应急预案存在文题不符问题。"
  },
  {
    "id": "CRANE-ISSUE-006",
    "title": "附件已被引用但当前正文不可见",
    "layer": "L0",
    "severity": "info",
    "finding_type": "visibility_gap",
    "label_source_type": "visibility_assumption",
    "doc_supported": true,
    "gemini_supported": false,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "附件1/2 在目录出现，但当前 seed case 不含附件正文。"
  },
  {
    "id": "CRANE-ISSUE-007",
    "title": "工期基准存在双重表述",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "hard_evidence",
    "label_source_type": "doc_fact",
    "doc_supported": true,
    "gemini_supported": true,
    "manual_review_needed": false,
    "status": "seeded_unreviewed",
    "notes": "固定开工日期与甲方批准为准并存。"
  },
  {
    "id": "CRANE-ISSUE-008",
    "title": "成本管理计划缺失",
    "layer": "L2",
    "severity": "low",
    "finding_type": "suggestion_enhancement",
    "label_source_type": "gemini_inference",
    "doc_supported": false,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "来自 Gemini 深审结论，不视为已确认硬缺陷。"
  }
]
```

---

## 14.9 冷轧厂 `evaluation_notes.md`

```markdown
# evaluation_notes

## purpose
- 用作机电安装类施工组织设计的 bootstrap seed case
- 验证目录结构异常、visibility gap、危大识别推断、应急预案错配等问题模式
- 用作后续 `structured_review` 的 parser / rule engine / report builder 回归样本

## primary_checks
- 是否能识别重复章节标题
- 是否能将附件引用与附件缺失区分开
- 是否能识别工期基准双重表述
- 是否能保留 Gemini seed 的危大工程、煤气区域、吊装承载力问题作为待复核项
- 是否能从原文抽出 22 台电机、7 天停机窗口、煤气区域等关键 facts

## known_limitations
- 当前 issue truth 不是专家确认结果
- 吊装专项方案缺失等问题暂不能自动视为 hard evidence
- 附件1/附件2 当前仅有引用关系，没有附件正文

## next_review_actions
- 补充附件可见性策略
- 结合 structured_review 规则核复核危大专项方案命中逻辑
- 人工复核煤气区域风险是否属于 L1 还是 L2
```

---

## 14.10 冷轧厂 `README.md`

```markdown
# cn_baosteel_coldrolling_crane_230235

当前版本：`v0.1.0-gemini-seed`

## 说明
这是一个基于原始施组与 Gemini deepresearch 审查结果构建的 bootstrap seed case。

## 不应误解为
- 不是专家确认 gold
- 不是最终 ground truth
- 不是 formal reviewer 的权威标准答案

## 当前主要用途
- parser 回归
- visibility 回归
- expected facts 抽取回归
- rule hit 初步回归
```

---

## 14.11 培花 `case_metadata.json`

```json
{
  "case_id": "cn_puhua_rainwater_storage_pool",
  "case_version": "v0.1.0-gemini-seed",
  "schema_version": "v1",
  "title": "施工组织设计-培花初期雨水调蓄池建设工程",
  "doc_type": "construction_org",
  "discipline_tags": [
    "municipal",
    "deep_excavation",
    "foundation_pit",
    "support_system",
    "dewatering",
    "pipe_jacking"
  ],
  "expected_packs": [
    "construction_org.base",
    "deep_excavation.base",
    "dewatering.base",
    "pipe_jacking.base"
  ],
  "label_source": "gemini_deepresearch",
  "label_status": "seeded_unreviewed",
  "truth_level": "bootstrap",
  "review_status": "not_final",
  "source_files": [
    "fixtures/copied/supervision/施工组织设计-培花初期雨水调蓄池建设工程.pdf"
  ],
  "seed_review_files": [
    "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-培花初期雨水调蓄池建设工程.md"
  ],
  "notes": "本版本既包含 seed 问题，也包含正向 rule hit 预留，用于深基坑/危大识别回归。"
}
```

---

## 14.12 培花 `source_ref.json`

```json
{
  "source_document": {
    "relative_path": "fixtures/copied/supervision/施工组织设计-培花初期雨水调蓄池建设工程.pdf",
    "doc_type": "construction_org",
    "file_kind": "pdf"
  },
  "review_seed_documents": [
    {
      "relative_path": "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-培花初期雨水调蓄池建设工程.md",
      "source_type": "gemini_deepresearch_markdown"
    }
  ]
}
```

---

## 14.13 培花 `seed_sources/gemini_review_ref.json`

```json
{
  "seed_source": "gemini_deepresearch",
  "relative_path": "fixtures/copied/supervision/gemini-deepresearch审查结果-施工组织设计-培花初期雨水调蓄池建设工程.md",
  "status": "used_as_seed_only",
  "notes": "仅作为 bootstrap labels 来源，不能视作最终专家金标准。"
}
```

---

## 14.14 培花 `ground_truth_visibility.json`

```json
{
  "attachments": [
    {
      "name": "附图附表",
      "expected_visibility": "parsed",
      "manual_review_needed": false,
      "notes": "PDF 中存在附图附表章节与部分图表可视内容。"
    }
  ]
}
```

---

## 14.15 培花 `expected_facts.json`

```json
{
  "facts": [
    {
      "key": "storage_volume_m3",
      "value": 10400,
      "value_type": "integer",
      "support_type": "doc_fact",
      "notes": "调蓄池规模。"
    },
    {
      "key": "max_excavation_depth_m",
      "value": 22.05,
      "value_type": "number",
      "support_type": "doc_fact",
      "notes": "局部最大开挖深度。"
    },
    {
      "key": "standard_zone_depth_m",
      "value": 20.05,
      "value_type": "number",
      "support_type": "doc_fact",
      "notes": "标准区开挖深度。"
    },
    {
      "key": "has_hazardous_work_section",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "存在 7.7 危大工程清单及安全管理措施。"
    },
    {
      "key": "has_scheme_plan_section",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "存在 4.5 施工方案编制计划。"
    },
    {
      "key": "foundation_pit_safety_level",
      "value": "level_1",
      "value_type": "string",
      "support_type": "doc_fact",
      "notes": "主体调蓄池基坑安全等级一级。"
    },
    {
      "key": "has_microtunneling",
      "value": true,
      "value_type": "boolean",
      "support_type": "doc_fact",
      "notes": "放空管采用微顶管。"
    },
    {
      "key": "microtunneling_length_m",
      "value": 37,
      "value_type": "integer",
      "support_type": "doc_fact",
      "notes": "微顶管长度约37m。"
    },
    {
      "key": "cost_management_plan_missing",
      "value": true,
      "value_type": "boolean",
      "support_type": "gemini_inference",
      "notes": "Gemini 指出成本管理计划缺失。"
    },
    {
      "key": "third_party_monitoring_wording_needs_hardening",
      "value": true,
      "value_type": "boolean",
      "support_type": "gemini_inference",
      "notes": "Gemini 指出第三方监测主体表述仍需增强。"
    }
  ]
}
```

---

## 14.16 培花 `expected_rule_hits.json`

```json
[
  {
    "rule_id": "construction_org.has_hazardous_work_section",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "7.7 危大工程清单及安全管理措施存在。"
  },
  {
    "rule_id": "construction_org.scheme_plan_present",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "4.5 施工方案编制计划存在。"
  },
  {
    "rule_id": "deep_excavation.max_depth_over_5m",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "局部 22.05m。"
  },
  {
    "rule_id": "pipe_jacking.special_scheme_required",
    "expected_status": "hit",
    "expected_match_type": "direct_hit",
    "notes": "微顶管属于高风险专项施工内容。"
  },
  {
    "rule_id": "construction_org.cost_management_plan_present",
    "expected_status": "manual_review_needed",
    "expected_match_type": "inferred_risk",
    "notes": "Gemini 指出成本管理计划缺失，但当前原文需进一步复核。"
  }
]
```

---

## 14.17 培花 `ground_truth_issues.json`

```json
[
  {
    "id": "PUHUA-ISSUE-001",
    "title": "成本管理计划缺失",
    "layer": "L2",
    "severity": "low",
    "finding_type": "suggestion_enhancement",
    "label_source_type": "gemini_inference",
    "doc_supported": false,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "Gemini seed issue，用作后续目录完整性复核项。"
  },
  {
    "id": "PUHUA-ISSUE-002",
    "title": "临建防火材质约束未明确到 A 级不燃材料",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "engineering_inference",
    "label_source_type": "gemini_inference",
    "doc_supported": false,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "Gemini seed issue。"
  },
  {
    "id": "PUHUA-ISSUE-003",
    "title": "第三方监测主体表述不够刚性",
    "layer": "L2",
    "severity": "medium",
    "finding_type": "engineering_inference",
    "label_source_type": "gemini_inference",
    "doc_supported": false,
    "gemini_supported": true,
    "manual_review_needed": true,
    "status": "seeded_unreviewed",
    "notes": "Gemini seed issue。"
  }
]
```

---

## 14.18 培花 `evaluation_notes.md`

```markdown
# evaluation_notes

## purpose
- 用作市政深基坑类施工组织设计的 bootstrap seed case
- 用作正向 rule hit case
- 验证危大工程识别、专项方案计划、深基坑参数抽取、微顶管识别

## primary_checks
- 是否能识别 7.7 危大工程清单
- 是否能识别 4.5 施工方案编制计划
- 是否能抽出最大开挖深度 22.05m
- 是否能抽出调蓄池规模 10400m3
- 是否能识别微顶管长度约 37m

## known_limitations
- 成本管理计划缺失仍是 Gemini seed issue，尚未专家确认
- 第三方监测主体表述需要后续人工复核
- 该 case 同时作为 positive sample 和 seeded issue sample

## next_review_actions
- 为深基坑 / 微顶管 / 支撑体系补充更细粒度 expected rule hits
- 增加周边管线与环境保护等级 facts
- 后续接入 structured_review 时优先作为正向命中 case
```

---

## 14.19 培花 `README.md`

```markdown
# cn_puhua_rainwater_storage_pool

当前版本：`v0.1.0-gemini-seed`

## 说明
这是一个基于原始施组与 Gemini deepresearch 审查结果构建的 bootstrap seed case。

## 当前定位
- 深基坑类施工组织设计样本
- 正向 rule hit case
- 危大工程识别与方案编制计划识别样本

## 注意
该 case 中的部分问题项仍属于 Gemini seed inference，不代表专家已确认缺陷。
```

---

## 15. Codex 实施步骤

### Step 1：创建目录

创建 `fixtures/review_eval/`、`schemas/`、两个 case 目录与版本目录。

### Step 2：写入 schema

把第 12 节中的 6 个 schema 文件落盘。

### Step 3：写入 pool README

把第 14.1 节内容写成 `fixtures/review_eval/README.md`。

### Step 4：初始化冷轧厂 case

生成第 14.2 至 14.10 中的全部文件。

### Step 5：初始化培花 case

生成第 14.11 至 14.19 中的全部文件。

### Step 6：检查路径引用

确认 `source_ref.json` 中引用的源文件路径与仓库实际存在路径一致。

### Step 7：基本 JSON 合法性校验

确保所有 JSON 文件格式合法、可被后续脚本读取。

### Step 8：补一个顶层说明

如果仓库内已有测试说明文档，可在 `docs/testing.md` 后续改造中补一句：

* 当前已有 `fixtures/review_eval/` 作为 bootstrap golden pool

本阶段如果不改 docs，也至少要保证 `fixtures/review_eval/README.md` 说明完整。

---

## 16. 验收标准（Definition of Done）

以下条件全部满足，才算这次任务完成：

1. 已在仓库中创建 `fixtures/review_eval/` 完整目录树。
2. 已创建 6 个 schema 文件。
3. 已创建 2 个 case。
4. 每个 case 都有独立版本目录 `v0.1.0-gemini-seed/`。
5. 每个 case 都包含 9 个落地文件。
6. 冷轧厂 case：

   * 有重复章节 issue
   * 有 visibility 文件
   * 附件1/附件2 被标记为 `referenced_only`
   * 未被误标为 `missing`
7. 培花 case：

   * 有深基坑 facts
   * 有危大工程相关 expected rule hit
   * 同时具备 positive sample 属性
8. 所有 metadata 都写明：

   * `label_source`
   * `label_status`
   * `truth_level`
   * `review_status`
9. 没有任何地方把这批数据写成“专家确认 gold truth”。
10. 所有 JSON 文件格式合法，文件路径真实存在。

---

## 17. 不要做什么

1. 不要把 `v0.1.0-gemini-seed` 改成 `v1.0.0`。
2. 不要把 Gemini 推断问题统统写成 `hard_evidence`。
3. 不要把“附件未解析/仅引用”写成 `missing`。
4. 不要为冷轧厂单案例写正则硬编码。
5. 不要复制源文件到 case 版本目录。
6. 不要省略版本目录。
7. 不要只建目录不写内容。

---

## 18. 一句话执行指令

Codex 现在要做的不是“造一个最终黄金标准库”，而是：

> **在 `fixtures/review_eval/` 下，基于两份真实施组和两份 Gemini deepresearch 审查结果，创建一套带版本号的 bootstrap golden pool，并落地 2 个 `v0.1.0-gemini-seed` mini golden cases。**

这个任务完成后，你就已经拥有了后续 `structured_review` 的第一套可持续迭代的评测底座。