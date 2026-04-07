"use client";

import { useEffect, useState } from "react";
import { fetchHeartbeat } from "@/lib/api";

function connectionTone(state: "healthy" | "lagging" | "offline" | "checking") {
  if (state === "healthy") return "is-healthy";
  if (state === "lagging") return "is-warning";
  if (state === "offline") return "is-unhealthy";
  return "is-neutral";
}

function connectionLabel(state: "healthy" | "lagging" | "offline" | "checking") {
  if (state === "healthy") return "引擎在线";
  if (state === "lagging") return "连通延迟";
  if (state === "offline") return "引擎中断";
  return "正在建立长连接...";
}

function formatDistanceFromNow(value?: string | null) {
  if (!value) return "无运行记录";
  const deltaMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(deltaMs / 60000));
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  return `${days} 天前`;
}

export function SystemHeartbeat() {
  const [heartbeat, setHeartbeat] = useState<{ runningTaskCount: number; latestTaskUpdatedAt?: string | null } | null>(null);
  const [lastSuccess, setLastSuccess] = useState<number | null>(null);
  const [tick, setTick] = useState(Date.now());

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const res = await fetchHeartbeat();
        if (mounted) {
          setHeartbeat(res);
          setLastSuccess(Date.now());
        }
      } catch (err) {
        // failed heartbeat
      }
    };
    void poll();
    const iv = setInterval(poll, 15000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  useEffect(() => {
    const iv = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(iv);
  }, []);

  let state: "healthy" | "lagging" | "offline" | "checking" = "checking";
  if (lastSuccess) {
    const drift = tick - lastSuccess;
    if (drift > 60000) state = "offline";
    else if (drift > 20000) state = "lagging";
    else state = "healthy";
  }

  return (
    <div className={`glass-panel heartbeat-badge ${connectionTone(state)}`} style={{ padding: "16px 20px" }}>
      <span className={`pulse-dot ${connectionTone(state)}`} />
      <div>
        <strong style={{ fontSize: "1rem" }}>{connectionLabel(state)}</strong>
        <p className="muted small">
          {heartbeat?.runningTaskCount ?? 0} 个任务重负载 · 活动 {formatDistanceFromNow(heartbeat?.latestTaskUpdatedAt)}
        </p>
      </div>
    </div>
  );
}
