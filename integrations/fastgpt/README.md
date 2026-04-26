# hermes-review-agent FastGPT 迁移 bundle

本目录维护 `hermes-review-agent` 到 FastGPT 的迁移产物生成逻辑。当前方案采用：

- 1 个主工作流：固定编排正式审查链路。
- 6 个工作流工具：分别承接规则配置、上下文构建、AI 主审、确定性审查、008 支撑层、最终组装。
- 治理快照 + dataset manifest：从 Python 真源导出，并在生成期编译进 code node，避免 FastGPT 运行态 hidden object 输入丢失。

注意：FastGPT v4.14.1+ UI 中显示为「工作流工具 / 我的工具」。页面「导入配置」使用 `.workflow*.json`；`.create*.json` 是 OpenAPI 创建 payload，`.template*.json` 是模板包装，不作为页面导入文件。

## 生成流程

```bash
cd /Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt
npm install
npm run generate:all
npm test
```

`npm run generate:all` 会按当前 `artifacts/fastgpt/workflow_tool_registry.local.json` 生成 linked JSON。若换 FastGPT 实例，先更新 registry 副本中的模型名与 6 个工作流工具 AppId，再重新执行 `node ./scripts/apply_runtime_overrides.mjs <registry.json>`。

FastGPT 页面里的「导入配置」入口只接受顶层 `nodes / edges / chatConfig` 的 workflow 结构。不要把 `.create*.json` 或 `.template*.json` 作为页面导入文件使用。

如需把已导入的工作流工具 ID 回填到主工作流：

```bash
cp /Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow_tool_registry.template.json /tmp/hermes-fastgpt-registry.json
# 编辑 /tmp/hermes-fastgpt-registry.json，填入 aiModel 与 6 个工作流工具 ID
node ./scripts/apply_runtime_overrides.mjs /tmp/hermes-fastgpt-registry.json
```

本轮新增 `hermes_review_config_wft`。旧的本地 registry 若只包含 5 个工具 ID，`npm run generate:all` 会在 linked 主工作流校验阶段提示 `__WFT_HERMES_REVIEW_CONFIG_ID__` 未回填；这是部署前绑定缺口，需先在 FastGPT 导入配置工具并把新 AppId 写入 registry。

## 导入顺序

1. 在 FastGPT「工作流工具 / 我的工具」中新建或打开 6 个工作流工具，分别导入 `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/*.workflow.linked.json`。
2. 在 FastGPT「我的工具」确认 6 个工作流工具存在。
3. 将工具 ID 回填到 registry JSON，并生成 linked 主工作流。
4. 导入 `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.linked.workflow.json`。

压缩交付包生成命令：

```bash
cd /Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt
npm run build:delivery
```

## 质量诊断

完整后台流日志必须通过主应用 AppId 拉取，raw JSON 只能放 `/tmp` 或其他临时目录，不提交 repo。拿到 AppId 后使用共享导出脚本：

```bash
python3 /Users/lucas/.codex/skills/fastgpt-shared/scripts/export_fastgpt_flow_logs.py \
  --base-url https://xtaiqa.jg-pm.com/api \
  --api-key "$FASTGPT_API_KEY" \
  --app-id "$FASTGPT_APP_ID" \
  --export-dir /tmp/hermes-fastgpt-flowlogs

npm run diagnose:quality -- --latest /tmp/hermes-fastgpt-flowlogs \
  --output reports/fastgpt-quality-diagnostics-$(date +%F).md
```

没有 AppId 时，只能对 `detail=true` 响应或现有 summary JSON 做浅层诊断；报告必须标注 `summary-only`，不得宣称拿到了 token、耗时、reviewer findings 或 traceability。

## 主要产物

- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.workflow.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.create.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.linked.workflow.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.linked.create.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/*.workflow.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/*.workflow.linked.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/*.create.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/governance/governance_snapshot.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/governance/dataset_manifest.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-fastgpt-parity-matrix.md`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-fastgpt-import-readiness.md`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-fastgpt-layout-validation.md`

## 边界说明

- 不新增 repo-owned Helper API。
- 不使用 MCP。
- 当前 6 个 workflow tool AppId 是当前 FastGPT 实例绑定信息，不可跨实例复用。
- dataset placeholders 仅作为治理清单/后续知识库绑定提示；当前工作流没有 datasetSearchNode，业务验收以最终中文正式/降级报告闭环为准。
- 旧的 `/integrations/fastgpt/toolset/hermesStructuredReview` 仅保留为迁移参考与本地测试素材；当前交付物不是系统插件 `.pkg`。
- v1 输出 Markdown / HTML / JSON；PDF 二进制导出不纳入本阶段承诺。
