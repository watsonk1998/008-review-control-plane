# 运行手册

## 1. 前置条件

本机需要：

- Python 3.11+
- Node.js 20+
- npm
- 可通过环境变量或部署侧配置文件提供：
  - `LLM_*` / `OPENAI_*`
  - `FASTGPT_*`
- 勘查副本存在（默认值，可改环境变量）：
  - `/tmp/008-discovery/DeepTutor`
  - `/tmp/008-discovery/gpt-researcher`

## 2. 安装依赖

```bash
cd .
make bootstrap
```

说明：bootstrap 脚本使用 `pip install --no-build-isolation -e ...`，以规避本机网络抖动时反复重新拉取 `setuptools/wheel` 导致的安装失败。

## 3. 推荐启动顺序

### 一键启动

```bash
make dev
```

### 分开启动

```bash
make dev-bridge
make dev-api
make dev-web
```

默认端口：

- DeepTutor bridge: `8121`
- API: `8018`
- Web: `3008`

## 4. 手动启动命令

### DeepTutor bridge

```bash
cd .
apps/api/.venv/bin/python scripts/run_deeptutor_bridge.py --port 8121
```

### API

```bash
cd apps/api
export DEEPTUTOR_BASE_URL=http://127.0.0.1:8121
export GPT_RESEARCHER_EXTERNAL_PATH=/tmp/008-discovery/gpt-researcher
. .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8018
```

### Web

```bash
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8018 npm run dev -- --port 3008
```

## 5. 验证命令

```bash
make test
make smoke
make verify-connectivity
```

## 6. 常见问题

### GPT Researcher import 失败

先确认：

- `GPT_RESEARCHER_EXTERNAL_PATH` 指向有效 repo
- `apps/api/.venv` 已通过 `make bootstrap` 安装依赖

### DeepTutor 不可用

确认：

- `DEEPTUTOR_EXTERNAL_PATH` 指向有效 repo
- bridge 已启动并监听 `8121`

### FastGPT Mode B 无结果或解析失败

- Mode B 依赖 `collectionId`
- 008 会保留 raw response，并在 JSON 解析失败时显式报错
- 没有 collectionId 时应优先使用 Mode A

### 前端连不上 API

确认：

- `NEXT_PUBLIC_API_BASE_URL`
- API 端口是否为 `8018`

## 7. 工件位置

- 任务状态库：`artifacts/tasks/runtime.sqlite`
- 单任务工件：`artifacts/tasks/<task-id>/`
- 联通验证：`artifacts/verification/`
