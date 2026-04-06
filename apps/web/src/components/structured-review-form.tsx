"use client";

import type {
  CreateTaskRequest,
  ReviewDocumentType,
  SupportScopeResponse,
} from "@/types/control-plane";

const DOCUMENT_TYPE_OPTIONS: Array<{ value: ReviewDocumentType; label: string }> = [
  { value: "construction_org", label: "施工组织设计" },
  { value: "hazardous_special_scheme", label: "危大专项方案" },
  { value: "construction_scheme", label: "一般施工方案（experimental）" },
  { value: "supervision_plan", label: "监理规划（experimental）" },
  { value: "review_support_material", label: "审查辅助材料（experimental）" },
];

const DISCIPLINE_OPTIONS = [
  { value: "lifting_operations", label: "起重吊装" },
  { value: "temporary_power", label: "临时用电" },
  { value: "hot_work", label: "动火作业" },
  { value: "gas_area_ops", label: "煤气区域" },
  { value: "special_equipment", label: "特种设备" },
  { value: "working_at_height", label: "高处作业" },
];

function getChinesePackName(packId: string) {
  const pureId = packId.replace('.base', '');
  const docTypeMatch = DOCUMENT_TYPE_OPTIONS.find(o => o.value === pureId);
  if (docTypeMatch) return docTypeMatch.label + " (基础模块)";
  const disciplineMatch = DISCIPLINE_OPTIONS.find(o => o.value === pureId);
  if (disciplineMatch) return disciplineMatch.label + " (基础模块)";
  return packId;
}

function renderPromotionCriteria(criteria: Record<string, boolean>) {
  const order = [
    ["testsReady", "测试用例"],
    ["versionedCasesReady", "基准样本"],
    ["policyEvidenceReady", "政策依据"],
    ["ruleCoverage", "规则覆盖率"],
  ] as const;
  return order
    .map(([key, label]) => `${label}:${criteria[key] ? "✓" : "✗"}`)
    .join(" / ");
}

interface StructuredReviewFormProps {
  form: CreateTaskRequest;
  setForm: React.Dispatch<React.SetStateAction<CreateTaskRequest>>;
  supportScope?: SupportScopeResponse | null;
}

const READINESS_MAP: Record<string, string> = {
  official: "稳定支持",
  experimental: "实验性特性",
  skeleton: "骨架开发中",
  ready: "正式就绪",
  placeholder: "占位开发中",
};

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
          <p className="eyebrow">结构化审查级联配置</p>
          <h3>正式审查参数</h3>
        </div>
          <p className="muted small">支持范围只以 `/api/tasks/support-scope` 为准；documentType readiness 与 pack readiness 明确分离。</p>
        </div>

      {documentReadiness === "experimental" ? (
        <div className="callout warning-callout">
          当前所选文档类型处于“实验性方案”阶段。系统会如实展示已就绪的执行模块，但这并不代表该系统已具备在此文档上的稳定自动化审查能力。
        </div>
      ) : null}
      {documentReadiness === "skeleton" ? (
        <div className="callout warning-callout">
          当前所选文档类型仍处于“骨架开发”期。可查看初步覆盖范围，但这绝不代表目前拥有的系统已达到正式基线支持标准。
        </div>
      ) : null}
      {!documentReadiness ? <div className="callout">网络域加载中：环境未同步之前，系统将默认阻断所有推理操作。</div> : null}

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
            <span>严格匹配规则（保留特性）</span>
          </label>
          <small>当前仅作为兼容字段透传给后端，后续将介入正式降级拦截。</small>
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
        <small>可留空，后端仍会根据查询词、上传样本及解析摘要自动补全所需策略包。</small>
      </div>

      {documentReadiness ? (
        <div className="callout">
          <strong>当前链路支持度</strong>
          <p>主文档可用性：{READINESS_MAP[(documentReadiness || "").trim().toLowerCase()] || documentReadiness}</p>
          <p>已就绪模块：{readyPacks.map((pack) => getChinesePackName(pack.packId)).join("，") || "无"}</p>
          <p>排期中模块：{placeholderPacks.map((pack) => getChinesePackName(pack.packId)).join("，") || "无"}</p>
          {relevantPacks.length ? (
            <div className="stack-sm">
              <strong>策略包晋升准入条件</strong>
              <ul className="source-list">
                {relevantPacks.map((pack) => (
                  <li key={pack.packId}>
                    <strong>
                      {getChinesePackName(pack.packId)} · {READINESS_MAP[(pack.readiness || "").trim().toLowerCase()] || pack.readiness}
                    </strong>
                    <p className="muted small">{renderPromotionCriteria(pack.promotionCriteria || {})}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="muted small">说明：单项模块就绪仅代表该逻辑节点可独立流转，绝不意味着全局链路已达到官方安全验收基线标准。</p>
        </div>
      ) : null}
    </section>
  );
}
