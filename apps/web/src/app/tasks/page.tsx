"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { fetchRecentTasks } from "@/lib/api";
import type { RecentTaskSummary } from "@/types/control-plane";

const STATUS_LABELS: Record<string, string> = {
  created: "已创建",
  planned: "已规划",
  running: "执行中",
  waiting_external: "等待外部回调",
  succeeded: "已完成",
  failed: "失败",
  partial: "部分完成",
};

const DOC_LABELS: Record<string, string> = {
  construction_org: "施工组织设计",
  construction_scheme: "一般施工方案",
  hazardous_special_scheme: "危大专项方案",
  distribution_network_special_scheme: "配电配网工程",
  supervision_plan: "监理规划",
  review_support_material: "审查辅助材料",
};

type FilterValue = "all" | "running" | "succeeded" | "failed" | "partial";

export default function TasksPage() {
  const [tasks, setTasks] = useState<RecentTaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterValue>("all");

  useEffect(() => {
    let mounted = true;
    fetchRecentTasks(50)
      .then((items) => {
        if (!mounted) return;
        setTasks(items);
      })
      .catch(() => {
        if (!mounted) return;
        setTasks([]);
      })
      .finally(() => {
        if (!mounted) return;
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const reviewTasks = useMemo(
    () => tasks.filter((task) => (task.taskType || "structured_review") === "structured_review" && Boolean(task.sourceDocumentRef)),
    [tasks],
  );

  const filteredTasks = useMemo(() => {
    if (filter === "all") return reviewTasks;
    return reviewTasks.filter((task) => task.status === filter);
  }, [filter, reviewTasks]);

  return (
    <main className="home-dashboard stack-lg" style={{ maxWidth: "980px", margin: "0 auto", padding: "40px 0" }}>
      <header className="hero-simple" style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, color: "var(--foreground)", marginBottom: "8px" }}>审查任务</h1>
          <p style={{ fontSize: "0.95rem", color: "var(--muted)" }}>查看历史审查记录、当前执行状态与正式报告回看入口。</p>
        </div>
        <Link className="primary-button" href="/">
          建果AI方案审查
        </Link>
      </header>

      <section className="glass-panel" style={{ background: "#FFFFFF", padding: "20px 24px", borderRadius: "12px", border: "1px solid #E2E8F0" }}>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          {[
            ["all", "全部"],
            ["running", "运行中"],
            ["succeeded", "已完成"],
            ["failed", "失败"],
            ["partial", "需人工关注"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={filter === value ? "primary-button" : "secondary-button"}
              onClick={() => setFilter(value as FilterValue)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="glass-panel" style={{ background: "#FFFFFF", borderRadius: "12px", border: "1px solid #E2E8F0", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--muted)" }}>正在加载历史任务…</div>
        ) : filteredTasks.length ? (
          <div className="stack-sm" style={{ padding: "16px" }}>
            {filteredTasks.map((task) => {
              const fileName = task.sourceDocumentRef?.displayName || task.sourceDocumentRef?.fileName || task.query;
              return (
                <Link
                  key={task.id}
                  href={`/tasks/${task.id}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 2fr) minmax(160px, 1fr) minmax(120px, 120px)",
                    gap: "16px",
                    alignItems: "center",
                    padding: "16px",
                    borderRadius: "10px",
                    border: "1px solid #E2E8F0",
                    textDecoration: "none",
                    color: "inherit",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "#0F172A", marginBottom: "6px" }}>{fileName}</div>
                    <div className="muted small">
                      {DOC_LABELS[task.documentType || ""] || "未识别文档类型"} · 最近更新 {new Date(task.updatedAt).toLocaleString()}
                    </div>
                  </div>
                  <div className="muted small">{STATUS_LABELS[task.status] || task.status}</div>
                  <div style={{ textAlign: "right", color: "#0284C7", fontWeight: 600 }}>查看详情</div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--muted)" }}>当前筛选条件下暂无历史任务。</div>
        )}
      </section>
    </main>
  );
}
