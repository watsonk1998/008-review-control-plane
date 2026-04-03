"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createTask,
  fetchFixtures,
  fetchHealth,
  getApiBaseUrl,
} from "@/lib/api";
import type {
  CapabilityHealth,
  CapabilityMode,
  CreateTaskRequest,
  FixtureRecord,
  HealthResponse,
  TaskType,
} from "@/types/control-plane";

const TASK_OPTIONS: Array<{ value: TaskType; label: string; hint: string }> = [
  {
    value: "knowledge_qa",
    label: "知识问答",
    hint: "DeepResearchAgent 先规划，再调 Fast / DeepTutor / LLM。",
  },
  {
    value: "deep_research",
    label: "深度研究",
    hint: "DeepResearchAgent 路由 GPT Researcher 做研究报告。",
  },
  {
    value: "document_research",
    label: "文档研究",
    hint: "围绕本地 fixture 文档做研究与报告。",
  },
  {
    value: "review_assist",
    label: "审查辅助",
    hint: "辅助审查，不直接给正式审查结论。",
  },
  {
    value: "structured_review",
    label: "结构化正式审查",
    hint: "走 parse → facts → rules → evidence → report 的正式结构化审查链路。",
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

function statusTone(available: boolean) {
  return available ? "is-healthy" : "is-unhealthy";
}

export function HomeDashboard() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [fixtures, setFixtures] = useState<FixtureRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sourceUrlInput, setSourceUrlInput] = useState("");
  const [form, setForm] = useState<CreateTaskRequest>({
    taskType: "knowledge_qa",
    capabilityMode: "auto",
    query: "请说明施工组织设计中与安全生产管理相关的关键要求。",
    fixtureId: "",
    datasetId: "",
    collectionId: "",
    useWeb: false,
    debug: true,
    sourceUrls: [],
  });

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [healthData, fixtureData] = await Promise.all([
        fetchHealth(),
        fetchFixtures(),
      ]);
      setHealth(healthData);
      setFixtures(fixtureData);
      if (!form.fixtureId && fixtureData[0]) {
        setForm((current) => ({ ...current, fixtureId: fixtureData[0].id }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载系统状态失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const groupedFixtures = useMemo(() => {
    return fixtures.reduce<Record<string, FixtureRecord[]>>((acc, item) => {
      acc[item.domain] = acc[item.domain] || [];
      acc[item.domain].push(item);
      return acc;
    }, {});
  }, [fixtures]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const task = await createTask({
        ...form,
        fixtureId: form.fixtureId || undefined,
        datasetId: form.datasetId || undefined,
        collectionId: form.collectionId || undefined,
        sourceUrls: sourceUrlInput
          .split(/\n+/)
          .map((item) => item.trim())
          .filter(Boolean),
      });
      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="hero card">
        <div>
          <p className="eyebrow">008 · Review Control Plane</p>
          <h1>多能力总控编排平台</h1>
          <p className="hero-copy">
            这个 008 项目把 DeepResearchAgent 定位为 orchestration / control plane，
            统一前端入口、后端任务编排、DeepTutor / GPT Researcher / FastGPT / 本地
            LLM 接入。
          </p>
        </div>
        <div className="hero-aside">
          <div className="metric">
            <span>API Base</span>
            <strong>{getApiBaseUrl()}</strong>
          </div>
          <div className="metric">
            <span>Fixtures</span>
            <strong>{health?.fixtureCount ?? fixtures.length}</strong>
          </div>
        </div>
      </section>

      <section className="grid two-up">
        <div className="card stack-lg">
          <div className="section-heading">
            <div>
              <p className="eyebrow">System Health</p>
              <h2>能力与连接状态</h2>
            </div>
            <button
              className="ghost-button"
              onClick={() => void refresh()}
              type="button"
            >
              刷新
            </button>
          </div>

          {loading ? <p className="muted">正在加载健康状态…</p> : null}
          {error ? <p className="error-text">{error}</p> : null}

          <div className="stack-md">
            {health?.capabilities.map((capability: CapabilityHealth) => (
              <article key={capability.name} className="status-row">
                <div>
                  <div className="status-name">{capability.name}</div>
                  <p className="muted small">
                    {capability.detail || capability.mode}
                  </p>
                </div>
                <span
                  className={`status-pill ${statusTone(capability.available)}`}
                >
                  {capability.available ? "available" : "unavailable"}
                </span>
              </article>
            ))}
          </div>
        </div>

        <div className="card stack-lg">
          <div>
            <p className="eyebrow">Capability Boundary</p>
            <h2>能力边界说明</h2>
          </div>
          <div className="stack-md">
            {CAPABILITY_BOUNDARY.map((item) => (
              <article className="boundary-item" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="card stack-xl">
        <div>
          <p className="eyebrow">Create Task</p>
          <h2>发起新任务</h2>
          <p className="muted">
            每个任务都先进入 DeepResearchAgent-compatible runtime，
            再由总控层决定是否调用 Fast / DeepTutor / GPT Researcher / LLM。
          </p>
        </div>

        <form className="task-form" onSubmit={handleSubmit}>
          <div className="form-grid two-columns">
            <label className="field">
              <span>任务类型</span>
              <select
                value={form.taskType}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    taskType: event.target.value as TaskType,
                  }))
                }
              >
                {TASK_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <small>
                {TASK_OPTIONS.find((item) => item.value === form.taskType)?.hint}
              </small>
            </label>

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
              <small>
                {
                  CAPABILITY_OPTIONS.find(
                    (item) => item.value === form.capabilityMode,
                  )?.hint
                }
              </small>
            </label>
          </div>

          <label className="field">
            <span>查询 / 任务描述</span>
            <textarea
              rows={6}
              value={form.query}
              onChange={(event) =>
                setForm((current) => ({ ...current, query: event.target.value }))
              }
              placeholder="输入规范问题、研究任务或审查辅助要求"
            />
          </label>

          <label className="field">
            <span>Fixture 样本</span>
            <select
              value={form.fixtureId || ""}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  fixtureId: event.target.value,
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
            <small>document_research / review_assist 推荐选择 docx fixture。</small>
          </label>

          <label className="field">
            <span>Source URLs（可选，多行）</span>
            <textarea
              rows={3}
              value={sourceUrlInput}
              onChange={(event) => setSourceUrlInput(event.target.value)}
              placeholder={"https://example.com/source-a\nhttps://example.com/source-b"}
            />
          </label>

          <div className="toggle-row">
            <label className="checkbox-row">
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
            <label className="checkbox-row">
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
            <button
              className="ghost-button"
              onClick={() => setShowAdvanced((value) => !value)}
              type="button"
            >
              {showAdvanced ? "收起高级项" : "展开高级项"}
            </button>
          </div>

          {showAdvanced ? (
            <div className="form-grid two-columns advanced-panel">
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
          ) : null}

          <div className="form-footer">
            <p className="muted small">
              review_assist 仅输出辅助审查要点；structured_review 会输出 issues、matrices 与正式报告。
            </p>
            <button
              className="primary-button"
              disabled={submitting || !form.query.trim()}
              type="submit"
            >
              {submitting ? "正在创建任务…" : "创建任务并进入详情页"}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
