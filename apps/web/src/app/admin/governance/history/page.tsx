"use client";

import { useEffect, useState } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge } from "@/components/admin/admin-components";

export default function HistoryAdminPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/governance/history")
      .then(r => r.json())
      .then(d => {
        setLogs(d);
        setLoading(false);
      })
      .catch(e => console.error(e));
  }, []);

  return (
    <div>
      <AdminPageHeader 
        title="配置变更记录 (History & Rollback)" 
        description="追溯所有在可视化编辑台中发起的直接 YAML 修改操作，支持操作审计与基线对齐。"
      />

      <AdminFilterBar>
        <input type="text" placeholder="按实体 ID 搜索..." style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }} />
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.95rem" }}>
          <thead style={{ background: "#F1F5F9", textAlign: "left", color: "#475569" }}>
            <tr>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>记录 ID</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>操作对象</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>操作类型</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>操作时间</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0", textAlign: "right" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "#94A3B8" }}>
                   {loading ? "正在加载操作流水..." : "暂无历史变更记录。"}
                </td>
              </tr>
            ) : logs.map(log => (
              <tr key={log.id} style={{ borderBottom: "1px solid #E2E8F0" }}>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#64748B", fontSize: "0.85rem" }}>{log.id.slice(0, 8)}...</td>
                <td style={{ padding: "12px 16px", fontWeight: 500, color: "#334155" }}>
                  {log.entity_id} <span style={{ color: "#94A3B8", fontSize: "0.85rem", marginLeft: "8px" }}>({log.entity_type})</span>
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge status={log.action === "update" ? "info" : "neutral"} label={log.action} />
                </td>
                <td style={{ padding: "12px 16px" }}>{new Date(log.created_at).toLocaleString('zh-CN')}</td>
                <td style={{ padding: "12px 16px", textAlign: "right" }}>
                  {log.changes?.backup_file && (
                    <button style={{ color: "#DC2626", background: "none", border: "none", cursor: "pointer", fontSize: "0.85rem" }} onClick={() => alert("目前支持手动前往服务端拉回备份: " + log.changes.backup_file)}>尝试回滚 (撤销)</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
