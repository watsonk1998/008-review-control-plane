# 审查 Agent 前后端接口冻结说明（最小验收版）

## 1. 接口清单

### 文件上传
- `POST /api/uploads/documents`
- 作用：上传目标/Basis/Context 文件，返回 `file_id`

### 创建任务
- `POST /api/review-tasks`
- 作用：以前端冻结契约创建正式审查任务；后端内部再编译为现有 `CreateTaskRequest + plan.hermesInput`

### 状态查询
- `GET /api/review-tasks/{task_id}`
- 作用：返回前端冻结后的状态与进度字段

> 前端展示规则补充：任务详情页的模拟进度必须在进入详情页时从 `0%` 起步，并按 `4 秒 1%` 推进；非终态最多 `90%`，终态才显示 `100%`。不得因任务后台已运行一段时间而在页面首屏瞬时跳高。

### SSE 进度
- `GET /api/review-tasks/{task_id}/events`
- 作用：输出 `task_created / progress / artifact_ready / completed / failed` 五类事件

### 最终结果
- `GET /api/review-tasks/{task_id}/result`
- 作用：返回冻结后的 `summary / modules / key_findings / recommendations / export_links / metadata / raw`

> 正式报告展示补充：网页预览与 PDF 导出必须同源消费 Hermes controller 生成的正式展示层（如 `finalReportViewModel / reportHtml / reportPrintCss`）。前端不得再单独拼接一套网页报告，同时下载旧的 support-layer PDF。

### 反馈
- `POST /api/review-reports/{report_id}/feedback`
- 作用：记录 `helpful / inaccurate / missing / save_as_template` 四类轻反馈

## 2. 请求 / 响应示例

### create task request
```json
{
  "classification": {
    "l1": "special_scheme_review",
    "l2": "distribution_network_special_scheme",
    "l3": ["temporary_power", "execution_continuity"]
  },
  "documents": {
    "target_file_ids": ["4de81fc3abc6455b8026b4fbe820d662"],
    "basis_file_ids": ["42a2e1aac1eb4d81b72330bbe05785ae"],
    "project_context_file_ids": ["0361121726314f7f9ff90be716f85f15"]
  },
  "builtin_asset_selections": {
    "standard_ids": ["gb50016"],
    "template_ids": ["structured_review_primary_worker"],
    "rule_pack_ids": ["power_outage_work.base"]
  },
  "review_intent": {
    "enabled_modules": ["structure_completeness", "execution_continuity", "legality_compliance"],
    "disabled_modules": ["evidence_validation"],
    "focus_requirements": ["重点检查停送电链路闭环", "重点检查专项章节完整性"]
  },
  "metadata": {
    "client_request_id": "req-e2e-001",
    "source": "mock-frontend",
    "debug": false
  }
}
```

### create task response
```json
{
  "task_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "status": "created",
  "review_brief_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "links": {
    "status": "/api/review-tasks/602224cc98e44b89b8fdc16fc9a4363d",
    "events": "/api/review-tasks/602224cc98e44b89b8fdc16fc9a4363d/events",
    "result": "/api/review-tasks/602224cc98e44b89b8fdc16fc9a4363d/result"
  }
}
```

### status response
```json
{
  "task_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "status": "completed",
  "progress_stage": "done",
  "progress_message": "Task completed",
  "created_at": "2026-04-11T07:38:54.831801Z",
  "updated_at": "2026-04-11T07:43:53.788792Z",
  "report_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "error": null,
  "degraded": false
}
```

### SSE event
```json
{
  "event": "progress",
  "task_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "stage": "modules_running",
  "message": "Selected agent: execution_risk_reviewer",
  "timestamp": "2026-04-11T07:40:53.214069Z",
  "status": "running"
}
```

### final result
```json
{
  "task_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "status": "completed",
  "report_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "summary": {
    "overall_conclusion": "修改后重新报审",
    "risk_level": "high",
    "key_counts": {
      "issues": 3,
      "manual_review_needed": 0
    },
    "key_metrics": {
      "high": 2,
      "medium": 1,
      "low": 0
    }
  },
  "metadata": {
    "generated_at": "2026-04-11T07:43:53.788792Z",
    "degraded": false,
    "traceability_available": true,
    "assembler": "HermesReviewAssembler"
  }
}
```

### feedback request / response
```json
{
  "feedback_type": "helpful",
  "comment": "结构完整性和执行链路结果可直接给前端验收页消费。"
}
```

```json
{
  "accepted": true,
  "report_id": "602224cc98e44b89b8fdc16fc9a4363d",
  "feedback_id": "cd36024de1244415820b5dc0fef78698"
}
```

## 3. 状态机枚举

### task status
- `created`
- `compiling`
- `running`
- `assembling`
- `completed`
- `failed`
- `degraded`

### progress stage
- `review_brief_compiling`
- `assets_loading`
- `agents_running`
- `modules_running`
- `report_assembling`
- `done`

### SSE event types
- `task_created`
- `progress`
- `artifact_ready`
- `completed`
- `failed`

## 4. 当前架构对应关系

- `HermesReviewAssembler` 是唯一官方最终输出入口
- `FinalReportMerger` 是 assembler 内部 helper，不是前端可感知对象
- `StructuredReviewCapabilityFacade` 是 008 能力暴露边界
- 前端不直接调用子 Agent、008 内部模块、Hermes prompt 或 merger/helper
- 前端只对接任务式接口：上传 / 创建任务 / 查状态 / 收 SSE / 取结果 / 提反馈

## 5. mock frontend 使用说明

### 路径
- 页面代码：`/Users/lucas/repos/review/008-review-control-plane/apps/web/src/app/review-acceptance/page.tsx`
- 页面组件：`/Users/lucas/repos/review/008-review-control-plane/apps/web/src/components/review-acceptance-page.tsx`
- 浏览器访问：`/review-acceptance`

### 功能
- 上传 target / basis / context 文件
- 选择 classification
- 勾选 enabled / disabled modules
- 输入 focus requirements
- 创建 `/api/review-tasks`
- 查看冻结后的状态 / SSE / 最终结果
- 提交轻反馈

### 启动
```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/api
. .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8018
```

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/web
npm run dev -- --hostname 127.0.0.1 --port 3018
```

### E2E 样例
- target：`/Users/lucas/repos/review/008-review-control-plane/fixtures/supervision/停电施工方案-威彦达.docx`
- basis：最小 `basis.md`
- context：最小 `context.txt`
- 页面截图：`/var/folders/x8/cmk3pv794cl1lvp_q508s1mc0000gn/T/playwright-mcp-output/1775896132802/page-2026-04-11T08-31-04-123Z.png`


## 6. 有效性核验补充（2026-04-15 supersede）

- “证据验证”中的有效性核验对象，指 **被审方案 `编制依据/编制说明` 章节中的规范性依据**，不是系统内置审查 basis。
- 表格冻结为三列：`序号 / 规范名称 / 核验状态`。
- `核验状态` 仅允许：`现行有效 / 疑似废止或替代 / 待人工核验`。
- 合同、委托函、图纸、技术资料、审批资料等非规范性条目不得进入该表。
