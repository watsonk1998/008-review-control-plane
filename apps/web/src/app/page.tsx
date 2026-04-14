import { CreateTaskForm } from "@/components/create-task-form";
import { fetchFixtures, fetchSupportScope } from "@/lib/api";

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

export default async function Home(props: { searchParams: SearchParams }) {
  // Parallel fetch initial foundation data (eliminating sequential waterfalls)
  const [fixtures, supportScope, searchParams] = await Promise.all([
    fetchFixtures().catch(() => []),
    fetchSupportScope().catch(() => null),
    props.searchParams,
  ]);

  const externalContext = {
    agentId: typeof searchParams?.agentId === "string" ? searchParams.agentId : undefined,
    callBackUrl: typeof searchParams?.callBackUrl === "string" ? searchParams.callBackUrl : undefined,
    userId: typeof searchParams?.userId === "string" ? searchParams.userId : undefined,
    tenantId: typeof searchParams?.tenantId === "string" ? searchParams.tenantId : undefined,
  };

  return (
    <div className="home-dashboard stack-lg" style={{ maxWidth: "800px", margin: "0 auto", padding: "40px 0" }}>
      <header className="hero-simple" style={{ marginBottom: "32px", textAlign: "center" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 600, color: "var(--foreground)", marginBottom: "12px" }}>发起审查任务</h1>
        <p style={{ fontSize: "1rem", color: "var(--muted)" }}>上传待审文件，选择方案分类与审查参数，即可智能执行形式审查。</p>
      </header>

      <main className="workbench-primary">
        <CreateTaskForm supportScope={supportScope} externalContext={externalContext} />
      </main>
    </div>
  );
}
