import { ReactNode } from "react";
import Link from "next/link";

export default function GovernanceLayout({ children }: { children: ReactNode }) {
  return (
    <div className="shell" style={{ display: "flex", flexDirection: "row", gap: "2rem" }}>
      <aside className="workbench-sidebar" style={{ width: "240px", borderRight: "1px solid var(--border)", paddingRight: "1rem" }}>
        <h3>治理控制台</h3>
        <nav style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "1rem" }}>
          <Link href="/admin/governance">⬅️ 治理大盘 (Dashboard)</Link>
          <Link href="/admin/governance/bases">📚 审查依据库 (Bases)</Link>
          <Link href="/admin/governance/packs">📦 审查包 (Packs)</Link>
          <Link href="/admin/governance/profiles">⚙️ 场景映射 (Profiles)</Link>
          <Link href="/admin/governance/releases">📝 发布审批 (Releases)</Link>
          <Link href="/admin/governance/simulation">🧪 试跑验证舱 (Simulation Lab)</Link>
        </nav>
      </aside>
      <main style={{ flex: 1, padding: "1rem" }}>
        {children}
      </main>
    </div>
  );
}
