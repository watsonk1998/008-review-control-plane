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

# FastGPT 接入说明

## 配置解析

- 默认通过 `FASTGPT_*` 环境变量注入；若部署侧使用本地 JSON 配置文件，也应由运行环境显式指定
- 统一入口：`apps/api/src/config/fastgpt.py`
- 统一 adapter：`apps/api/src/adapters/fastgpt_adapter.py`

优先级：

1. `FASTGPT_BASE_URL`
2. `FASTGPT_API_URL`
3. `FASTGPT_API_KEY`
4. `FASTGPT_SEARCH_API_KEY`
5. 文件回退

## Mode A：全库 chunks 检索

接口：

`POST {BASE_URL}/core/dataset/searchTest`

特点：

- 首选模式
- 直接获取 chunks
- 避免把 FastGPT 当黑盒问答器

## Mode B：单文件 collection 定向检索

接口：

`POST {BASE_URL}/v1/chat/completions`

特点：

- 需要 `collectionId`
- 约定返回正文必须能 `JSON.parse`
- 008 在解析失败时保留 raw response，并抛出明确错误

## datasetId / collectionId 来源

- datasetId：008 内默认 registry 或请求体高级项
- collectionId：请求体高级项 / 环境变量注入

## 已验证

- Mode A 真实成功
- Mode B 已验证到原始响应链路；若返回非 JSON，008 会显式记录 parse failure

## 已知限制

- 当前没有统一 collection registry，collectionId 需要按任务提供
