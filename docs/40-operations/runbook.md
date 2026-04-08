> [!NOTE]
> **本文档职责**
> - 负责：
>   - 说明系统运行、维护、常见操作与排障流程
> - 不负责：
>   - 不定义产品能力边界
>   - 不替代架构、PRD 或验收文档
> - 主适用读者：
>   - 运维人员、研发工程师、值班人员
> - 冲突处理：
>   - 涉及产品定义与 official 能力时，以 product / governance 层文档为准
> - 文档状态：
>   - 运行维护文档

---

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

## 8. weknora 部署与紧急排障

### 部署模型（非 Git 仓库源）
weknora 服务器部署目录：`/root/008-review-control-plane`

> [!WARNING]
> 该目录**不是一个 git checkout**，请绝对不要在远端服务器上执行 `git pull`！

标准服务器更新流程：
1. 确保在**本地开发机**完成 commit 与 push
2. 通过 `rsync` 仅同步源码体到服务端目录 `/root/008-review-control-plane`
3. 视变更范围决定重建的镜像层级：
   - 对于纯 Web （前端）变更：若源码树已同步，仅需重建并拉起 `web`。
   - 对后端 API / Python 依赖库产生变更：**必须坚决重建** `api`，以及由于共享基础镜像需要同步连带重建的 `deeptutor-bridge`。
   ```bash
   # 重启命令范例
   docker compose up -d --build api web deeptutor-bridge
   ```

### 排障画像：WeasyPrint 底层依赖事故

当遭遇前端“专项方案不显示”，且由于 `support-scope` 响应 `500 Internal Server Error` 导致页面发生降级时，切勿盲目认定前端 selector 发生损坏。

**根因还原：**
由于 API 渲染服务基于 `python:3.11-slim`，该基础 Debian Docker 映像将部分图形计算库（Pango, libcairo）精简掉了。当 Uvicorn 进行 `import md2pdf -> weasyprint` 生命周期时，`weasyprint` 中的 `cffi` 寻找底层 `libpangoft2-1.0-0.so` 系统库失败并抛出 OSErrors，当场引发核心进程死机。
  
**紧急验证命令集：**
当发生此情况或系统启动期间，实施以下连环求证动作：
```bash
# 1. 探底容器存活长效性
docker compose ps
# (期望：Up 并长时间保持，不能处于Restarting死循环状态)

# 2. 从内部剖析 API 的死前遗言
docker compose logs api --tail=50

# 3. 本机环回测血
curl http://localhost:81/api/tasks/support-scope
# (期望：吐出满载 capabilityTree 树结构的 200 OK 载荷)

# 4. 前端联机验证
curl -I http://localhost:81
# (无视渲染直接查首部，期望：200 OK，而非 500 Server Error)
```
排查中必须保证这四组证据链连通闭环，再移交业务侧继续验收。
