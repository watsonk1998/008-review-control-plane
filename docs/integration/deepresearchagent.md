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
