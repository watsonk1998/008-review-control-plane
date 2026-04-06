# 测试记录

## 测试基线

### 后端单元/集成测试

命令：

```bash
cd apps/api
. .venv/bin/activate
pytest -q
```

当前目标：覆盖 legacy runtime + structured_review parser / executor / runtime integration。

### 前端构建检查

命令：

```bash
cd apps/web
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
make eval-review-replay
```

- `test-review-unit`：跑 `tests/test_structured_review.py`
- `test-review-integration`：跑 runtime 中 `structured_review` 分支（覆盖 fixture 与 `sourceDocumentRef`）
- `eval-review`：执行 legacy CI 稳定子集，并同时执行 official versioned stage gate；新增 experimental versioned cases 只进入 diagnostics
- `eval-review-ablations`：输出 parser / visibility / rule engine / llm explanation 的消融结果；其中 `disable_visibility_check` 仅允许走内部 ablation wiring
- `eval-review-cross-pack`：对比自动 pack 选择与强制 expected packs 的结果
- `eval-review-cross-model`：固定 facts/rules，仅替换 explanation model；facts / rule hits / policy refs 不应漂移
- `eval-review-replay`：按 case 回放 structured_review，并保留真实工件到 `artifacts/eval-replay/`；默认回放 legacy stable + official versioned stage-gate cases，也可通过 `CASE_ID / CASE_VERSION / DOC_TYPE / OUTPUT_DIR` 过滤

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

当前 P0 / experimental 数据集：

- legacy CI 稳定子集：12 cases
- 本地完整评测池：30 cases
- versioned cases：10 cases，其中 3 个 official CI stage-gate cases
- 新增 experimental versioned cases：
  - `cn_construction_scheme_attachment_gap_001`
  - `cn_supervision_plan_monitoring_gap_001`
  - `cn_review_support_material_context_only_001`
  - `cn_construction_org_gas_area_ops_001`
- P0 正式支持：
  - `construction_org`
  - `hazardous_special_scheme`
- skeleton / experimental 覆盖：
  - `construction_scheme`
  - `supervision_plan`
  - `review_support_material`

验收要点：

- 能输出 `summary / resolvedProfile / issues / matrices / artifactIndex / reportMarkdown`
- `structured_review` 同时支持 `fixtureId` 与 `sourceDocumentRef`
- public API 不接受 `disable_visibility_check`
- `result.visibility` 与 `unresolvedFacts` 可被 API/UI/eval 一致消费
- `result.visibility.parseMode / parseWarnings / manualReviewReason / preflight` 是 canonical L0 消费入口
- `summary.visibilitySummary` 仅作为 display summary 保留
- `artifactIndex` 中必须包含 `structured-review-l0-visibility`；report 语义工件会额外输出 `structured-review-report-buckets`
- fresh task 的 `structured-review-l0-visibility.json.visibility` 必须与 `structured-review-result.json.visibility` 一致
- issue 会显式输出 `issueKind / applicabilityState / missingFactKeys / blockingReasons`
- 能识别重复章节、附件可视域缺口、专项方案挂接不清、停机窗口与资源压力
- 能识别施工组织设计核心章节完整性缺口
- 能识别一般施工方案核心章节完整性缺口
- 能识别监理规划核心章节缺口与监测监控安排缺口
- 能识别审查支持材料只能补充背景、不能替代正式方案正文
- 能识别危大专项方案核心章节缺口、验算依据缺口、措施-监测闭环问题
- 能识别煤气区域作业控制与应急链路缺口
- 能区分 `attachment_unparsed / referenced_only / unknown / missing`
- `missing` 只在有明确证据时产出
- parser-limited PDF 必须前置触发 `manualReviewNeeded=true`，且 `visibility.preflight.gateDecision=manual_review_required`
- 重复的一级/二级关键章节或附件边界标题若会破坏 canonical section extraction，必须前置触发 `weak_section_structure_signal`
- `structured-review-l0-visibility.json` 必须包含 `checklist / blockingReasons / parserLimitations / attachmentTaxonomySummary`
- `structured-review-rule-hits.json` 与 `rule-hit-matrix.json` 必须包含 `applicabilityState / requiredFactKeys / missingFactKeys / clauseIds / blockingReasons`
- `unresolvedFacts` 必须包含 `sourceExtractor / blockingReason / visibilityLimited / blockingRuleIds / blockingIssueIds`
- visible-scope 内的章节/监测监控缺失必须落为 `hard_defect / applies`，不得因为空 `docEvidence` 漂移为 `evidence_gap`
- parser-limited 下的章节/监测监控缺失必须落为 `blocked_by_missing_fact`，且 `missingFactKeys / blockingReasons` 至少其一可解释
- `evidence_gap` 若出现，必须具备显式 explainability；空 `docEvidence` 不能单独成为证据缺口依据
- blocked issue 的 `docEvidence / policyEvidence` 必须携带 `evidenceGapReason`；document-side evidence 必须有 `sourceProvenance`
- artifact API 可列出和下载工件，且与 `result.artifactIndex` 同口径；对新任务 `artifactIndex` 即使为空也优先于目录扫描
- 详情页优先展示 `resolvedProfile / visibility / unresolvedFacts / artifactIndex / reviewerDecision`，再展示报告与原始 JSON
- reviewer 结果页以结构化方式展示 `attachmentVisibility / ruleHits / conflicts / sectionStructure`；raw JSON 只保留为折叠调试信息
- reviewer 结果页需同时展示 `reviewPreparation` 摘要，并至少暴露 `provenance.sourceTier / caseVersion`；同时保留“仅用于 internal-reviewed preparation，不是 reviewed truth”的语义边界
- `GET /api/tasks/{taskId}/review-preparation` 必须返回带 provenance 的 preparation asset；未命中版本化样本时必须显式回退 `sourceTier=runtime_only`
- review-preparation summary/asset 必须对 issue / attachment 显式表达 `eligible / deferred / rejected` promotion disposition；attachment summary 需额外暴露 `rejectedAttachmentIds`
- `/api/tasks/support-scope` 需同时返回 pack `promotionCriteria`；表单/UI 不得自行发明 official/experimental/promotion 结论

## P1 主门槛

- legacy CI 稳定子集作为**回归地板**：
  - issue recall ≥ `0.75`
  - l1 hit rate ≥ `0.85`
  - pack selection accuracy ≥ `0.95`
  - policy ref accuracy ≥ `0.75`
  - attachment visibility accuracy ≥ `0.55`
  - severity accuracy ≥ `0.75`
  - manual review flag accuracy ≥ `0.95`
- official versioned stage gate 作为**主质量门槛**：
  - facts accuracy ≥ `0.90`
  - rule hit accuracy ≥ `0.85`
  - hazard identification accuracy ≥ `0.90`
  - attachment visibility accuracy ≥ `0.90`
  - manual review flag accuracy ≥ `0.80`
- experimental versioned cases进入 diagnostics，但不提升 skeleton documentType 为 official CI gate
- `layeredMetrics` 必须按 `L0 / L1 / L2 / L3 / CrossCutting` 分组输出，其中 L3 当前允许 `diagnosticOnly=true`
- `L0` 必须额外输出 `preflight_gate_consistency`
- `L2` 必须额外输出 `evidence_traceability`
- `CrossCutting` 必须额外输出 diagnostic-only 的 `review_preparation_provenance_consistency`
- eval 输出必须显式区分 `gateRole=blocking` 与 `gateRole=diagnostic`
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
