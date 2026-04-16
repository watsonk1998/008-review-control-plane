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
const STAGE_LABELS: Record<string, string> = {
  planning: "资料接收中",
  dispatch: "文档解析中",
  parse: "文档解析中",
  extract: "依据与规则映射中",
  rules: "结构化审查中",
  evidence: "结构化审查中",
  agent_select: "专项子审查并行运行中",
  agent_running: "专项子审查并行运行中",
  agent_done: "专项子审查并行运行中",
  hermes_controller: "主审综合裁决中",
  report: "报告生成中",
  finalize: "已完成",
};

// Stage-based progress provides a FLOOR guarantee only.
// Values are deliberately low — the time-based simulation is the primary driver.
// This prevents the progress bar from jumping to 60%+ as soon as the first
// agent_running event arrives.
function estimateStageFloor({
  totalAgents,
  completedAgents,
  stage,
  status,
}: {
  totalAgents: number;
  completedAgents: number;
  stage?: string;
  status?: string;
}) {
  const normalizedStatus = (status || "").trim().toLowerCase();
  if (["succeeded", "accepted"].includes(normalizedStatus)) return 100;
  if (["failed", "partial", "rejected", "needs_attachment"].includes(normalizedStatus)) return 96;
  if (stage === "finalize") return 95;
  if (stage === "report") return 88;
  if (stage === "hermes_controller") return 80;
  if (["agent_select", "agent_running", "agent_done"].includes(stage || "")) {
    if (!totalAgents) return 25;
    // Scale 25-75% based on agent completion ratio
    return Math.max(25, Math.min(75, Math.round(25 + (Math.min(completedAgents, totalAgents) / totalAgents) * 50)));
  }
  if (stage === "rules" || stage === "evidence") return 18;
  if (stage === "extract") return 12;
  if (stage === "dispatch" || stage === "parse") return 6;
  if (stage === "planning") return 3;
  return 0;
}

// Primary progress driver: 1% every 6 seconds, capped at 90%.
function estimateSimulatedProgress(elapsedSeconds: number) {
  return Math.min(90, Math.max(0, Math.floor(elapsedSeconds / 6)));
}

function formatElapsed(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  if (hours > 0) return `${hours}时${String(minutes).padStart(2, "0")}分${String(secs).padStart(2, "0")}秒`;
  return `${minutes}分${String(secs).padStart(2, "0")}秒`;
}

function isStructuredReviewResult(result: unknown): result is StructuredReviewResult {
  return Boolean(
    result &&
      typeof result === "object" &&
      ("hermesController" in result || "support_result_008" in result || "summary" in result)
  );
}

function manualReviewReasonLabel(value: string | null | undefined) {
  switch (value) {
    case "parser_limited_pdf_requires_manual_review":
      return "PDF 当前仅完成基础文本识别，需结合原件人工复核";
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
      return "关键章节或附件边界标题重复，章节定位结果不稳定";
    case "manual_confirmation_required":
      return "需要人工确认";
    default:
      return value || "—";
  }
}

function renderReportText(text: string) {
  let html = text.trim();
  
  // Replace inline markdown: **text** -> <strong>text</strong>
  html = html.replace(/(\*\*)(.*?)\1/g, '<strong>$2</strong>');
  // Replace inline markdown: `text` -> <code>text</code>
  html = html.replace(/(`)(.*?)\1/g, '<code>$2</code>');

  return <span dangerouslySetInnerHTML={{ __html: html }} />;
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
        if (line.startsWith("> ")) {
          return <blockquote className="report-blockquote" key={key} style={{ borderLeft: '4px solid #CBD5E1', paddingLeft: '16px', color: '#475569', fontStyle: 'italic', margin: '8px 0', background: '#F8FAFC', padding: '12px 16px', borderRadius: '4px' }}>{renderReportText(line.slice(2))}</blockquote>;
        }
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
  const [now, setNow] = useState(() => Date.now());
  const [progressViewStartedAt, setProgressViewStartedAt] = useState(() => Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const pollingFailureCountRef = useRef(0);
  const progressTaskIdRef = useRef<string | null>(null);
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
      if (progressTaskIdRef.current !== taskData.id) {
        progressTaskIdRef.current = taskData.id;
        setProgressViewStartedAt(Date.now());
      }
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

  useEffect(() => {
    if (!task || TERMINAL_STATES.has((task.status || "").trim().toLowerCase())) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [task]);

  const structuredResult = useMemo(() => {
    if (!task?.result || !isStructuredReviewResult(task.result)) return null;
    return task.result;
  }, [task]);

  const structuredArtifacts = useMemo(() => {
    if (!structuredResult) return [];
    return Array.isArray(structuredResult?.artifactIndex) ? structuredResult?.artifactIndex : artifacts;
  }, [artifacts, structuredResult]);

  const canonicalStructuredReportMarkdown = useMemo(() => {
    if (!structuredResult) return "";
    return structuredResult?.finalReportMarkdown || structuredResult?.finalReportPacket?.report_markdown || structuredResult?.reportMarkdown || structuredResult?.hermesController?.finalAnswer || "";
  }, [structuredResult]);

  const reportArtifact = useMemo(
    () =>
      structuredArtifacts.find((artifact) => artifact.artifactRole === "formal_final_report") ||
      structuredArtifacts.find((artifact) => artifact.primary && artifact.fileName.toLowerCase().endsWith(".pdf")) ||
      structuredArtifacts.find((artifact) => artifact.fileName === "hermes-controller-final-report.pdf") ||
      structuredArtifacts.find((artifact) => artifact.fileName.toLowerCase().endsWith(".pdf")) ||
      structuredArtifacts.find((artifact) => artifact.name === "hermes-controller-final-report") ||
      structuredArtifacts.find((artifact) => artifact.name === "structured-review-report"),
    [structuredArtifacts],
  );

  const progressSummary = useMemo(() => {
    const latestEvent = events[events.length - 1];
    const completedAgentEvents = events.filter((event) => event.stage === "agent_done");
    const debugTotalAgents = latestEvent?.debug?.totalAgents;
    const debugCompletedAgents = latestEvent?.debug?.completedAgents;
    const totalAgents = typeof debugTotalAgents === "number"
      ? debugTotalAgents
      : structuredResult?.hermesController?.selectedAgents?.length || 0;
    const completedAgents = typeof debugCompletedAgents === "number"
      ? debugCompletedAgents
      : completedAgentEvents.length;
    const stage = latestEvent?.stage || "";
    // Use the task's actual creation time as the elapsed baseline so that
    // navigating to a task that has been running for several minutes does NOT
    // reset the simulated progress back to 0%.
    const taskStartMs = task?.createdAt ? new Date(task.createdAt).getTime() : progressViewStartedAt;
    const elapsedSeconds = TERMINAL_STATES.has((task?.status || "").trim().toLowerCase())
      ? 0
      : Math.max(0, Math.floor((now - taskStartMs) / 1000));
    const stageFloor = estimateStageFloor({
      totalAgents,
      completedAgents,
      stage,
      status: task?.status,
    });
    const simulatedPercent = estimateSimulatedProgress(elapsedSeconds);
    // Time-based simulation is the PRIMARY driver (smooth ramp-up).
    // Stage signals only provide a FLOOR — they guarantee the bar never
    // drops below a sensible minimum for the current pipeline stage,
    // but do NOT jump ahead of the time-based ramp.
    const effectivePercent = TERMINAL_STATES.has((task?.status || "").trim().toLowerCase())
      ? 100
      : Math.max(simulatedPercent, stageFloor);
    return {
      latestEvent,
      currentStage: STAGE_LABELS[stage] || "审查执行中",
      totalAgents,
      completedAgents,
      simulatedPercent,
      stageFloor,
      progressPercent: effectivePercent,
    };
  }, [events, structuredResult, task?.status, task?.createdAt, now, progressViewStartedAt]);

  const reviewElapsedSeconds = useMemo(() => {
    if (!task) return 0;
    const startAt = events[0]?.timestamp || task.createdAt;
    const endAt = TERMINAL_STATES.has((task.status || "").trim().toLowerCase()) ? task.updatedAt : new Date(now).toISOString();
    const startTime = new Date(startAt).getTime();
    const endTime = new Date(endAt).getTime();
    if (Number.isNaN(startTime) || Number.isNaN(endTime)) return 0;
    return Math.max(0, Math.floor((endTime - startTime) / 1000));
  }, [events, now, task]);

  return (
    <main className="home-dashboard stack-lg" style={{ maxWidth: "1040px", margin: "0 auto", padding: "40px 0 64px" }}>
      <header className="hero-simple" style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#172033", marginBottom: "8px" }}>任务详情</h1>
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
          <section className="glass-panel" style={{ background: "#FFFFFF", padding: "32px", borderRadius: "24px", border: "1px solid #ECE7DF", boxShadow: "0 18px 40px rgba(15,23,42,0.05)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
              <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                <span style={{ fontSize: "1.1rem", fontWeight: 600 }}>当前审查状态</span>
                <span
                  className={`status-pill ${
                    task.status === "succeeded" || (task.status as string) === "accepted"
                      ? "is-healthy"
                      : task.status === "failed" || (task.status as string) === "rejected"
                        ? "is-unhealthy"
                        : task.status === "partial" || (task.status as string) === "needs_attachment"
                          ? "is-warning"
                          : "is-neutral"
                  }`}
                  style={{ fontSize: "1rem", padding: "6px 16px" }}
                >
                  {TASK_STATUS_MAP[(task.status || "").trim().toLowerCase()] || task.status}
                </span>
              </div>
              <div style={{ color: "#64748B", fontSize: "0.9rem" }}>
                创建时间：{new Date(task.createdAt).toLocaleString()}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "20px", padding: "18px 20px", borderRadius: "20px", background: "#F8F5EF", border: "1px solid #ECE7DF" }}>
              {TERMINAL_STATES.has((task.status || "").trim().toLowerCase()) ? (
                <span style={{ width: "26px", height: "26px", borderRadius: "999px", background: "#172033", opacity: 0.12, display: "inline-block", flexShrink: 0 }} />
              ) : (
                <div className="spinner" style={{ width: "26px", height: "26px", borderWidth: "3px", borderColor: "rgba(23, 32, 51, 0.14)", borderTopColor: "#172033", flexShrink: 0 }} />
              )}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: "#172033", marginBottom: "4px" }}>
                  {["succeeded", "accepted"].includes((task.status || "").trim().toLowerCase())
                    ? "审查已完成"
                    : TERMINAL_STATES.has((task.status || "").trim().toLowerCase())
                      ? "审查流程已结束"
                      : "系统正在持续审查中，请稍候"}
                </div>
                <div style={{ color: "#6B7280", fontSize: "0.92rem" }}>审查时间：{formatElapsed(reviewElapsedSeconds)}</div>
              </div>
            </div>

            <div style={{ marginBottom: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "0.88rem", color: "#7A7A7A" }}>
                <span>审查进度</span>
                <span>{progressSummary.progressPercent}%</span>
              </div>
              <div style={{ width: "100%", height: "10px", background: "#F1ECE4", borderRadius: "999px", overflow: "hidden" }}>
                <div style={{ width: `${progressSummary.progressPercent}%`, height: "100%", background: "linear-gradient(90deg, #172033 0%, #43506A 100%)", borderRadius: "999px", transition: "width 0.3s ease" }} />
              </div>
            </div>

            {/* 人工复核需求 — 已按合同冻结要求从首屏移除，数据仍在正式报告中体现 */}
            {/* 预检/降级说明 — 已按合同冻结要求从首屏移除，详情见正式报告 */}

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
                      导出正式排版 PDF
                    </a>
                  ) : null}
                </div>
              </div>
            ) : null}
            
            {/* 正式报告直出 — 不再使用折叠交互 */}
            {structuredResult && task.status === "succeeded" && (
                <div style={{ marginTop: "32px" }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "16px", color: "#172033" }}>正式审查报告</h3>
                  {structuredResult?.reportHtml ? (
                    <StructuredReportHtml
                      htmlContent={structuredResult?.reportHtml}
                      printCss={structuredResult?.reportPrintCss}
                    />
                  ) : (
                    <StructuredReportMarkdown markdown={canonicalStructuredReportMarkdown} />
                  )}
                </div>
            )}
          </section>

        </div>
      ) : null}
    </main>
  );
}
