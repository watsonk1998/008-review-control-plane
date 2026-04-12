"use client";

import { useState } from "react";

export default function SimulationLab() {
  const [docType, setDocType] = useState("construction_org");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [learningMode, setLearningMode] = useState(false);

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
          pack_ids: ["review.visibility"], // simple mock data
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
      <h2 style={{ marginBottom: "1rem" }}>🧪 试跑验证舱 (Simulation Lab)</h2>
      <div style={{ padding: "1rem", backgroundColor: "var(--warning-bg, #fff3cd)", color: "var(--warning-text, #856404)", border: "1px solid #ffeeba", borderRadius: "8px", marginBottom: "2rem" }}>
        <strong>⚠️ 模拟环境隔离保护中</strong>
        <p>在此舱内发起的审查测试将全程隔离。不会触发正式事件记录，不会通过大模型实际计费(视模式而定)，也不会改变持久化事实。</p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        <select value={docType} onChange={e => setDocType(e.target.value)} style={{ padding: "0.5rem" }}>
          <option value="construction_org">施工组织设计 (construction_org)</option>
          <option value="hazardous_special_scheme">危大工程专项方案 (hazardous_special_scheme)</option>
        </select>
        
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.5rem" }}>
          <input type="checkbox" checked={learningMode} onChange={e => setLearningMode(e.target.checked)} />
          启用离线仿真学习 (Learning Mode)
        </label>

        <button onClick={handleRun} disabled={loading} style={{ padding: "0.5rem 1rem", backgroundColor: "var(--primary-color, #007bff)", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}>
          {loading ? "运行中..." : "启动模拟审查"}
        </button>
      </div>

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          
          {result.generated_candidates && result.generated_candidates.length > 0 && (
            <div style={{ border: "1px solid #17a2b8", borderRadius: "8px", padding: "1rem", backgroundColor: "#e0f7fa" }}>
              <h3 style={{ color: "#00838f" }}>✨ 发掘到的候选建议 (Learning Extraction)</h3>
              <p style={{ marginBottom: "1rem" }}>引擎在脱机学习中捕获到以下新启发，已自动落入候选池作为草稿。</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {result.generated_candidates.map((cand: any, idx: number) => (
                  <div key={idx} style={{ backgroundColor: "rgba(255,255,255,0.7)", padding: "1rem", borderRadius: "4px" }}>
                    <strong>{cand.candidate_type}</strong>
                    <pre style={{ margin: "0.5rem 0 0 0", whiteSpace: "pre-wrap" }}>{cand.content}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ border: "1px solid var(--border)", borderRadius: "8px", padding: "1rem" }}>
            <h3>测试返回结果 (Snapshot)</h3>
            {result.user_visible_title && <h4 style={{ color: "#d9534f" }}>{result.user_visible_title}</h4>}
            <pre style={{ backgroundColor: "#f8f9fa", padding: "1rem", borderRadius: "4px", overflow: "auto", maxHeight: "400px", marginTop: "1rem" }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
