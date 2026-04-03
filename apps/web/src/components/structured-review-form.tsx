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
  policyPackInput: string;
  setPolicyPackInput: React.Dispatch<React.SetStateAction<string>>;
}

export function StructuredReviewForm({
  form,
  setForm,
  policyPackInput,
  setPolicyPackInput,
}: StructuredReviewFormProps) {
  if (form.taskType !== "structured_review") {
    return null;
  }

  const selectedTags = new Set(form.disciplineTags || []);

  return (
    <section className="card stack-lg">
      <div>
        <p className="eyebrow">Structured Review Profile</p>
        <h3>正式审查参数</h3>
        <p className="muted small">
          P1 起 structured_review 支持显式传入 documentType、disciplineTags、strictMode 与 policyPackIds。
        </p>
      </div>

      <div className="form-grid two-columns">
        <label className="field">
          <span>documentType</span>
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
          <span>strictMode</span>
          <label className="checkbox-row">
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
            <span>默认开启严格模式</span>
          </label>
          <small>关闭后仍保留结构化输出，但会降低人工复核/缺口类提示的保守性。</small>
        </label>
      </div>

      <div className="field">
        <span>disciplineTags</span>
        <div className="form-grid two-columns">
          {DISCIPLINE_OPTIONS.map((option) => (
            <label className="checkbox-row" key={option.value}>
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
        <small>可留空，后端仍会根据 query / fixture / parse hints 自动补齐。</small>
      </div>

      <label className="field">
        <span>policyPackIds（高级覆盖，可选）</span>
        <textarea
          rows={3}
          value={policyPackInput}
          onChange={(event) => setPolicyPackInput(event.target.value)}
          placeholder={"construction_org.base\nlifting_operations.base"}
        />
        <small>留空表示自动选 pack；填写后按“基础 pack + 指定 pack”组合执行。</small>
      </label>
    </section>
  );
}
