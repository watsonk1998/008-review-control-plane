"use client";

import type {
  CreateTaskRequest,
  ReviewDocumentType,
  SupportScopeResponse,
} from "@/types/control-plane";

const DOCUMENT_TYPE_OPTIONS: Array<{ value: ReviewDocumentType; label: string }> = [
  { value: "construction_org", label: "施工组织设计" },
  { value: "hazardous_special_scheme", label: "危大专项方案" },
  { value: "construction_scheme", label: "一般施工方案（骨架）" },
  { value: "supervision_plan", label: "监理规划（骨架）" },
  { value: "review_support_material", label: "审查辅助材料（骨架）" },
];

const DISCIPLINE_OPTIONS = [
  { value: "lifting_operations", label: "起重吊装" },
  { value: "temporary_power", label: "临时用电" },
  { value: "hot_work", label: "动火作业" },
  { value: "gas_area_ops", label: "煤气区域" },
  { value: "special_equipment", label: "特种设备" },
  { value: "working_at_height", label: "高处作业" },
];

interface StructuredReviewFormProps {
  form: CreateTaskRequest;
  setForm: React.Dispatch<React.SetStateAction<CreateTaskRequest>>;
  supportScope?: SupportScopeResponse | null;
}

export function StructuredReviewForm({
  form,
  setForm,
  supportScope,
}: StructuredReviewFormProps) {
  if (form.taskType !== "structured_review") {
    return null;
  }

  const selectedTags = new Set(form.disciplineTags || []);
  const documentSupportMap = new Map(
    (supportScope?.documentTypes || []).map((item) => [item.documentType, item.readiness]),
  );
  const selectedDocumentType = form.documentType || "construction_org";
  const documentReadiness = documentSupportMap.get(selectedDocumentType);
  const relevantPacks = (supportScope?.packs || []).filter((pack) => {
    if (pack.docTypes.includes(selectedDocumentType)) return true;
    return pack.disciplineTags.some((tag) => selectedTags.has(tag));
  });
  const readyPacks = relevantPacks.filter((pack) => pack.readiness === "ready");
  const placeholderPacks = relevantPacks.filter((pack) => pack.readiness === "placeholder");

  return (
    <section className="stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Structured Review Profile</p>
          <h3>正式审查参数</h3>
        </div>
        <p className="muted small">支持范围只以 `/api/tasks/support-scope` 为准；文档类型的 official / skeleton 与 pack readiness 不再前端硬编码。</p>
      </div>

      {documentReadiness === "skeleton" ? (
        <div className="callout warning-callout">
          当前所选文档类型仍属 skeleton / experimental。系统会如实展示已 ready 的 pack，但不会把该 documentType 伪装成 official support。
        </div>
      ) : null}
      {!documentReadiness ? <div className="callout">support-scope 加载中；未返回前不展示本地 fallback 结论。</div> : null}

      <div className="form-grid review-profile-grid">
        <label className="field">
          <span>文档类型</span>
          <select
            value={form.documentType || "construction_org"}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                documentType: event.target.value as ReviewDocumentType,
              }))
            }
          >
            {DOCUMENT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>审查策略</span>
          <label className="checkbox-row inline-check">
            <input
              checked={form.strictMode ?? true}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  strictMode: event.target.checked,
                }))
              }
              type="checkbox"
            />
            <span>strictMode（保留字段）</span>
          </label>
          <small>当前仅作为兼容字段透传，尚未启用新的裁决语义。</small>
        </label>
      </div>

      <div className="field">
        <span>专业标签</span>
        <div className="review-discipline-grid">
          {DISCIPLINE_OPTIONS.map((option) => (
            <label className="checkbox-row inline-check" key={option.value}>
              <input
                checked={selectedTags.has(option.value)}
                onChange={(event) =>
                  setForm((current) => {
                    const next = new Set(current.disciplineTags || []);
                    if (event.target.checked) {
                      next.add(option.value);
                    } else {
                      next.delete(option.value);
                    }
                    return {
                      ...current,
                      disciplineTags: Array.from(next),
                    };
                  })
                }
                type="checkbox"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        <small>可留空，后端仍会根据 query、fixture 与 parse hints 自动补齐。</small>
      </div>

      {documentReadiness ? (
        <div className="callout">
          <strong>当前 support-scope</strong>
          <p>documentType readiness：{documentReadiness}</p>
          <p>ready packs：{readyPacks.map((pack) => pack.packId).join("，") || "无"}</p>
          <p>placeholder packs：{placeholderPacks.map((pack) => pack.packId).join("，") || "无"}</p>
        </div>
      ) : null}
    </section>
  );
}
