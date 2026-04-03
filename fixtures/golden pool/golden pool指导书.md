
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
