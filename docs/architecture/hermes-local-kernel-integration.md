# External/Hermes-Agent 本地内核接入设计

本方案定义了在不破坏 `008-review-control-plane` 业务主链的情况下，安全、非侵入式地接入 `external/hermes-agent` 本地内核的具体设计。

## 1. Current State (当前状态)

* **链路现状**：当前 runtime **未真正启用**由于 submodule 挂载引入的 `external/hermes-agent`，而是主要通过 `HermesExternalAdapter` 携带 HTTP payload 去调用另外起的一个 `hermes_server_shim.py`，或者干脆降级使用纯本地的 `HermesLLMAdapter`。
* **内核现状**：`external/hermes-agent` 作为 pinned upstream submodule (`af9caec44fdab7a1b883dede16fe1ce8c2d60fb9`) 存在，建立了物理隔离边界，保证了上游内核逻辑的独立性。
* **总结**：“边界已建立，但本地内核尚未启用”。008 仍将上游当成一个完全外置的服务端点。

## 2. Target State (目标形态)

为了实现在本地进行内核执行并进行深度配置（Skills、Prompts、Memory 等资产），同时保障内核代码（`external/*`）的纯净：

* 建立 **Local Kernel Adapter** 架构，将内核变成由 008 业务线程通过 Launcher 以 **Subprocess / Sidecar** 的方式直接拉起并通信的常驻或按需子系统。
* Router 增加一个接入端点判断逻辑，灵活调度。

## 3. Recommended Integration Architecture (主推方案)

**主推：Local Sidecar / Subprocess Kernel 模式**

这是一个避免直接 `import` 内核源码引发环境隔离、依赖冲突和循环污染的最佳安全实践模式。

### 核心组件
1. **`HermesLocalKernelAdapter`**（壳层与 Launcher 间的接口抽象）
2. **`HermesKernelLauncher`**（负责实际启动外部进程，应用环境和 Overlays 的调度器）

### 目录映射与 Overlay 机制
* `external/hermes-agent/`: 上游只读内核（Pinned, Default Checkout）。
* `overlays/hermes-agent/`:
  * `skills/`: 项目特有的飞书等业务审查技能。
  * `config/`: 替换内核中的 `century.json` 寻址。
  * `prompts/`: 定制的 System Prompts 或者 Role Prompts。
* Launcher 启动时，基于环境变量或启动参数，将 Overlays 注入或挂载到内核 Subprocess 的工作上下文中。

### 业务防腐层
* 由 `HermesLocalKernelAdapter` 把 008 原生的 `ReviewBrief` / `FactPacket` 翻译为 Hermes Kernel 能直接消费的请求形态（类似现在调用 external http 那样）。
* 审查结束后，回收 Kernel 输出并转换回兼容 `HermesReviewEngine` 的标准 contract。

## 4. Kernel-safe Rules (安全边界纪律)

### 必须留在 Shell (008 控制面)
* Controller Orchestration。
* Assembler 及其依赖的 Final Report 合并协议。
* Module Binding Policy 和 Rule pack 的治理。
* 路由和兜底策略。

### 可以通过 Overlay 覆盖挂载 (送入 Kernel)
* 相关的 Tool 注册 (`skills/`)。
* 业务化的专用 Prompt 和执行模式参配置 (`config/` / `prompts/`)。
* Knowledge 记忆检索挂载。

### 严禁的操作 (不得直接去改)
* 直接修改或提交 `external/hermes-agent` 中的 `run_agent.py` 或内部 loop 代码。
* 强行把针对 Review 控制面的特化业务模型或 HTTP 中间件推到上游内核代码库里。
* 在 `apps/api/src/*` 代码里肆无忌惮地 `from ... import run_agent, model_tools`。

## 5. Migration Plan (迁移路径)

必须分阶段实施，确保每一步不阻断现有主流程：

* **Stage 1 (Inventory)**：盘点现有历史冗余，确认是否存在散落代码。✅ 已完成，现状良好。
* **Stage 2 (Skeleton)**：新增 `HermesLocalKernelAdapter` 及 `HermesKernelLauncher` 骨架代码，制定接口防腐协议，实现占位符功能。✅ 已完成。
* **Stage 3 (Smoke Path)**：打通 Local Kernel 的通信链路（不放入主网，提供 Feature Flag 开关支持，允许以 CLI 等单独维度做 dry-run 和 E2E测试）。✅ 已完成。
* **Stage 4 (Minimal Real Execution & Overlay)**：实现真正的 Subprocess 调用路径 (`invoke_kernel.py` shim)，使得 008 可以通过 Launcher 唤起具备真实大模型请求能力的本地内核进程，并注入 Overlay（如 System Prompts），同时返回结构化结果供 Adapter 合成为 FactPacket。✅ 已完成。
* **Stage 5 (Routing Shift)**：改造 `HermesRouterAdapter`，正式将 `local_kernel` 列入路由优选列表（比如：`local_kernel` -> `external` -> `llm_fallback`）。✅ 已完成。

## 6. Smoke Path 实现详情

### 触发方式

### 触发方式

```bash
# 1. 完整 smoke 路径 (仅做诊断输出)
python apps/api/scripts/run_local_hermes_smoke.py

# 仅检查路径和 overlay 解析（不进入 smoke 执行）
python apps/api/scripts/run_local_hermes_smoke.py --dry-run

# JSON 输出模式
python apps/api/scripts/run_local_hermes_smoke.py --json

# 2. Minimal Real Review (真实调用本地大模型)
export DASHSCOPE_API_KEY="sk-..."
python apps/api/scripts/run_local_hermes_minimal_review.py
```

### Launcher 支持的模式

| 模式 | 方法 | 行为 |
|---|---|---|
| `dry_run` | `launcher.dry_run()` | 检查路径、解析 overlay、生成 LaunchPlan，不启动进程 |
| `smoke` | `launcher.smoke(payload)` | 在 dry_run 基础上验证 kernel 标志文件，回显 payload，返回受控 SmokeResult |
| `invoke` | `launcher.invoke(payload)` | 真实唤起 `invoke_kernel.py` 的 subprocess 进行对话和 Overlay Prompt 挂载 |

### Smoke Contract

smoke path 验证以下内容：

1. `external/hermes-agent` 能被 launcher 定位
2. launcher 能解析 overlay 根目录
3. overlay 子目录（skills, memory, config, prompts）的存在性
4. `HermesLocalKernelAdapter.smoke_exercise()` 能走完最小执行链
5. 返回受控的 `LocalKernelSmokeReport`，包含 `FactPacket`（标记为 `degraded=True, error="smoke_only"`）

### 主链隔离保障被解除 (Phase 1 移除)

* `HermesLocalKernelAdapter` 现已正式接入 `main_dependencies.py`
* `get_hermes_engine()` 返回配置了 `local_kernel` 兜底的首选策略
* `verify_hermes_boundary.py` 移除了关于隔离状态的硬断言，将 local kernel 视为合法的核心生产引擎。

## 7. Overlay 目录结构

```
overlays/hermes-agent/
├── README.md                               # 用途说明
├── skills/
│   └── README.md                           # 技能注册样本格式
├── memory/
│   └── README.md                           # 记忆配置说明
├── config/
│   ├── README.md                           # 配置说明
│   └── local_kernel_launch.yaml            # 启动配置样本
└── prompts/
    ├── README.md                           # 提示词说明
    └── hermes_review_system_prompt.md      # 从 hermes_llm_adapter.py 提取的 system prompt
```

### 已迁移的资产

| 资产 | 来源 | overlay 位置 | 原位保留 |
|---|---|---|---|
| Hermes System Prompt | `hermes_llm_adapter.py:HERMES_SYSTEM_PROMPT` | `prompts/hermes_review_system_prompt.md` | ✅ 原文件不变 |
| Launch Config 样本 | 新增 | `config/local_kernel_launch.yaml` | N/A |

### 尚未迁移的资产

* Skills 定义（当前 LLM adapter 中无独立 skill 注册）
* Memory 配置（当前无独立 memory 配置文件）
* 更多业务 prompt（需等待 local kernel 真正启用后按需迁移）

## 8. Compatibility & Risks (兼容性与风险提示)

### 为什么不建议直接在代码里 `import` 上游内部模块
* _隔离破窗_：一旦开始 `import run_agent`，很快各类工具函数、特化配置都会强耦合。上游一但更改入参或 `pydantic` 版本可能引发 008 核心进程崩溃。
* _依赖树复杂_：强行在同进程跑可能存在 Pydantic V1/V2 冲突、FastAPI 中间件冲突或日志系统串台问题。

### 本方案的主要风险
* **启动与上下文时延**：如果每次 Review 请求都要唤起一个重型 Python Subprocess 并加载大模型 Runtime ，可能引发性能问题（相比于 Resident Shim）。因此 Launcher 的设计应考虑到提供类似于 Resident Sidecar / Worker Pool 的模式。
* **挂载点匹配**：上游必须提供暴露良好的环境变量或命令行参数接口以允许被外部 Launcher 注入 Overlays 资产。如果上游不支持，则可能需要有限度地修改（`patches/`）。

### 当前状态声明

> **路由正式切换。** `get_hermes_engine()` 现在将优先探测 `local_kernel`。若未就绪或发生崩溃，系统将自动依次降级至 `external` 和 `llm_fallback`，降级细节会在 runtime diagnostics 中暴露。
> `HermesLocalKernelAdapter` 已经正式跨入 Main Chain 生产序列。

## 9. Support Layer Demotion (PR3)

008 结构化审查引擎（`StructuredReviewCapabilityFacade`, `FactPacketAdapter`, `pipeline`, `report_builder`）现在被严格定义为 **advisory support layer**，禁止输出官方最终评级/判决语义。

### 强制措施

| 措施 | 位置 | 效果 |
|---|---|---|
| `ownership='support_material'` 强制标注 | `FactPacketAdapter`, `StructuredReviewCapabilityFacade` | 所有 008 产出的 FactPacket 和 normalized result 均携带 support_material 所有权标记 |
| 禁止字段剥离 | `_normalize_primary_review_result()` | `final_grade`, `verdict`, `official_decision`, `approval_status` 在 support 层输出中被显式 pop 掉 |
| `_advisory_note` 注入 | `_normalize_primary_review_result()` | summary 级别的 `overallConclusion` 被标注为"仅供参考" |
| support issue 注解 | `_annotate_support_issue_source()` (`review_task_contracts.py`) | 附加 `supportDerived=True`，移除 `raw_data` 和 `source_packets` |
| 边界脚本验证 | `verify_hermes_boundary.py` → `verify_support_layer_demotion()` | 自动扫描 support layer 文件，若检测到 `final_grade` / `verdict` / `official_decision` / `approval_status` 字段赋值则报错 |

### 决策所有权

- **Hermes Assembler** (`assembler.py`) 是唯一允许发出 `final_grade`、`executive_summary`、`top_risks` 等官方最终裁决字段的组件。
- 008 结构化引擎的 `overallConclusion` 仅作为 advisory input 供 Assembler 参考，不会出现在 `/result` 正式协议中。

## 10. Live Overlay & Promotion Governance (PR4)

### Overlay 资产活注入

`HermesKernelLauncher` 现在支持通过 `repo_root` 构造函数自动解析 kernel 和 overlay 路径。Launcher 在每次 `invoke()` 调用时，通过 `--overlay-root` 参数将 overlay 根目录传递给 `invoke_kernel.py` shim，shim 在子进程内读取实际的 overlay 资产。

#### 注入链路

```
HermesKernelLauncher.__init__(repo_root=...)
  ├─ kernel_path = repo_root / external / hermes-agent
  ├─ overlays_path = repo_root / overlays / hermes-agent
  │
  invoke(payload)
  ├─ --overlay-root → overlays/hermes-agent/
  │   ├─ prompts/hermes_review_system_prompt.md  → system prompt 覆盖
  │   ├─ config/local_kernel_launch.yaml         → 启动配置
  │   └─ scripts/invoke_kernel.py                → shim 入口
  │
  invoke_kernel.py (subprocess)
  └─ 读取 overlay prompt → 注入 AIAgent ephemeral_system_prompt
```

#### Overlay 健康检查

`launcher.verify_overlay_manifest()` 返回结构化报告：
- overlay 根目录是否存在
- 各子目录（skills, memory, config, prompts）是否存在
- 关键资产（system prompt, launch config, invoke shim）是否就绪
- 错误和警告列表

### 模板晋升治理 (Template Promotion Governance)

新增 `template_promotion_policy.py` 模块，强制执行模板晋升生命周期：

```
runtime_candidate → validated → promoted_to_seed
                 └─ rejected (annotated, not deleted)
```

#### 晋升规则

| 规则 | 含义 |
|---|---|
| 结构完整性 | 必须是合法的 AgentTemplate JSON，含 id, agent_name, agent_purpose, execution_mode |
| 使用证据 | 必须有关联的 task_id（即必须被实际使用过） |
| 非实验性 | `metadata.experimental` 必须为 false |
| 文档类型覆盖 | `supported_document_types` 不能为空 |

#### 晋升流程

1. `list_candidates()` — 列举 runtime_dir 中所有候选模板
2. `validate_candidate(id)` — 执行 4 项验证规则
3. `promote(id)` — 验证通过后拷贝到 seed_dir，剥离实验标记，记录晋升日志

#### 边界脚本验证

`verify_hermes_boundary.py` 新增两项检查：
- `verify_live_overlay_governance()` — 验证关键 overlay 资产文件存在
- `verify_template_promotion_governance()` — 验证晋升治理模块和目录结构存在
