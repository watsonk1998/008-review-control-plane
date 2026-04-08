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

# 本地 LLM 配置说明

## 配置文件

默认优先读取 `LLM_*` / `OPENAI_*` 环境变量；若部署侧使用本地 JSON 配置文件，也应由运行环境显式指定

当前 008 使用：

- chat profile：`dashscope`
- embedding profile：`dashscope_embedding`

## 统一解析入口

- `apps/api/src/config/llm.py`
  - `resolve_llm_config()`
  - `resolve_embedding_config()`
- `apps/api/src/adapters/llm_gateway.py`

## 读取优先级

### Chat

1. `LLM_BASE_URL` / `OPENAI_BASE_URL`
2. `LLM_API_KEY` / `OPENAI_API_KEY`
3. `LLM_MODEL`
4. `LLM_PROVIDER`
5. 文件回退

### Embedding

1. `EMBEDDING_BASE_URL`
2. `EMBEDDING_API_KEY`
3. `EMBEDDING_MODEL` / `OPENAI_EMBEDDING_MODEL`
4. `EMBEDDING_PROVIDER`
5. 文件回退

## 安全约束

- 仅服务端读取密钥
- 前端只拿到 sanitized 配置摘要
- 日志与 artifacts 中对密钥做脱敏

## 已验证

- LLM health 已真实成功返回 `pong`
- GPT Researcher 的 env bridge 也基于该配置成功 import/health
