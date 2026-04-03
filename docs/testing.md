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
make eval-review-ablations
make eval-review-cross-pack
make eval-review-cross-model
```

- `test-review-unit`：跑 `tests/test_structured_review.py`
- `test-review-integration`：跑 runtime 中 `structured_review` 分支（覆盖 fixture 与 `sourceDocumentRef`）
- `eval-review`：执行 legacy CI 稳定子集，并同时执行 official versioned stage gate
- `eval-review-ablations`：输出 parser / visibility / rule engine / llm explanation 的消融结果
- `eval-review-cross-pack`：对比自动 pack 选择与强制 expected packs 的结果
- `eval-review-cross-model`：固定 facts/rules，仅替换 explanation model

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

- `fixtures/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx`
- `fixtures/supervision/监理实施规划（南校区宿舍楼）20250710(1).docx`

### 测试 4：审查辅助

目标链路：DeepResearchRuntime → FastGPT → DeepTutor / GPT Researcher → LLM

验收要点：

- 输出包含“辅助审查要点”
- 输出包含“这是辅助审查结果，不等于正式审查结论。”
- `review_assist` shape 不因 `structured_review` 引入而回归

### 测试 5：结构化正式审查

目标链路：DocumentLoader / review parser → facts → rules → evidence → report

当前 P0 数据集：

- legacy CI 稳定子集：12 cases
- 本地完整评测池：26 cases
- versioned cases：6 cases，其中 3 个 official CI stage-gate cases
- P0 正式支持：
  - `construction_org`
  - `hazardous_special_scheme`
- skeleton / registry 覆盖：
  - `construction_scheme`
  - `supervision_plan`
  - `review_support_material`

验收要点：

- 能输出 `summary / resolvedProfile / issues / matrices / artifactIndex / reportMarkdown`
- `structured_review` 同时支持 `fixtureId` 与 `sourceDocumentRef`
- public API 不接受 `disable_visibility_check`
- `result.visibility` 与 `unresolvedFacts` 可被 API/UI/eval 一致消费
- `summary.visibilitySummary` 仅作为 display summary 保留
- 能识别重复章节、附件可视域缺口、专项方案挂接不清、停机窗口与资源压力
- 能识别施工组织设计核心章节完整性缺口
- 能识别危大专项方案核心章节缺口、验算依据缺口、措施-监测闭环问题
- 能区分 `attachment_unparsed / referenced_only / unknown / missing`
- `missing` 只在有明确证据时产出
- artifact API 可列出和下载工件，且与 `result.artifactIndex` 同口径
- 详情页能展示 top-level visibility / issues / rule-hit trace / reviewer decision / 原始 JSON

## P1 主门槛

- issue recall ≥ `0.80`
- l1 hit rate ≥ `0.80`
- pack selection accuracy ≥ `0.85`
- policy ref accuracy ≥ `0.85`
- attachment visibility accuracy ≥ `0.90`
- severity accuracy ≥ `0.75`
- manual review flag accuracy ≥ `0.85`
- versioned official stage gate：
  - facts accuracy ≥ `0.90`
  - rule hit accuracy ≥ `0.85`
  - hazard identification accuracy ≥ `0.90`
  - attachment visibility accuracy ≥ `0.90`
  - manual review flag accuracy ≥ `0.80`
- `review_assist` 回归失败数 = `0`

## 推荐回归命令

```bash
make test
make test-review-unit
make test-review-integration
make eval-review
make eval-review-ablations
make eval-review-cross-pack
make eval-review-cross-model
make smoke
make verify-connectivity
```
