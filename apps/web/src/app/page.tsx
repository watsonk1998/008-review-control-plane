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
    <main className="shell">
      <section className="hero-header hero">
        <div className="hero-copy">
          <p className="eyebrow">008 · AI 智能审查控制总线</p>
          <h1>建果AI审查</h1>
          <p className="subtitle">
            发起结构化智能审查，实时感知总控调度心跳。全息追踪复杂任务的执行轨迹与形式审查证据链。
          </p>
          <div className="meta-grid" style={{ marginTop: 24, maxWidth: 500 }}>
            <div>
              <span className="muted small">API 终端节点</span>
              <strong style={{ display: "block", marginTop: 4 }}>{getApiBaseUrl()}</strong>
            </div>
            <div>
              <span className="muted small">冻结接口验收页</span>
              <strong style={{ display: "block", marginTop: 4 }}>
                <Link href="/review-acceptance">/review-acceptance</Link>
              </strong>
            </div>
          </div>
        </div>

        <div className="hero-aside">
          <SystemHeartbeat />
        </div>
      </section>

      <div className="workbench-grid">
        <section className="workbench-primary">
          <CreateTaskForm fixtures={fixtures} supportScope={supportScope} />
        </section>

        <aside className="workbench-sidebar stack-lg">
          <Suspense fallback={<div className="skeleton" style={{ height: "240px" }} />}>
            <SystemHealth />
          </Suspense>

          <Suspense fallback={<div className="skeleton" style={{ height: "400px" }} />}>
            <RecentTasks />
          </Suspense>
        </aside>
      </div>
    </main>
  );
}
