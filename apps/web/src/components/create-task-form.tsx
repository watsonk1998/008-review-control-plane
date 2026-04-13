"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { StructuredReviewForm } from "./structured-review-form";
import { createTask, uploadDocument } from "@/lib/api";
import type {
  CreateTaskRequest,
  FixtureRecord,
  SupportScopeResponse,
} from "@/types/control-plane";

export function CreateTaskForm({
  supportScope,
}: {
  fixtures: FixtureRecord[];
  supportScope: SupportScopeResponse | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingDocument, setUploadingDocument] = useState(false);

  // Mocks for modular functions
  const [moduleFuncs, setModuleFuncs] = useState({
    docIntegrity: true,
    paramConsistency: true,
    compliance: true,
    flowContinuity: false,
    evidenceVerification: false,
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
    documentType: "construction_org",
    disciplineTags: [],
    strictMode: true,
    policyPackIds: [],
  });

  const canSubmit = Boolean(form.sourceDocumentRef);
  const availablePacks = supportScope?.packs?.filter(p => p.readiness === "ready" || p.readiness === "official") || [];

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
    alert("该延展项目资料槽位功能（辅助证据上传）正在接入底层接口，目前已预留槽位但暂未激活。");
  }

  function togglePack(packId: string, checked: boolean) {
    setForm(curr => {
      const set = new Set(curr.policyPackIds);
      if (checked) set.add(packId);
      else set.delete(packId);
      return { ...curr, policyPackIds: Array.from(set) };
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      // 模块设置不写入实际 policy 阵列（避免污染 backend strict policy pack array）
      // 实际上仅在描述 query 处注入作为提示说明
      let finalQuery = form.query;
      const activedModules = [
        moduleFuncs.docIntegrity ? "章节完整性" : "",
        moduleFuncs.paramConsistency ? "参数一致性" : "",
        moduleFuncs.compliance ? "合法合规性" : "",
        moduleFuncs.flowContinuity ? "工序连贯性" : "",
        moduleFuncs.evidenceVerification ? "证据验证" : ""
      ].filter(Boolean);
      
      if (activedModules.length > 0) {
        finalQuery = `【期望检查动作】: ${activedModules.join(", ")}\n\n${finalQuery}`;
      }

      const task = await createTask({
        ...form,
        query: finalQuery,
        fixtureId: undefined,
        sourceDocumentRef: form.sourceDocumentRef,
      });

      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务发起失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="glass-panel stack-lg" style={{ border: "none", boxShadow: "0 1px 3px rgba(0,0,0,0.05)", borderRadius: "12px", background: "#FFFFFF", padding: "32px", width: "100%" }}>
      <form className="task-form stack-lg" onSubmit={handleSubmit} style={{ gap: "32px", display: "flex", flexDirection: "column" }}>

        {/* 1. 确定待审文件（选择方案类型） */}
        <section>
          <header style={{ marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
            <h3 style={{ fontSize: "1.1rem", color: "#1E293B", fontWeight: 600 }}>1. 确定待审文件（选择方案类型）</h3>
            <p style={{ fontSize: "0.85rem", color: "#64748B", marginTop: "4px" }}>级联分类选择目标审查域，系统将据此拉取基础规则</p>
          </header>
          <StructuredReviewForm form={form} setForm={setForm} supportScope={supportScope} />
        </section>

        {/* 2. 上传资料结构化阵列 */}
        <section>
          <header style={{ marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
            <h3 style={{ fontSize: "1.1rem", color: "#1E293B", fontWeight: 600 }}>2. 上传资料结构化阵列</h3>
          </header>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            {/* 待审主要文件对象 */}
            <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "20px" }}>
              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "#0F172A", display: "block" }}>待审主要文件对象 (必须提供)</span>
                <span style={{ fontSize: "0.8rem", color: "#64748B" }}>承载本次审查核验目标的主体文件（方案报告本身）</span>
              </div>
              
              {form.sourceDocumentRef ? (
                <div className="doc-ready-card" style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", color: "#15803D", padding: "16px", borderRadius: "6px", display: "flex", gap: "12px", alignItems: "center" }}>
                  <svg fill="currentColor" viewBox="0 0 20 20" style={{ width: 24, flexShrink: 0 }}>
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div className="doc-ready-info" style={{ flex: 1, minWidth: 0 }}>
                     <div style={{ fontSize: "0.9rem", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                       {form.sourceDocumentRef.displayName || form.sourceDocumentRef.fileName}
                     </div>
                  </div>
                  <button type="button" className="ghost-button" onClick={() => setForm(c => ({...c, sourceDocumentRef: undefined}))} style={{ padding: "4px 8px", fontSize: "0.85rem" }}>更换</button>
                </div>
              ) : (
                <label className={`upload-zone ${uploadingDocument ? "is-uploading" : ""}`} style={{ background: "#FFFFFF", border: "1px dashed #CBD5E1", padding: "24px", textAlign: "center", display: "block", borderRadius: "6px", cursor: "pointer" }}>
                  {uploadingDocument ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                      <div className="spinner" style={{ borderColor: "rgba(15, 23, 42, 0.1)", borderTopColor: "#0F172A", width: "24px", height: "24px" }} />
                      <span style={{ color: "#0F172A", fontSize: "0.9rem" }}>解析并上传中...</span>
                    </div>
                  ) : (
                     <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
                        <div style={{ color: "#475569" }}>
                          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width="24" height="24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                          </svg>
                        </div>
                        <strong style={{ color: "#334155", fontSize: "0.9rem" }}>上传 PDF 或 DOCX 文件</strong>
                     </div>
                  )}
                  <input
                    type="file"
                    accept=".docx,.pdf,.md,.txt"
                    disabled={uploadingDocument}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) { handleDocumentUpload(file); e.currentTarget.value = ""; }
                    }}
                    style={{ display: "none" }}
                  />
                </label>
              )}
            </div>

            {/* 随附延展项目资料 */}
            <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "20px" }}>
               <div style={{ marginBottom: "16px" }}>
                 <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "#0F172A", display: "block" }}>随附延展项目资料 (供参项)</span>
                 <span style={{ fontSize: "0.8rem", color: "#64748B" }}>接口预置槽位 (仅做占位展示，供后续验证使用)</span>
               </div>
               
               <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {["项目主建合同", "施工执行图纸", "地质勘测详报"].map((label) => (
                     <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#FFFFFF", padding: "10px 16px", borderRadius: "6px", border: "1px solid #E2E8F0" }}>
                       <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                         <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                         <span style={{ fontSize: "0.9rem", color: "#475569" }}>{label}</span>
                       </div>
                       <button type="button" onClick={handleMockPlaceholderUpload} style={{ background: "none", border: "none", fontSize: "0.85rem", color: "#2563EB", cursor: "pointer", fontWeight: 500 }}>
                         + 上传
                       </button>
                     </div>
                  ))}
               </div>
            </div>
          </div>
        </section>

        {/* 3. 风控审查规则框圈约束 */}
        <section>
          <header style={{ marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
            <h3 style={{ fontSize: "1.1rem", color: "#1E293B", fontWeight: 600 }}>3. 风控审查规则框圈约束</h3>
          </header>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            
            {/* 标准审查依据库 */}
            <div>
              <strong style={{ fontSize: "0.95rem", color: "#334155", display: "block", marginBottom: "12px" }}>标准审查依据库（智能联配、支持扩增）</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
                {availablePacks.map(pack => (
                  <label key={pack.packId} className="checkbox-row inline-check" style={{ background: "#F1F5F9", padding: "8px 12px", borderRadius: "6px", border: "1px solid #CBD5E1" }}>
                     <input type="checkbox" checked={form.policyPackIds.includes(pack.packId)} onChange={(e) => togglePack(pack.packId, e.target.checked)} />
                     <span style={{ fontSize: "0.85rem", color: "#0F172A" }}>{pack.label || pack.packId}</span>
                  </label>
                ))}
                
                <label className="checkbox-row inline-check" style={{ background: "#F8FAFC", padding: "8px 12px", borderRadius: "6px", border: "1px dashed #CBD5E1", cursor: "pointer", opacity: 0.7 }}>
                     <span style={{ fontSize: "0.85rem", color: "#64748B" }}>+ 本地标准附加拉起（预留入口）...</span>
                </label>
              </div>
            </div>

            {/* 审查动作模块集 */}
            <div>
              <strong style={{ fontSize: "0.95rem", color: "#334155", display: "block", marginBottom: "12px" }}>审查动作模块集 (五大功能开关)</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center" }}>
                 <label className="checkbox-row inline-check">
                   <input type="checkbox" checked={moduleFuncs.docIntegrity} onChange={(e) => setModuleFuncs(c => ({...c, docIntegrity: e.target.checked}))}/>
                   <span>章节完整性</span>
                 </label>
                 <label className="checkbox-row inline-check">
                   <input type="checkbox" checked={moduleFuncs.paramConsistency} onChange={(e) => setModuleFuncs(c => ({...c, paramConsistency: e.target.checked}))}/>
                   <span>参数一致性</span>
                 </label>
                 <label className="checkbox-row inline-check">
                   <input type="checkbox" checked={moduleFuncs.compliance} onChange={(e) => setModuleFuncs(c => ({...c, compliance: e.target.checked}))}/>
                   <span>合法合规性</span>
                 </label>
                 <label className="checkbox-row inline-check">
                   <input type="checkbox" checked={moduleFuncs.flowContinuity} onChange={(e) => setModuleFuncs(c => ({...c, flowContinuity: e.target.checked}))}/>
                   <span>工序连贯性</span>
                 </label>
                 <label className="checkbox-row inline-check">
                   <input type="checkbox" checked={moduleFuncs.evidenceVerification} onChange={(e) => setModuleFuncs(c => ({...c, evidenceVerification: e.target.checked}))}/>
                   <span>证据验证</span>
                 </label>
                 <span style={{ fontSize: "0.85rem", color: "#16A34A", display: "inline-flex", alignItems: "center", gap: "4px", marginLeft: "8px" }}>
                   ✅ 最终报告将严格依据此骨架生成
                 </span>
              </div>
            </div>

            {/* 用户重点要求指派区 */}
            <div>
               <strong style={{ fontSize: "0.95rem", color: "#334155", display: "block", marginBottom: "8px" }}>用户重点要求指派区 (聚焦单次特异性意图偏好)</strong>
               <textarea 
                  rows={3} 
                  value={form.query} 
                  onChange={(e) => setForm(c => ({...c, query: e.target.value}))} 
                  placeholder="用户重点任务/检查指向说明（非必填）：&#10;1. 比如：本次工程注意不能突破三区规定的绿化红线要求..." 
                  style={{ width: "100%", padding: "12px", borderRadius: "6px", border: "1px solid #CBD5E1", fontSize: "0.95rem", color: "#0F172A", background: "#F8FAFC", resize: "vertical" }}
               />
            </div>
          </div>
        </section>

        {error && <div style={{ background: "#FEF2F2", color: "#B91C1C", padding: "12px", borderRadius: "6px", fontSize: "0.95rem" }}>{error}</div>}
        
        {/* 4. 提交动作区 */}
        <div className="form-footer" style={{ borderTop: "1px solid #E2E8F0", paddingTop: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
             <Link href="/tasks" style={{ fontSize: "0.9rem", color: "#2563EB", textDecoration: "none" }}>查看最近任务记录及状态 →</Link>
          </div>
          <button type="submit" className="primary-button" disabled={submitting || !canSubmit} style={{ minWidth: "180px", padding: "14px 32px", fontSize: "1.05rem", background: "#0B192C", borderRadius: "6px", cursor: canSubmit ? "pointer" : "not-allowed" }}>
            {submitting ? "编译并提交..." : "编译并提交任务"}
          </button>
        </div>
      </form>
    </div>
  );
}

