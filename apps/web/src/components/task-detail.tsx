"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  fetchTask,
  fetchTaskArtifacts,
  fetchTaskEvents,
  getTaskStreamUrl,
  resolveApiUrl,
} from "@/lib/api";
import type {
  StructuredReviewResult,
  TaskArtifact,
  TaskEvent,
  TaskRecord,
} from "@/types/control-plane";

const TASK_STATUS_MAP: Record<string, string> = {
  pending: "排队中",
  running: "执行中",
  succeeded: "执行成功",
  failed: "执行失败",
  partial: "部分成功",
  accepted: "验收通过",
  rejected: "安全驳回",
  needs_attachment: "需补充附件"
};

const TERMINAL_STATES = new Set(["succeeded", "failed", "partial", "accepted", "rejected", "needs_attachment"]);
const STREAM_RECONNECT_DELAY_MS = 4_000;

function isStructuredReviewResult(result: unknown): result is StructuredReviewResult {
  return Boolean(
    result &&
      typeof result === "object" &&
      "summary" in result &&
      "issues" in result &&
      "matrices" in result &&
      "resolvedProfile" in result,
  );
}

function manualReviewReasonLabel(value: string | null | undefined) {
  switch (value) {
    case "parser_limited_pdf_requires_manual_review":
      return "PDF 当前仅 text-only 可视域，需按 parser-limited 路径人工复核";
    case "explicit_missing_marker":
      return "附件被正文显式标记为缺失/后补";
    case "title_detected_but_body_not_reliably_parsed":
      return "检测到附件标题，但当前解析能力不足以确认正文";
    case "title_detected_without_attachment_body":
      return "检测到附件标题，但未见附件正文";
    case "reference_detected_in_limited_parser":
      return "仅检测到附件引用，且当前解析路径受限";
    case "reference_detected_without_attachment_body":
      return "仅检测到附件引用，未见附件正文";
    case "visibility_gap":
      return "存在可视域缺口";
    case "attachment_unparsed":
      return "附件未解析";
    case "referenced_only":
      return "仅检测到引用";
    case "visibility_unknown":
      return "当前可视域无法确定";
    case "weak_section_structure_signal":
      return "关键章节或附件边界标题重复，canonical section extraction 不稳定";
    case "manual_confirmation_required":
      return "需要人工确认";
    default:
      return value || "—";
  }
}

function splitLabelValue(text: string) {
  const index = text.indexOf("：");
  if (index <= 0 || index > 18) return null;
  return {
    label: text.slice(0, index + 1),
    value: text.slice(index + 1),
  };
}

function renderReportText(text: string) {
  const parts = splitLabelValue(text.trim());
  if (!parts) return text.trim();
  return (
    <>
      <strong>{parts.label}</strong>
      {parts.value}
    </>
  );
}

function StructuredReportMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.split(/\r?\n/);
  return (
    <div className="report-document">
      {lines.map((line, index) => {
        const key = `${index}-${line}`;
        if (!line.trim()) return <div className="report-spacer" key={key} />;
        if (line.startsWith("# ")) return <h3 className="report-title" key={key}>{line.slice(2).trim()}</h3>;
        if (line.startsWith("## ")) return <h4 className="report-section-title" key={key}>{line.slice(3).trim()}</h4>;
        if (line.startsWith("### ")) return <h5 className="report-subsection-title" key={key}>{line.slice(4).trim()}</h5>;
        if (line.startsWith("  - ")) {
          return <div className="report-item report-item-nested" key={key}>{renderReportText(line.slice(4))}</div>;
        }
        if (line.startsWith("- ")) {
          return <div className="report-item" key={key}>{renderReportText(line.slice(2))}</div>;
        }
        return <p className="report-paragraph" key={key}>{renderReportText(line)}</p>;
      })}
    </div>
  );
}

function StructuredReportHtml({ htmlContent, printCss }: { htmlContent: string; printCss?: string }) {
  return (
    <div className="structured-report-host">
      {printCss ? <style>{printCss}</style> : null}
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
    </div>
  );
}

export function TaskDetail({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskRecord | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [artifacts, setArtifacts] = useState<TaskArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transportMode, setTransportMode] = useState<"connecting" | "sse" | "polling">("connecting");

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const pollingFailureCountRef = useRef(0);
  const transportModeRef = useRef<"connecting" | "sse" | "polling">("connecting");
  const reconnectStreamRef = useRef<() => void>(() => {});
  const mountedRef = useRef(false);

  useEffect(() => {
    transportModeRef.current = transportMode;
  }, [transportMode]);

  const clearPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      window.clearTimeout(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  }, []);

  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closeStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const applyTaskState = useCallback(
    ({
      taskData,
      eventData,
      artifactData,
    }: {
      taskData: TaskRecord;
      eventData: TaskEvent[];
      artifactData: TaskArtifact[];
    }) => {
      setTask(taskData);
      setEvents(eventData);
      setArtifacts(artifactData);
      setError(null);
      setLoading(false);
    },
    [],
  );

  const loadTaskSnapshot = useCallback(
    async () => {
      try {
        const [taskData, eventData] = await Promise.all([fetchTask(taskId), fetchTaskEvents(taskId)]);
        const artifactData =
          taskData.taskType === "structured_review"
            ? await fetchTaskArtifacts(taskId).catch(() => [])
            : [];
        if (!mountedRef.current) {
          return { done: true, ok: true };
        }
        applyTaskState({ taskData, eventData, artifactData });
        return { done: TERMINAL_STATES.has(taskData.status), ok: true };
      } catch (err) {
        if (!mountedRef.current) {
          return { done: true, ok: false };
        }
        setError(err instanceof Error ? err.message : "任务详情加载失败");
        setLoading(false);
        return { done: false, ok: false };
      }
    },
    [applyTaskState, taskId],
  );

  const startPolling = useCallback(() => {
    clearPolling();

    async function poll() {
      if (!mountedRef.current || transportModeRef.current !== "polling") {
        return;
      }

      const result = await loadTaskSnapshot();
      if (result.ok) {
        pollingFailureCountRef.current = 0;
      } else {
        pollingFailureCountRef.current += 1;
      }

      const nextDelay = Math.min(3_000 + pollingFailureCountRef.current * 2_000, 10_000);
      if (mountedRef.current && transportModeRef.current === "polling" && !result.done) {
        pollingTimerRef.current = window.setTimeout(poll, nextDelay);
      }
    }

    void poll();
  }, [clearPolling, loadTaskSnapshot]);

  const connectStream = useCallback(() => {
    clearReconnect();
    closeStream();

    const source = new EventSource(getTaskStreamUrl(taskId));
    eventSourceRef.current = source;
    transportModeRef.current = "connecting";
    setTransportMode("connecting");

    source.onopen = () => {
      if (!mountedRef.current) return;
      clearPolling();
      pollingFailureCountRef.current = 0;
      transportModeRef.current = "sse";
      setTransportMode("sse");
    };

    source.addEventListener("snapshot", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as {
        task: TaskRecord | null;
        events: TaskEvent[];
        artifacts: TaskArtifact[];
      };
      if (!payload.task) return;
      applyTaskState({
        taskData: payload.task,
        eventData: payload.events || [],
        artifactData: payload.artifacts || [],
      });
    });

    source.addEventListener("task", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskRecord;
      setTask(payload);
      setError(null);
      setLoading(false);
    });

    source.addEventListener("event", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskEvent;
      setEvents((current) => [...current, payload]);
    });

    source.addEventListener("artifacts", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskArtifact[];
      setArtifacts(payload);
    });

    source.onerror = () => {
      if (!mountedRef.current) return;
      closeStream();
      transportModeRef.current = "polling";
      setTransportMode("polling");
      startPolling();
      reconnectTimerRef.current = window.setTimeout(() => {
        if (!mountedRef.current) return;
        reconnectStreamRef.current();
      }, STREAM_RECONNECT_DELAY_MS);
    };
  }, [applyTaskState, clearPolling, clearReconnect, closeStream, startPolling, taskId]);

  useEffect(() => {
    reconnectStreamRef.current = connectStream;
  }, [connectStream]);

  useEffect(() => {
    mountedRef.current = true;
    const initialSync = window.setTimeout(() => {
      void loadTaskSnapshot();
      connectStream();
    }, 0);

    return () => {
      mountedRef.current = false;
      window.clearTimeout(initialSync);
      clearPolling();
      clearReconnect();
      closeStream();
    };
  }, [clearPolling, clearReconnect, closeStream, connectStream, loadTaskSnapshot]);

  const structuredResult = useMemo(() => {
    if (!task?.result || !isStructuredReviewResult(task.result)) return null;
    return task.result;
  }, [task]);

  const structuredArtifacts = useMemo(() => {
    if (!structuredResult) return [];
    return Array.isArray(structuredResult.artifactIndex) ? structuredResult.artifactIndex : artifacts;
  }, [artifacts, structuredResult]);

  const canonicalStructuredReportMarkdown = useMemo(() => {
    if (!structuredResult) return "";
    return structuredResult.finalReportMarkdown || structuredResult.finalReportPacket?.report_markdown || structuredResult.reportMarkdown || "";
  }, [structuredResult]);

  const reportArtifact = useMemo(
    () => structuredArtifacts.find((artifact) => artifact.name === "structured-review-report"),
    [structuredArtifacts],
  );

  return (
    <main className="home-dashboard stack-lg" style={{ maxWidth: "900px", margin: "0 auto", padding: "40px 0" }}>
      <header className="hero-simple" style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--foreground)", marginBottom: "8px" }}>任务详情</h1>
        <p style={{ fontSize: "0.95rem", color: "var(--muted)" }}>任务编号: {taskId}</p>
        <Link className="secondary-button" style={{ marginTop: "16px", display: "inline-flex" }} href="/">
          返回首页
        </Link>
      </header>

      {loading ? (
        <div className="card" style={{ padding: "32px", textAlign: "center", color: "var(--muted)" }}>
          <div className="spinner" style={{ margin: "0 auto 16px auto", borderColor: "rgba(15, 23, 42, 0.1)", borderTopColor: "#0F172A" }} />
          <p>正在加载任务状态…</p>
        </div>
      ) : null}
      
      {error ? (
        <div className="card" style={{ padding: "24px", color: "#B91C1C", background: "#FEF2F2", border: "1px solid #FCA5A5" }}>
          <p>{error}</p>
        </div>
      ) : null}

      {task && !loading && !error ? (
        <div className="stack-lg">
          {/* 状态总览卡片 */}
          <section className="glass-panel" style={{ background: "#FFFFFF", padding: "32px", borderRadius: "12px", border: "1px solid #E2E8F0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
              <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                <span style={{ fontSize: "1.1rem", fontWeight: 600 }}>当前审查状态</span>
                <span
                  className={`status-pill ${
                    task.status === "succeeded" || task.status === "accepted"
                      ? "is-healthy"
                      : task.status === "failed" || task.status === "rejected"
                        ? "is-unhealthy"
                        : task.status === "partial" || task.status === "needs_attachment"
                          ? "is-warning"
                          : "is-neutral"
                  }`}
                  style={{ fontSize: "1rem", padding: "6px 16px" }}
                >
                  {TASK_STATUS_MAP[(task.status || "").trim().toLowerCase()] || task.status.toUpperCase()}
                </span>
              </div>
              <div style={{ color: "#64748B", fontSize: "0.9rem" }}>
                创建时间: {new Date(task.createdAt).toLocaleString()}
              </div>
            </div>

            {/* 人工复核需求 */}
            {structuredResult && structuredResult.summary.manualReviewNeeded ? (
              <div className="callout warning-callout" style={{ marginTop: "16px" }}>
                <strong>需要人工复核</strong>
                <p>审查发现存在需要人工确认的阻断项或可视域缺口。请在下方正式报告中查看详情。</p>
              </div>
            ) : null}

            {/* 预检/降级说明 */}
            {structuredResult?.visibility?.parserLimited || structuredResult?.visibility?.manualReviewReason ? (
              <div className="callout warning-callout" style={{ marginTop: "16px" }}>
                <strong>预检与文档解析说明</strong>
                <p>
                  {structuredResult.visibility.parserLimited
                    ? "当前文档部分内容受限于解析引擎，部分结果按保守口径处理。"
                    : "系统预检提示文档完整性存在潜在问题。"}
                </p>
                {structuredResult.visibility.manualReviewReason ? (
                  <p>系统降级指引: {manualReviewReasonLabel(structuredResult.visibility.manualReviewReason)}</p>
                ) : null}
              </div>
            ) : null}

            {/* 正式报告入口 */}
            {structuredResult && task.status === "succeeded" ? (
              <div style={{ marginTop: "32px", paddingTop: "24px", borderTop: "1px solid #F1F5F9" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "16px" }}>审查结果</h3>
                <div style={{ background: "#F8FAFC", padding: "20px", borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h4 style={{ fontWeight: 600, color: "#0F172A", marginBottom: "4px" }}>正式审查报告已生成</h4>
                    <p style={{ fontSize: "0.9rem", color: "#64748B" }}>包含基础评估、合规性、完整性及正式整改建议</p>
                  </div>
                  {reportArtifact ? (
                    <a className="primary-button" href={resolveApiUrl(reportArtifact.downloadUrl)} rel="noreferrer" target="_blank" style={{ textDecoration: "none" }}>
                      下载完整报告(PDF/MD)
                    </a>
                  ) : null}
                </div>
              </div>
            ) : null}
            
            {/* 假如渲染在网页里的精简报告 */}
            {structuredResult && task.status === "succeeded" && (
                <div style={{ marginTop: "32px" }}>
                  <details className="card expert-report-card">
                  <summary style={{ fontWeight: 600, padding: "16px", cursor: "pointer", background: "#F1F5F9", borderRadius: "8px" }}>网页版报告在线预览</summary>
                  <div style={{ padding: "24px" }}>
                  {structuredResult.reportHtml ? (
                    <StructuredReportHtml
                      htmlContent={structuredResult.reportHtml}
                      printCss={structuredResult.reportPrintCss}
                    />
                  ) : (
                    <StructuredReportMarkdown markdown={canonicalStructuredReportMarkdown} />
                  )}
                  </div>
                  </details>
                </div>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
