"use client";

import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import { ReviewDecisionPanel } from "@/components/review-decision-panel";
import {
  fetchTask,
  fetchTaskArtifacts,
  fetchTaskEvents,
  getTaskStreamUrl,
  resolveApiUrl,
} from "@/lib/api";
import type {
  AttachmentVisibilityMatrixItem,
  ConflictMatrix,
  EvidenceSpan,
  ReviewIssue,
  RuleHitMatrixRow,
  SectionStructureMatrixItem,
  StructuredReviewResult,
  TaskArtifact,
  TaskEvent,
  TaskRecord,
} from "@/types/control-plane";

const TERMINAL_STATES = new Set(["succeeded", "failed", "partial"]);
const REVIEW_LAYERS = ["L1", "L2", "L3"] as const;
const STREAM_RECONNECT_DELAY_MS = 4_000;

function renderJson(data: unknown) {
  return JSON.stringify(data, null, 2);
}

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

function severityTone(severity: string) {
  if (severity === "high") return "is-unhealthy";
  if (severity === "medium") return "is-warning";
  return "is-healthy";
}

function streamTone(mode: "connecting" | "sse" | "polling") {
  if (mode === "sse") return "is-healthy";
  if (mode === "polling") return "is-warning";
  return "is-neutral";
}

function eventKey(event: TaskEvent) {
  return [
    event.timestamp,
    event.stage,
    event.capability,
    event.status,
    event.message,
    event.artifactPath || "",
  ].join("::");
}

function renderEvidenceList(title: string, evidence: EvidenceSpan[]) {
  if (!evidence.length) {
    return <p className="muted small">{title}：暂无</p>;
  }
  return (
    <div className="stack-sm">
      <strong>{title}</strong>
      <ul className="source-list">
        {evidence.slice(0, 3).map((item, index) => (
          <li key={`${item.sourceId}-${index}`}>
            <strong>{item.sourceType}</strong>
            <p className="muted small">{item.sourceId}</p>
            <p>{item.excerpt}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function findingTone(findingType: string) {
  if (findingType === "hard_evidence") return "is-unhealthy";
  if (findingType === "visibility_gap") return "is-warning";
  return "is-neutral";
}

function issueKindTone(issueKind: string) {
  if (issueKind === "hard_defect") return "is-unhealthy";
  if (issueKind === "visibility_gap" || issueKind === "evidence_gap") return "is-warning";
  return "is-neutral";
}

function ArtifactList({ artifacts }: { artifacts: TaskArtifact[] }) {
  if (!artifacts.length) {
    return <p className="muted">暂无工件。</p>;
  }
  return (
    <div className="artifact-list">
      {artifacts.map((artifact) => (
        <a
          className="ghost-button"
          href={resolveApiUrl(artifact.downloadUrl)}
          key={artifact.fileName}
          rel="noreferrer"
          target="_blank"
        >
          {artifact.fileName}
          {artifact.category ? ` · ${artifact.category}` : ""}
        </a>
      ))}
    </div>
  );
}

function humanizeToken(value: string) {
  const withSpaces = value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim();
  return withSpaces ? withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1) : value;
}

function parseModeLabel(value: string | null | undefined) {
  switch (value) {
    case "docx_structured":
      return "DOCX structured";
    case "pdf_text_only":
      return "PDF text only";
    case "markdown_text":
      return "Markdown text";
    case "plain_text":
      return "Plain text";
    default:
      return "unknown";
  }
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
    case "manual_confirmation_required":
      return "需要人工确认";
    default:
      return value || "—";
  }
}

function preflightGateLabel(value: string | null | undefined) {
  switch (value) {
    case "manual_review_required":
      return "manual_review_required（需先进入人工复核）";
    case "ready":
      return "ready（未触发前置阻断）";
    default:
      return value || "—";
  }
}

function reviewerTaskStateLabel(value: string) {
  switch (value) {
    case "accepted":
      return "accepted（已完成复核）";
    case "rejected":
      return "rejected（确认存在阻断问题）";
    case "needs_attachment":
      return "needs supplement（需补件/补充材料）";
    default:
      return "pending（待处理）";
  }
}

function renderScalar(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value)) return value.length ? value.map((item) => renderScalar(item)).join("，") : "—";
  if (typeof value === "object") return renderJson(value);
  return String(value);
}

function CompactJsonDetails({ summary, data }: { summary: string; data: unknown }) {
  return (
    <details>
      <summary>{summary}</summary>
      <pre className="code-block compact">{renderJson(data)}</pre>
    </details>
  );
}

function ReviewKeyValueList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  if (!items.length) {
    return <p className="muted">无</p>;
  }
  return (
    <dl className="review-kv-list">
      {items.map((item, index) => (
        <div className="review-kv-row" key={`${item.label}-${index}`}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ReviewTokenList({ items, emptyLabel = "无" }: { items: string[]; emptyLabel?: string }) {
  if (!items.length) {
    return <p className="muted">{emptyLabel}</p>;
  }
  return (
    <div className="review-token-list">
      {items.map((item, index) => (
        <span className="status-pill is-neutral" key={`${item}-${index}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function VisibilitySummaryPanel({ visibility }: { visibility: StructuredReviewResult["visibility"] }) {
  const countItems = Object.entries(visibility.counts || {}).map(([key, value]) => ({
    label: humanizeToken(key),
    value: String(value),
  }));
  const reasonItems = Object.entries(visibility.reasonCounts || {}).map(([key, value]) => ({
    label: key,
    value: String(value),
  }));

  return (
    <div className="stack-md">
      <ReviewKeyValueList
        items={[
          { label: "parseMode", value: parseModeLabel(visibility.parseMode) },
          { label: "parserLimited", value: visibility.parserLimited ? "true" : "false" },
          { label: "fileType", value: visibility.fileType || "unknown" },
          { label: "attachmentCount", value: String(visibility.attachmentCount) },
          { label: "manualReviewNeeded", value: visibility.manualReviewNeeded ? "true" : "false" },
          { label: "manualReviewReason", value: manualReviewReasonLabel(visibility.manualReviewReason) },
          { label: "preflightGate", value: preflightGateLabel(visibility.preflight?.gateDecision) },
        ]}
      />
      {visibility.parserLimited || visibility.manualReviewReason ? (
        <div className="callout warning-callout">
          <strong>L0 parser / visibility 提示</strong>
          <p>
            {visibility.parserLimited
              ? "当前解析路径存在明确限制；下述 visibility 结论应按保守口径理解。"
              : "当前结果已触发人工复核条件。"}
          </p>
          {visibility.manualReviewReason ? (
            <p>主人工复核原因：{manualReviewReasonLabel(visibility.manualReviewReason)}</p>
          ) : null}
        </div>
      ) : null}
      <div className="stack-sm">
        <strong>Pre-review gate</strong>
        <ReviewKeyValueList
          items={[
            {
              label: "blockingReasons",
              value: visibility.preflight?.blockingReasons?.length
                ? visibility.preflight.blockingReasons.map((item) => humanizeToken(item)).join("，")
                : "—",
            },
            {
              label: "parserLimitations",
              value: visibility.preflight?.parserLimitations?.length
                ? visibility.preflight.parserLimitations.join("，")
                : "—",
            },
          ]}
        />
      </div>
      <div className="stack-sm">
        <strong>Pre-review checklist</strong>
        {visibility.preflight?.checklist?.length ? (
          <ul className="source-list">
            {visibility.preflight.checklist.map((item) => (
              <li key={item.key}>
                <strong>{item.key}</strong>
                <p className="muted small">
                  {item.status}
                  {item.blocking ? " · blocking" : ""}
                </p>
                <p>{item.summary}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">无</p>
        )}
      </div>
      <div className="stack-sm">
        <strong>状态计数</strong>
        <ReviewKeyValueList items={countItems} />
      </div>
      <div className="stack-sm">
        <strong>原因计数</strong>
        <ReviewKeyValueList items={reasonItems} />
      </div>
      <div className="stack-sm">
        <strong>重复章节</strong>
        <ReviewTokenList items={visibility.duplicateSectionTitles} />
      </div>
      <div className="stack-sm">
        <strong>Parse warnings</strong>
        <ReviewTokenList items={visibility.parseWarnings} />
      </div>
    </div>
  );
}

function AttachmentVisibilityList({ items }: { items: AttachmentVisibilityMatrixItem[] }) {
  if (!items.length) {
    return <p className="muted">当前没有附件可视域条目。</p>;
  }
  return (
    <ul className="source-list">
      {items.map((item) => (
        <li key={item.id}>
          <div className="section-heading compact">
            <div>
              <strong>
                {item.attachmentNumber ? `附件${item.attachmentNumber}` : item.id} · {item.title}
              </strong>
              <p className="muted small">
                parseState={item.parseState} · titleBlock={item.titleBlockId || "none"}
              </p>
            </div>
            <div className="pill-row">
              <span className={`status-pill ${item.manualReviewNeeded ? "is-warning" : "is-healthy"}`}>{item.visibility}</span>
              <span className={`status-pill ${item.manualReviewNeeded ? "is-warning" : "is-neutral"}`}>
              {item.manualReviewNeeded ? "manual review" : "visible"}
              </span>
            </div>
          </div>
          <ReviewKeyValueList
            items={[
              { label: "reason", value: item.reason || "—" },
              {
                label: "referenceBlockIds",
                value: item.referenceBlockIds.length ? item.referenceBlockIds.join("，") : "—",
              },
            ]}
          />
        </li>
      ))}
    </ul>
  );
}

function RuleHitList({ items }: { items: RuleHitMatrixRow[] }) {
  if (!items.length) {
    return <p className="muted">暂无规则命中。</p>;
  }
  return (
    <ul className="source-list">
      {items.map((row) => (
        <li key={`${row.packId}-${row.ruleId}`}>
          <div className="section-heading compact">
            <div>
              <strong>{row.ruleId}</strong>
              <p className="muted small">pack={row.packId}</p>
            </div>
            <div className="pill-row">
              <span className={`status-pill ${row.packReadiness === "ready" ? "is-healthy" : "is-warning"}`}>
                {row.packReadiness}
              </span>
              <span className={`status-pill ${row.status === "pass" ? "is-healthy" : row.status === "not_applicable" ? "is-neutral" : "is-warning"}`}>
                {row.status}
              </span>
            </div>
          </div>
          <ReviewKeyValueList
            items={[
              { label: "layer", value: row.layerHint },
              { label: "severity", value: row.severityHint },
              { label: "matchType", value: row.matchType },
              {
                label: "requiredFactKeys",
                value: row.requiredFactKeys?.length ? row.requiredFactKeys.join("，") : "—",
              },
              {
                label: "missingFactKeys",
                value: row.missingFactKeys?.length ? row.missingFactKeys.join("，") : "—",
              },
              {
                label: "clauseIds",
                value: row.clauseIds?.length ? row.clauseIds.join("，") : "—",
              },
              {
                label: "blockingReasons",
                value: row.blockingReasons?.length ? row.blockingReasons.join("，") : "—",
              },
            ]}
          />
        </li>
      ))}
    </ul>
  );
}

function ConflictList({ conflicts }: { conflicts: ConflictMatrix }) {
  const entries = Object.entries(conflicts.values || {});
  if (!entries.length) {
    return <p className="muted">暂无冲突矩阵。</p>;
  }
  return (
    <div className="grid two-up">
      {entries.map(([key, value]) => (
        <article className="boundary-item subtle stack-sm" key={key}>
          <strong>{humanizeToken(key)}</strong>
          <ReviewKeyValueList
            items={Object.entries((value as Record<string, unknown>) || {}).map(([nestedKey, nestedValue]) => ({
              label: nestedKey,
              value: renderScalar(nestedValue),
            }))}
          />
        </article>
      ))}
    </div>
  );
}

function SectionStructureList({ sections }: { sections: SectionStructureMatrixItem[] }) {
  if (!sections.length) {
    return <p className="muted">暂无章节结构。</p>;
  }
  return (
    <ul className="source-list">
      {sections.map((section) => (
        <li key={section.id}>
          <div
            className="section-heading compact review-section-row"
            style={{ paddingLeft: `${Math.max(section.level - 1, 0) * 16}px` }}
          >
            <div>
              <strong>{section.title}</strong>
              <p className="muted small">
                level={section.level} · parent={section.parentId || "root"}
              </p>
            </div>
            {section.duplicate ? <span className="status-pill is-warning">duplicate</span> : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

function HazardIdentificationList({
  values,
}: {
  values: StructuredReviewResult["matrices"]["hazardIdentification"]["values"];
}) {
  const entries = Object.entries(values || {});
  if (!entries.length) {
    return <p className="muted">暂无 hazard identification 数据。</p>;
  }
  return (
    <ReviewKeyValueList
      items={entries.map(([key, value]) => ({
        label: key,
        value: renderScalar(value),
      }))}
    />
  );
}

export function TaskDetail({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskRecord | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [artifacts, setArtifacts] = useState<TaskArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transportMode, setTransportMode] = useState<"connecting" | "sse" | "polling">("connecting");
  const [transportMessage, setTransportMessage] = useState("正在建立实时流…");
  const [highlightedEventKeys, setHighlightedEventKeys] = useState<string[]>([]);
  const [lastStreamHeartbeatAt, setLastStreamHeartbeatAt] = useState<number | null>(null);
  const [nowTick, setNowTick] = useState(() => Date.now());

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

  useEffect(() => {
    const interval = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const highlightNewEvents = useCallback((newEvents: TaskEvent[], existingEvents: TaskEvent[]) => {
    const existingKeys = new Set(existingEvents.map(eventKey));
    const nextKeys = newEvents.map(eventKey).filter((key) => !existingKeys.has(key));
    if (!nextKeys.length) return;

    setHighlightedEventKeys((current) => Array.from(new Set([...current, ...nextKeys])));

    nextKeys.forEach((key) => {
      window.setTimeout(() => {
        setHighlightedEventKeys((current) => current.filter((item) => item !== key));
      }, 1_800);
    });
  }, []);

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
      highlight,
    }: {
      taskData: TaskRecord;
      eventData: TaskEvent[];
      artifactData: TaskArtifact[];
      highlight: boolean;
    }) => {
      setTask(taskData);
      setEvents((current) => {
        if (highlight) {
          highlightNewEvents(eventData, current);
        }
        return eventData;
      });
      setArtifacts(artifactData);
      setError(null);
      setLoading(false);
    },
    [highlightNewEvents],
  );

  const loadTaskSnapshot = useCallback(
    async ({ highlight = false }: { highlight?: boolean } = {}) => {
      try {
        const [taskData, eventData] = await Promise.all([fetchTask(taskId), fetchTaskEvents(taskId)]);
        const artifactData =
          taskData.taskType === "structured_review"
            ? await fetchTaskArtifacts(taskId).catch(() => [])
            : [];
        if (!mountedRef.current) {
          return { done: true, ok: true };
        }
        applyTaskState({ taskData, eventData, artifactData, highlight });
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

      const result = await loadTaskSnapshot({ highlight: true });
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
    setTransportMessage("正在建立实时流…");

    source.onopen = () => {
      if (!mountedRef.current) return;
      clearPolling();
      pollingFailureCountRef.current = 0;
      transportModeRef.current = "sse";
      setTransportMode("sse");
      setTransportMessage("实时流已连接，任务状态将自动推送。");
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
        highlight: false,
      });
      setLastStreamHeartbeatAt(Date.now());
    });

    source.addEventListener("task", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskRecord;
      setTask(payload);
      setError(null);
      setLoading(false);
      setLastStreamHeartbeatAt(Date.now());
    });

    source.addEventListener("event", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskEvent;
      setEvents((current) => {
        if (current.some((item) => eventKey(item) === eventKey(payload))) {
          return current;
        }
        highlightNewEvents([payload], current);
        return [...current, payload];
      });
      setLastStreamHeartbeatAt(Date.now());
    });

    source.addEventListener("artifacts", (rawEvent) => {
      if (!mountedRef.current) return;
      const payload = JSON.parse(rawEvent.data) as TaskArtifact[];
      setArtifacts(payload);
      setLastStreamHeartbeatAt(Date.now());
    });

    source.addEventListener("heartbeat", () => {
      if (!mountedRef.current) return;
      setLastStreamHeartbeatAt(Date.now());
    });

    source.onerror = () => {
      if (!mountedRef.current) return;
      closeStream();
      transportModeRef.current = "polling";
      setTransportMode("polling");
      setTransportMessage("实时流已断开，切换轮询中。");
      startPolling();
      reconnectTimerRef.current = window.setTimeout(() => {
        if (!mountedRef.current) return;
        reconnectStreamRef.current();
      }, STREAM_RECONNECT_DELAY_MS);
    };
  }, [applyTaskState, clearPolling, clearReconnect, closeStream, highlightNewEvents, startPolling, taskId]);

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

  const summary = useMemo(() => {
    if (!task?.result || isStructuredReviewResult(task.result)) return null;
    return {
      capabilities: (task.result.capabilitiesUsed as string[] | undefined) || [],
      answer: (task.result.finalAnswer as string | undefined) || "",
      sources: (task.result.sources as Array<Record<string, unknown>> | undefined) || [],
      artifacts: (task.result.artifacts as string[] | undefined) || [],
    };
  }, [task]);

  const structuredResult = useMemo(() => {
    if (!task?.result || !isStructuredReviewResult(task.result)) return null;
    return task.result;
  }, [task]);

  const structuredArtifacts = useMemo(() => {
    if (!structuredResult) return [];
    return Array.isArray(structuredResult.artifactIndex) ? structuredResult.artifactIndex : artifacts;
  }, [artifacts, structuredResult]);

  const reviewerDecision = task?.reviewerDecision || null;

  const issuesByLayer = useMemo(() => {
    if (!structuredResult) return { L1: [], L2: [], L3: [] } as Record<string, ReviewIssue[]>;
    return REVIEW_LAYERS.reduce<Record<string, ReviewIssue[]>>((acc, layer) => {
      acc[layer] = structuredResult.issues.filter((issue) => issue.layer === layer);
      return acc;
    }, { L1: [], L2: [], L3: [] });
  }, [structuredResult]);

  const issuesByKind = useMemo(() => {
    if (!structuredResult) {
      return { hard_defect: [], visibility_gap: [], evidence_gap: [], enhancement: [] } as Record<string, ReviewIssue[]>;
    }
    return structuredResult.issues.reduce<Record<string, ReviewIssue[]>>(
      (acc, issue) => {
        acc[issue.issueKind] = [...(acc[issue.issueKind] || []), issue];
        return acc;
      },
      { hard_defect: [], visibility_gap: [], evidence_gap: [], enhancement: [] },
    );
  }, [structuredResult]);

  const l0Artifact = useMemo(
    () => structuredArtifacts.find((artifact) => artifact.name === "structured-review-l0-visibility"),
    [structuredArtifacts],
  );

  const reviewerSummary = useMemo(() => {
    if (!reviewerDecision) return null;
    const issueReviewed = reviewerDecision.issues.filter((item) => item.state !== "pending").length;
    const attachmentReviewed = reviewerDecision.attachments.filter((item) => item.state !== "pending").length;
    return {
      taskState: reviewerDecision.taskState,
      issueReviewed,
      issueTotal: reviewerDecision.issues.length,
      attachmentReviewed,
      attachmentTotal: reviewerDecision.attachments.length,
      updatedAt: reviewerDecision.updatedAt || null,
    };
  }, [reviewerDecision]);
  const reviewPreparation = task?.reviewPreparation || null;

  const streamFreshness = useMemo(() => {
    if (!lastStreamHeartbeatAt) return "等待心跳";
    return `最近心跳 ${Math.max(1, Math.round((nowTick - lastStreamHeartbeatAt) / 1000))} 秒前`;
  }, [lastStreamHeartbeatAt, nowTick]);

  return (
    <main className="shell stack-xl">
      <section className="section-heading">
        <div>
          <p className="eyebrow">Task Detail</p>
          <h1>{taskId}</h1>
        </div>
        <Link className="ghost-button" href="/">
          返回首页
        </Link>
      </section>

      <section className={`status-banner ${streamTone(transportMode)}`}>
        <strong>
          {transportMode === "sse"
            ? "实时流连接中"
            : transportMode === "polling"
              ? "轮询降级中"
              : "正在连接实时流"}
        </strong>
        <p>
          {transportMessage} · {streamFreshness}
        </p>
      </section>

      {loading ? (
        <div className="card">
          <p className="muted">正在加载任务状态…</p>
        </div>
      ) : null}
      {error ? (
        <div className="card">
          <p className="error-text">{error}</p>
        </div>
      ) : null}

      {task ? (
        <>
          <section className="grid two-up">
            <article className="card stack-md">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Overview</p>
                  <h2>任务概览</h2>
                </div>
                <span
                  className={`status-pill ${
                    task.status === "succeeded"
                      ? "is-healthy"
                      : task.status === "failed"
                        ? "is-unhealthy"
                        : task.status === "partial"
                          ? "is-warning"
                          : "is-neutral"
                  }`}
                >
                  {task.status}
                </span>
              </div>
              <dl className="meta-grid">
                <div>
                  <dt>taskType</dt>
                  <dd>{task.taskType}</dd>
                </div>
                <div>
                  <dt>capabilityMode</dt>
                  <dd>{task.capabilityMode}</dd>
                </div>
                <div>
                  <dt>createdAt</dt>
                  <dd>{new Date(task.createdAt).toLocaleString()}</dd>
                </div>
                <div>
                  <dt>updatedAt</dt>
                  <dd>{new Date(task.updatedAt).toLocaleString()}</dd>
                </div>
              </dl>
              <div className="callout">
                <strong>Query</strong>
                <p>{task.query}</p>
              </div>
              {task.error ? (
                <div className="callout error-callout">
                  <strong>Error</strong>
                  <pre>{renderJson(task.error)}</pre>
                </div>
              ) : null}
            </article>

            <article className="card stack-md">
              <div>
                <p className="eyebrow">Plan</p>
                <h2>DeepResearchAgent 计划</h2>
              </div>
              {task.plan ? <pre className="code-block">{renderJson(task.plan)}</pre> : <p className="muted">计划尚未生成。</p>}
            </article>
          </section>

          <section className="card stack-lg">
            <div>
              <p className="eyebrow">Execution Timeline</p>
              <h2>调用链路 / 中间步骤</h2>
            </div>
            <div className="timeline">
              {events.map((event, index) => {
                const key = eventKey(event);
                return (
                  <article
                    className={`timeline-item ${highlightedEventKeys.includes(key) ? "is-new-event" : ""}`}
                    key={`${key}-${index}`}
                  >
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <div className="timeline-header">
                        <strong>{event.stage}</strong>
                        <span className="muted small">{event.capability}</span>
                        <span
                          className={`status-pill ${
                            event.status === "completed"
                              ? "is-healthy"
                              : event.status === "failed"
                                ? "is-unhealthy"
                                : "is-neutral"
                          }`}
                        >
                          {event.status}
                        </span>
                      </div>
                      <p>{event.message}</p>
                      <p className="muted small">{new Date(event.timestamp).toLocaleString()}</p>
                      {event.artifactPath ? <p className="muted small">artifact: {event.artifactPath}</p> : null}
                      {event.debug ? <pre className="code-block compact">{renderJson(event.debug)}</pre> : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {structuredResult ? (
            <>
              {reviewerSummary ? (
                <section className="card stack-md">
                  <div>
                    <p className="eyebrow">Reviewer Cockpit</p>
                    <h2>人工复核状态</h2>
                  </div>
                  <ReviewKeyValueList
                    items={[
                      { label: "taskState", value: reviewerTaskStateLabel(reviewerSummary.taskState) },
                      { label: "issues reviewed", value: `${reviewerSummary.issueReviewed}/${reviewerSummary.issueTotal}` },
                      {
                        label: "attachments reviewed",
                        value: `${reviewerSummary.attachmentReviewed}/${reviewerSummary.attachmentTotal}`,
                      },
                      {
                        label: "updatedAt",
                        value: reviewerSummary.updatedAt ? new Date(reviewerSummary.updatedAt).toLocaleString() : "—",
                      },
                      {
                        label: "reviewPreparation",
                        value: reviewPreparation
                          ? `${reviewPreparation.truthTier} / ${reviewPreparation.readyForPromotion ? "ready" : "not ready"}`
                          : "—",
                      },
                    ]}
                  />
                  {reviewPreparation ? (
                    <div className="callout">
                      <strong>Internal-reviewed preparation</strong>
                      <p>{reviewPreparation.disclaimer}</p>
                      <p>
                        blocking reasons：
                        {reviewPreparation.blockingReasons.length
                          ? reviewPreparation.blockingReasons.join("，")
                          : " 无"}
                      </p>
                    </div>
                  ) : null}
                </section>
              ) : null}

              <ReviewDecisionPanel
                taskId={task.id}
                issues={structuredResult.issues}
                attachments={structuredResult.matrices.attachmentVisibility}
                decision={reviewerDecision}
                onSaved={(nextTask) =>
                  setTask((current) =>
                    current ? { ...current, reviewerDecision: nextTask.reviewerDecision, reviewPreparation: nextTask.reviewPreparation } : current,
                  )
                }
              />

              <section className="grid two-up">
                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Canonical Contract</p>
                    <h2>审查主 contract</h2>
                  </div>
                  <div className="callout">
                    <strong>Resolved Profile</strong>
                    <p>documentType：{structuredResult.resolvedProfile.documentType}</p>
                    <p>disciplineTags：{structuredResult.resolvedProfile.disciplineTags.join("，") || "auto"}</p>
                    <p>policyPackIds：{structuredResult.resolvedProfile.policyPackIds.join(" → ") || "auto"}</p>
                    <p>strictMode：{structuredResult.resolvedProfile.strictMode ? "true" : "false"}（reserved）</p>
                  </div>
                  <div className="callout">
                    <strong>Canonical Visibility</strong>
                    <VisibilitySummaryPanel visibility={structuredResult.visibility} />
                    {l0Artifact ? (
                      <p className="muted small">
                        L0 artifact：
                        <a href={resolveApiUrl(l0Artifact.downloadUrl)} rel="noreferrer" target="_blank">
                          {l0Artifact.fileName}
                        </a>
                      </p>
                    ) : null}
                  </div>
                  <div className="callout">
                    <strong>Unresolved Facts</strong>
                    {structuredResult.unresolvedFacts.length ? (
                      <ul className="source-list">
                        {structuredResult.unresolvedFacts.map((item) => (
                          <li key={`${item.code}-${item.factKey}`}>
                            <strong>{item.code}</strong>
                            <p className="muted small">{item.factKey}</p>
                            <p>{item.summary}</p>
                            {"sourceExtractor" in item || "blockingRuleIds" in item ? (
                              <p className="muted small">
                                source={String((item as Record<string, unknown>).sourceExtractor || "—")} · blockingRules=
                                {Array.isArray((item as Record<string, unknown>).blockingRuleIds) &&
                                ((item as Record<string, unknown>).blockingRuleIds as string[]).length
                                  ? ((item as Record<string, unknown>).blockingRuleIds as string[]).join("，")
                                  : "—"}
                              </p>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>无</p>
                    )}
                  </div>
                  <div className="callout">
                    <strong>总体结论</strong>
                    <p>{structuredResult.summary.overallConclusion}</p>
                    <p>{structuredResult.summary.manualReviewNeeded ? "需要结合附件原件或可视域缺口做人工复核" : "当前无需额外人工复核"}</p>
                  </div>
                  {structuredResult.notice ? <div className="callout warning-callout">{structuredResult.notice}</div> : null}
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Artifacts</p>
                    <h2>审查工件</h2>
                  </div>
                  <ArtifactList artifacts={structuredArtifacts} />
                  <div className="stack-sm">
                    <strong>Issue Buckets</strong>
                    <ReviewKeyValueList
                      items={[
                        { label: "hard defect", value: String(issuesByKind.hard_defect.length) },
                        { label: "visibility gap", value: String(issuesByKind.visibility_gap.length) },
                        { label: "evidence gap", value: String(issuesByKind.evidence_gap.length) },
                        { label: "enhancement", value: String(issuesByKind.enhancement.length) },
                      ]}
                    />
                  </div>
                </article>
              </section>

              {REVIEW_LAYERS.map((layer) => (
                <section className="card stack-lg" key={layer}>
                  <div>
                    <p className="eyebrow">Issues · {layer}</p>
                    <h2>{layer} 问题</h2>
                  </div>
                  {issuesByLayer[layer].length ? (
                    <div className="stack-md">
                      {issuesByLayer[layer].map((issue: ReviewIssue) => (
                        <article className="boundary-item" key={issue.id}>
                          <div className="section-heading compact">
                            <div>
                              <h3>
                                {issue.id} · {issue.title}
                              </h3>
                              <p className="muted small">
                                {issue.layer} / {issue.findingType}
                              </p>
                            </div>
                            <span className={`status-pill ${severityTone(issue.severity)}`}>{issue.severity}</span>
                          </div>
                          <p>{issue.summary}</p>
                          {issue.manualReviewNeeded ? (
                            <p className="error-text">
                              需要人工复核该问题：{manualReviewReasonLabel(issue.manualReviewReason || "manual_confirmation_required")}。
                            </p>
                          ) : null}
                          {issue.evidenceMissing ? <p className="muted small">证据状态：当前存在 evidence gap，需补齐文档或条文证据。</p> : null}
                          <div className="stack-sm">
                            <div className="artifact-list">
                              <span className={`status-pill ${findingTone(issue.findingType)}`}>{issue.findingType}</span>
                              <span className={`status-pill ${issueKindTone(issue.issueKind)}`}>{issue.issueKind}</span>
                              <span className={`status-pill ${severityTone(issue.severity)}`}>{issue.severity}</span>
                              <span className="status-pill is-neutral">{issue.applicabilityState}</span>
                            </div>
                            <strong>整改建议</strong>
                            <ul>
                              {issue.recommendation.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                          {renderEvidenceList("文档证据", issue.docEvidence)}
                          {renderEvidenceList("规范证据", issue.policyEvidence)}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">该层暂无问题。</p>
                  )}
                </section>
              ))}

              <section className="grid two-up">
                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">L0 Visibility</p>
                    <h2>可视域与解析降级</h2>
                  </div>
                  <div className="callout">
                    <strong>Attachment Visibility Matrix</strong>
                    <p>top-level visibility 已在上方 canonical contract 卡片中展示；这里保留结构化明细。</p>
                  </div>
                  <AttachmentVisibilityList items={structuredResult.matrices.attachmentVisibility} />
                  <CompactJsonDetails
                    summary="查看 attachment visibility JSON"
                    data={structuredResult.matrices.attachmentVisibility}
                  />
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Matrices</p>
                    <h2>审查矩阵</h2>
                  </div>
                  <div className="stack-md">
                    <div>
                      <strong>Hazard Identification</strong>
                      <HazardIdentificationList values={structuredResult.matrices.hazardIdentification.values} />
                    </div>
                    <div>
                      <strong>Rule Hits</strong>
                      <RuleHitList items={structuredResult.matrices.ruleHits} />
                    </div>
                    <div>
                      <strong>Conflicts</strong>
                      <ConflictList conflicts={structuredResult.matrices.conflicts} />
                    </div>
                  </div>
                  <CompactJsonDetails summary="查看 matrices JSON" data={structuredResult.matrices} />
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Structure</p>
                    <h2>章节结构</h2>
                  </div>
                  <SectionStructureList sections={structuredResult.matrices.sectionStructure} />
                  <CompactJsonDetails
                    summary="查看 section structure JSON"
                    data={structuredResult.matrices.sectionStructure}
                  />
                </article>
              </section>

              <section className="card stack-lg">
                <div>
                  <p className="eyebrow">Structured Review Report</p>
                  <h2>报告与原始结果</h2>
                </div>
                <pre className="result-block">{structuredResult.reportMarkdown}</pre>
                <details>
                  <summary>查看原始 JSON</summary>
                  <pre className="code-block">{renderJson(structuredResult)}</pre>
                </details>
              </section>
            </>
          ) : (
            <section className="grid two-up">
              <article className="card stack-lg">
                <div>
                  <p className="eyebrow">Result</p>
                  <h2>最终结果</h2>
                </div>
                {summary ? (
                  <>
                    <div className="callout">
                      <strong>Capabilities Used</strong>
                      <p>{summary.capabilities.join(" → ") || "暂无"}</p>
                    </div>
                    <pre className="result-block">{summary.answer || "结果尚未写入。"}</pre>
                    {task.result && typeof task.result === "object" && "notice" in task.result ? (
                      <div className="callout warning-callout">{String((task.result as Record<string, unknown>).notice)}</div>
                    ) : null}
                  </>
                ) : (
                  <p className="muted">任务还在执行，结果稍后出现。</p>
                )}
              </article>

              <article className="card stack-lg">
                <div>
                  <p className="eyebrow">Sources & Debug</p>
                  <h2>来源 / chunks / artifacts</h2>
                </div>
                {summary?.sources?.length ? (
                  <ul className="source-list">
                    {summary.sources.map((source, index) => (
                      <li key={index}>
                        <strong>{String(source.label || source.mode || `source-${index + 1}`)}</strong>
                        <p className="muted small">score: {String(source.score ?? "n/a")}</p>
                        <p>{String(source.preview || "")}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">暂无来源摘要。</p>
                )}
                {summary?.artifacts?.length ? (
                  <div className="artifact-list">
                    {summary.artifacts.map((artifact) => (
                      <code key={artifact}>{artifact}</code>
                    ))}
                  </div>
                ) : null}
                {task.result ? <pre className="code-block">{renderJson(task.result)}</pre> : null}
              </article>
            </section>
          )}
        </>
      ) : null}
    </main>
  );
}
