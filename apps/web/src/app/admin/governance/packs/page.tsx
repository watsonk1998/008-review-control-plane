"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminDrawer, SectionTitle, KeyValueRow } from "@/components/admin/admin-components";

export default function PacksAdminPage() {
  const [selectedPack, setSelectedPack] = useState<any>(null);
  const [packs, setPacks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/governance/packs")
      .then(res => res.json())
      .then(data => {
        setPacks(data);
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
        title="审查包配置" 
        description="基于底层依据库衍生出的应用层容器。将多项零散的合规强条（Rule Packs）组合为面向特定领域（如模板工程、脚手架工程）的实战可打分包。"
      >
        <button className="primary-button" onClick={() => alert("【系统架构限制】\n\n创建新的 Pack 审查包需要绑定核心大模型流转 Prompt 和 Rule ID。\n请在代码库 `config/packs/` 维护 YAML 并走流转，前端管理台不开放直接创建能力。")}>新建审查包</button>
      </AdminPageHeader>

      <AdminFilterBar>
        <input type="text" placeholder="搜索包名称或标识..." style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px", width: "240px" }} />
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>所有状态</option>
          <option>正式就绪 (ready)</option>
          <option>实验中 (experimental)</option>
          <option>占位符 (placeholder)</option>
        </select>
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            <tr>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>审查包名称</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>审查包标识 (pack_id)</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>当前状态</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>包含依据</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>家族层级</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>优先级</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {(loading || packs.length === 0) && (
               <tr>
                 <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                   {loading ? "正在加载真实后端环境数据..." : "暂无审查包数据。"}
                 </td>
               </tr>
            )}
            {packs.map((p, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                <td style={{ padding: "12px 16px", fontWeight: 500 }}>{p.display_name}</td>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#64748B" }}>{p.pack_id}</td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge 
                    status={p.status === 'ready' ? 'success' : p.status === 'experimental' ? 'info' : 'neutral'} 
                    label={p.status === 'ready' ? '稳定就绪' : p.status === 'experimental' ? '实验中' : p.status || '未知'} 
                  />
                </td>
                <td style={{ padding: "12px 16px" }}>{p.basis_ids?.length || 0} 项</td>
                <td style={{ padding: "12px 16px" }}>{p.family || '-'}</td>
                <td style={{ padding: "12px 16px", color: "#64748B", fontSize: "0.9rem" }}>{p.priority || '-'}</td>
                <td style={{ padding: "12px 16px" }}>
                  <button onClick={() => setSelectedPack(p)} style={{ background: "none", border: "none", color: "#0284C7", cursor: "pointer", fontWeight: 500 }}>查看</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AdminDrawer title="审查包详情" open={!!selectedPack} onClose={() => setSelectedPack(null)}>
        {selectedPack && (
          <div className="stack-lg">
            <SectionTitle title="基本信息" />
            <KeyValueRow label="包名称" value={selectedPack.display_name} />
            <KeyValueRow label="标识符" value={<span style={{fontFamily:"monospace"}}>{selectedPack.pack_id}</span>} />
            <KeyValueRow label="状态" value={
              <StatusBadge status={selectedPack.status === 'ready' ? 'success' : 'neutral'} label={selectedPack.status || '未知'} />
            } />
            <KeyValueRow label="家族族系" value={selectedPack.family || '默认'} />
            <KeyValueRow label="角色" value={selectedPack.role || '-'} />

            <div style={{ marginTop: "32px" }}>
              <SectionTitle title="挂载依据清单 (basis_ids)" />
              {selectedPack.basis_ids && selectedPack.basis_ids.length > 0 ? (
                <div style={{ background: "#F8FAFC", padding: "12px", borderRadius: "6px", fontSize: "0.9rem", color: "#334155" }}>
                  <ul style={{ margin: 0, paddingLeft: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    {selectedPack.basis_ids.map((bid: string) => (
                       <li key={bid}><span style={{fontFamily:"monospace", color:"#64748B"}}>{bid}</span></li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div style={{ color: "#94A3B8", fontStyle: "italic", padding: "12px", background: "#F8FAFC", borderRadius: "6px" }}>
                  当前审查包暂未挂载任何底层依据 (Basis)
                </div>
              )}
            </div>
            
            <div style={{ marginTop: "24px" }}>
               <SectionTitle title="默认关联配置" />
               <div style={{ fontSize: "0.85rem", color: "#64748B" }}>默认挂载如下 profiles:</div>
               <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "8px" }}>
                 {selectedPack.default_profiles?.map((prof: string) => (
                    <span key={prof} style={{ background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "4px 8px" }}>{prof}</span>
                 )) || <span>暂无默认路由</span>}
               </div>
            </div>

            <div style={{ marginTop: "32px", borderTop: "1px solid #E2E8F0", paddingTop: "16px", display: "flex", gap: "12px" }}>
              <button className="primary-button" style={{ flex: 1 }}>编辑挂载</button>
              <button className="secondary-button" style={{ flex: 1 }}>查看审计流</button>
            </div>
          </div>
        )}
      </AdminDrawer>
    </div>
  );
}
