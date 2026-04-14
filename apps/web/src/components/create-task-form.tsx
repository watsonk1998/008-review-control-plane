"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { StructuredReviewForm } from "./structured-review-form";
import { createTask, uploadDocument } from "@/lib/api";
import type {
  CreateTaskRequest,
  ExternalIntegrationContext,
  ReviewModuleName,
  SupportScopeResponse,
} from "@/types/control-plane";

const MODULE_OPTIONS: Array<{ key: keyof ModuleState; value: ReviewModuleName; label: string }> = [
  { key: "docIntegrity", value: "structure_completeness", label: "章节完整性" },
  { key: "paramConsistency", value: "parameter_consistency", label: "参数一致性" },
  { key: "compliance", value: "legality_compliance", label: "合法合规性" },
  { key: "flowContinuity", value: "execution_continuity", label: "工序连贯性" },
  { key: "evidenceVerification", value: "evidence_validation", label: "证据验证" },
];

type ModuleState = {
  docIntegrity: boolean;
  paramConsistency: boolean;
  compliance: boolean;
  flowContinuity: boolean;
  evidenceVerification: boolean;
};

const HIDDEN_BASIS_KEYWORDS = ["监理工程师对停电施工方案的审核规则及要点"];

function filterBasisTitles(items: string[] | undefined) {
  return (items || []).filter((item) => !HIDDEN_BASIS_KEYWORDS.some((keyword) => item.includes(keyword)));
}

export function CreateTaskForm({
  supportScope,
  externalContext,
}: {
  supportScope: SupportScopeResponse | null;
  externalContext?: ExternalIntegrationContext;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [moduleState, setModuleState] = useState<ModuleState>({
    docIntegrity: true,
    paramConsistency: true,
    compliance: true,
    flowContinuity: true,
    evidenceVerification: true,
  });

  const [form, setForm] = useState<CreateTaskRequest>({
    taskType: "structured_review",
    capabilityMode: "auto",
    query: "",
    fixtureId: "",
    sourceDocumentRef: undefined,
    datasetId: "",
    collectionId: "",
    useWeb: false,
    debug: false,
    sourceUrls: [],
    documentType: "distribution_network_special_scheme",
    disciplineTags: ["power_outage_work"],
    strictMode: true,
    policyPackIds: [],
    externalContext,
  });

  const canSubmit = Boolean(form.sourceDocumentRef);

  const selectedModules = useMemo(
    () => MODULE_OPTIONS.filter((item) => moduleState[item.key]).map((item) => item.value),
    [moduleState],
  );
  const disabledModules = useMemo(
    () => MODULE_OPTIONS.filter((item) => !moduleState[item.key]).map((item) => item.value),
    [moduleState],
  );
  const visibleBasisTitles = useMemo(
    () => filterBasisTitles(form.documentType ? supportScope?.basisMapping?.[form.documentType] : []),
    [form.documentType, supportScope],
  );

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

  function handleMockPlaceholderUpload() {
    alert("辅助资料上传槽位已预留，当前版本仅保留展示入口，后续将接入正式校验链路。");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const task = await createTask({
        ...form,
        fixtureId: undefined,
        sourceDocumentRef: form.sourceDocumentRef,
        reviewIntent: {
          enabled_modules: selectedModules,
          disabled_modules: disabledModules,
          focus_requirements: form.query
            .split(/\n+/)
            .map((item) => item.trim())
            .filter(Boolean),
        },
      });
      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务发起失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-panel stack-lg" style={{ borderRadius: "28px", padding: "40px 40px 32px", background: "#FFFFFF", boxShadow: "0 20px 60px rgba(15,23,42,0.05)", border: "1px solid rgba(15,23,42,0.06)" }}>
      <form className="task-form stack-lg" onSubmit={handleSubmit} style={{ gap: "36px", display: "flex", flexDirection: "column" }}>
        <section>
          <header style={{ marginBottom: "18px", paddingBottom: "16px", borderBottom: "1px solid #ECE7DF" }}>
            <h3 style={{ fontSize: "1.16rem", color: "#172033", fontWeight: 700 }}>1. 方案类型选择</h3>
            <p style={{ fontSize: "0.92rem", color: "#7A7A7A", marginTop: "6px" }}>选择方案类型后，系统将自动装配对应的审查规范与执行链路。</p>
          </header>
          <StructuredReviewForm form={form} setForm={setForm} supportScope={supportScope} />
        </section>

        <section>
          <header style={{ marginBottom: "18px", paddingBottom: "16px", borderBottom: "1px solid #ECE7DF" }}>
            <h3 style={{ fontSize: "1.16rem", color: "#172033", fontWeight: 700 }}>2. 上传资料</h3>
          </header>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.1fr) minmax(0,0.9fr)", gap: "22px" }}>
            <div style={{ background: "#F7F5F0", border: "1px solid #ECE7DF", borderRadius: "24px", padding: "24px" }}>
              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "0.98rem", fontWeight: 700, color: "#172033", display: "block" }}>待审主文件</span>
                <span style={{ fontSize: "0.82rem", color: "#7A7A7A" }}>上传本次需要审查的 PDF 或 DOCX 文件。</span>
              </div>

              {form.sourceDocumentRef ? (
                <div style={{ background: "#FFFFFF", border: "1px solid #D9E9D8", color: "#1F6F43", padding: "16px 18px", borderRadius: "18px", display: "flex", gap: "12px", alignItems: "center", boxShadow: "var(--shadow-sm)" }}>
                  <div style={{ width: 36, height: 36, borderRadius: 18, background: "#EDF8EF", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem" }}>✓</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "0.94rem", fontWeight: 600, color: "#172033", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {form.sourceDocumentRef.displayName || form.sourceDocumentRef.fileName}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#7A7A7A", marginTop: "2px" }}>文件已就绪，可直接发起审查</div>
                  </div>
                  <button type="button" className="ghost-button" onClick={() => setForm((c) => ({ ...c, sourceDocumentRef: undefined }))}>
                    更换
                  </button>
                </div>
              ) : (
                <label className={`upload-zone ${uploadingDocument ? "is-uploading" : ""}`} style={{ background: "#FFFFFF", border: "1px dashed #D4D0C8", borderRadius: "22px", minHeight: "192px" }}>
                  {uploadingDocument ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px", alignItems: "center" }}>
                      <div className="spinner" style={{ borderColor: "rgba(15, 23, 42, 0.08)", borderTopColor: "#172033", width: "28px", height: "28px" }} />
                      <span style={{ color: "#172033", fontSize: "0.95rem", fontWeight: 500 }}>正在上传并准备审查文件…</span>
                    </div>
                  ) : (
                    <>
                      <div className="upload-icon" style={{ width: 56, height: 56, borderRadius: 28, background: "#F6F3EE" }}>
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="24" height="24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.7} d="M12 16V4m0 0l-4 4m4-4l4 4M5 17v1a2 2 0 002 2h10a2 2 0 002-2v-1" />
                        </svg>
                      </div>
                      <strong style={{ color: "#1F2937", fontSize: "1rem", fontWeight: 600 }}>上传待审文件</strong>
                      <span style={{ color: "#7A7A7A", fontSize: "0.86rem" }}>支持 PDF / DOCX / Markdown / TXT</span>
                    </>
                  )}
                  <input type="file" accept=".docx,.pdf,.md,.txt" disabled={uploadingDocument} onChange={(e) => { const file = e.target.files?.[0]; if (file) { void handleDocumentUpload(file); e.currentTarget.value = ""; } }} />
                </label>
              )}
            </div>

            <div style={{ background: "#F7F5F0", border: "1px solid #ECE7DF", borderRadius: "24px", padding: "24px" }}>
              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "0.98rem", fontWeight: 700, color: "#172033", display: "block" }}>辅助资料</span>
                <span style={{ fontSize: "0.82rem", color: "#7A7A7A" }}>当前版本保留入口，后续会接入正式校验链路。</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {["项目主建合同", "施工执行图纸", "地质勘测详报"].map((label) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#FFFFFF", padding: "12px 16px", borderRadius: "16px", border: "1px solid #E7E2D8" }}>
                    <span style={{ fontSize: "0.92rem", color: "#475569" }}>{label}</span>
                    <button type="button" onClick={handleMockPlaceholderUpload} style={{ background: "transparent", border: "none", color: "#4A5870", fontWeight: 600 }}>上传</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section>
          <header style={{ marginBottom: "18px", paddingBottom: "16px", borderBottom: "1px solid #ECE7DF" }}>
            <h3 style={{ fontSize: "1.16rem", color: "#172033", fontWeight: 700 }}>3. 审查规则</h3>
          </header>

          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div>
              <strong style={{ fontSize: "0.96rem", color: "#334155", display: "block", marginBottom: "12px" }}>审查依据规范</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                {visibleBasisTitles.length ? visibleBasisTitles.map((basisTitle) => (
                  <div key={basisTitle} style={{ background: "#F5FAF6", border: "1px solid #D5E9D9", color: "#1F6F43", padding: "8px 14px", borderRadius: "999px", fontSize: "0.86rem", display: "inline-flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "0.78rem" }}>●</span>
                    <span style={{ fontWeight: 600 }}>{basisTitle}</span>
                  </div>
                )) : null}
                <div style={{ background: "#F5F3EE", border: "1px solid #E7E2D8", color: "#6B7280", padding: "8px 14px", borderRadius: "999px", fontSize: "0.86rem" }}>
                  已自动匹配审查依据规范
                </div>
              </div>
            </div>

            <div>
              <strong style={{ fontSize: "0.96rem", color: "#334155", display: "block", marginBottom: "14px" }}>审查模块</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: "12px" }}>
                {MODULE_OPTIONS.map((module) => {
                  const active = moduleState[module.key];
                  return (
                    <button
                      key={module.value}
                      type="button"
                      onClick={() => setModuleState((current) => ({ ...current, [module.key]: !current[module.key] }))}
                      style={{
                        borderRadius: "18px",
                        border: active ? "1px solid #D7D1C6" : "1px solid #ECE7DF",
                        background: active ? "#FFFFFF" : "#F8F5EF",
                        padding: "18px 14px",
                        textAlign: "left",
                        boxShadow: active ? "0 8px 20px rgba(15,23,42,0.05)" : "none",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <span style={{ width: 30, height: 30, borderRadius: 15, background: active ? "#172033" : "#EDE8DF", color: active ? "#FFFFFF" : "#6B7280", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "0.82rem", fontWeight: 700 }}>
                          {active ? "开" : "关"}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.94rem", fontWeight: 600, color: "#172033" }}>{module.label}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <strong style={{ fontSize: "0.96rem", color: "#334155", display: "block", marginBottom: "8px" }}>自定义规则</strong>
              <textarea
                rows={4}
                value={form.query}
                onChange={(e) => setForm((c) => ({ ...c, query: e.target.value }))}
                placeholder="可输入本次审查的专项关注点，例如：重点关注停复电窗口、反送电风险、作业票据闭环等。"
                style={{ width: "100%", padding: "14px 16px", borderRadius: "18px", border: "1px solid #E7E2D8", fontSize: "0.95rem", color: "#172033", background: "#FCFBF8", resize: "vertical", minHeight: "120px" }}
              />
            </div>
          </div>
        </section>

        {error ? <div style={{ background: "#FEF2F2", color: "#B91C1C", padding: "12px 14px", borderRadius: "14px", fontSize: "0.95rem" }}>{error}</div> : null}

        <div className="form-footer" style={{ borderTop: "1px solid #ECE7DF", paddingTop: "22px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
          <Link href="/tasks" style={{ fontSize: "0.92rem", color: "#4A5870", textDecoration: "none", fontWeight: 500 }}>查看历史审查记录</Link>
          <button type="submit" className="primary-button" disabled={submitting || !canSubmit} style={{ minWidth: "220px", padding: "15px 28px", fontSize: "1rem", borderRadius: "14px", background: "#172033" }}>
            {submitting ? "正在提交审查任务…" : "建果AI方案审查"}
          </button>
        </div>
      </form>
    </div>
  );
}
