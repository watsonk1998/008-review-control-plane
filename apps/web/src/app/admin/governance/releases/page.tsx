"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminDrawer, SectionTitle, KeyValueRow } from "@/components/admin/admin-components";

export default function ReleasesAdminPage() {
  const [selectedRelease, setSelectedRelease] = useState<any>(null);
  const [releases, setReleases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/governance/drafts")
      .then(res => res.json())
      .then(data => {
        setReleases(data);
        if (data.length > 0) setSelectedRelease(data[0]);
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
        title="发布审批待办" 
        description="守护生产防线，任何依据、审查包或验证映射的变更必须经过审批队列在此统一放行。"
      />

      <div style={{ display: "flex", gap: "24px", alignItems: "flex-start" }}>
        
        {/* Left List */}
        <div style={{ width: "380px", flexShrink: 0, background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden", minHeight: "500px" }}>
          <div style={{ padding: "16px", background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: "1rem", color: "#334155" }}>流转队列</h3>
            <span style={{ background: "#EF4444", color: "#FFF", borderRadius: "999px", padding: "2px 8px", fontSize: "0.8rem", fontWeight: 600 }}>{releases.filter(r => r.status === 'pending_approval' || r.status === 'draft').length} 待办</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {(loading || releases.length === 0) && (
               <div style={{ padding: "24px", textAlign: "center", color: "#64748B", fontStyle: "italic" }}>
                 {loading ? "获取真实队列中..." : "队列为空。"}
               </div>
            )}
            {releases.map((r, i) => (
              <div 
                key={i} 
                onClick={() => setSelectedRelease(r)}
                style={{ 
                  padding: "16px", 
                  borderBottom: "1px solid #F1F5F9", 
                  cursor: "pointer", 
                  background: selectedRelease?.id === r.id ? "#F0F9FF" : "transparent" 
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontWeight: 600, color: "#0F172A", fontSize: "0.95rem" }}>{r.id.split('-').pop() || r.id}</span>
                    <StatusBadge status={r.status === 'pending_approval' || r.status === 'draft' ? 'warning' : r.status === 'published' ? 'success' : 'error'} label={r.target_entity_type} />
                  </div>
                  <span style={{ fontSize: "0.80rem", color: "#64748B" }}>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
                <div style={{ color: "#475569", fontSize: "0.9rem", marginBottom: "8px" }}>
                  {r.target_entity_id}
                </div>
                <div style={{ fontSize: "0.8rem", color: "#94A3B8" }}>
                  由 <strong>{r.created_by}</strong> 提交申请
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Detail Pane */}
        {selectedRelease ? (
          <div style={{ flex: 1, background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", padding: "24px", minHeight: "500px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }}>
              <div>
                <h2 style={{ margin: "0 0 8px 0", fontSize: "1.5rem" }}>{selectedRelease.target_entity_id}</h2>
                <div style={{ display: "flex", gap: "12px", color: "#64748B", fontSize: "0.9rem" }}>
                  <span>实体类型：{selectedRelease.target_entity_type}</span>
                  <span>申请人：{selectedRelease.created_by}</span>
                </div>
              </div>
              <StatusBadge status={selectedRelease.status === 'pending_approval' || selectedRelease.status === 'draft' ? 'warning' : selectedRelease.status === 'published' ? 'success' : 'neutral'} label={selectedRelease.status} />
            </div>

            <SectionTitle title="数据对比摘要 (Diff / JSON Payload)" />
            <div style={{ fontFamily: "monospace", fontSize: "0.85rem", background: "#1E293B", color: "#34D399", padding: "16px", borderRadius: "8px", whiteSpace: "pre-wrap", marginBottom: "32px", overflowX: "auto", maxHeight: "300px" }}>
              {JSON.stringify(selectedRelease.proposed_changes, null, 2)}
            </div>

            {(selectedRelease.status === 'pending_approval' || selectedRelease.status === 'draft') && (
              <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: "24px" }}>
                <SectionTitle title="操作决断" />
                <textarea 
                  placeholder="填写安全审计放行意见..." 
                  style={{ width: "100%", padding: "12px", borderRadius: "6px", border: "1px solid #CBD5E1", minHeight: "80px", marginBottom: "16px" }}
                />
                <div style={{ display: "flex", gap: "16px" }}>
                  <button className="primary-button" style={{ background: "#059669", padding: "10px 24px" }}>正式发布入网 (Merge)</button>
                  <button className="secondary-button" style={{ color: "#DC2626", borderColor: "#FECACA", background: "#FEF2F2", padding: "10px 24px" }}>阻断打回 (Reject)</button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#F8FAFC", borderRadius: "8px", border: "1px dashed #CBD5E1", minHeight: "500px", color: "#94A3B8" }}>
            {loading ? '正在加载数据详情...' : '请在左侧选择一条审核事件查看详细变更'}
          </div>
        )}

      </div>
    </div>
  );
}
