# 测试记录

## 测试基线

### 后端单元/集成测试

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/api
. .venv/bin/activate
pytest -q
```

当前目标：覆盖 legacy runtime + structured_review parser / executor / runtime integration。

### 前端构建检查

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/web
npm run lint
npm run build
```

### review domain 专项命令

```bash
make test-review-unit
make test-review-integration
make eval-review
```

- `test-review-unit`：跑 `tests/test_structured_review.py`
- `test-review-integration`：跑 runtime 中 `structured_review` 分支
- `eval-review`：执行 `fixtures/review_eval/` 下的 golden cases

## 功能测试矩阵

### 测试 1：标准问答

目标链路：DeepResearchRuntime → FastGPT → DeepTutor

已验证：

- 真实成功任务（前端发起）：`5e778a1c468340cf895846ffa3a3d146`
- 历史 API 成功任务：`2e6e5025afe94556af23b20197a86a8e`
- 能看到 plan / events / Fast chunk / DeepTutor 返回

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

### 测试 4：审查辅助

目标链路：DeepResearchRuntime → FastGPT → DeepTutor / GPT Researcher → LLM

验收要点：

- 输出包含“辅助审查要点”
- 输出包含“这是辅助审查结果，不等于正式审查结论。”
- `review_assist` shape 不因 `structured_review` 引入而回归

### 测试 5：结构化正式审查

目标链路：DocumentLoader / review parser → facts → rules → evidence → report

当前最小 golden case：

- `fixtures/review_eval/construction_org/case_001`

验收要点：

- 能输出 `summary / issues / matrices / reportMarkdown / artifacts`
- 能识别重复章节、附件可视域缺口、专项方案挂接不清、停机窗口与资源压力
- 能区分 `attachment_unparsed` 与可直接证实的正文缺陷
- 详情页能展示 issues / matrices / 原始 JSON

## 当前 golden case 目标指标

- issue recall ≥ `0.75`
- attachment visibility accuracy = `1.0`
- `review_assist` 回归失败数 = `0`

## 推荐回归命令

```bash
make test
make test-review-unit
make test-review-integration
make eval-review
make smoke
make verify-connectivity
```
