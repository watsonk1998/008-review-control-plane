"use client";

import Link from "next/link";

export default function TasksPage() {
  return (
    <main className="home-dashboard stack-lg" style={{ maxWidth: "900px", margin: "0 auto", padding: "40px 0" }}>
      <header className="hero-simple" style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--foreground)", marginBottom: "8px" }}>我的任务</h1>
          <p style={{ fontSize: "0.95rem", color: "var(--muted)" }}>查看您提交的历史审查任务</p>
        </div>
        <Link className="primary-button" href="/">
          发起新审查
        </Link>
      </header>
      
      <section className="glass-panel" style={{ background: "#FFFFFF", padding: "40px", borderRadius: "12px", border: "1px solid #E2E8F0", textAlign: "center", color: "var(--muted)" }}>
        <h3 style={{ fontSize: "1.1rem", fontWeight: 500, marginBottom: "8px", color: "var(--foreground)" }}>暂无历史任务</h3>
        <p style={{ fontSize: "0.95rem" }}>
          记录系统尚未接入列表页，暂只支持通过任务 ID 直接访问详情页 (如 /tasks/1234)。
        </p>
      </section>
    </main>
  );
}
