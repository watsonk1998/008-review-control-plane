"use client";

import { useEffect, useState } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminEmptyState, JsonConfigEditor } from "@/components/admin/admin-components";

export default function RulePacksAdminPage() {
  const [rulePacks, setRulePacks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorData, setEditorData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/admin/governance/rule-packs")
      .then(r => r.json())
      .then(d => {
        setRulePacks(d);
        setLoading(false);
      });
  }, []);

  const handleEditAll = () => {
    const payload: any = {};
    rulePacks.forEach((rp: any) => {
      payload[rp.rule_pack_id] = rp;
    });
    setEditorData(payload);
    setEditorOpen(true);
  };

  const handleSave = async (newData: any) => {
    const res = await fetch("/api/admin/governance/rule-packs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newData)
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const r = await fetch("/api/admin/governance/rule-packs");
    const d = await r.json();
    setRulePacks(d);
  };

  return (
    <div>
      <AdminPageHeader 
        title="规则集配置 (Rule Packs)" 
        description="最细粒度的单条审查规则集合，包含具体的验证Prompt和问题提示逻辑。直接存储于 YAML 真理源。"
      >
        <button className="primary-button" onClick={handleEditAll}>可视化全量编辑规则集</button>
      </AdminPageHeader>

      <AdminFilterBar>
        <input type="text" placeholder="搜索规则集名称 / ID..." style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px", width: "300px" }} />
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.95rem" }}>
          <thead style={{ background: "#F1F5F9", textAlign: "left", color: "#475569" }}>
            <tr>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>规则集 ID / 标识</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>显示名称</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>检查项数量</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0" }}>状态</th>
              <th style={{ padding: "12px 16px", fontWeight: 600, borderBottom: "1px solid #E2E8F0", textAlign: "right" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {rulePacks.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "#94A3B8" }}>
                   {loading ? "正在加载底层真实数据..." : "暂无规则集数据。请通过上方进行新增。"}
                </td>
              </tr>
            ) : rulePacks.map(rp => (
              <tr key={rp.rule_pack_id} style={{ borderBottom: "1px solid #E2E8F0" }}>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#334155" }}>{rp.rule_pack_id}</td>
                <td style={{ padding: "12px 16px", fontWeight: 500 }}>{rp.display_name}</td>
                <td style={{ padding: "12px 16px" }}>{rp.checks?.length || 0} 项</td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge status={rp.status === "active" ? "success" : "neutral"} label={rp.status === "active" ? "生效中" : rp.status || "草稿"} />
                </td>
                <td style={{ padding: "12px 16px", textAlign: "right" }}>
                  <button style={{ color: "#2563EB", background: "none", border: "none", cursor: "pointer", fontSize: "0.9rem" }} onClick={handleEditAll}>查看详情/编辑</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JsonConfigEditor
        title="规则集全量大纲 (Rule Pack Registry)"
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        initialData={editorData}
        onSave={handleSave}
      />
    </div>
  );
}
