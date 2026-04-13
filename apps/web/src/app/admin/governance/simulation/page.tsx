"use client";

import { useState, useEffect } from "react";
import { AdminPageHeader, StatusBadge } from "@/components/admin/admin-components";

export default function SimulationLab() {
  const [docType, setDocType] = useState("construction_org");
  const [selectedPackId, setSelectedPackId] = useState("");
  const [availablePacks, setAvailablePacks] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [learningMode, setLearningMode] = useState(false);

  useEffect(() => {
    fetch("/api/admin/governance/packs")
      .then(res => res.json())
      .then(data => {
        setAvailablePacks(data || []);
        if (data && data.length > 0) {
          setSelectedPackId(data[0].pack_id);
        }
      })
      .catch(err => console.error("Failed to load packs:", err));
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/admin/governance/simulation/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_type: docType,
          target_file_id: "test-fixture.docx",
          pack_ids: selectedPackId ? [selectedPackId] : [],
          rule_pack_ids: [],
          simulation_mode: true,
          learning_mode: learningMode
        })
      });
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <AdminPageHeader 
        title="试跑验证舱 (Simulation Lab)" 
        description="系统底层隔离的离线测试靶场。用于手工发起模拟包组合跑批，并收集提取经验反馈作为新的治理候选。"
      />

      <div style={{ padding: "16px", backgroundColor: "#FEF3C7", color: "#92400E", border: "1px solid #FCD34D", borderRadius: "8px", marginBottom: "32px", fontSize: "0.9rem" }}>
        <strong style={{ display: "block", marginBottom: "4px" }}>⚠️ 模拟环境隔离保护处于激活状态</strong>
        在此舱内发起的测试将全程隐蔽隔离：绝不干扰正式审查状态机，无报告污染，隔离知识蒸馏。
      </div>

      <div style={{ background: "#FFF", borderRadius: "8px", border: "1px solid #E2E8F0", padding: "24px", marginBottom: "32px" }}>
        <h3 style={{ margin: "0 0 16px 0", fontSize: "1.1rem", color: "#334155" }}>设置审查载荷与验证参数</h3>
        
        <div style={{ display: "flex", gap: "24px", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1, minWidth: "220px" }}>
            <label style={{ fontSize: "0.85rem", color: "#64748B", fontWeight: 500 }}>表单对象类型 (docType)</label>
            <select value={docType} onChange={e => setDocType(e.target.value)} style={{ padding: "10px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
              <option value="construction_org">施工组织设计综述 (construction_org)</option>
              <option value="hazardous_special_scheme">危大工程专项方案特项 (hazardous_special_scheme)</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1, minWidth: "220px" }}>
            <label style={{ fontSize: "0.85rem", color: "#64748B", fontWeight: 500 }}>挂载靶标审查包 (pack_id)</label>
            <select value={selectedPackId} onChange={e => setSelectedPackId(e.target.value)} style={{ padding: "10px", border: "1px solid #CBD5E1", borderRadius: "6px" }}>
              {availablePacks.map(p => (
                <option key={p.pack_id} value={p.pack_id}>{p.pack_id} - {p.display_name}</option>
              ))}
              {availablePacks.length === 0 && <option value="">(无审查包数据)</option>}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", flexShrink: 0 }}>
             <label style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px", cursor: "pointer", background: "#F1F5F9", borderRadius: "6px", border: "1px solid #E2E8F0", userSelect: "none" }}>
               <input type="checkbox" checked={learningMode} onChange={e => setLearningMode(e.target.checked)} style={{ cursor: "pointer" }} />
               <span style={{ fontSize: "0.9rem", color: "#475569" }}>并发启动离线特征捕获 (Candidate Learning)</span>
             </label>
          </div>

          <button onClick={handleRun} disabled={loading} className="primary-button" style={{ height: "42px", padding: "0 24px", minWidth: "120px" }}>
            {loading ? "执行中..." : "发射请求"}
          </button>
        </div>
      </div>

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {result.generated_candidates && result.generated_candidates.length > 0 && (
            <div style={{ border: "1px solid #0D9488", borderRadius: "8px", padding: "20px", backgroundColor: "#F0FDFA" }}>
              <h3 style={{ color: "#0F766E", margin: "0 0 12px 0", fontSize: "1.1rem" }}>✨ 仿真脱壳捕获到了知识沉淀 (New Candidates Generated!)</h3>
              <p style={{ marginBottom: "16px", color: "#115E59", fontSize: "0.9rem" }}>后台已通过学习网络捕获到如下新策略，并且已将它们推送到<strong>【候选建议池 (Candidates)】</strong>，等待管理员评估与转换。</p>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {result.generated_candidates.map((cand: any, idx: number) => (
                  <div key={idx} style={{ backgroundColor: "#FFFFFF", padding: "16px", borderRadius: "6px", border: "1px solid #99F6E4" }}>
                    <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "12px" }}>
                       <span style={{ fontWeight: 600, color: "#115E59" }}>{cand.candidate_type}</span>
                       <span style={{ fontSize: "0.8rem", color: "#0D9488", background: "#CCFBF1", padding: "2px 8px", borderRadius: "4px" }}>状态: {cand.status}</span>
                    </div>
                    <pre style={{ margin: "0", whiteSpace: "pre-wrap", fontSize: "0.9rem", color: "#334155", background: "#F8FAFC", padding: "12px", borderRadius: "4px" }}>{cand.content}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ border: "1px solid #E2E8F0", borderRadius: "8px", padding: "24px", background: "#FFF" }}>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", marginBottom: "20px" }}>
              <h3 style={{ margin: 0, fontSize: "1.1rem" }}>主审查线程脱壳结果 (Snapshot)</h3>
              {result.user_visible_title && <StatusBadge status="warning" label={result.user_visible_title} />}
            </div>
            
            <pre style={{ backgroundColor: "#F8FAFC", padding: "20px", borderRadius: "6px", overflow: "auto", maxHeight: "500px", border: "1px solid #E2E8F0", color: "#0F172A", fontSize: "0.85rem", lineHeight: 1.6 }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
