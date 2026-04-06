import Link from "next/link";
import { fetchRecentTasks } from "@/lib/api";
import type { TaskStatus } from "@/types/control-plane";

function taskStatusTone(status: TaskStatus) {
  if (status === "succeeded") return "is-healthy";
  if (status === "failed") return "is-unhealthy";
  if (status === "partial") return "is-warning";
  return "is-neutral";
}

const TASK_STATUS_MAP: Record<string, string> = {
  pending: "排队中",
  running: "执行中",
  succeeded: "成功",
  failed: "失败",
  partial: "部分成功",
  accepted: "已验收",
  rejected: "已驳回",
  needs_attachment: "需补件"
};

const TASK_TYPE_MAP: Record<string, string> = {
  structured_review: "正式审查",
  review_assist: "审查辅助",
  knowledge_qa: "知识问答",
  document_research: "文档研究",
  deep_research: "深度研究",
};

function formatDistanceFromNow(value?: string | null) {
  if (!value) return "暂无记录";
  const deltaMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(deltaMs / 60000));
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  return `${days} 天前`;
}

export async function RecentTasks() {
  const recentTasks = await fetchRecentTasks(8).catch(() => []);

  return (
    <div className="glass-panel stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">近期派发记录</p>
          <h2 className="section-title">最近任务</h2>
        </div>
      </div>

      {recentTasks.length ? (
        <div className="task-list">
          {recentTasks.map((task) => (
            <Link className="task-item" href={`/tasks/${task.id}`} key={task.id}>
              <div className="task-meta">
                <p>{TASK_TYPE_MAP[task.taskType] || task.taskType}</p>
                <span>{formatDistanceFromNow(task.updatedAt)}</span>
              </div>
              <span className={`status-pill ${taskStatusTone(task.status)}`}>
                {TASK_STATUS_MAP[task.status] || task.status.toUpperCase()}
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <p className="muted small">暂无最近任务</p>
      )}
    </div>
  );
}
