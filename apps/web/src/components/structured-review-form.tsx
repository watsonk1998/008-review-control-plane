"use client";

import type { CreateTaskRequest, ReviewDocumentType } from "@/types/control-plane";

const DOCUMENT_TYPE_OPTIONS: Array<{ value: ReviewDocumentType; label: string }> = [
  { value: "construction_org", label: "施工组织设计" },
  { value: "hazardous_special_scheme", label: "危大专项方案" },
  { value: "construction_scheme", label: "一般施工方案" },
  { value: "supervision_plan", label: "监理规划" },
  { value: "review_support_material", label: "审查辅助材料" },
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
}

export function StructuredReviewForm({
  form,
  setForm,
}: StructuredReviewFormProps) {
  if (form.taskType !== "structured_review") {
    return null;
  }

  const selectedTags = new Set(form.disciplineTags || []);

  return (
    <section className="stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Structured Review Profile</p>
          <h3>正式审查参数</h3>
        </div>
        <p className="muted small">默认输出问题、证据、矩阵与 Markdown 报告。</p>
      </div>

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
            <span>严格模式（默认开启）</span>
          </label>
          <small>关闭后会减少保守型人工复核提示，但仍输出结构化结果。</small>
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
