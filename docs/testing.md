# 测试记录

## 测试基线

### 后端单元/集成测试

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/api
. .venv/bin/activate
pytest -q
```

当前结果：`8 passed`

### 前端构建检查

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/web
npm run lint
npm run build
```

已通过。

### 前端端到端页面验证

- 成功 UI 任务：`5e778a1c468340cf895846ffa3a3d146`
- 页面工件：
  - `artifacts/verification/end-to-end-ui-or-api.png`
  - `artifacts/verification/end-to-end-ui-or-api.json`

## 功能测试矩阵

### 测试 1：标准问答

目标链路：DeepResearchRuntime → FastGPT → DeepTutor

已验证：

- 真实成功任务（前端发起）：`5e778a1c468340cf895846ffa3a3d146`
- 历史 API 成功任务：`2e6e5025afe94556af23b20197a86a8e`
- 能看到 plan / events / Fast chunk / DeepTutor 返回

对应工件：

- `artifacts/tasks/2e6e5025afe94556af23b20197a86a8e/fast-dataset.json`
- `artifacts/tasks/2e6e5025afe94556af23b20197a86a8e/deeptutor.json`
- `artifacts/verification/end-to-end-ui-or-api.png`
- `artifacts/verification/end-to-end-ui-or-api.json`

### 测试 2：深度研究

目标链路：DeepResearchRuntime → GPT Researcher

已验证：

- API 成功任务：`0a76e1d975e2453c8fa263c6aa280412`
- 直连 adapter 成功工件：`artifacts/verification/gpt-researcher-deep-research.json`
- 当前策略：若提供 `sourceUrls` 且 `useWeb=false`，008 会先拉取来源正文，再以 GPT Researcher report writer 生成 source-grounded deep research，避免把成败完全绑定到外部搜索引擎。

### 测试 3：文档研究

目标链路：fixture/docx → GPT Researcher

样本：

- `fixtures/copied/supervision/230235-冷轧厂2030单元三台行车电气系统改造-施工组织设计.docx`
- `fixtures/copied/supervision/监理实施规划（南校区宿舍楼）20250710(1).docx`

已验证：

- API 成功任务：`7f0fc83965e94a66874e00b96e5a03ee`
- 联通工件：`artifacts/verification/gpt-researcher-connectivity.json`
- 任务工件：
  - `artifacts/tasks/7f0fc83965e94a66874e00b96e5a03ee/document-preview.json`
  - `artifacts/tasks/7f0fc83965e94a66874e00b96e5a03ee/document-research.json`

### 测试 4：审查辅助

目标链路：DeepResearchRuntime → FastGPT → DeepTutor / GPT Researcher → LLM

已验证：

- API 成功任务：`23a57bd1d3a94454965452143325018b`
- 返回 `capabilitiesUsed = ["fast", "deeptutor", "gpt_researcher", "llm_gateway"]`
- 输出包含“辅助审查要点”和“这是辅助审查结果，不等于正式审查结论。”
- 任务工件：
  - `artifacts/tasks/23a57bd1d3a94454965452143325018b/review-fast.json`
  - `artifacts/tasks/23a57bd1d3a94454965452143325018b/review-summary.json`
  - `artifacts/tasks/23a57bd1d3a94454965452143325018b/review-doc-preview.json`

## 测试汇总工件

- `artifacts/verification/task-matrix.json`
- `artifacts/verification/llm-health.json`
- `artifacts/verification/fast-mode-a.json`
- `artifacts/verification/fast-mode-b.md`
- `artifacts/verification/deeptutor-connectivity.json`
- `artifacts/verification/gpt-researcher-connectivity.json`
- `artifacts/verification/gpt-researcher-deep-research.json`

## 推荐回归命令

```bash
make test
make smoke
make verify-connectivity
```
