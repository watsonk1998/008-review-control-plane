"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  createReviewTask,
  fetchReviewTask,
  fetchReviewTaskResult,
  fetchSupportScope,
  getReviewTaskEventsUrl,
  resolveApiUrl,
  submitReviewReportFeedback,
  uploadReviewDocument,
} from "@/lib/api";
import type {
  FrozenUploadResponse,
  ReviewFeedbackType,
  ReviewModuleName,
  ReviewTaskCreateRequest,
  ReviewTaskResultResponse,
  ReviewTaskStatusResponse,
  ReviewTaskSseEvent,
  SupportScopeResponse,
} from "@/types/control-plane";

const MODULE_OPTIONS: Array<{ value: ReviewModuleName; label: string }> = [
  { value: "structure_completeness", label: "结构完整性" },
  { value: "parameter_consistency", label: "参数一致性" },
  { value: "legality_compliance", label: "合法合规性" },
  { value: "execution_continuity", label: "工序连贯性" },
  { value: "evidence_validation", label: "证据验证" },
];

function splitLines(value: string) {
  return value
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function riskLabel(value: string) {
  return ({ high: "高风险", medium: "中等风险", low: "低风险", unknown: "未判定" } as Record<string, string>)[value] || value;
}

function moduleStatusLabel(value: string) {
  return ({ available: "已生成", partial: "部分覆盖", not_applicable: "未启用" } as Record<string, string>)[value] || value;
}

export function ReviewAcceptancePage() {
  const [supportScope, setSupportScope] = useState<SupportScopeResponse | null>(null);
  const [targetFile, setTargetFile] = useState<FrozenUploadResponse | null>(null);
  const [basisFiles, setBasisFiles] = useState<FrozenUploadResponse[]>([]);
  const [contextFiles, setContextFiles] = useState<FrozenUploadResponse[]>([]);
  const [l1, setL1] = useState("general_management_review");
  const [l2, setL2] = useState("distribution_network_special_scheme");
  const [l3, setL3] = useState("power_outage_work");
  const [standardIds, setStandardIds] = useState("gb50016");
  const [templateIds, setTemplateIds] = useState("structured_review_primary_worker");
  const [rulePackIds, setRulePackIds] = useState("distribution_network.power_outage.v1\ndistribution_network.operation_chain.v1\ndistribution_network.restoration_closure.v1");
  const [focusRequirements, setFocusRequirements] = useState("重点检查停送电链路闭环\n重点检查专项章节完整性");
  const [enabledModules, setEnabledModules] = useState<ReviewModuleName[]>([
    "structure_completeness",
    "execution_continuity",
    "legality_compliance",
  ]);
  const [disabledModules, setDisabledModules] = useState<ReviewModuleName[]>([]);
  const [task, setTask] = useState<ReviewTaskStatusResponse | null>(null);
  const [result, setResult] = useState<ReviewTaskResultResponse | null>(null);
  const [events, setEvents] = useState<ReviewTaskSseEvent[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    void fetchSupportScope().then(setSupportScope).catch(() => setSupportScope(null));
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const documentOptions = useMemo(() => {
    return (supportScope?.documentTypes || []).map((item) => ({ value: item.documentType, label: item.label }));
  }, [supportScope]);

  const requestPayload = useMemo<ReviewTaskCreateRequest>(() => {
    return {
      classification: {
        l1,
        l2: l2 as ReviewTaskCreateRequest["classification"]["l2"],
        l3: splitLines(l3),
      },
      documents: {
        target_file_ids: targetFile ? [targetFile.file_id] : [],
        basis_file_ids: basisFiles.map((item) => item.file_id),
        project_context_file_ids: contextFiles.map((item) => item.file_id),
      },
      builtin_asset_selections: {
        standard_ids: splitLines(standardIds.replaceAll(",", "\n")),
        template_ids: splitLines(templateIds.replaceAll(",", "\n")),
        rule_pack_ids: splitLines(rulePackIds.replaceAll(",", "\n")),
      },
      review_intent: {
        enabled_modules: enabledModules,
        disabled_modules: disabledModules,
        focus_requirements: splitLines(focusRequirements),
      },
      metadata: {
        client_request_id: "acceptance-request",
        source: "mock-frontend",
        debug: false,
      },
    };
  }, [basisFiles, contextFiles, disabledModules, enabledModules, focusRequirements, l1, l2, l3, rulePackIds, standardIds, targetFile, templateIds]);

  async function handleUpload(kind: "target" | "basis" | "context", file: File) {
    setUploading(kind);
    setError(null);
    try {
      const uploaded = await uploadReviewDocument(file);
      if (kind === "target") setTargetFile(uploaded);
      if (kind === "basis") setBasisFiles((current) => [...current, uploaded]);
      if (kind === "context") setContextFiles((current) => [...current, uploaded]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "文件上传失败");
    } finally {
      setUploading(null);
    }
  }

  function subscribe(taskId: string) {
    eventSourceRef.current?.close();
    const source = new EventSource(getReviewTaskEventsUrl(taskId));
    eventSourceRef.current = source;

    ["task_created", "progress", "artifact_ready", "completed", "failed"].forEach((eventName) => {
      source.addEventListener(eventName, async (rawEvent) => {
        const payload = JSON.parse(rawEvent.data) as ReviewTaskSseEvent;
        setEvents((current) => [...current, payload]);
        if (payload.event === "completed" || payload.event === "failed") {
          const latestTask = await fetchReviewTask(taskId).catch(() => null);
          if (latestTask) setTask(latestTask);
          if (payload.event === "completed") {
            const latestResult = await fetchReviewTaskResult(taskId).catch(() => null);
            if (latestResult) setResult(latestResult);
          }
          source.close();
        }
      });
    });
  }

  async function handleCreateTask() {
    setSubmitting(true);
    setError(null);
    setFeedbackMessage(null);
    setEvents([]);
    setResult(null);
    try {
      const created = await createReviewTask(requestPayload);
      const latestTask = await fetchReviewTask(created.task_id);
      setTask(latestTask);
      subscribe(created.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建审查任务失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFeedback(feedbackType: ReviewFeedbackType) {
    if (!result) return;
    setFeedbackMessage(null);
    try {
      const response = await submitReviewReportFeedback(result.report_id, {
        feedback_type: feedbackType,
        source: "review-acceptance-page",
      });
      setFeedbackMessage(`反馈已记录：${response.feedback_id}`);
    } catch (err) {
      setFeedbackMessage(err instanceof Error ? err.message : "反馈提交失败");
    }
  }

  return (
    <main className="page-shell stack-xl">
      <section className="hero-card stack-md">
        <p className="eyebrow">审查 Agent 前后端冻结验收</p>
        <h1 className="page-title">最小前端验收闭环</h1>
        <p className="muted">该页面用于冻结契约验收，验证上传、任务创建、实时进度、结果回看与反馈闭环。</p>
      </section>

      <section className="glass-panel stack-lg">
        <h2>1. 文件上传</h2>
        <div className="form-grid review-profile-grid">
          <label className="field">
            <span>目标审查文件</span>
            <input type="file" accept=".docx,.pdf,.md,.txt" disabled={uploading === "target"} onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload("target", file);
              event.currentTarget.value = "";
            }} />
            <small>{targetFile ? `${targetFile.file_name} (${targetFile.file_id})` : "尚未上传"}</small>
          </label>
          <label className="field">
            <span>审查依据文件</span>
            <input type="file" accept=".docx,.pdf,.md,.txt" disabled={uploading === "basis"} onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload("basis", file);
              event.currentTarget.value = "";
            }} />
            <small>{basisFiles.length ? basisFiles.map((item) => item.file_name).join("、") : "可选"}</small>
          </label>
          <label className="field">
            <span>上下文资料</span>
            <input type="file" accept=".docx,.pdf,.md,.txt" disabled={uploading === "context"} onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload("context", file);
              event.currentTarget.value = "";
            }} />
            <small>{contextFiles.length ? contextFiles.map((item) => item.file_name).join("、") : "可选"}</small>
          </label>
        </div>
      </section>

      <section className="glass-panel stack-lg">
        <h2>2. 冻结后的任务参数</h2>
        <div className="form-grid review-profile-grid">
          <label className="field"><span>L1</span><input value={l1} onChange={(e) => setL1(e.target.value)} /></label>
          <label className="field"><span>L2</span>
            <select value={l2} onChange={(e) => setL2(e.target.value)}>
              {documentOptions.length ? documentOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>) : <option value="distribution_network_special_scheme">配网工程专项方案</option>}
            </select>
          </label>
          <label className="field"><span>L3（每行一个）</span><textarea rows={3} value={l3} onChange={(e) => setL3(e.target.value)} /></label>
          <label className="field"><span>standard_ids</span><textarea rows={2} value={standardIds} onChange={(e) => setStandardIds(e.target.value)} /></label>
          <label className="field"><span>template_ids</span><textarea rows={2} value={templateIds} onChange={(e) => setTemplateIds(e.target.value)} /></label>
          <label className="field"><span>rule_pack_ids</span><textarea rows={2} value={rulePackIds} onChange={(e) => setRulePackIds(e.target.value)} /></label>
        </div>

        <div className="stack-md">
          <div>
            <strong>启用模块</strong>
            <div className="task-type-toggle" role="group" aria-label="enabled-modules">
              {MODULE_OPTIONS.map((module) => (
                <button
                  key={module.value}
                  type="button"
                  className={`task-type-chip ${enabledModules.includes(module.value) ? "is-active" : ""}`}
                  onClick={() => setEnabledModules((current) => current.includes(module.value) ? current.filter((item) => item !== module.value) : [...current, module.value])}
                >
                  {module.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <strong>关闭模块</strong>
            <div className="task-type-toggle" role="group" aria-label="disabled-modules">
              {MODULE_OPTIONS.map((module) => (
                <button
                  key={module.value}
                  type="button"
                  className={`task-type-chip ${disabledModules.includes(module.value) ? "is-active" : ""}`}
                  onClick={() => setDisabledModules((current) => current.includes(module.value) ? current.filter((item) => item !== module.value) : [...current, module.value])}
                >
                  {module.label}
                </button>
              ))}
            </div>
          </div>
          <label className="field">
            <span>自定义规则（每行一条）</span>
            <textarea rows={4} value={focusRequirements} onChange={(e) => setFocusRequirements(e.target.value)} />
          </label>
        </div>

        <div className="stack-sm">
          <button className="ghost-button" type="button" onClick={() => void handleCreateTask()} disabled={submitting || !targetFile}>
            {submitting ? "正在创建任务…" : "创建冻结契约任务"}
          </button>
          {error ? <div className="callout warning-callout">{error}</div> : null}
        </div>
      </section>

      <section className="glass-panel stack-lg">
        <h2>3. 请求体预览</h2>
        <pre className="code-block">{prettyJson(requestPayload)}</pre>
      </section>

      <section className="glass-panel stack-lg">
        <h2>4. 任务状态与实时事件</h2>
        {task ? <pre className="code-block">{prettyJson(task)}</pre> : <p className="muted">尚未创建任务</p>}
        <div className="stack-sm">
          <h3>实时事件时间线</h3>
          {events.length ? events.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className="callout">
              <strong>{event.event}</strong> · {event.stage} · {event.status}
              <div className="muted small">{event.message}</div>
              {event.artifact ? <div className="muted small">工件：{event.artifact.file_name}</div> : null}
            </div>
          )) : <p className="muted">尚未收到 实时 事件</p>}
        </div>
      </section>

      <section className="glass-panel stack-lg">
        <h2>5. 最终结果</h2>
        {result ? (
          <>
            <div className="callout">
              <strong>{result.summary.overall_conclusion}</strong>
              <div className="muted small">风险等级：{riskLabel(result.summary.risk_level)} · 报告编号：{result.report_id}</div>
            </div>
            <div className="form-grid review-profile-grid">
              {Object.entries(result.modules).map(([key, module]) => (
                <div key={key} className="glass-panel stack-sm">
                  <strong>{module.title}</strong>
                  <div className="muted small">状态：{moduleStatusLabel(module.status)}</div>
                  <div className="muted small">发现项：{module.findings.length}</div>
                  <pre className="code-block">{prettyJson(module.severity_summary)}</pre>
                </div>
              ))}
            </div>
            <div className="stack-sm">
              <h3>导出文件</h3>
              <ul>
                {result.export_links.pdf ? <li><a href={resolveApiUrl(result.export_links.pdf)} target="_blank">正式排版 PDF</a></li> : <li className="muted small">正式 PDF 尚未生成</li>}
              </ul>
            </div>
            <div className="stack-sm">
              <h3>轻反馈</h3>
              <div className="task-type-toggle">
                {[
                  ["helpful", "有帮助"],
                  ["inaccurate", "不准确"],
                  ["missing", "有遗漏"],
                  ["save_as_template", "存为模板"],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className="task-type-chip"
                    onClick={() => void handleFeedback(value as ReviewFeedbackType)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {feedbackMessage ? <p className="muted small">{feedbackMessage}</p> : null}
            </div>
            <details>
              <summary>原始 JSON（开发视图）</summary>
              <pre className="code-block">{prettyJson(result)}</pre>
            </details>
          </>
        ) : (
          <p className="muted">任务完成后会在这里展示冻结后的最终结果契约。</p>
        )}
      </section>
    </main>
  );
}
