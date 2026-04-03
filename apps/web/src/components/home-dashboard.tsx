"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { StructuredReviewForm } from "@/components/structured-review-form";
import {
  createTask,
  fetchFixtures,
  fetchHealth,
  fetchHeartbeat,
  fetchRecentTasks,
  fetchSupportScope,
  getApiBaseUrl,
  uploadDocument,
} from "@/lib/api";
import type {
  CapabilityHealth,
  CapabilityMode,
  CreateTaskRequest,
  FixtureRecord,
  HealthResponse,
  HeartbeatResponse,
  RecentTaskSummary,
  SupportScopeResponse,
  TaskStatus,
  TaskType,
} from "@/types/control-plane";

const TASK_OPTIONS: Array<{ value: TaskType; label: string; hint: string }> = [
  {
    value: "structured_review",
    label: "正式审查",
    hint: "支持 fixture 或上传文档；P0 正式支持 construction_org / hazardous_special_scheme。",
  },
  {
    value: "review_assist",
    label: "审查辅助",
    hint: "输出辅助审查要点，不给正式审查结论。",
  },
  {
    value: "knowledge_qa",
    label: "知识问答",
    hint: "先规划，再调 Fast / DeepTutor / LLM。",
  },
  {
    value: "document_research",
    label: "文档研究",
    hint: "围绕本地 fixture 文档做研究与报告。",
  },
  {
    value: "deep_research",
    label: "深度研究",
    hint: "路由 GPT Researcher 产出研究报告。",
  },
];

const CAPABILITY_OPTIONS: Array<{
  value: CapabilityMode;
  label: string;
  hint: string;
}> = [
  { value: "auto", label: "Auto", hint: "由总控层决定能力链路。" },
  { value: "deeptutor", label: "DeepTutor", hint: "偏知识解释与规范问答。" },
  {
    value: "gpt_researcher",
    label: "GPT Researcher",
    hint: "偏研究报告与来源归纳。",
  },
  {
    value: "fast",
    label: "FastGPT Chunks",
    hint: "直接拉取知识片段并轻量总结。",
  },
  {
    value: "llm_only",
    label: "LLM Only",
    hint: "仅内部调试；跳过外部知识检索。",
  },
];

const CAPABILITY_BOUNDARY = [
  {
    title: "DeepResearchAgent",
    body: "总控编排 / planner / router / coordinator，不直接承担正式审查结论。",
  },
  {
    title: "DeepTutor",
    body: "标准规范问答、知识解释、基于上下文的说明服务。",
  },
  {
    title: "GPT Researcher",
    body: "深度研究、本地文档研究、报告与来源整理。",
  },
  {
    title: "FastGPT",
    body: "底层知识片段检索层，优先 chunks，不是首选答案黑盒。",
  },
];

const ACTIVE_TASK_STATUSES = new Set<TaskStatus>([
  "created",
  "planned",
  "running",
  "waiting_external",
]);

function taskStatusTone(status: TaskStatus) {
  if (status === "succeeded") return "is-healthy";
  if (status === "failed") return "is-unhealthy";
  if (status === "partial") return "is-warning";
  return "is-neutral";
}

function connectionTone(state: "healthy" | "lagging" | "offline" | "checking") {
  if (state === "healthy") return "is-healthy";
  if (state === "lagging") return "is-warning";
  if (state === "offline") return "is-unhealthy";
  return "is-neutral";
}

function connectionLabel(state: "healthy" | "lagging" | "offline" | "checking") {
  if (state === "healthy") return "在线";
  if (state === "lagging") return "延迟升高";
  if (state === "offline") return "连接中断";
  return "检查中";
}

function formatTime(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDistanceFromNow(value?: string | null) {
  if (!value) return "暂无记录";
  const deltaMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(deltaMs / 60000));
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  return `${days} 天前`;
}

export function HomeDashboard() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatResponse | null>(null);
  const [fixtures, setFixtures] = useState<FixtureRecord[]>([]);
  const [supportScope, setSupportScope] = useState<SupportScopeResponse | null>(null);
  const [recentTasks, setRecentTasks] = useState<RecentTaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sourceUrlInput, setSourceUrlInput] = useState("");
  const [policyPackInput, setPolicyPackInput] = useState("");
  const [lastHeartbeatSuccessAt, setLastHeartbeatSuccessAt] = useState<number | null>(null);
  const [lastFullRefreshAt, setLastFullRefreshAt] = useState<number | null>(null);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [apiReachable, setApiReachable] = useState(false);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [form, setForm] = useState<CreateTaskRequest>({
    taskType: "structured_review",
    capabilityMode: "auto",
    query: "请对该施工组织设计执行正式结构化审查，并输出问题清单、证据定位与整改建议。",
    fixtureId: "",
    sourceDocumentRef: undefined,
    datasetId: "",
    collectionId: "",
    useWeb: false,
    debug: true,
    sourceUrls: [],
    documentType: "construction_org",
    disciplineTags: [],
    strictMode: true,
    policyPackIds: [],
  });

  const groupedFixtures = useMemo(() => {
    return fixtures.reduce<Record<string, FixtureRecord[]>>((acc, item) => {
      acc[item.domain] = acc[item.domain] || [];
      acc[item.domain].push(item);
      return acc;
    }, {});
  }, [fixtures]);

  const selectedTask = useMemo(
    () => TASK_OPTIONS.find((item) => item.value === form.taskType) ?? TASK_OPTIONS[0],
    [form.taskType],
  );

  const selectedCapability = useMemo(
    () =>
      CAPABILITY_OPTIONS.find((item) => item.value === form.capabilityMode) ??
      CAPABILITY_OPTIONS[0],
    [form.capabilityMode],
  );

  const heartbeatState = useMemo(() => {
    if (!lastHeartbeatSuccessAt) return "checking";
    const delta = nowTick - lastHeartbeatSuccessAt;
    if (delta > 60_000) return "offline";
    if (delta > 25_000) return "lagging";
    return "healthy";
  }, [lastHeartbeatSuccessAt, nowTick]);

  const availableCapabilities = useMemo(
    () => health?.capabilities.filter((capability) => capability.available) ?? [],
    [health],
  );

  const hasUnavailableCapabilities = useMemo(
    () => Boolean(health?.capabilities.some((capability) => !capability.available)),
    [health],
  );

  const canSubmit =
    apiReachable &&
    Boolean(form.query.trim()) &&
    (form.taskType !== "structured_review" || Boolean(form.fixtureId || form.sourceDocumentRef));

  const refreshLight = useCallback(async () => {
    const [heartbeatData, taskData] = await Promise.all([
      fetchHeartbeat(),
      fetchRecentTasks(8),
    ]);
    setHeartbeat(heartbeatData);
    setRecentTasks(taskData);
    setApiReachable(true);
    setError(null);
    setLastHeartbeatSuccessAt(Date.now());
  }, []);

  const refreshFull = useCallback(
    async ({ manual = false }: { manual?: boolean } = {}) => {
      if (manual) {
        setRefreshing(true);
      } else if (!lastFullRefreshAt) {
        setLoading(true);
      }

      try {
        const [healthData, fixtureData, heartbeatData, taskData, supportScopeData] = await Promise.all([
          fetchHealth(),
          fetchFixtures(),
          fetchHeartbeat(),
          fetchRecentTasks(8),
          fetchSupportScope(),
        ]);
        setHealth(healthData);
        setFixtures(fixtureData);
        setSupportScope(supportScopeData);
        setHeartbeat(heartbeatData);
        setRecentTasks(taskData);
        setApiReachable(true);
        setError(null);
        const now = Date.now();
        setLastHeartbeatSuccessAt(now);
        setLastFullRefreshAt(now);
      } catch (err) {
        setApiReachable(false);
        setError(err instanceof Error ? err.message : "加载控制台状态失败");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [lastFullRefreshAt],
  );

  useEffect(() => {
    void refreshFull();
  }, [refreshFull]);

  useEffect(() => {
    const clock = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(clock);
  }, []);

  useEffect(() => {
    async function refreshVisibleDashboard() {
      if (document.visibilityState !== "visible") return;
      try {
        await refreshLight();
        if (!lastFullRefreshAt || Date.now() - lastFullRefreshAt >= 60_000) {
          await refreshFull();
        }
      } catch (err) {
        setApiReachable(false);
        setError(err instanceof Error ? err.message : "心跳刷新失败");
      }
    }

    const interval = window.setInterval(() => {
      void refreshVisibleDashboard();
    }, 10_000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshVisibleDashboard();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [lastFullRefreshAt, refreshFull, refreshLight]);

  async function handleDocumentUpload(file: File) {
    setUploadingDocument(true);
    setError(null);
    try {
      const sourceDocumentRef = await uploadDocument(file);
      setForm((current) => ({
        ...current,
        fixtureId: "",
        sourceDocumentRef,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "文档上传失败");
    } finally {
      setUploadingDocument(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const structuredPolicyPackIds = policyPackInput
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean);

      const task = await createTask({
        ...form,
        fixtureId:
          form.taskType === "structured_review" && form.sourceDocumentRef
            ? undefined
            : form.fixtureId || undefined,
        sourceDocumentRef:
          form.taskType === "structured_review" && form.sourceDocumentRef
            ? form.sourceDocumentRef
            : undefined,
        datasetId: form.datasetId || undefined,
        collectionId: form.collectionId || undefined,
        sourceUrls: sourceUrlInput
          .split(/\n+/)
          .map((item) => item.trim())
          .filter(Boolean),
        documentType:
          form.taskType === "structured_review"
            ? form.documentType || "construction_org"
            : undefined,
        disciplineTags:
          form.taskType === "structured_review"
            ? form.disciplineTags || []
            : undefined,
        strictMode:
          form.taskType === "structured_review"
            ? form.strictMode ?? true
            : undefined,
        policyPackIds:
          form.taskType === "structured_review"
            ? structuredPolicyPackIds
            : undefined,
      });

      setRecentTasks((current) => [
        {
          id: task.id,
          taskType: task.taskType,
          capabilityMode: task.capabilityMode,
          status: task.status,
          query: task.query,
          fixtureId: task.fixtureId,
          sourceDocumentRef: task.sourceDocumentRef,
          documentType: task.documentType,
          createdAt: task.createdAt,
          updatedAt: task.updatedAt,
        },
        ...current.filter((item) => item.id !== task.id),
      ].slice(0, 8));

      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="shell workbench-shell">
      <section className="workbench-hero">
        <div className="workbench-hero-copy">
          <p className="eyebrow">008 · Review Control Plane</p>
          <h1>正式审查工作台</h1>
          <p>
            直接发起结构化审查，持续感知系统心跳，并从最近任务继续追踪执行过程。
          </p>
        </div>

        <div className="workbench-hero-side">
          <div className={`heartbeat-badge ${connectionTone(heartbeatState)}`}>
            <span className={`pulse-dot ${connectionTone(heartbeatState)}`} />
            <div>
              <strong>{connectionLabel(heartbeatState)}</strong>
              <p className="muted small">
                {heartbeat?.runningTaskCount ?? 0} 个运行中任务 · 最近更新{" "}
                {formatDistanceFromNow(heartbeat?.latestTaskUpdatedAt)}
              </p>
            </div>
          </div>

          <button
            className="ghost-button"
            disabled={refreshing}
            onClick={() => void refreshFull({ manual: true })}
            type="button"
          >
            {refreshing ? "刷新中…" : "手动刷新"}
          </button>
        </div>

        <div className="workbench-meta">
          <div>
            <span>API Base</span>
            <strong>{getApiBaseUrl()}</strong>
          </div>
          <div>
            <span>Capabilities</span>
            <strong>
              {availableCapabilities.length}/{health?.capabilities.length ?? "—"}
            </strong>
          </div>
          <div>
            <span>上次全量刷新</span>
            <strong>{formatTime(lastFullRefreshAt ? new Date(lastFullRefreshAt).toISOString() : null)}</strong>
          </div>
        </div>
      </section>

      {error ? (
        <section className="status-banner is-unhealthy">
          <strong>控制台连接异常</strong>
          <p>{error}</p>
        </section>
      ) : null}

      <section className="workbench-grid">
        <section className="workbench-primary">
          <div className="workbench-panel stack-lg">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Create Task</p>
                <h2>直接发起任务</h2>
              </div>
              <p className="muted small">{selectedTask.hint}</p>
            </div>

            <div className="task-type-toggle" role="tablist" aria-label="任务类型">
              {TASK_OPTIONS.map((item) => (
                <button
                  aria-selected={form.taskType === item.value}
                  className={`task-type-chip ${form.taskType === item.value ? "is-active" : ""}`}
                  key={item.value}
                  onClick={() =>
                    setForm((current) => ({
                      ...current,
                      taskType: item.value,
                      capabilityMode:
                        item.value === "structured_review" ? "auto" : current.capabilityMode,
                    }))
                  }
                  role="tab"
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>

            <form className="task-form stack-lg" onSubmit={handleSubmit}>
              {form.taskType !== "structured_review" ? (
                <label className="field">
                  <span>能力模式</span>
                  <select
                    value={form.capabilityMode}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        capabilityMode: event.target.value as CapabilityMode,
                      }))
                    }
                  >
                    {CAPABILITY_OPTIONS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  <small>{selectedCapability.hint}</small>
                </label>
              ) : null}

              <label className="field">
                <span>{form.taskType === "structured_review" ? "审查任务描述" : "查询 / 任务描述"}</span>
                <textarea
                  rows={form.taskType === "structured_review" ? 5 : 6}
                  value={form.query}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, query: event.target.value }))
                  }
                  placeholder={
                    form.taskType === "structured_review"
                      ? "输入正式审查要求，例如：执行危大专项方案正式审查"
                      : "输入规范问题、研究任务或审查辅助要求"
                  }
                />
              </label>

              <label className="field">
                <span>Fixture 样本（可选）</span>
                <select
                  value={form.fixtureId || ""}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      fixtureId: event.target.value,
                      sourceDocumentRef: event.target.value ? undefined : current.sourceDocumentRef,
                    }))
                  }
                >
                  <option value="">不指定</option>
                  {Object.entries(groupedFixtures).map(([domain, items]) => (
                    <optgroup key={domain} label={domain}>
                      {items.map((fixture) => (
                        <option key={fixture.id} value={fixture.id}>
                          {fixture.title}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                <small>
                  {form.taskType === "structured_review"
                    ? "正式审查现在支持 fixture 或上传文档二选一；fixture 仍是更稳定的回归路径。"
                    : "文档研究 / 审查辅助推荐选择 docx fixture。"}
                </small>
              </label>

              {form.taskType === "structured_review" ? (
                <label className="field">
                  <span>上传文档（可选）</span>
                  <input
                    accept=".docx,.pdf,.md,.txt"
                    disabled={uploadingDocument}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (!file) return;
                      void handleDocumentUpload(file);
                      event.currentTarget.value = "";
                    }}
                    type="file"
                  />
                  <small>
                    {form.sourceDocumentRef
                      ? `当前已选择上传文档：${form.sourceDocumentRef.displayName || form.sourceDocumentRef.fileName}`
                      : "上传后将自动切换为 sourceDocumentRef 输入路径。"}
                  </small>
                </label>
              ) : null}

              <StructuredReviewForm form={form} setForm={setForm} supportScope={supportScope} />

              <div className="toggle-row">
                <button
                  className="ghost-button"
                  onClick={() => setShowAdvanced((value) => !value)}
                  type="button"
                >
                  {showAdvanced ? "收起高级项" : "展开高级项"}
                </button>
                <p className="muted small">
                  高级项用于 source URLs、dataset / collection、debug 与 policy pack 覆盖。
                </p>
              </div>

              {showAdvanced ? (
                <div className="advanced-panel stack-lg">
                  {form.taskType !== "structured_review" ? (
                    <label className="field">
                      <span>能力模式说明</span>
                      <small>{selectedCapability.hint}</small>
                    </label>
                  ) : null}

                  <label className="field">
                    <span>Source URLs（可选，多行）</span>
                    <textarea
                      rows={3}
                      value={sourceUrlInput}
                      onChange={(event) => setSourceUrlInput(event.target.value)}
                      placeholder={"https://example.com/source-a\nhttps://example.com/source-b"}
                    />
                  </label>

                  {form.taskType === "structured_review" ? (
                    <label className="field">
                      <span>policyPackIds（高级覆盖，可选）</span>
                      <textarea
                        rows={3}
                        value={policyPackInput}
                        onChange={(event) => setPolicyPackInput(event.target.value)}
                        placeholder={"construction_org.base\nlifting_operations.base"}
                      />
                      <small>留空表示自动选 pack；填写后按“基础 pack + 指定 pack”组合执行。</small>
                    </label>
                  ) : null}

                  <div className="form-grid two-columns">
                    <label className="field">
                      <span>datasetId</span>
                      <input
                        type="text"
                        value={form.datasetId || ""}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            datasetId: event.target.value,
                          }))
                        }
                        placeholder="Fast 模式 A 的 datasetId"
                      />
                    </label>

                    <label className="field">
                      <span>collectionId</span>
                      <input
                        type="text"
                        value={form.collectionId || ""}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            collectionId: event.target.value,
                          }))
                        }
                        placeholder="Fast 模式 B 的 collectionId"
                      />
                    </label>
                  </div>

                  <div className="toggle-row">
                    <label className="checkbox-row inline-check">
                      <input
                        checked={form.useWeb}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            useWeb: event.target.checked,
                          }))
                        }
                        type="checkbox"
                      />
                      <span>useWeb（用于 GPT Researcher）</span>
                    </label>

                    <label className="checkbox-row inline-check">
                      <input
                        checked={form.debug}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            debug: event.target.checked,
                          }))
                        }
                        type="checkbox"
                      />
                      <span>debug 模式</span>
                    </label>
                  </div>
                </div>
              ) : null}

              <div className="form-footer">
                <div className="stack-sm">
                  <p className="muted small">
                    structured_review 会输出 issues、matrices 与正式报告；review_assist 仅输出辅助审查要点。
                  </p>
                  {!apiReachable ? (
                    <p className="error-text">API 当前不可达，表单可继续编辑，但暂时无法创建任务。</p>
                  ) : null}
                  {form.taskType === "structured_review" && !form.fixtureId && !form.sourceDocumentRef ? (
                    <p className="error-text">正式审查需要选择 fixture 或上传文档。</p>
                  ) : null}
                  {form.taskType === "structured_review" && form.sourceDocumentRef ? (
                    <p className="muted small">
                      当前输入源：上传文档 · {form.sourceDocumentRef.displayName || form.sourceDocumentRef.fileName}
                    </p>
                  ) : null}
                  {form.taskType === "structured_review" && form.fixtureId ? (
                    <p className="muted small">当前输入源：fixture · {form.fixtureId}</p>
                  ) : null}
                </div>

                <button
                  className="primary-button"
                  disabled={submitting || !canSubmit}
                  type="submit"
                >
                  {submitting ? "正在创建任务…" : "创建任务并进入详情页"}
                </button>
              </div>
            </form>
          </div>
        </section>

        <aside className="workbench-sidebar">
          <section className="workbench-panel stack-lg">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">System Health</p>
                <h2>系统状态摘要</h2>
              </div>
              <span className={`status-pill ${connectionTone(heartbeatState)}`}>
                {connectionLabel(heartbeatState)}
              </span>
            </div>

            {loading ? <p className="muted">正在加载系统状态…</p> : null}

            <div className="system-metrics">
              <div>
                <span>可用能力</span>
                <strong>
                  {availableCapabilities.length}/{health?.capabilities.length ?? "—"}
                </strong>
              </div>
              <div>
                <span>Fixtures</span>
                <strong>{health?.fixtureCount ?? fixtures.length}</strong>
              </div>
              <div>
                <span>最新心跳</span>
                <strong>{heartbeat?.serverTime ? formatTime(heartbeat.serverTime) : "—"}</strong>
              </div>
            </div>

            <div className="capability-list">
              {health?.capabilities.map((capability: CapabilityHealth) => (
                <article className="capability-row" key={capability.name}>
                  <div>
                    <strong>{capability.name}</strong>
                    <p className="muted small">{capability.detail || capability.mode}</p>
                  </div>
                  <span className={`status-pill ${capability.available ? "is-healthy" : "is-warning"}`}>
                    {capability.available ? "available" : "degraded"}
                  </span>
                </article>
              ))}
            </div>

            {hasUnavailableCapabilities ? (
              <p className="muted small">
                部分能力当前降级，但不阻断进入工作台或创建任务。
              </p>
            ) : null}
          </section>

          <section className="workbench-panel stack-lg">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Recent Tasks</p>
                <h2>最近任务 / 继续查看</h2>
              </div>
            </div>

            {recentTasks.length ? (
              <div className="recent-task-list">
                {recentTasks.map((task) => (
                  <Link
                    className={`recent-task-item ${ACTIVE_TASK_STATUSES.has(task.status) ? "is-live" : ""}`}
                    href={`/tasks/${task.id}`}
                    key={task.id}
                  >
                    <div className="recent-task-head">
                      <strong>{TASK_OPTIONS.find((item) => item.value === task.taskType)?.label ?? task.taskType}</strong>
                      <span className={`status-pill ${taskStatusTone(task.status)}`}>{task.status}</span>
                    </div>
                    <p>{task.query}</p>
                    <div className="recent-task-meta">
                      <span>{task.documentType || task.capabilityMode}</span>
                      <span>{formatTime(task.updatedAt)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="muted">暂无最近任务。</p>
            )}
          </section>
        </aside>
      </section>

      <section className="workbench-panel stack-lg boundary-panel">
        <div>
          <p className="eyebrow">Capability Boundary</p>
          <h2>能力边界说明</h2>
        </div>
        <div className="boundary-grid">
          {CAPABILITY_BOUNDARY.map((item) => (
            <article className="boundary-item subtle" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
