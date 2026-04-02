# DeepTutor 接入说明

## 接入方式

采用 **轻量 bridge**：

- bridge 文件：`/Users/lucas/repos/review/008-review-control-plane/scripts/run_deeptutor_bridge.py`
- 默认源码路径：`/tmp/008-discovery/DeepTutor`
- 暴露接口：
  - `GET /api/v1/system/status`
  - `WebSocket /api/v1/chat`

## 为什么不是全量官方服务

官方 DeepTutor 栈更偏完整 RAG 平台，未使用模块依赖较重。008 当前只需要稳定接入其聊天/解释能力，因此用 bridge 复用真实 `ChatAgent + SessionManager`，把没用到的重模块隔离掉。

## 008 内 adapter

文件：`/Users/lucas/repos/review/008-review-control-plane/apps/api/src/adapters/deeptutor_adapter.py`

统一方法：

- `health_check()`
- `ask_knowledge_question(...)`
- `ask_with_context(...)`

## 联通验证

已验证：

- `http://127.0.0.1:8121/api/v1/system/status`
- WebSocket chat 流式返回中文结果
- 真实 API 任务 `2e6e5025afe94556af23b20197a86a8e` 中已被 DeepResearchRuntime 调用

## 已知限制

- 当前 bridge 不等于完整 DeepTutor 发行版
- 更适合作为外部问答/解释能力服务，而非其完整知识平台镜像
