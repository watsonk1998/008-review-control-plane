"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminDrawer, SectionTitle, KeyValueRow, JsonConfigEditor } from "@/components/admin/admin-components";

export default function ProfilesAdminPage() {
  const [selectedProfile, setSelectedProfile] = useState<any>(null);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  
  // For single-operator visual YAML editor
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorData, setEditorData] = useState<any>(null);

  const handleEditAll = () => {
    // profiles format is already a dictionary according to ProfileMappingDTO
    const payload: any = {};
    profiles.forEach((p: any) => {
      payload[p.profile_id] = {
        packs: p.packs,
        rule_packs: p.rule_packs
      };
    });
    setEditorData(payload);
    setEditorOpen(true);
  };

  const handleSave = async (newData: any) => {
    const res = await fetch("/api/admin/governance/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newData)
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err);
    }
    // Refresh
    const r = await fetch("/api/admin/governance/profiles");
    const d = await r.json();
    setProfiles(Object.keys(d.mappings || {}).map(k => ({ profile_id: k, ...d.mappings[k] })));
  };
useEffect(() => {
    fetch("/api/admin/governance/profiles")
      .then(res => res.json())
      .then(data => {
        if (data && data.mappings) {
          const arr = Object.entries(data.mappings).map(([k, v]: [string, any]) => ({
            profile_id: k,
            pack: v.default_pack_id || '-',
            l1: v.scope || '-',
            l2: v.category || '-',
            l3: v.subcategory || '-',
            status: v.status || 'active',
            ...v
          }));
          setProfiles(arr);
        } else {
          setProfiles([]);
        }
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
        title="场景映射" 
        description="承接前端级联方案分类，将具体的工程三级细项强绑定至底层的审查包 (Packs) 和规则集 (Rule Packs)。"
      >
        <button className="primary-button" onClick={handleEditAll}>全文本可视化编排场景映射</button>
      </AdminPageHeader>

      <AdminFilterBar>
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>筛选一级分类 (L1)</option>
          <option>危大工程专项方案类</option>
          <option>一般专项与管理体系类</option>
          <option>施工组织设计类</option>
        </select>
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>筛选映射状态</option>
          <option>完整承接 (active)</option>
          <option>草稿待审 (draft)</option>
          <option>规则部分缺失 (missing)</option>
        </select>
        <button className="secondary-button" style={{ marginLeft: "auto" }} onClick={() => alert("数据同步正常")}>一键扫描空白映射区</button>
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            <tr>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>映射 ID</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>域属约束</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>子类约束</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>隐式挂载基准包</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>映射健康度</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {(loading || profiles.length === 0) && (
               <tr>
                 <td colSpan={6} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                   {loading ? "正在加载底层数据库..." : "暂无映射配置数据。"}
                 </td>
               </tr>
            )}
            {profiles.map((p, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                <td style={{ padding: "12px 16px", fontWeight: 500 }}>{p.profile_id}</td>
                <td style={{ padding: "12px 16px", color: "#64748B" }}>{p.l1}</td>
                <td style={{ padding: "12px 16px", fontWeight: 500, color: "#0F172A" }}>{p.l3 !== '-' ? p.l3 : p.l2}</td>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#64748B" }}>{p.pack}</td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge 
                    status={p.status === 'active' ? 'success' : p.status === 'draft' ? 'warning' : p.status === 'missing' ? 'error' : 'neutral'} 
                    label={p.status === 'active' ? '完整接管' : p.status === 'draft' ? '调试中' : p.status === 'missing' ? '审查包脱落' : p.status} 
                  />
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <button onClick={() => setSelectedProfile(p)} style={{ background: "none", border: "none", color: "#0284C7", cursor: "pointer", fontWeight: 500 }}>分析</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AdminDrawer title="场景映射影响分析" open={!!selectedProfile} onClose={() => setSelectedProfile(null)}>
        {selectedProfile && (
          <div className="stack-lg">
            <SectionTitle title="映射流" />
            <div style={{ background: "#F8FAFC", padding: "16px", borderRadius: "8px" }}>
              <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px", color: "#64748B" }}>
                <span>前端表单传入约束域</span>
              </div>
              <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "#0F172A", marginBottom: "16px" }}>
                【L1】 {selectedProfile.l1} <br/>
                【L2/L3】 {selectedProfile.l2} / {selectedProfile.l3}
              </div>
              
              <div style={{ borderTop: "1px solid #E2E8F0", margin: "16px 0" }}></div>
              
              <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "#0284C7" }}>
                <span>⤵ 映射出底层基准场景 (profile_id):</span>
              </div>
              <div style={{ marginTop: "4px", fontSize: "1.05rem", fontFamily: "monospace", fontWeight: 600, color: "#0369A1" }}>
                {selectedProfile.profile_id}
              </div>
            </div>

            <div style={{ marginTop: "32px" }}>
              <SectionTitle title="挂载审查网络 / 元数据" />
              <KeyValueRow label="默认基准包" value={<span style={{fontFamily:"monospace"}}>{selectedProfile.pack}</span>} />
              
              <div style={{ marginTop: "12px", background: "#F1F5F9", padding: "12px", borderRadius: "6px", fontSize: "0.85rem", overflowX: "auto" }}>
                 <pre>{JSON.stringify(selectedProfile, null, 2)}</pre>
              </div>

              <div style={{ marginTop: "16px" }}>
                <KeyValueRow label="健康度检查" value={
                  selectedProfile.status === 'missing' 
                    ? <span style={{ color: "#DC2626" }}>高危：该三级节点没有配置绑定的专家规则集合，审查引擎可能击穿落空。</span>
                    : <span style={{ color: "#166534" }}>安全：规则网络完整覆盖。</span>
                } />
              </div>
            </div>

            <div style={{ marginTop: "32px", borderTop: "1px solid #E2E8F0", paddingTop: "16px", display: "flex", gap: "12px", flexDirection: "column" }}>
              <button className="primary-button" style={{ width: "100%" }} onClick={() => alert("当前处于只读取流\n变更请提交草案，禁止页面内越权热修。")}>编辑挂载约束</button>
              <button className="secondary-button" style={{ width: "100%" }} onClick={() => alert("目前支持通过审批工作流推入")}>推入配置清单</button>
            </div>
          </div>
        )}
      </AdminDrawer>

      <JsonConfigEditor
        title="场景映射编辑 (Profile Mappings)"
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        initialData={editorData}
        onSave={handleSave}
      />
    </div>
  );
}

