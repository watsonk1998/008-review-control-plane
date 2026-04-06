"use client";

import { useEffect, useMemo, useState } from "react";

import { updateReviewerDecision } from "@/lib/api";
import type {
  AttachmentVisibilityMatrixItem,
  ReviewIssue,
  ReviewPreparationSummary,
  ReviewerDecision,
  ReviewerDecisionUpdateRequest,
  ReviewerIssueDecision,
  TaskRecord,
} from "@/types/control-plane";

const TASK_STATE_OPTIONS: Array<{
  value: ReviewerDecisionUpdateRequest["taskState"];
  label: string;
}> = [
  { value: "pending", label: "pending（待处理）" },
  { value: "accepted", label: "accepted（已完成复核）" },
  { value: "rejected", label: "rejected（确认存在阻断问题）" },
  { value: "needs_attachment", label: "needs supplement（需补件/补充材料）" },
];

const ITEM_STATE_OPTIONS: Array<{
  value: ReviewerIssueDecision["state"];
  label: string;
}> = [
  { value: "pending", label: "pending（待处理 / unresolved）" },
  { value: "confirmed", label: "confirmed（确认问题成立）" },
  { value: "dismissed", label: "rejected（驳回 / 不成立）" },
  { value: "needs_attachment", label: "needs supplement（需补件/补充材料）" },
];

function buildFallbackDecision(
  issues: ReviewIssue[],
  attachments: AttachmentVisibilityMatrixItem[],
): ReviewerDecisionUpdateRequest {
  return {
    taskState: "pending",
    note: "",
    issues: issues.map((issue) => ({
      issueId: issue.id,
      state: "pending",
      note: "",
    })),
    attachments: attachments.map((item) => ({
      attachmentId: item.id,
      state: "pending",
      note: "",
    })),
  };
}

function deriveTaskState(
  issues: ReviewerDecisionUpdateRequest["issues"],
  attachments: ReviewerDecisionUpdateRequest["attachments"],
): ReviewerDecisionUpdateRequest["taskState"] {
  if (issues.some((item) => item.state === "confirmed")) {
    return "rejected";
  }
  if ([...issues, ...attachments].some((item) => item.state === "needs_attachment")) {
    return "needs_attachment";
  }
  if ((issues.length || attachments.length) && [...issues, ...attachments].every((item) => item.state !== "pending")) {
    return "accepted";
  }
  return "pending";
}

function reviewPreparationDispositionLabel(value: string | null | undefined) {
  switch (value) {
    case "eligible":
      return "eligible（可进入 preparation）";
    case "rejected":
      return "rejected（明确不进入 promotion）";
    default:
      return "deferred（仍待补充/待确认）";
  }
}

export function ReviewDecisionPanel({
  taskId,
  issues,
  attachments,
  decision,
  reviewPreparation,
  onSaved,
}: {
  taskId: string;
  issues: ReviewIssue[];
  attachments: AttachmentVisibilityMatrixItem[];
  decision?: ReviewerDecision | null;
  reviewPreparation?: ReviewPreparationSummary | null;
  onSaved: (next: TaskRecord) => void;
}) {
  const fallbackDecision = useMemo(() => buildFallbackDecision(issues, attachments), [attachments, issues]);
  const [form, setForm] = useState<ReviewerDecisionUpdateRequest>(
    decision
      ? {
          taskState: decision.taskState,
          note: decision.note || "",
          issues: decision.issues.map((item) => ({ ...item, note: item.note || "" })),
          attachments: decision.attachments.map((item) => ({ ...item, note: item.note || "" })),
        }
      : fallbackDecision,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setForm(
      decision
        ? {
            taskState: decision.taskState,
            note: decision.note || "",
            issues: decision.issues.map((item) => ({ ...item, note: item.note || "" })),
            attachments: decision.attachments.map((item) => ({ ...item, note: item.note || "" })),
          }
        : fallbackDecision,
    );
  }, [decision, fallbackDecision]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const nextTask = await updateReviewerDecision(taskId, form);
      onSaved(nextTask);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存复核结论失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card stack-lg">
      <div>
        <p className="eyebrow">Reviewer Decision</p>
        <h2>最小人工复核面板</h2>
      </div>

      <div className="callout">
        UI 使用 reviewer 语义标签展示状态；后端 on-wire enum 保持稳定，以保证历史任务回放与持久化兼容。
      </div>

      <div className="form-grid two-columns">
        <label className="field">
          <span>任务结论</span>
          <select
            value={form.taskState}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                taskState: event.target.value as ReviewerDecisionUpdateRequest["taskState"],
              }))
            }
          >
            {TASK_STATE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>任务备注</span>
          <textarea
            rows={3}
            value={form.note || ""}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                note: event.target.value,
              }))
            }
          />
        </label>
      </div>

      <div className="stack-md">
        <strong>Issue 级复核</strong>
        {issues.length ? (
          issues.map((issue) => {
            const current = form.issues.find((item) => item.issueId === issue.id) || {
              issueId: issue.id,
              state: "pending" as const,
              note: "",
            };
            const issueDisposition = reviewPreparation?.eligibleIssueIds?.includes(issue.id)
              ? "eligible"
              : reviewPreparation?.rejectedIssueIds?.includes(issue.id)
                ? "rejected"
                : "deferred";
            return (
              <article className="boundary-item" key={issue.id}>
                <div className="section-heading compact">
                  <div>
                    <h3>
                      {issue.id} · {issue.title}
                    </h3>
                    <p className="muted small">
                      {issue.layer} / {issue.severity} / {issue.findingType}
                    </p>
                    <p className="muted small">promotion disposition={reviewPreparationDispositionLabel(issueDisposition)}</p>
                  </div>
                </div>
                <div className="form-grid two-columns">
                  <label className="field">
                    <span>状态</span>
                    <select
                      value={current.state}
                      onChange={(event) =>
                        setForm((formState) => {
                          const nextIssues = formState.issues.map((item) =>
                            item.issueId === issue.id
                              ? { ...item, state: event.target.value as ReviewerIssueDecision["state"] }
                              : item,
                          );
                          return {
                            ...formState,
                            taskState: deriveTaskState(nextIssues, formState.attachments),
                            issues: nextIssues,
                          };
                        })
                      }
                    >
                      {ITEM_STATE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>备注</span>
                    <textarea
                      rows={2}
                      value={current.note || ""}
                      onChange={(event) =>
                        setForm((formState) => ({
                          ...formState,
                          issues: formState.issues.map((item) =>
                            item.issueId === issue.id
                              ? { ...item, note: event.target.value }
                              : item,
                          ),
                        }))
                      }
                    />
                  </label>
                </div>
              </article>
            );
          })
        ) : (
          <p className="muted">当前没有可复核的 issue。</p>
        )}
      </div>

      <div className="stack-md">
        <strong>附件级复核</strong>
        {attachments.length ? (
          attachments.map((item) => {
            const current = form.attachments.find((attachment) => attachment.attachmentId === item.id) || {
              attachmentId: item.id,
              state: "pending" as const,
              note: "",
            };
            const attachmentDisposition = reviewPreparation?.eligibleAttachmentIds?.includes(item.id)
              ? "eligible"
              : reviewPreparation?.rejectedAttachmentIds?.includes(item.id)
                ? "rejected"
                : "deferred";
            return (
              <article className="boundary-item" key={item.id}>
                <div className="section-heading compact">
                  <div>
                    <h3>
                      {item.attachmentNumber || item.id} · {item.title}
                    </h3>
                    <p className="muted small">
                      visibility={item.visibility} / parseState={item.parseState}
                    </p>
                    <p className="muted small">promotion disposition={reviewPreparationDispositionLabel(attachmentDisposition)}</p>
                  </div>
                </div>
                <div className="form-grid two-columns">
                  <label className="field">
                    <span>状态</span>
                    <select
                      value={current.state}
                      onChange={(event) =>
                        setForm((formState) => {
                          const nextAttachments = formState.attachments.map((attachment) =>
                            attachment.attachmentId === item.id
                              ? { ...attachment, state: event.target.value as ReviewerIssueDecision["state"] }
                              : attachment,
                          );
                          return {
                            ...formState,
                            taskState: deriveTaskState(formState.issues, nextAttachments),
                            attachments: nextAttachments,
                          };
                        })
                      }
                    >
                      {ITEM_STATE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>备注</span>
                    <textarea
                      rows={2}
                      value={current.note || ""}
                      onChange={(event) =>
                        setForm((formState) => ({
                          ...formState,
                          attachments: formState.attachments.map((attachment) =>
                            attachment.attachmentId === item.id
                              ? { ...attachment, note: event.target.value }
                              : attachment,
                          ),
                        }))
                      }
                    />
                  </label>
                </div>
              </article>
            );
          })
        ) : (
          <p className="muted">当前没有附件级复核项。</p>
        )}
      </div>

      {error ? <p className="error-text">{error}</p> : null}
      <div className="form-footer">
        <button className="primary-button" disabled={saving} onClick={handleSave} type="button">
          {saving ? "保存中…" : "保存复核结论"}
        </button>
        {decision?.updatedAt ? (
          <p className="muted small">上次保存：{new Date(decision.updatedAt).toLocaleString()}</p>
        ) : (
          <p className="muted small">尚未保存，默认状态均为 pending（待处理）。</p>
        )}
      </div>
    </section>
  );
}
