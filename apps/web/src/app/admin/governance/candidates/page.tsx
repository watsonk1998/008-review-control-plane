"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminDrawer, SectionTitle, KeyValueRow } from "@/components/admin/admin-components";

export default function CandidatesAdminPage() {
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/governance/candidates")
      .then(res => res.json())
      .then(data => {
        setCandidates(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <AdminPageHeader 
        title="候选建议池" 
        description="承接脱机仿真跑批或人工抽检产生的待补充规则，经安全审查后才允许擢升挂载到主包链路上。"
      >
        <button className="primary-button">手工录入候选</button>
      </AdminPageHeader>

      <AdminFilterBar>
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>全部来源</option>
          <option>离线仿真学习提取</option>
          <option>专家人工驳回提取</option>
          <option>manual</option>
          <option>simulation</option>
        </select>
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>待处理状态</option>
          <option>草稿 (draft)</option>
          <option>待审核 (pending_review)</option>
          <option>已打回 (rejected)</option>
        </select>
        <button className="secondary-button" style={{ marginLeft: "auto" }}>批量转译规则</button>
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            <tr>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>内部追踪号</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>影响域 (profile_id)</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>建议类型</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>抽取源</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>审核状态</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>上报时间</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {(loading || candidates.length === 0) && (
               <tr>
                 <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                   {loading ? "正在加载底层数据库..." : "暂无候选建议数据。"}
                 </td>
               </tr>
            )}
            {candidates.map((c, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#64748B" }}>{c.id}</td>
                <td style={{ padding: "12px 16px", color: "#64748B", fontWeight: 500 }}>{c.profile_id}</td>
                <td style={{ padding: "12px 16px", color: "#64748B" }}>{c.candidate_type}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{ padding: "2px 6px", background: c.source === "manual" ? "#FEF08A" : "#E0E7FF", color: c.source === "manual" ? "#854D0E" : "#3730A3", borderRadius: "4px", fontSize: "0.85rem" }}>
                    {c.source}
                  </span>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge 
                    status={c.status === 'pending_review' ? 'warning' : c.status === 'approved_for_transcription' ? 'success' : c.status === 'rejected' ? 'error' : 'neutral'} 
                    label={c.status} 
                  />
                </td>
                <td style={{ padding: "12px 16px", color: "#64748B", fontSize: "0.9rem" }}>{new Date(c.created_at).toLocaleString()}</td>
                <td style={{ padding: "12px 16px" }}>
                  <button onClick={() => setSelectedCandidate(c)} style={{ background: "none", border: "none", color: "#0284C7", cursor: "pointer", fontWeight: 500 }}>专家介入</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AdminDrawer title="治理候选评审单" open={!!selectedCandidate} onClose={() => setSelectedCandidate(null)}>
        {selectedCandidate && (
          <div className="stack-lg">
            <SectionTitle title="候选上下文" />
            <div style={{ background: "#F8FAFC", padding: "16px", borderRadius: "8px", border: "1px solid #E2E8F0" }}>
              <KeyValueRow label="追踪编码" value={<span style={{fontFamily:"monospace"}}>{selectedCandidate.id}</span>} />
              <KeyValueRow label="方案锚点 (profile_id)" value={selectedCandidate.profile_id} />
              <KeyValueRow label="建议类型" value={selectedCandidate.candidate_type} />
              <KeyValueRow label="反馈源" value={selectedCandidate.source} />
              <KeyValueRow label="提交记录" value={`${selectedCandidate.created_by} @ ${new Date(selectedCandidate.created_at).toLocaleString()}`} />
            </div>

            <div style={{ marginTop: "24px" }}>
              <SectionTitle title="学习提炼内容 / JSON Load" />
              <pre style={{ background: "#F1F5F9", padding: "16px", borderRadius: "8px", border: "1px solid #E2E8F0", color: "#0F172A", lineHeight: 1.5, fontSize: "0.85rem", overflowX: "auto", whiteSpace: "pre-wrap" }}>
                {selectedCandidate.content}
              </pre>
            </div>

            <div style={{ marginTop: "24px" }}>
              <SectionTitle title="目标挂载规则包" />
              <select style={{ width: "100%", padding: "10px", border: "1px solid #CBD5E1", borderRadius: "6px", background: "#F8FAFC" }} disabled>
                <option>{selectedCandidate.profile_id} (待路由分发)</option>
              </select>
            </div>

            {selectedCandidate.reviewer_notes && (
              <div style={{ marginTop: "24px" }}>
                <SectionTitle title="审核意见" />
                <div style={{ background: "#FEF2F2", padding: "12px", borderRadius: "6px", color: "#991B1B", fontSize: "0.9rem" }}>
                  {selectedCandidate.reviewer_notes}
                </div>
              </div>
            )}

            <div style={{ marginTop: "32px", borderTop: "1px solid #E2E8F0", paddingTop: "16px", display: "flex", gap: "12px" }}>
              <button className="primary-button" style={{ flex: 1 }}>转写合并 (Approve)</button>
              <button className="secondary-button" style={{ flex: 1, color: "#DC2626", borderColor: "#FECACA", background: "#FEF2F2" }}>驳回舍弃 (Reject)</button>
            </div>
          </div>
        )}
      </AdminDrawer>
    </div>
  );
}
