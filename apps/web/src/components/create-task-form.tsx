"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { StructuredReviewForm } from "./structured-review-form";
import { createTask, uploadDocument } from "@/lib/api";
import type {
  CapabilityMode,
  CreateTaskRequest,
  FixtureRecord,
  SupportScopeResponse,
  TaskType,
} from "@/types/control-plane";

const TASK_OPTIONS: Array<{ value: TaskType; label: string; hint: string }> = [
  { value: "structured_review", label: "正式审查", hint: "执行正式结构化主链审查" },
  { value: "review_assist", label: "审查辅助", hint: "仅总结要点，无审查结论" },
  { value: "knowledge_qa", label: "知识问答", hint: "调用 DeepTutor 问答" },
  { value: "document_research", label: "文档研究", hint: "提取事实特征与研判" },
  { value: "deep_research", label: "深度研究", hint: "GPT Researcher 产出报告" },
];

const CAPABILITY_OPTIONS: Array<{ value: CapabilityMode; label: string; hint: string }> = [
  { value: "auto", label: "Auto", hint: "总控决定链路" },
  { value: "deeptutor", label: "DeepTutor", hint: "问答与解释" },
  { value: "gpt_researcher", label: "GPT Researcher", hint: "报告与来源" },
  { value: "fast", label: "FastGPT Chunks", hint: "知识片段化" },
  { value: "llm_only", label: "LLM Only", hint: "跳过检索" },
];

export function CreateTaskForm({
  fixtures,
  supportScope,
}: {
  fixtures: FixtureRecord[];
  supportScope: SupportScopeResponse | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sourceUrlInput, setSourceUrlInput] = useState("");
  const [policyPackInput, setPolicyPackInput] = useState("");

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
    [form.taskType]
  );

  const selectedCapability = useMemo(
    () => CAPABILITY_OPTIONS.find((item) => item.value === form.capabilityMode) ?? CAPABILITY_OPTIONS[0],
    [form.capabilityMode]
  );

  const canSubmit = Boolean(form.query.trim()) && (form.taskType !== "structured_review" || Boolean(form.fixtureId || form.sourceDocumentRef));

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
      const structuredPolicyPackIds = policyPackInput.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean);

      const task = await createTask({
        ...form,
        fixtureId: form.taskType === "structured_review" && form.sourceDocumentRef ? undefined : form.fixtureId || undefined,
        sourceDocumentRef: form.taskType === "structured_review" && form.sourceDocumentRef ? form.sourceDocumentRef : undefined,
        datasetId: form.datasetId || undefined,
        collectionId: form.collectionId || undefined,
        sourceUrls: sourceUrlInput.split(/\n+/).map((item) => item.trim()).filter(Boolean),
        documentType: form.taskType === "structured_review" ? form.documentType || "construction_org" : undefined,
        disciplineTags: form.taskType === "structured_review" ? form.disciplineTags || [] : undefined,
        strictMode: form.taskType === "structured_review" ? form.strictMode ?? true : undefined,
        policyPackIds: form.taskType === "structured_review" ? structuredPolicyPackIds : undefined,
      });

      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-panel stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">任务编排与调度</p>
          <h2 className="section-title">发起核查任务</h2>
        </div>
        <p className="muted small">{selectedTask.hint}</p>
      </div>

      <div className="task-type-toggle" role="tablist">
        {TASK_OPTIONS.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={form.taskType === item.value}
            className={`task-type-chip ${form.taskType === item.value ? "is-active" : ""}`}
            onClick={() => setForm((current) => ({ ...current, taskType: item.value, capabilityMode: item.value === "structured_review" ? "auto" : current.capabilityMode }))}
          >
            {item.label}
          </button>
        ))}
      </div>

      <form className="task-form stack-lg" onSubmit={handleSubmit}>
        {form.taskType !== "structured_review" && (
          <label className="field">
            <span>能力编排引擎</span>
            <select
              value={form.capabilityMode}
              onChange={(e) => setForm((curr) => ({ ...curr, capabilityMode: e.target.value as CapabilityMode }))}
            >
              {CAPABILITY_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
            <small>{selectedCapability.hint}</small>
          </label>
        )}

        <label className="field">
          <span>{form.taskType === "structured_review" ? "结构化审查指令" : "查询 / 任务描述"}</span>
          <textarea
            rows={form.taskType === "structured_review" ? 4 : 5}
            value={form.query}
            onChange={(e) => setForm((curr) => ({ ...curr, query: e.target.value }))}
          />
        </label>

        <label className="field">
          <span>选择基准样本 (Fixture)</span>
          <select
            value={form.fixtureId || ""}
            onChange={(e) => setForm((curr) => ({ ...curr, fixtureId: e.target.value, sourceDocumentRef: e.target.value ? undefined : curr.sourceDocumentRef }))}
          >
            <option value="">上传自定义文档</option>
            {Object.entries(groupedFixtures).map(([domain, items]) => (
              <optgroup key={domain} label={domain}>
                {items.map((fixture) => (
                  <option key={fixture.id} value={fixture.id}>{fixture.title}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        {form.taskType === "structured_review" && !form.fixtureId && (
          <div className="field">
            <span>目标审查文档</span>
            {form.sourceDocumentRef ? (
              <div className="doc-ready-card" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'var(--healthy-bg)', border: '1px solid var(--healthy-border)', borderRadius: '8px', color: 'var(--healthy)' }}>
                <svg fill="currentColor" viewBox="0 0 20 20" style={{ width: '24px', height: '24px' }}>
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="doc-ready-info">
                  <strong style={{ display: 'block', fontSize: '0.9rem' }}>文档已安全上传并在系统中就绪</strong>
                  <span>{form.sourceDocumentRef.displayName || form.sourceDocumentRef.fileName}</span>
                </div>
                <button type="button" className="ghost-button" style={{ marginLeft: "auto", padding: "4px 8px", fontSize: "0.8rem" }} onClick={() => setForm(c => ({...c, sourceDocumentRef: undefined}))}>撤销</button>
              </div>
            ) : (
              <label className={`upload-zone ${uploadingDocument ? "is-uploading" : ""}`} style={{ border: '2px dashed var(--card-border)', borderRadius: '12px', padding: '32px 24px', textAlign: 'center', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', cursor: uploadingDocument ? 'wait' : 'pointer' }}>
                {uploadingDocument ? (
                  <>
                    <div className="spinner" style={{ width: '24px', height: '24px', borderRadius: '50%', border: '3px solid rgba(99,102,241,0.2)', borderTopColor: '#6366F1' }} />
                    <div className="upload-text">
                      <strong style={{ display: 'block', marginBottom: '4px' }}>正在通过加密通道上传并启动解析引擎</strong>
                      <span style={{ fontSize: '0.85rem' }}>请稍候，网络传输可能需要十几秒...</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="upload-icon" style={{ width: '48px', height: '48px', borderRadius: '50%', border: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ width: '24px', height: '24px' }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div className="upload-text">
                      <strong style={{ display: 'block', marginBottom: '4px' }}>点击选择或拖拽文件到这里上传</strong>
                      <span style={{ fontSize: '0.85rem' }}>强制要求 .docx 或 .pdf 格式。端到端直传</span>
                    </div>
                  </>
                )}
                <input
                  type="file"
                  accept=".docx,.pdf,.md,.txt"
                  disabled={uploadingDocument}
                  style={{ position: 'absolute', inset: '0', opacity: '0', cursor: uploadingDocument ? 'wait' : 'pointer' }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) { handleDocumentUpload(file); e.currentTarget.value = ""; }
                  }}
                />
              </label>
            )}
          </div>
        )}

        <StructuredReviewForm form={form} setForm={setForm} supportScope={supportScope} />

        <div className="toggle-row">
          <button type="button" className="ghost-button" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "- 收起高级配置" : "+ 展开高级配置"}
          </button>
        </div>

        {showAdvanced && (
          <div className="advanced-panel stack-lg">
             <label className="field">
               <span>覆盖策略集 (Policy Packs)</span>
               <textarea rows={2} value={policyPackInput} onChange={(e) => setPolicyPackInput(e.target.value)} placeholder="留空为自动匹配" />
             </label>
             <label className="checkbox-row inline-check">
               <input type="checkbox" checked={form.useWeb} onChange={(e) => setForm((c) => ({ ...c, useWeb: e.target.checked }))} />
               <span>启用 GPT Researcher 联网功能</span>
             </label>
             <label className="checkbox-row inline-check">
               <input type="checkbox" checked={form.debug} onChange={(e) => setForm((c) => ({ ...c, debug: e.target.checked }))} />
               <span>开启诊断模式 (Debug Logs)</span>
             </label>
          </div>
        )}

        {error && <p className="error-text">{error}</p>}
        <div className="form-footer" style={{ marginTop: "12px" }}>
          <button type="submit" className="primary-button" disabled={submitting || !canSubmit}>
            {submitting ? "系统调度中..." : "启动审查引擎 [Enter]"}
          </button>
        </div>
      </form>
    </div>
  );
}
