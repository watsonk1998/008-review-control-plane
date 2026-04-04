"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  EvidenceSpan,
  ReviewIssue,
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
              <ReviewDecisionPanel
                taskId={task.id}
                issues={structuredResult.issues}
                attachments={structuredResult.matrices.attachmentVisibility}
                decision={reviewerDecision}
                onSaved={(nextDecision) =>
                  setTask((current) =>
                    current
                      ? {
                          ...current,
                          reviewerDecision: nextDecision,
                        }
                      : current,
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
                    <p>parserLimited：{structuredResult.visibility.parserLimited ? "true" : "false"}</p>
                    <p>fileType：{structuredResult.visibility.fileType || "unknown"}</p>
                    <p>附件数量：{structuredResult.visibility.attachmentCount}</p>
                    <p>状态计数：{renderJson(structuredResult.visibility.counts)}</p>
                    <p>原因计数：{renderJson(structuredResult.visibility.reasonCounts)}</p>
                    <p>重复章节：{structuredResult.visibility.duplicateSectionTitles.join("，") || "无"}</p>
                    <p>parse warnings：{structuredResult.visibility.parseWarnings.join("，") || "无"}</p>
                    <p>需人工复核：{structuredResult.visibility.manualReviewNeeded ? "true" : "false"}</p>
                  </div>
                  <div className="callout">
                    <strong>Unresolved Facts</strong>
                    {structuredResult.unresolvedFacts.length ? (
                      <ul>
                        {structuredResult.unresolvedFacts.map((item) => (
                          <li key={`${item.code}-${item.factKey}`}>
                            {item.code} · {item.summary}
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
                              需要人工复核该问题：{issue.manualReviewReason || "manual_confirmation_required"}。
                            </p>
                          ) : null}
                          {issue.evidenceMissing ? <p className="muted small">证据状态：当前存在 evidence gap，需补齐文档或条文证据。</p> : null}
                          <div className="stack-sm">
                            <div className="artifact-list">
                              <span className={`status-pill ${findingTone(issue.findingType)}`}>{issue.findingType}</span>
                              <span className={`status-pill ${severityTone(issue.severity)}`}>{issue.severity}</span>
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
                  <pre className="code-block compact">{renderJson(structuredResult.matrices.attachmentVisibility)}</pre>
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Matrices</p>
                    <h2>审查矩阵</h2>
                  </div>
                  <div className="stack-md">
                    <div>
                      <strong>Hazard Identification</strong>
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.hazardIdentification.values)}</pre>
                    </div>
                    <div>
                      <strong>Rule Hits</strong>
                      {structuredResult.matrices.ruleHits.length ? (
                        <ul className="source-list">
                          {structuredResult.matrices.ruleHits.map((row) => (
                            <li key={`${row.packId}-${row.ruleId}`}>
                              <strong>{row.ruleId}</strong>
                              <p className="muted small">
                                pack={row.packId} · readiness={row.packReadiness} · status={row.status}
                              </p>
                              <p className="muted small">
                                layer={row.layerHint} · severity={row.severityHint} · match={row.matchType}
                              </p>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted">暂无规则命中。</p>
                      )}
                    </div>
                    <div>
                      <strong>Conflicts</strong>
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.conflicts.values)}</pre>
                    </div>
                  </div>
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Structure</p>
                    <h2>章节结构</h2>
                  </div>
                  <pre className="code-block compact">{renderJson(structuredResult.matrices.sectionStructure)}</pre>
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
