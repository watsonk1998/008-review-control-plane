"use client";

import { ReactNode, useState, useEffect } from "react";

export function AdminPageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <div>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, color: "#0F172A", margin: "0 0 8px 0" }}>{title}</h1>
        <p style={{ color: "#64748B", fontSize: "0.95rem", margin: 0 }}>{description}</p>
      </div>
      {children && <div style={{ display: "flex", gap: "12px" }}>{children}</div>}
    </div>
  );
}

export function AdminFilterBar({ children }: { children: ReactNode }) {
  return (
    <div style={{ 
      display: "flex", 
      gap: "16px", 
      padding: "16px", 
      background: "#F8FAFC", 
      border: "1px solid #E2E8F0", 
      borderRadius: "8px",
      marginBottom: "20px",
      alignItems: "center",
      flexWrap: "wrap"
    }}>
      {children}
    </div>
  );
}

export function StatusBadge({ status, label }: { status: "success"|"warning"|"error"|"neutral"|"info", label: string }) {
  const colors = {
    success: { bg: "#DCFCE7", text: "#166534", border: "#BBF7D0" },
    warning: { bg: "#FEF9C3", text: "#854D0E", border: "#FEF08A" },
    error:   { bg: "#FEE2E2", text: "#991B1B", border: "#FECACA" },
    neutral: { bg: "#F1F5F9", text: "#475569", border: "#E2E8F0" },
    info:    { bg: "#E0F2FE", text: "#075985", border: "#BAE6FD" }
  };
  const c = colors[status];
  return (
    <span style={{ 
      display: "inline-flex", 
      alignItems: "center", 
      padding: "2px 8px", 
      borderRadius: "999px", 
      fontSize: "0.8rem", 
      fontWeight: 500,
      background: c.bg,
      color: c.text,
      border: `1px solid ${c.border}`
    }}>
      {label}
    </span>
  );
}

export function AdminEmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div style={{
      padding: "48px 24px",
      textAlign: "center",
      background: "#FAFAFA",
      border: "1px dashed #CBD5E1",
      borderRadius: "12px"
    }}>
      <h3 style={{ margin: "0 0 8px 0", color: "#334155", fontSize: "1.1rem" }}>{title}</h3>
      <p style={{ margin: "0 0 16px 0", color: "#64748B", fontSize: "0.95rem" }}>{description}</p>
      {action}
    </div>
  );
}

export function AdminDrawer({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <>
      {/* Backdrop */}
      <div 
        style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.4)", zIndex: 40, backdropFilter: "blur(2px)" }}
        onClick={onClose}
      />
      {/* Drawer */}
      <div style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: "500px", maxWidth: "90vw",
        background: "#FFF", zIndex: 50,
        boxShadow: "-4px 0 24px rgba(0,0,0,0.1)",
        display: "flex", flexDirection: "column",
        transform: open ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.3s ease"
      }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#0F172A", fontWeight: 600 }}>{title}</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "#64748B" }}>×</button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
          {children}
        </div>
      </div>
    </>
  );
}

export function SectionTitle({ title }: { title: string }) {
  return <h4 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", fontWeight: 600, color: "#334155", borderBottom: "1px solid #E2E8F0", paddingBottom: "8px" }}>{title}</h4>;
}

export function KeyValueRow({ label, value }: { label: string, value: ReactNode }) {
  return (
    <div style={{ display: "flex", marginBottom: "8px", fontSize: "0.9rem" }}>
      <span style={{ width: "120px", color: "#64748B", flexShrink: 0 }}>{label}</span>
      <span style={{ color: "#0F172A", fontWeight: 500, flex: 1 }}>{value}</span>
    </div>
  );
}


export function JsonConfigEditor({
  title,
  open,
  onClose,
  initialData,
  onSave
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  initialData: any;
  onSave: (newData: any) => Promise<void>;
}) {
  const [editedText, setEditedText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string|null>(null);
  const [showDiff, setShowDiff] = useState(false);
  
  useEffect(() => {
    if (open && initialData) {
      setEditedText(JSON.stringify(initialData, null, 2));
      setShowDiff(false);
      setError(null);
    }
  }, [open, initialData]);

  if (!open) return null;

  const handlePreview = () => {
    try {
      JSON.parse(editedText); // format validation
      setError(null);
      setShowDiff(true);
    } catch (e) {
      setError("JSON 格式错误，请检查语法。");
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const parsed = JSON.parse(editedText);
      await onSave(parsed);
      onClose();
    } catch (e: any) {
      setError(e.message || "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.4)", zIndex: 100, backdropFilter: "blur(2px)" }} />
      <div style={{
        position: "fixed", top: "5vh", left: "50%", transform: "translateX(-50%)", 
        width: "90vw", maxWidth: "1000px", height: "90vh",
        background: "#FFF", zIndex: 110, borderRadius: "12px",
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
        display: "flex", flexDirection: "column"
      }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#0F172A", fontWeight: 600 }}>{title}</h2>
            <p style={{ margin: "4px 0 0 0", color: "#64748B", fontSize: "0.9rem" }}>直接修改底层 YAML 对应的真理源 JSON 表示。保存后立即落盘并产生备份历史。</p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "#64748B" }}>×</button>
        </div>
        
        <div style={{ flex: 1, padding: "24px", overflowY: "auto", display: "flex", gap: "24px", background: "#F8FAFC" }}>
          {/* Editor */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div style={{ marginBottom: "8px", fontWeight: 600, color: "#334155", display: "flex", justifyContent: "space-between" }}>
              <span>编辑区</span>
            </div>
            <textarea
              value={editedText}
              onChange={(e) => {
                setEditedText(e.target.value);
                setShowDiff(false);
              }}
              style={{
                flex: 1,
                width: "100%",
                padding: "16px",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                fontSize: "14px",
                lineHeight: "1.5",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                resize: "none",
                outline: "none"
              }}
              spellCheck={false}
            />
          </div>
          
          {/* Diff Preview Panel */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", opacity: showDiff ? 1 : 0.4, pointerEvents: showDiff ? "auto" : "none" }}>
            <div style={{ marginBottom: "8px", fontWeight: 600, color: "#334155" }}>变更对比 (Diff 预览)</div>
            <div style={{ 
              flex: 1, 
              background: "#1E293B", 
              borderRadius: "8px", 
              padding: "16px",
              color: "#E2E8F0",
              fontFamily: "ui-monospace, monospace",
              fontSize: "14px",
              overflowY: "auto",
              whiteSpace: "pre-wrap"
            }}>
              {showDiff ? (
                <div>
                  <div style={{ color: "#F87171", marginBottom: "8px" }}>- 旧版本配置将被归档作废</div>
                  <div style={{ color: "#4ADE80", marginBottom: "16px" }}>+ 新版本配置如下:</div>
                  {editedText}
                </div>
              ) : (
                <div style={{ color: "#94A3B8", textAlign: "center", marginTop: "100px" }}>
                  点击“校验并预览”查看配置变更
                </div>
              )}
            </div>
          </div>
        </div>

        {error && <div style={{ padding: "12px 24px", background: "#FEF2F2", color: "#DC2626", borderTop: "1px solid #FECACA" }}>{error}</div>}

        <div style={{ padding: "16px 24px", borderTop: "1px solid #E2E8F0", display: "flex", justifyContent: "flex-end", gap: "12px", background: "#FFF", borderRadius: "0 0 12px 12px" }}>
          <button className="secondary-button" onClick={onClose}>取消退出</button>
          {!showDiff ? (
            <button className="primary-button" onClick={handlePreview}>校验并预览 Diff</button>
          ) : (
            <button className="primary-button" style={{ background: "#059669" }} onClick={handleSave} disabled={isSaving}>
              {isSaving ? "保存同步中..." : "确认写入主干 YAML"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
