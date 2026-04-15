import { redirect } from "next/navigation";
import { CreateTaskForm } from "@/components/create-task-form";
import { fetchFixtures, fetchSupportScope } from "@/lib/api";

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

export default async function Home(props: { searchParams: SearchParams }) {
  const searchParams = await props.searchParams;

  // 建果平台点击已完成的审查项目时传 reviewId，直接跳转到任务详情页
  const reviewId =
    (typeof searchParams?.reviewId === "string" ? searchParams.reviewId : undefined) ??
    (typeof searchParams?.taskId === "string" ? searchParams.taskId : undefined);
  if (reviewId) {
    redirect(`/tasks/${reviewId}`);
  }

  // Parallel fetch initial foundation data (eliminating sequential waterfalls)
  const [fixtures, supportScope] = await Promise.all([
    fetchFixtures().catch(() => []),
    fetchSupportScope().catch(() => null),
  ]);

  const externalContext = {
    agentId: typeof searchParams?.agentId === "string" ? searchParams.agentId : undefined,
    callBackUrl:
      (typeof searchParams?.callBackUrl === "string" ? searchParams.callBackUrl : undefined) ??
      (typeof searchParams?.callbackUrl === "string" ? searchParams.callbackUrl : undefined),
    userId: typeof searchParams?.userId === "string" ? searchParams.userId : undefined,
    tenantId: typeof searchParams?.tenantId === "string" ? searchParams.tenantId : undefined,
  };

  return (
    <div className="home-dashboard stack-lg" style={{ maxWidth: "1120px", margin: "0 auto", padding: "48px 0 64px" }}>
      <header className="hero-simple" style={{ marginBottom: "36px", textAlign: "center" }}>
        <h1 style={{ fontSize: "2.4rem", fontWeight: 700, color: "#172033", marginBottom: "14px", letterSpacing: "-0.03em" }}>建果AI方案审查</h1>
      </header>

      <main className="workbench-primary">
        <CreateTaskForm supportScope={supportScope} externalContext={externalContext} />
      </main>
    </div>
  );
}
