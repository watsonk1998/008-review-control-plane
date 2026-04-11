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
* **Stage 3 (Smoke Path)**：打通 Local Kernel 的通信链路（不放入主网，提供 Feature Flag 开关支持，允许以 CLI 等单独维度做 E2E 测试）。✅ 已完成（dry-run + smoke 模式）。
* **Stage 4 (Overlay Setup)**：逐步建立 Overlays 挂载机制（Prompt、配置映射）。🔸 已开始（目录结构 + 样本资产已建立，运行时注入尚未实现）。
* **Stage 5 (Routing Shift)**：改造 `HermesRouterAdapter`，正式将 `local_kernel` 列入路由优选列表（比如：`local_kernel` -> `external` -> `llm_fallback`）。⬜ 尚未开始。

## 6. Smoke Path 实现详情

### 触发方式

```bash
# 完整 smoke 路径
python apps/api/scripts/run_local_hermes_smoke.py

# 仅检查路径和 overlay 解析（不进入 smoke 执行）
python apps/api/scripts/run_local_hermes_smoke.py --dry-run

# JSON 输出模式
python apps/api/scripts/run_local_hermes_smoke.py --json
```

### Launcher 支持的模式

| 模式 | 方法 | 行为 |
|---|---|---|
| `dry_run` | `launcher.dry_run()` | 检查路径、解析 overlay、生成 LaunchPlan，不启动进程 |
| `smoke` | `launcher.smoke(payload)` | 在 dry_run 基础上验证 kernel 标志文件（如 `run_agent.py`），回显 payload，返回受控 SmokeResult |

### Smoke Contract

smoke path 验证以下内容：

1. `external/hermes-agent` 能被 launcher 定位
2. launcher 能解析 overlay 根目录
3. overlay 子目录（skills, memory, config, prompts）的存在性
4. `HermesLocalKernelAdapter.smoke_exercise()` 能走完最小执行链
5. 返回受控的 `LocalKernelSmokeReport`，包含 `FactPacket`（标记为 `degraded=True, error="smoke_only"`）

### 主链隔离保障

* smoke 脚本是独立的 `apps/api/scripts/run_local_hermes_smoke.py`，不被任何 main chain import
* `HermesLocalKernelAdapter` 未出现在 `main_dependencies.py`
* `get_hermes_engine()` 的默认行为完全不变
* `verify_hermes_boundary.py` 会主动检查 smoke 脚本未被主链引用

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

> **业务主链行为不变。** `get_hermes_engine()` 仍返回 `HermesRouterAdapter(external, llm)`。
> Local kernel adapter / launcher 仅通过手动 smoke 脚本可触达，不参与 runtime 执行。

