import { fetchHealth, fetchFixtures } from "@/lib/api";

export async function SystemHealth() {
  const [health, fixtures] = await Promise.all([
    fetchHealth().catch(() => null),
    fetchFixtures().catch(() => []),
  ]);

  const availableCapabilities = health?.capabilities.filter((c) => c.available) || [];
  const hasUnavailable = health?.capabilities.some((c) => !c.available);

  return (
    <div className="glass-panel stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">系统健康监控</p>
          <h2 className="section-title">系统状态</h2>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <span>可用引擎</span>
          <strong>
            {availableCapabilities.length} / {health?.capabilities.length || "—"}
          </strong>
        </div>
        <div className="metric-card">
          <span>基础样本</span>
          <strong>{health?.fixtureCount ?? fixtures.length}</strong>
        </div>
      </div>

      <div className="task-list">
        {health?.capabilities.map((cap) => (
          <div className="capability-row" key={cap.name}>
            <div>
              <strong>{cap.name}</strong>
              <p>{cap.detail || cap.mode}</p>
            </div>
            <span
              className={`status-pill ${
                cap.available ? "is-healthy" : "is-warning"
              }`}
            >
              {cap.available ? "正常运行" : "离线断连"}
            </span>
          </div>
        ))}
      </div>

      {hasUnavailable && (
        <p className="muted small">部分模型/引擎降级，但不阻断总控台运行。</p>
      )}
    </div>
  );
}
