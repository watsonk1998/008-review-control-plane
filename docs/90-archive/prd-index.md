> [!NOTE]
> **本文档职责**
> - 负责：
>   - 保存历史 PRD 索引方式与旧导航结构
> - 不负责：
>   - 不作为当前 docs 的主导航入口
> - 主适用读者：
>   - 需要查看历史导航结构的读者
> - 冲突处理：
>   - 当前导航以 `docs/README.md` 为准
> - 文档状态：
>   - Archive / Historical Index / 非主真相源

---

# PRD 索引与文档职责说明

本文档保留为历史导航方式说明，原先曾作为 `docs/` 入口，用于把当前已经存在的产品、功能、架构、验收与运行文档整理成一套**可导航、可交接、可执行**的拆分式 PRD 文档包。

> [!important]
> 这不是新的独立需求来源，也不是对既有文档的二次改写。  
> 本文档只负责说明：**哪份文档管什么、谁是主真相源、应该按什么顺序阅读。**

---

## 1. 使用原则

- 不在本文件中重新定义 schema、API 字段或评测指标。
- 如出现口径冲突，以各主题的**主真相源文档**为准。
- 本文件只做导航和职责声明，不替代原始正文。

---

## 2. 文档分组

### 文档包分层地图（Document Hierarchy Map）

```text
  ┌─────────────────────────────────────────────────────────────────┐
  │                    008 审查控制面（Review Control Plane）         │
  │                  PRD 文档包 · 垂直分层地图                       │
  ├────────────┬──────────────────────────────────────┬─────────────┤
  │ A 产品总纲 │ product-strategy.md                  │← 定位/路线  │
  ├────────────┼──────────────────────────────────────┤             │
  │ B 功能规格 │ formal-review.md                     │← 契约/边界  │
  ├────────────┼──────────────────────────────────────┤             │
  │ C 架构约束 │ architecture.md                      │← 分层/职责  │
  ├────────────┼──────────────────────────────────────┤             │
  │ D 验收门槛 │ testing.md                           │← 指标/门禁  │
  ├────────────┼──────────────────────────────────────┤             │
  │ E 边界支撑 │ known-limitations / runbook /        │← 边界/运行  │
  │            │ integration/* / discovery            │             │
  └────────────┴──────────────────────────────────────┴─────────────┘
       ▲ 主真相源（Source of Truth）方向：上层文档约束下层，下层不反写上层
```

### A. 产品总纲

**主文档**：[`product-strategy.md`](./product-strategy.md)

- **角色**：产品总纲 / 路线图 / 治理约束
- **适用对象**：产品、项目负责人、架构负责人、核心研发
- **主真相源范围**：
  - 产品定位
  - 一句话定义
  - V0.3 目标 / 非目标
  - 路线分层
  - 成功判据
  - 治理原则

> 只要问题属于“008 到底是什么、当前版本为什么这样收边界、未来路线如何分层”，都先看本文件。

### B. 核心能力需求 / 功能规格

**主文档**：[`formal-review.md`](./formal-review.md)

- **角色**：`structured_review` 的正式需求规格与结果契约
- **适用对象**：后端研发、前端研发、评测研发、review domain 维护者
- **主真相源范围**：
  - 输入参数
  - 输出结构
  - official / experimental scope
  - pack registry
  - artifact API
  - manual review 语义
  - review-preparation 语义

> 只要问题属于“`structured_review` 应该接什么、产出什么、哪些字段是 canonical、哪些边界不能越过”，都先看本文件。

### C. 架构与实现约束

**主文档**：[`architecture.md`](./architecture.md)

- **角色**：系统分层、运行职责、模块边界、技术实现约束
- **适用对象**：研发、架构、接手维护人员
- **主真相源范围**：
  - control plane / orchestration 定位
  - runtime 与 review domain 的职责分离
  - API / orchestrator / adapters / state / artifacts 分层
  - 当前 formal review 最小规则核

> 只要问题属于“能力放在哪一层、谁负责任务编排、谁负责正式审查裁决”，都先看本文件。

### D. 验收与评测门槛

**主文档**：[`testing.md`](./testing.md)

- **角色**：测试基线、验收要点、评测门槛、回归命令
- **适用对象**：研发、测试、评测、发布责任人
- **主真相源范围**：
  - 功能测试矩阵
  - P0/P1 验收要点
  - legacy baseline
  - official versioned stage gate
  - layered metrics 与 gateRole

> 只要问题属于“怎么验证做对了、哪些指标是 blocking、哪些只算 diagnostics”，都先看本文件。

### E. 边界 / 限制 / 运行支撑

#### 1) 已知限制

**主文档**：[`known-limitations.md`](./known-limitations.md)

- **角色**：当前版本边界、降级路径与不可过度承诺项
- **适用对象**：产品、研发、联调、演示与交付人员
- **主真相源范围**：
  - bridge / direct import 的能力边界
  - single-document 限制
  - PDF text-only 降级路径
  - strictMode 当前状态

#### 2) 运行手册

**主文档**：[`runbook.md`](./runbook.md)

- **角色**：本地启动、联调、验证、常见问题排查
- **适用对象**：研发、联调、运维

#### 3) 外部能力接入说明

**文档集合**：

- [`integration/deepresearchagent.md`](./integration/deepresearchagent.md)
- [`integration/deeptutor.md`](./integration/deeptutor.md)
- [`integration/fastgpt.md`](./integration/fastgpt.md)
- [`integration/gpt-researcher.md`](./integration/gpt-researcher.md)
- [`integration/llm-config.md`](./integration/llm-config.md)

- **角色**：外部能力接入方式、配置解析、适配边界
- **适用对象**：后端研发、联调人员、环境维护人员

#### 4) 勘查背景

**主文档**：[`discovery.md`](./discovery.md)

- **角色**：前期勘查与接入决策背景
- **适用对象**：需要理解“为什么这样接”的研发与架构人员

> 这组文档提供的是边界、运行与来源背景，不是新的产品真相源。

---

## 3. 主真相源对照表

| 主题 | 主真相源 |
| --- | --- |
| 产品定位、目标、非目标、路线、治理 | [`product-strategy.md`](./product-strategy.md) |
| `structured_review` 输入/输出契约、scope、artifact、manual review | [`formal-review.md`](./formal-review.md) |
| 验收门槛、stage gate、回归命令 | [`testing.md`](./testing.md) |
| 技术分层、模块职责、实现约束 | [`architecture.md`](./architecture.md) |
| 当前限制、降级路径、不可承诺项 | [`known-limitations.md`](./known-limitations.md) |
| 启动、联调、排障 | [`runbook.md`](./runbook.md) |

**执行原则**：

- 不允许在 README、前端文案或临时说明中发明第二套 support scope、review 语义或 promotion 结论。
- 需要引用时，优先链接主真相源，而不是复制一份新说法。

---

## 4. 推荐阅读路径

### 阅读路径导航图（Reading Path Map）

```text
                    你是谁？
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
        产品/管理    研发实现    联调/运维
           │           │           │
           ▼           ▼           ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │strategy  │ │strategy  │ │runbook   │
     │          │ │          │ │          │
     │formal    │ │formal    │ │integr/*  │
     │          │ │          │ │          │
     │testing   │ │architect.│ │known-lim.│
     │          │ │          │ │          │
     │   END    │ │testing   │ │   END    │
     │          │ │          │ │          │
     │          │ │   END    │ │          │
     └──────────┘ └──────────┘ └──────────┘
```

### 路径 A：产品 / 管理

1. [`product-strategy.md`](./product-strategy.md)
2. [`formal-review.md`](./formal-review.md)
3. [`testing.md`](./testing.md)

适用：理解产品定位、阶段目标、正式能力边界与版本成功判据。

### 路径 B：研发实现

1. [`product-strategy.md`](./product-strategy.md)
2. [`formal-review.md`](./formal-review.md)
3. [`architecture.md`](./architecture.md)
4. [`testing.md`](./testing.md)

适用：理解先做什么、做到什么程度算完成、哪些字段/契约不可自行改写。

### 路径 C：联调 / 运维

1. [`runbook.md`](./runbook.md)
2. `integration/*.md`
3. [`known-limitations.md`](./known-limitations.md)

适用：本地启动、外部能力接入、环境问题排查、能力边界确认。

---

## 5. 给新同事的最小阅读集

如果只允许先看 3 份文档，建议顺序如下：

1. [`product-strategy.md`](./product-strategy.md) —— 先建立产品坐标
2. [`formal-review.md`](./formal-review.md) —— 再建立能力与契约边界
3. [`testing.md`](./testing.md) —— 最后明确验收门槛

完成这三份之后，应能回答：

- 008 当前是不是 review control plane
- `structured_review` 是不是正式主线
- official / experimental 如何区分
- 哪些字段是 canonical
- 什么叫“做完”而不是“看起来差不多”

---

## 6. 维护规则

- 新增产品级文档时，先判断它属于哪一组，再决定是否需要加入本索引。
- 若某主题已经有主真相源，新文档不得重复定义同一主题的 canonical 规则。
- 若主真相源发生迁移，应先更新本索引，再更新 README 中的文档入口。

---

## 7. 核心架构与流程图解（Architecture & Flow Diagrams）

### 7.1 正式审查主链流水线（Formal-Review Spine Pipeline）

展示数据如何从输入走向可信输出：

```text
  输入（Input）            正式审查主链（Formal-Review Spine）            输出 / 治理（Output / Governance）
  ────────── ┌────────────────────────────────────────────────────────┐ ─────────────────────────────────
             │                                                        │
  PDF/Fixture│  ┌───────┐     ┌───────┐     ┌───────┐                 │  ┌────────────┐
  ──────────►│  │ 解析  │────►│ 事实  │────►│ 规则  │                 │─►│ 工件索引   │
             │  │(Parse)│     │(Facts)│     │(Rules)│                 │  │(Artifacts) │
             │  └───┬───┘     └───┬───┘     └───┬───┘                 │  └─────┬──────┘
             │      │             │             │                     │        │
             │      ▼             ▼             ▼                     │        ▼
             │   可视域       未决事实       适用状态                   │  ┌────────────┐
             │ (visibility) (unresolved  (applicability               │  │ 审查报告   │
             │  parseMode     Facts)         State)                   │  │ (Report)   │
             │      │             │             │                     │  └─────┬──────┘
             │      ▼             ▼             ▼                     │        │
             │  ┌─────────┐   ┌────────────┐┌─────────┐               │        │
             │  │ 前置检查 │   │ 证据构建   ││ 问题种类 │             │        │
             │  │(L0 Gate)│   │ (Evidence) ││(Issues) │               │        │
             │  └────┬────┘   └─────┬──────┘└────┬────┘               │        │
             │       │              │            │                    │        │
             │       ▼              ▼            ▼                    │        ▼
             │  ┌──────────────────────────────────────┐              │  ┌────────────┐
             │  │        复核门禁（Reviewer Gate）       │              │  │ 人工裁决   │
             │  │ 需人工复核（manualReviewNeeded）→ 分流 │              │  │ (Decision) │
             │  └─────────────┬────────────────────────┘              │  └────────────┘
             │                │                                       │
             └────────────────┼───────────────────────────────────────┘
                              ▼
                   ┌───────────────────────┐
                   │   评测门禁（Eval Gate） │
                   │ 版本化用例（versioned） │
                   │ 分层指标（layered）     │
                   │ 阶段阻断（stage gate）  │
                   └───────────────────────┘
```

### 7.2 人类专家 × 系统 协作地图（Human-in-the-loop Collaboration Map）

主要展示人类专家在系统中的介入点、判断职责，以及系统本身**不可越权**的边界：

```text
  ┌──────────────────────────────────────────────────────────────────────┐
  │                   人类专家 × 系统 协作地图（Collaboration Map）           │
  ├──────────────────────────────────────────────────────────────────────┤
  │                                                                      │
  │  系统自动完成                 人工必须介入                 系统不得越权         │
  │  ──────────                 ──────────                 ──────────         │
  │                                                                      │
  │  [解析 Parse]─────────►┌─ 可视域盲区（Visibility）─┐                            │
  │  [事实 Facts]          │  · PDF 附件不可读        │◄── 人工确认"确实缺失"      │
  │  [规则 Rules]          │  · 图纸无法提取          │     vs "解析器读不到"      │
  │                        └───────────────────────┘                          │
  │                                                                      │
  │  [问题 Issue]─────────►┌─ 复核门禁（Reviewer Gate）┐                            │
  │  [证据 Evidence]       │  · 可视域缺口（vis._gap）│◄── 人工裁决审查意见处置      │
  │  [矩阵 Matrices]       │  · 证据缺口（evid._gap） │    同意 / 驳回 / 补充附件等  │
  │                        └───────────────────────┘                          │
  │                                                                      │
  │  [评测 Eval]──────────►┌─ 样本治理（Eval Gov.）────┐                            │
  │  [指标 Metrics]        │  · 双样本人工复核裁决      │◄── 人工标注专家级真相（gold）│
  │  [回放 Replay]         │  · 版本化测试用例晋升      │    绝不以系统初稿为最终真理  │
  │                        └───────────────────────┘                          │
  │                                                                      │
  │  ▼ 绝对禁区：模型不得自行签发正式结论 / 不得把"读不到"伪装成"事实缺失" ▼      │
  └──────────────────────────────────────────────────────────────────────┘
```

### 7.3 包与文档级别治理流程图（Pack / DocType Promotion Flow）

展示不同模块从孵化到成熟的流转过程：

```text
  包与文档类型治理晋升流程（Promotion Flow）

  占位符（placeholder）──► 就绪（ready）──► 实验性（experimental）──► 正式（official）
       │                    │                  │                      │
       │                    │                  │                      │
       ▼                    ▼                  ▼                      ▼
  仅有骨架/模板            有可执行规则       进入评测但不进入        通过完整门禁
  不参与正式审查          可被系统选中       阶段阻断（stage gate）   成为正式支持对象

  晋升门禁（Promotion Criteria）要求：
  ┌─────────────────────────────────────────────────────────────────────┐
  │  测试（tests）               ✓ 功能测试矩阵全面覆盖                     │
  │  版本用例（versioned cases） ✓ 拥有专属、稳定的版本化黄金标准用例        │
  │  政策证据（policy evidence） ✓ 条文引用准确、无虚构，且结果可追溯        │
  │  规则覆盖（rule coverage）   ✓ 规则实际命中率与识别率达标              │
  └─────────────────────────────────────────────────────────────────────┘
```

