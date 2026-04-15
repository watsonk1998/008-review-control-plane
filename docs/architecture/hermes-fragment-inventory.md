# Hermes Fragment Inventory

本文档用于系统盘点当前 `008-review-control-plane` 仓库中，历史上可能来源于（或受其同源影响的） Hermes-Agent 源码片段。

## 盘点目标

明确哪些是应该被 `external/hermes-agent` 替代的真正内核逻辑，哪些是已经演化为 008 控制面的专有资产（壳层逻辑），以及哪些应该被转换为 overlay / config / patch 的定制资源。

---

## 清单详情

### 1. 疑似片段：`apps/api/hermes_server_shim.py`

* **职责**：封装下游真正的 `run_agent.py`，暴露 HTTP API 供 008 远端调用。
* **是否 Active Path**：是。这是当前的 external 接入方式的主体部分（本地测试/网关）。
* **分类**：**类别 C (Overlay / Patch / Local Launcher)**
* **结论**：它并不是从上游随意扒下来的代码，而是我们自己写的 shim，用于启动上游代码。在未来的 Local Kernel Integration 中，这部分职能将被 `HermesKernelLauncher` 或标准的 Subprocess 挂载取代或收编。

### 2. 疑似片段：`apps/api/src/adapters/hermes_external_adapter.py`

* **职责**：作为 `HermesReviewEngine` 的外部接口实现，向远端/本机的 `hermes_server_shim` 发送 HTTP 请求。
* **是否 Active Path**：是。
* **分类**：**类别 B (保留在壳层)**
* **结论**：它属于 Control Plane 边界的标准 Adapter 抽象层，不是扒下来的内核，而是属于我们系统的业务接口层。应继续保留并维护。

### 3. 疑似片段：`apps/api/src/adapters/hermes_llm_adapter.py`

* **职责**：兜底实现，利用本地的 `llm_gateway` 在没有真实 Hermes 引擎可用时，模拟发送独立的第二次审查请求。包含了一个内置的 Hermes System Prompt。
* **是否 Active Path**：是。作为降级策略正在发挥作用。
* **分类**：**类别 B (保留在壳层)**
* **结论**：这也是 Control Plane 的适配器逻辑，必须留在项目中，提供主备链路的容灾保障。其中内置的 Prompt 可以考虑迁移为配置资产（类别 C）。

### 4. 疑似片段：`apps/api/src/adapters/hermes_router_adapter.py`

* **职责**：决定当前调用 external 还是 fallback 的路由逻辑。
* **是否 Active Path**：是。
* **分类**：**类别 B (保留在壳层)**
* **结论**：标准的壳层路由，保留。

### 5. 疑似片段：`apps/api/src/review/hermes_controller.py` & `apps/api/src/review/hermes/`

* **职责**：控制面的 orchestrator，负责动态生成 candidate template，调度 `HermesAgentRunner`，并最终通过 `HermesReviewAssembler` 对齐结果。
* **是否 Active Path**：是。
* **分类**：**类别 B (保留在壳层)**
* **结论**：这是 008 控制面真正的核心。上游 Hermes 自己是没有这套复杂的 `TaskCompiler` 和 `FactPacket` 设计的。这构成了 008 系统对于双路甚至多路审查的统筹控制权，坚定地保留在壳层并且独立演化。

### 6. 疑似片段：`apps/api/src/orchestrator/deepresearch_runtime.py` / `planner.py` / `router.py`

* **职责**：这些文件涉及大模型协作、执行规划。里面或许有局部命名借鉴，但主要还是 008 自己为了兼容前端指令或内部流程所做。
* **是否 Active Path**：是。
* **分类**：**类别 B (保留在壳层)**
* **结论**：与 Hermes 的真正运行循环无关，它们主要解决 “调用哪个大模型” 或 “怎样编排任务” 的高阶网关逻辑，属于本地业务代码。

### 7. 其他并未大面积存在的疑似点

在搜索 `run_agent.py`, `model_tools.py`, `agent/*` 等内部实现时，**未发现**当前业务代码中直接硬解码了上游 `NosuResearch/hermes-agent` 的工具或状态机执行循环。

也就是当前仓库实际上处于一个**相对干净的壳层状态**，并没有强行把上游的 `run_agent.py` 等内核逻辑拆散撒满 `apps/api/src/` 文件，而是仅仅通过 `hermes_server_shim.py` 这种极度隔绝的黑盒 HTTP 接口调用上游。

---

## 结论汇总

1. **当前仓库环境非常克制**：并没有大量历史遗留的 Vendored Kernel Fragments 被硬切入 `apps/api/src/` 的核心审查逻辑中。
2. **大部分带 "hermes" 命名的模块实际上属于【类别 B：应保留在壳层】**：比如 `HermesController`, `HermesReviewAssembler`, `HermesLLMAdapter`, `HermesExternalAdapter`，这些是为了对接或统筹“具有 Hermes 设计理念的审查”而构建的边界层，并不是 Hermes 自身的执行内核。
3. **未来的真正挑战**也是设计上的利好：**历史包袱较轻**。我们可以直接启动从“HTTP 外部黑盒”向“本地 Subprocess/Kernel Launcher+Overlay”挂载的设计平移，而不必大规模重构目前已被硬编码污染的执行循环。
4. **【类别 C：应改造成 Overlay】的相关能力目前大多缺失或硬编码在 shim / LLM Adapter 中**。比如真实的 Skills，Memory，以及定制的 Prompts。未来应该在 `overlays/hermes-agent/` 里显式声明这些配置，喂给 launcher。

---

## Overlay / Launcher 迁移进度

### 已开始通过 overlay/launcher 路线处理

| Fragment | 原位 | 处理方式 | overlay 位置 |
|---|---|---|---|
| Hermes System Prompt | `hermes_llm_adapter.py:HERMES_SYSTEM_PROMPT` | 复制到 overlay（原位保留） | `overlays/hermes-agent/prompts/hermes_review_system_prompt.md` |
| Kernel Launch Config | 新增样本 | 直接在 overlay 新建 | `overlays/hermes-agent/config/local_kernel_launch.yaml` |

### 仍留在原处、等待后续迁移

| Fragment | 位置 | 当前角色 | 迁移前置条件 |
|---|---|---|---|
| `hermes_server_shim.py` | `apps/api/` | HTTP shim gateway（active path） | local kernel subprocess 替代 shim 后可退役 |
| `HermesLLMAdapter` 内置 prompt | `hermes_llm_adapter.py` | 硬编码 system prompt（active fallback） | overlay prompt 注入机制就绪后可改为从 overlay 加载 |
| Skills 定义 | 不存在 | 当前无独立 skill 文件 | 需先确定 kernel skill registry 接口 |
| Memory 配置 | 不存在 | 当前无独立 memory 配置 | 需先确定 kernel memory 接口 |

