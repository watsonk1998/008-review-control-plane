"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, AdminFilterBar, StatusBadge, AdminDrawer, SectionTitle, KeyValueRow } from "@/components/admin/admin-components";

export default function BasesAdminPage() {
  const [selectedBasis, setSelectedBasis] = useState<any>(null);
  const [bases, setBases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/admin/governance/bases")
      .then(res => res.json())
      .then(data => {
        setBases(data);
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
        title="依据标准库" 
        description="系统中所有机器可读指令集与审查规则的唯一事实来源。提供各行业规范、法律法规及企业专属强条的溯源入口与版本控制。"
      >
        <button className="primary-button" onClick={() => alert("【系统安全限制】\n\n当前禁止从前端直接上传或修改底层审查依据！\n请严格遵守配置即代码规范，前往 external/ 目录通过 YAML 注册新标准。")}>上传规范原文</button>
        <button className="secondary-button" onClick={() => alert("【系统安全限制】\n\n依据库只读保护中。\n所有的手工录入必须走标准审核流并落地为 YAML，暂不开放界面侧的旁路修改。")}>手动录入依据</button>
      </AdminPageHeader>

      <AdminFilterBar>
        <input type="text" placeholder="检索规范名称或标准号..." style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px", width: "260px" }} />
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>全部类型</option>
          <option>法律法规</option>
          <option>国家标准</option>
          <option>行业标准</option>
          <option>企业规范</option>
        </select>
        <select style={{ padding: "8px 12px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
          <option>全部状态</option>
          <option>已发布 (published)</option>
          <option>草稿 (draft)</option>
          <option>已归档 (archived)</option>
        </select>
      </AdminFilterBar>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
            <tr>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>规范标题</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>依据标识 (basis_id)</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>层级类别</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>版本号</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>管辖范围</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>生效状态</th>
              <th style={{ padding: "12px 16px", color: "#475569", fontWeight: 500, fontSize: "0.9rem" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {(loading || bases.length === 0) && (
               <tr>
                 <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                   {loading ? "正在加载底层环境真实数据..." : "暂无依据库数据。"}
                 </td>
               </tr>
            )}
            {bases.map((b, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                <td style={{ padding: "12px 16px", fontWeight: 500 }}>{b.title}</td>
                <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#64748B" }}>{b.basis_id}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span style={{ padding: "2px 6px", background: "#F1F5F9", borderRadius: "4px", fontSize: "0.85rem", color: "#475569" }}>
                    {b.source_type}
                  </span>
                </td>
                <td style={{ padding: "12px 16px", color: "#64748B" }}>{b.version || '-'}</td>
                <td style={{ padding: "12px 16px", color: "#64748B" }}>{b.jurisdiction || '全国'}</td>
                <td style={{ padding: "12px 16px" }}>
                  <StatusBadge 
                    status={b.effective_status === 'published' ? 'success' : b.effective_status === 'draft' ? 'warning' : 'neutral'} 
                    label={b.effective_status === 'published' ? '正式发布' : b.effective_status === 'draft' ? '草稿' : b.effective_status || '历史'} 
                  />
                </td>
                <td style={{ padding: "12px 16px" }}>
                  <button onClick={() => setSelectedBasis(b)} style={{ background: "none", border: "none", color: "#0284C7", cursor: "pointer", fontWeight: 500 }}>详情</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AdminDrawer title="规范依据详情" open={!!selectedBasis} onClose={() => setSelectedBasis(null)}>
        {selectedBasis && (
          <div className="stack-lg">
            <SectionTitle title="规范元数据" />
            <KeyValueRow label="依据标题" value={selectedBasis.title} />
            <KeyValueRow label="标准层级" value={selectedBasis.source_type} />
            <KeyValueRow label="标准编号" value={selectedBasis.version || '-'} />
            <KeyValueRow label="系统全网唯一码" value={<span style={{fontFamily:"monospace"}}>{selectedBasis.basis_id}</span>} />
            <KeyValueRow label="管辖区域" value={selectedBasis.jurisdiction || '全国'} />
            <KeyValueRow label="所有者" value={selectedBasis.owner || 'System'} />
            <KeyValueRow label="状态" value={
              <StatusBadge status={selectedBasis.effective_status === 'published' ? 'success' : 'neutral'} label={selectedBasis.effective_status || '未知'} />
            } />

            <div style={{ marginTop: "32px" }}>
              <SectionTitle title="适用标签区 (applicability_tags)" />
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "8px" }}>
                 {selectedBasis.applicability_tags?.map((tag: string) => (
                    <span key={tag} style={{ background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "4px 8px", fontSize: "0.85rem" }}>{tag}</span>
                 )) || <span>暂无标签</span>}
              </div>
            </div>

            <div style={{ marginTop: "32px", borderTop: "1px solid #E2E8F0", paddingTop: "16px", display: "flex", gap: "12px" }}>
              <button className="primary-button" style={{ flex: 1 }}>编辑基准信息</button>
              <button className="secondary-button" style={{ color: "#DC2626", borderColor: "#FECACA", background: "#FEF2F2" }}>申请作废废止</button>
            </div>
          </div>
        )}
      </AdminDrawer>
    </div>
  );
}
