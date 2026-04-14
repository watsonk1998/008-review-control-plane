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
    <div className="home-dashboard stack-lg" style={{ maxWidth: "1120px", margin: "0 auto", padding: "48px 0 64px" }}>
      <header className="hero-simple" style={{ marginBottom: "36px", textAlign: "center" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "10px", padding: "8px 14px", borderRadius: "999px", background: "#F4F1EB", color: "#6B7280", fontSize: "0.85rem", marginBottom: "18px" }}>
          <span style={{ width: 8, height: 8, borderRadius: 4, background: "#172033", display: "inline-block" }} />
          审查工作台
        </div>
        <h1 style={{ fontSize: "2.4rem", fontWeight: 700, color: "#172033", marginBottom: "14px", letterSpacing: "-0.03em" }}>建果AI方案审查</h1>
        <p style={{ fontSize: "1rem", color: "#6B7280", maxWidth: "620px", margin: "0 auto", lineHeight: 1.75 }}>上传待审方案，选择适用类型与审查模块，系统将自动匹配依据规范并生成正式审查报告。</p>
      </header>

      <main className="workbench-primary">
        <CreateTaskForm supportScope={supportScope} externalContext={externalContext} />
      </main>
    </div>
  );
}
