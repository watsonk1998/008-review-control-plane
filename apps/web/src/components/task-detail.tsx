"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { fetchTask, fetchTaskEvents } from "@/lib/api";
import type { TaskEvent, TaskRecord } from "@/types/control-plane";

const TERMINAL_STATES = new Set(["succeeded", "failed", "partial"]);

function renderJson(data: unknown) {
  return JSON.stringify(data, null, 2);
}

export function TaskDetail({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<TaskRecord | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [taskData, eventData] = await Promise.all([fetchTask(taskId), fetchTaskEvents(taskId)]);
        if (cancelled) return true;
        setTask(taskData);
        setEvents(eventData);
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
    if (!task?.result) return null;
    return {
      capabilities: (task.result.capabilitiesUsed as string[] | undefined) || [],
      answer: (task.result.finalAnswer as string | undefined) || "",
      sources: (task.result.sources as Array<Record<string, unknown>> | undefined) || [],
      artifacts: (task.result.artifacts as string[] | undefined) || [],
    };
  }, [task]);

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
                  {task.result?.notice ? <div className="callout warning-callout">{String(task.result.notice)}</div> : null}
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
        </>
      ) : null}
    </main>
  );
}
