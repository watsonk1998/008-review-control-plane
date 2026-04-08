> [!NOTE]
> **本文档职责**
> - 负责：
>   - 说明特定外部能力或配置项在 008 中的接入方式、适配边界与运行角色
> - 不负责：
>   - 不替代整体架构、产品边界、验收标准或运行手册
> - 主适用读者：
>   - 架构负责人、研发工程师、集成维护者
> - 冲突处理：
>   - 涉及总体设计时，以 `docs/20-design/architecture.md` 为准；涉及产品边界时，以 governance 层文档为准
> - 文档状态：
>   - 集成设计说明

---

# DeepResearchAgent 接入说明

## 接入方式

008 没有直接把 007/上游 DeepResearchAgent 当作一个黑盒服务调用，而是在 008 内部实现了 **DeepResearchAgent-compatible orchestration layer**：

- `apps/api/src/orchestrator/planner.py`
- `apps/api/src/orchestrator/router.py`
- `apps/api/src/orchestrator/deepresearch_runtime.py`

## 为什么这样接

- 007 本地只有源码/脚本形态，没有稳定服务化接口
- 008 的目标是 control plane，不是继续加深某个业务审查器
- 在 008 内部实现 planner/router/coordinator 更利于未来统一更多外部能力

## 运行角色

- 先规划（plan）
- 再决策能力路由
- 再执行 adapter 调用
- 最终聚合成统一结果结构

## 最低统一输出

- `plan`
- `capabilitiesUsed`
- `finalAnswer`
- `sources`
- `steps`
- `artifacts`

## 已验证

- `knowledge_qa` 真实走通
- `review_assist`、`document_research`、`deep_research` 路由路径已在 runtime 中实现
