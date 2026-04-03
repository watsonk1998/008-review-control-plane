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

const P0_SUPPORTED_DOC_TYPES = new Set<ReviewDocumentType>([
  "construction_org",
  "hazardous_special_scheme",
]);

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
  const isP0Supported =
    (documentSupportMap.get(selectedDocumentType) || (P0_SUPPORTED_DOC_TYPES.has(selectedDocumentType) ? "official" : "skeleton")) ===
    "official";

  return (
    <section className="stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Structured Review Profile</p>
          <h3>正式审查参数</h3>
        </div>
        <p className="muted small">当前 P0 正式支持范围：施工组织设计、危大专项方案；其余类型仅保留骨架入口。</p>
      </div>

      {!isP0Supported ? (
        <div className="callout warning-callout">
          当前所选文档类型仍属 skeleton / experimental。P0 成功标准不覆盖该类型，建议改用施工组织设计或危大专项方案。
        </div>
      ) : null}

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
    </section>
  );
}
