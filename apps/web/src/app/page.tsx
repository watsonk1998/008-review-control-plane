import { Suspense } from "react";
import Link from "next/link";
import { CreateTaskForm } from "@/components/create-task-form";
import { SystemHealth } from "@/components/system-health";
import { RecentTasks } from "@/components/recent-tasks";
import { SystemHeartbeat } from "@/components/system-heartbeat";
import { fetchFixtures, fetchSupportScope, getApiBaseUrl } from "@/lib/api";

export default async function Home() {
  // Parallel fetch initial foundation data (eliminating sequential waterfalls)
  const [fixtures, supportScope] = await Promise.all([
    fetchFixtures().catch(() => []),
    fetchSupportScope().catch(() => null),
  ]);

  return (
    <div className="home-dashboard stack-lg" style={{ maxWidth: "800px", margin: "0 auto", padding: "40px 0" }}>
      <header className="hero-simple" style={{ marginBottom: "32px", textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 600, color: "var(--foreground)", marginBottom: "12px" }}>发起审查任务</h1>
        <p style={{ fontSize: "1rem", color: "var(--muted)" }}>上传待审文件，选择方案分类与审查参数，即可智能执行形式审查。</p>
      </header>

      <main className="workbench-primary">
        <CreateTaskForm fixtures={fixtures} supportScope={supportScope} />
      </main>
    </div>
  );
}
