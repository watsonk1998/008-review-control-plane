"use client";

import { useState, useEffect } from "react";

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  
  // Form state
  const [profileId, setProfileId] = useState("");
  const [candidateType, setCandidateType] = useState("rule_note");
  const [content, setContent] = useState("");

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/governance/candidates");
      if (res.ok) {
        const data = await res.json();
        setCandidates(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/admin/governance/candidates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_id: profileId,
          candidate_type: candidateType,
          content,
          source: "manual"
        })
      });
      if (res.ok) {
        setFormOpen(false);
        setProfileId("");
        setContent("");
        loadCandidates();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStatusChange = async (id: string, newStatus: string) => {
    try {
      await fetch(`/api/admin/governance/candidates/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      loadCandidates();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2>💡 候选建议池 (Candidate Pool)</h2>
        <button 
          onClick={() => setFormOpen(!formOpen)}
          style={{ padding: "0.5rem 1rem", backgroundColor: "var(--primary-color)", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
        >
          {formOpen ? "取消" : "新增手工建议"}
        </button>
      </div>

      <div style={{ padding: "1rem", backgroundColor: "var(--info-bg, #e2e3e5)", color: "#383d41", borderRadius: "8px", marginBottom: "2rem" }}>
        <p><strong>治理原则：</strong>候选建议不会自动生成 YAML 配置文件。管理员需通过审批状态进行跟踪，并在审批通过后（`approved_for_transcription`），人工将建议合并至正式的 YAML Registry 物料库中以生效。</p>
      </div>

      {formOpen && (
        <form onSubmit={handleSubmit} style={{ border: "1px solid var(--border)", padding: "1rem", borderRadius: "8px", marginBottom: "2rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>Profile ID (关联场景)</label>
            <input required value={profileId} onChange={e => setProfileId(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} placeholder="e.g. general_construction_scheme" />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>建议类型</label>
            <select value={candidateType} onChange={e => setCandidateType(e.target.value)} style={{ width: "100%", padding: "0.5rem" }}>
              <option value="rule_note">规则补充/修正 (rule_note)</option>
              <option value="template_hint">模板调整引导 (template_hint)</option>
              <option value="evidence_heuristic">审查证据启发 (evidence_heuristic)</option>
              <option value="disambiguation_hint">消歧义提示 (disambiguation_hint)</option>
            </select>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>建议内容</label>
            <textarea required value={content} onChange={e => setContent(e.target.value)} style={{ width: "100%", padding: "0.5rem", minHeight: "100px" }} placeholder="请输入发现的业务规则遗漏或审核经验..."></textarea>
          </div>
          <button type="submit" style={{ alignSelf: "flex-start", padding: "0.5rem 2rem", backgroundColor: "var(--primary-color)", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}>保存为草稿</button>
        </form>
      )}

      {loading ? (
        <p>加载中...</p>
      ) : candidates.length === 0 ? (
        <p className="muted">当前候选池为空。</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {candidates.map(c => (
            <div key={c.id} style={{ border: "1px solid var(--border)", borderRadius: "8px", padding: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
                <div>
                  <span style={{ fontWeight: "bold", marginRight: "1rem" }}>{c.candidate_type}</span>
                  <span style={{ fontSize: "0.9rem", color: "#666" }}>来源: {c.source} | Profile: {c.profile_id}</span>
                </div>
                <div>
                  <span style={{ padding: "0.2rem 0.5rem", backgroundColor: "#eee", borderRadius: "4px", fontSize: "0.9rem", marginRight: "1rem" }}>
                    状态: {c.status}
                  </span>
                  <select 
                    value={c.status} 
                    onChange={e => handleStatusChange(c.id, e.target.value)}
                    style={{ padding: "0.2rem" }}
                  >
                    <option value="draft">草稿 (draft)</option>
                    <option value="pending_review">待审阅 (pending_review)</option>
                    <option value="approved_for_transcription">批准转写 (approved_for_transcription)</option>
                    <option value="transcribed">已转写至YAML (transcribed)</option>
                    <option value="archived">已归档 (archived)</option>
                    <option value="rejected">已拒绝 (rejected)</option>
                  </select>
                </div>
              </div>
              <pre style={{ backgroundColor: "#f8f9fa", padding: "1rem", borderRadius: "4px", whiteSpace: "pre-wrap", wordWrap: "break-word" }}>
                {c.content}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
