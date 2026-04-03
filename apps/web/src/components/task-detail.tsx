"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { fetchTask, fetchTaskArtifacts, fetchTaskEvents, resolveApiUrl } from "@/lib/api";
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
  if (severity === "medium") return "is-neutral";
  return "is-healthy";
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

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [taskData, eventData] = await Promise.all([fetchTask(taskId), fetchTaskEvents(taskId)]);
        const artifactData =
          taskData.taskType === "structured_review" ? await fetchTaskArtifacts(taskId).catch(() => []) : [];
        if (cancelled) return true;
        setTask(taskData);
        setEvents(eventData);
        setArtifacts(artifactData);
        setError(null);
        setLoading(false);
        return TERMINAL_STATES.has(taskData.status);
      } catch (err) {
        if (cancelled) return true;
        setError(err instanceof Error ? err.message : "任务详情加载失败");
        setLoading(false);
        return true;
      }
    }

    void load();
    const interval = window.setInterval(async () => {
      const isDone = await load();
      if (isDone) {
        window.clearInterval(interval);
      }
    }, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [taskId]);

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
    return structuredResult.artifactIndex?.length ? structuredResult.artifactIndex : artifacts;
  }, [artifacts, structuredResult]);

  const issuesByLayer = useMemo(() => {
    if (!structuredResult) return { L1: [], L2: [], L3: [] } as Record<string, ReviewIssue[]>;
    return REVIEW_LAYERS.reduce<Record<string, ReviewIssue[]>>((acc, layer) => {
      acc[layer] = structuredResult.issues.filter((issue) => issue.layer === layer);
      return acc;
    }, { L1: [], L2: [], L3: [] });
  }, [structuredResult]);

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

      {loading ? <div className="card"><p className="muted">正在加载任务状态…</p></div> : null}
      {error ? <div className="card"><p className="error-text">{error}</p></div> : null}

      {task ? (
        <>
          <section className="grid two-up">
            <article className="card stack-md">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Overview</p>
                  <h2>任务概览</h2>
                </div>
                <span className={`status-pill ${task.status === "succeeded" ? "is-healthy" : task.status === "failed" ? "is-unhealthy" : "is-neutral"}`}>
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
              {events.map((event, index) => (
                <article className="timeline-item" key={`${event.timestamp}-${index}`}>
                  <div className="timeline-dot" />
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <strong>{event.stage}</strong>
                      <span className="muted small">{event.capability}</span>
                      <span className={`status-pill ${event.status === "completed" ? "is-healthy" : event.status === "failed" ? "is-unhealthy" : "is-neutral"}`}>
                        {event.status}
                      </span>
                    </div>
                    <p>{event.message}</p>
                    <p className="muted small">{new Date(event.timestamp).toLocaleString()}</p>
                    {event.artifactPath ? <p className="muted small">artifact: {event.artifactPath}</p> : null}
                    {event.debug ? <pre className="code-block compact">{renderJson(event.debug)}</pre> : null}
                  </div>
                </article>
              ))}
            </div>
          </section>

          {structuredResult ? (
            <>
              <section className="grid two-up">
                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Structured Review</p>
                    <h2>正式结构化审查结果</h2>
                  </div>
                  <div className="callout">
                    <strong>总体结论</strong>
                    <p>{structuredResult.summary.overallConclusion}</p>
                  </div>
                  <div className="callout">
                    <strong>Resolved Profile</strong>
                    <p>documentType：{structuredResult.resolvedProfile.documentType}</p>
                    <p>disciplineTags：{structuredResult.resolvedProfile.disciplineTags.join("，") || "auto"}</p>
                    <p>policyPackIds：{structuredResult.resolvedProfile.policyPackIds.join(" → ") || "auto"}</p>
                    <p>strictMode：{structuredResult.resolvedProfile.strictMode ? "true" : "false"}</p>
                  </div>
                  <div className="callout">
                    <strong>人工复核</strong>
                    <p>{structuredResult.summary.manualReviewNeeded ? "需要结合附件原件复核" : "当前无需额外人工复核"}</p>
                  </div>
                  {structuredResult.notice ? <div className="callout warning-callout">{structuredResult.notice}</div> : null}
                  <pre className="result-block">{structuredResult.reportMarkdown}</pre>
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
                              <h3>{issue.id} · {issue.title}</h3>
                              <p className="muted small">{issue.layer} / {issue.findingType}</p>
                            </div>
                            <span className={`status-pill ${severityTone(issue.severity)}`}>{issue.severity}</span>
                          </div>
                          <p>{issue.summary}</p>
                          {issue.whetherManualReviewNeeded ? <p className="error-text">需要人工复核该问题的可视域或附件证据。</p> : null}
                          <div className="stack-sm">
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
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.ruleHits)}</pre>
                    </div>
                    <div>
                      <strong>Conflicts</strong>
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.conflicts.values)}</pre>
                    </div>
                  </div>
                </article>

                <article className="card stack-lg">
                  <div>
                    <p className="eyebrow">Visibility & Structure</p>
                    <h2>附件 / 章节结构</h2>
                  </div>
                  <div className="stack-md">
                    <div>
                      <strong>Attachment Visibility</strong>
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.attachmentVisibility)}</pre>
                    </div>
                    <div>
                      <strong>Section Structure</strong>
                      <pre className="code-block compact">{renderJson(structuredResult.matrices.sectionStructure)}</pre>
                    </div>
                  </div>
                </article>
              </section>

              <section className="card stack-lg">
                <div>
                  <p className="eyebrow">Artifacts & Debug</p>
                  <h2>工件 / 原始 JSON</h2>
                </div>
                <ArtifactList artifacts={structuredArtifacts} />
                <pre className="code-block">{renderJson(structuredResult)}</pre>
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
