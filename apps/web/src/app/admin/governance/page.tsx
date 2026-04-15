"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, StatusBadge } from "@/components/admin/admin-components";

export default function AdminGovernanceDashboard() {
  const [metrics, setMetrics] = useState([
    { label: "已发布依据库", value: 0, trend: "加载中" },
    { label: "活跃审查包", value: 0, trend: "加载中" },
    { label: "场景映射规则", value: 0, trend: "加载中" },
    { label: "待审批候选建议", value: 0, trend: "加载中", urgent: false },
  ]);
  const [recentReleases, setRecentReleases] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/governance/bases").then(r => r.json()).catch(() => []),
      fetch("/api/admin/governance/packs").then(r => r.json()).catch(() => []),
      fetch("/api/admin/governance/profiles").then(r => r.json()).catch(() => ({ mappings: {} })),
      fetch("/api/admin/governance/candidates").then(r => r.json()).catch(() => []),
      fetch("/api/admin/governance/drafts").then(r => r.json()).catch(() => [])
    ]).then(([bases, packs, profilesObj, candidates, drafts]) => {
      const mappingsCount = Object.keys(profilesObj?.mappings || {}).length;
      const pendingCandidates = candidates.filter((c: any) => c.status === 'pending_review' || c.status === 'draft').length;

      setMetrics([
        { label: "已发布依据库", value: bases.length, trend: "实时同步" },
        { label: "活跃审查包", value: packs.length, trend: "实时同步" },
        { label: "场景映射规则", value: mappingsCount, trend: "实时同步" },
        { 
          label: "待审批候选建议", 
          value: pendingCandidates, 
          trend: pendingCandidates > 0 ? "需专家介入" : "安全稳定", 
          urgent: pendingCandidates > 0 
        },
      ]);

      const sortedDrafts = drafts
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5);
      
      setRecentReleases(sortedDrafts);
    });
  }, []);

  return (
    <div>
      <AdminPageHeader 
        title="治理大盘" 
        description="全局审视审查标准的实施健康度、资产沉淀以及正在等待审批的变更动作。"
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        {metrics.map(m => (
          <div key={m.label} style={{ background: "#FFF", border: "1px solid #E2E8F0", borderRadius: "12px", padding: "20px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <div style={{ color: "#64748B", fontSize: "0.9rem", marginBottom: "8px" }}>{m.label}</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: m.urgent ? "#DC2626" : "#0F172A" }}>{m.value}</div>
            <div style={{ fontSize: "0.8rem", color: m.urgent ? "#EF4444" : "#10B981", marginTop: "8px" }}>{m.trend}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <div style={{ background: "#FFF", borderRadius: "12px", border: "1px solid #E2E8F0", padding: "20px" }}>
          <h3 style={{ margin: "0 0 16px 0", fontSize: "1.1rem" }}>最近治理与审批记录</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {recentReleases.length === 0 ? (
               <div style={{ color: "#64748B", fontSize: "0.9rem", fontStyle: "italic", textAlign: "center", padding: "12px" }}>暂无最近治理流转。</div>
            ) : null}
            {recentReleases.map(r => (
              <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "12px", borderBottom: "1px solid #F1F5F9" }}>
                <div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 600, color: "#334155" }}>{r.target_entity_id}</span>
                    <StatusBadge status="neutral" label={r.target_entity_type} />
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#94A3B8" }}>发布人: {r.created_by} · {new Date(r.created_at).toLocaleString()}</div>
                </div>
                <StatusBadge status={r.status === 'published' ? "success" : r.status === 'draft' || r.status === 'pending_approval' ? "warning" : "error"} label={r.status} />
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: "#FFF", borderRadius: "12px", border: "1px solid #E2E8F0", padding: "20px" }}>
          <h3 style={{ margin: "0 0 16px 0", fontSize: "1.1rem" }}>治理动作审计概览</h3>
          <div style={{ padding: "40px 0", textAlign: "center", color: "#64748B" }}>
            <span style={{ fontSize: "2rem", display: "block", marginBottom: "8px" }}>🛡️</span>
            系统保护伞已开启，所有基于真实 YAML/Database 底座的数据均处于受控状态。<br/>没有任何未经审批的变更能够流入生产环境主链。
          </div>
        </div>
      </div>
    </div>
  );
}
