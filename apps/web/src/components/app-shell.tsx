"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname() || "";
  const isAdmin = pathname.startsWith("/admin");

  return (
    <div className="platform-layout">
      {/* 1. Top Nav (全局平台顶栏) */}
      <header className="platform-topnav">
        <div className="topnav-brand">
          <Link href="/" className="brand-logo">
            <span className="brand-icon">008</span>
            <span className="brand-name">建果AI审查平台</span>
          </Link>
          <div className="brand-divider"></div>
          <span className="platform-subtitle">
            {isAdmin ? "管理员治理工作台" : "用户审查工作台"}
          </span>
        </div>
        
        <div className="topnav-actions">
          <nav className="topnav-links">
            <Link href="/" className={!isAdmin ? "active" : ""}>用户入口</Link>
            <Link href="/admin/governance" className={isAdmin ? "active" : ""}>治理中心</Link>
          </nav>
          <div className="user-profile">
            <div className="avatar">U</div>
            <span className="username">Admin</span>
          </div>
        </div>
      </header>

      <div className="platform-body">
        {/* 2. Primary Side Nav (左侧主导航) */}
        <aside className="platform-sidenav">
          <nav className="nav-menu">
            {isAdmin ? (
              <>
                <div className="nav-group-title">配置与治理</div>
                <Link href="/admin/governance" className={`nav-item ${pathname === "/admin/governance" ? "active" : ""}`}>
                  <span className="nav-icon">⬅️</span> 大盘
                </Link>
                <Link href="/admin/governance/bases" className={`nav-item ${pathname.includes("/bases") ? "active" : ""}`}>
                  <span className="nav-icon">📚</span> 依据库
                </Link>
                <Link href="/admin/governance/packs" className={`nav-item ${pathname.includes("/packs") ? "active" : ""}`}>
                  <span className="nav-icon">📦</span> 审查包
                </Link>
                <Link href="/admin/governance/profiles" className={`nav-item ${pathname.includes("/profiles") ? "active" : ""}`}>
                  <span className="nav-icon">⚙️</span> 场景映射
                </Link>
                <Link href="/admin/governance/candidates" className={`nav-item ${pathname.includes("/candidates") ? "active" : ""}`}>
                  <span className="nav-icon">💡</span> 候选建议
                </Link>
                <Link href="/admin/governance/releases" className={`nav-item ${pathname.includes("/releases") ? "active" : ""}`}>
                  <span className="nav-icon">📝</span> 发布审批
                </Link>
                <div className="nav-group-title mt-4">实验与测试</div>
                <Link href="/admin/governance/simulation" className={`nav-item ${pathname.includes("/simulation") ? "active" : ""}`}>
                  <span className="nav-icon">🧪</span> 试跑验证舱
                </Link>
              </>
            ) : (
              <>
                <div className="nav-group-title">工作台</div>
                <Link href="/" className={`nav-item ${pathname === "/" ? "active" : ""}`}>
                  <span className="nav-icon">🚀</span> 发起审查
                </Link>
                <Link href="/tasks" className={`nav-item ${pathname.startsWith("/tasks") ? "active" : ""}`}>
                  <span className="nav-icon">📋</span> 我的任务
                </Link>
              </>
            )}
          </nav>
        </aside>

        {/* 3. Main Content Area */}
        <main className="platform-main">
          <div className="platform-content-inner">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
