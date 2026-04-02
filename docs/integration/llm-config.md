# 本地 LLM 配置说明

## 配置文件

默认读取：`/Users/lucas/tools/from-obsidian/AI/config/century.json`

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
