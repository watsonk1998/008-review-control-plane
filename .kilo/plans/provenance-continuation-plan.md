# Provenance 证据溯源重构 — 续接执行计划

## ⚠️ 关键约束（Kilo 必须遵守）

1. **禁止修改 `external/hermes-agent/` 内任何文件**
2. **禁止截断或重写 `sqlite_store.py` 的现有 CRUD 方法**（get_task, create_task, update_task, list_tasks, append_event, list_events, _row_to_task 等必须完整保留）
3. **每完成一个文件的修改后立即 commit**，不要积攒多个文件再一次性 commit
4. **修改后必须执行语法验证**：`python -c "import ast; ast.parse(open('path').read())"`
5. **JSON 模板文件修改后必须验证**：`python -c "import json; json.load(open('path'))"`
6. **不要使用 worktree 模式**，直接在当前分支 `report-visual-upgrade` 上工作

---

## 1. 已完成的部分（commit f6d4b29，已部署）

以下文件已经修改并 commit，**不需要重做**：

### contracts.py ✅
- `FindingItem` 新增 `hallucination_risk: bool = False`
- `FindingItem` 新增 `evidence_span_ids: list[str] = Field(default_factory=list)`

### assembler.py ✅  
- 重构了 review outcome 合并逻辑
- 模块级门禁实现

### support_packet_builder.py ✅
- 新增 `_register_span()` 方法
- `build_packet()` 中构造 `provenance_registry: dict[str, EvidenceSpan]`
- 从 facts 注册文档证据 spans

---

## 2. 需要续接的任务（按顺序执行）

### 任务 2.1：models.py 增强

**文件**: `apps/api/src/domain/models.py`

**目标**: 为 EvidenceSpan 添加稳定 span_id，增强 AnnotatedFact 和 FactRelationship

**变更要点**:
- `EvidenceSpan` 类新增 `span_id: str = ""` 字段（默认空字符串保持向后兼容）
- 现有 `AnnotatedFact` 类确认有 `evidence_span_ids: list[str]` 和 `provenance_ids: list[str]`（已有则跳过）
- 现有 `FactRelationship` 类确认有 `provenance_ids: list[str]`（已有则跳过）
- **不要删除或修改任何现有字段**，只能添加新字段

**验证**:
```bash
python -c "import ast; ast.parse(open('apps/api/src/domain/models.py').read())"
```

**完成后立即 commit**:
```bash
git add apps/api/src/domain/models.py
git commit -m "feat(models): add span_id to EvidenceSpan for provenance tracking"
```

---

### 任务 2.2：schema.py API Schema 更新

**文件**: `apps/api/src/review/schema.py`

**目标**: API 层 schema 对接 provenance 新字段

**变更要点**:
- 如果有 Pydantic response model 对应 FindingItem，同步新增 `hallucination_risk` 和 `evidence_span_ids`
- 如果有 EvidenceSpan 的 API 表示层，同步新增 `span_id`
- **不要修改与 provenance 无关的 schema**

**验证 + commit**:
```bash
python -c "import ast; ast.parse(open('apps/api/src/review/schema.py').read())"
git add apps/api/src/review/schema.py
git commit -m "feat(schema): sync provenance fields to API schema"
```

---

### 任务 2.3：pipeline.py Span ID 生成

**文件**: `apps/api/src/review/pipeline.py`

**目标**: 文档提取时为每个 Block/Table 生成确定性 span_id

**变更要点**:
- 在文档解析/提取阶段，为每个 EvidenceSpan 生成确定性 span_id
- span_id 生成算法：`hashlib.md5(f"{source_type}:{source_id}:{locator}".encode()).hexdigest()[:16]`
- 绑定到对应的 EvidenceLocator
- **不要修改 pipeline 的执行流程和阶段顺序**

**验证 + commit**:
```bash
python -c "import ast; ast.parse(open('apps/api/src/review/pipeline.py').read())"
git add apps/api/src/review/pipeline.py
git commit -m "feat(pipeline): generate deterministic span_id during document extraction"
```

---

### 任务 2.4：clause_store.py 注册表对接

**文件**: `apps/api/src/review/evidence/clause_store.py`

**目标**: 证据条款存储与 provenance_registry 对接

**变更要点**:
- 在存储/检索 evidence spans 时，确保 span_id 被正确传递
- 如果 clause_store 有创建 EvidenceSpan 的逻辑，同步生成 span_id
- **不要修改 clause_store 的存储格式或接口签名**

**验证 + commit**:
```bash
python -c "import ast; ast.parse(open('apps/api/src/review/evidence/clause_store.py').read())"
git add apps/api/src/review/evidence/clause_store.py
git commit -m "feat(clause_store): integrate span_id into evidence clause storage"
```

---

### 任务 2.5：final_report_view_model.py 幻觉风险标记

**文件**: `apps/api/src/review/report/final_report_view_model.py`

**目标**: 报告渲染时标记幻觉风险的 issue

**变更要点**:
- 在构建 view model 时，检查 `finding.hallucination_risk` 字段
- 如果 `hallucination_risk == True`，在渲染的 HTML 中添加 CSS 类 `highlight-hallucination-risk`
- 对应 CSS 样式使用淡红色背景标记（`background: rgba(239, 68, 68, 0.08)`）
- **禁止使用 Emoji 表情符号**（参见 AGENTS.md HG-23）
- **不要修改 executive summary 逻辑**（参见 AGENTS.md 相关修正）

**验证 + commit**:
```bash
python -c "import ast; ast.parse(open('apps/api/src/review/report/final_report_view_model.py').read())"
git add apps/api/src/review/report/final_report_view_model.py
git commit -m "feat(report): add hallucination risk visual indicator in final report"
```

---

## 3. 全量验证（所有任务完成后）

```bash
# 语法验证
cd /Users/lucas/repos/review/hermes-review-agent
for f in apps/api/src/domain/models.py \
         apps/api/src/review/schema.py \
         apps/api/src/review/pipeline.py \
         apps/api/src/review/evidence/clause_store.py \
         apps/api/src/review/report/final_report_view_model.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK: $f" || echo "FAIL: $f"
done

# 单元测试
cd apps/api && .venv/bin/pytest tests/ -x -q
```

---

## 4. 架构参考

```
请求 → pipeline.py (生成 span_id)
          ↓
    clause_store.py (存储/检索带 span_id 的证据)
          ↓
    support_packet_builder.py (构建 provenance_registry) ← ✅ 已完成
          ↓
    assembler.py (校验 span_id 合法性) ← ✅ 已完成
          ↓
    final_report_view_model.py (幻觉风险高亮渲染)
```

## 5. 绝对禁止

- ❌ 不要修改 `sqlite_store.py` 的 _row_to_task / create_task / get_task / update_task 等方法
- ❌ 不要修改 `external/hermes-agent/` 任何文件
- ❌ 不要修改 `task-detail.tsx` 的 CSS 清洗逻辑
- ❌ 不要修改进度条逻辑（已校准完毕）
- ❌ 不要使用 Emoji 表情符号
