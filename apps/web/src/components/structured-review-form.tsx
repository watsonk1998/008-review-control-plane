"use client";

import type {
  CreateTaskRequest,
  ReviewDocumentType,
  SupportScopeResponse,
} from "@/types/control-plane";

const FALLBACK_DOCUMENT_OPTIONS: Array<{ value: ReviewDocumentType; label: string }> = [
  { value: "construction_org", label: "施工组织设计" },
  { value: "hazardous_special_scheme", label: "危大工程专项施工方案" },
  { value: "distribution_network_special_scheme", label: "配网工程专项施工方案（experimental）" },
  { value: "construction_scheme", label: "一般施工方案（experimental）" },
  { value: "supervision_plan", label: "监理规划（experimental）" },
  { value: "review_support_material", label: "审查辅助材料（experimental）" },
];

const LEGACY_DISCIPLINE_OPTIONS = [
  { value: "lifting_operations", label: "起重吊装（横向风险）" },
  { value: "temporary_power", label: "临时用电 / 停送电" },
  { value: "hot_work", label: "动火作业" },
  { value: "gas_area_ops", label: "煤气区域" },
  { value: "special_equipment", label: "特种设备" },
  { value: "working_at_height", label: "高处作业" },
];

function getChinesePackName(
  packId: string,
  supportScope?: SupportScopeResponse | null,
) {
  const fromScope = supportScope?.packs.find((pack) => pack.packId === packId)?.label;
  if (fromScope) return fromScope;
  const pureId = packId.replace(".base", "");
  const docTypeMatch = FALLBACK_DOCUMENT_OPTIONS.find((option) => option.value === pureId);
  if (docTypeMatch) return `${docTypeMatch.label} (基础模块)`;
  const disciplineMatch = LEGACY_DISCIPLINE_OPTIONS.find((option) => option.value === pureId);
  if (disciplineMatch) return `${disciplineMatch.label} (基础模块)`;
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

function getCapabilityEntry(supportScope?: SupportScopeResponse | null) {
  return supportScope?.capabilityTree?.find((entry) => entry.entryKey === "special_scheme_review") || null;
}

function getAllowedTags(
  documentType: ReviewDocumentType,
  supportScope?: SupportScopeResponse | null,
) {
  const capabilityEntry = getCapabilityEntry(supportScope);
  const family = capabilityEntry?.families.find((item) => item.documentType === documentType);
  const familyTags = family?.children.map((item) => item.tag) || [];
  const crossCuttingTags =
    capabilityEntry?.crossCuttingModules
      .filter((item) => item.docTypes.includes(documentType))
      .map((item) => item.tag) || [];
  return new Set([...familyTags, ...crossCuttingTags]);
}

function sanitizeDisciplineTags(
  documentType: ReviewDocumentType,
  disciplineTags: string[] | undefined,
  supportScope?: SupportScopeResponse | null,
) {
  const allowedTags = getAllowedTags(documentType, supportScope);
  if (!allowedTags.size) return disciplineTags || [];
  return (disciplineTags || []).filter((tag) => allowedTags.has(tag));
}

export function StructuredReviewForm({
  form,
  setForm,
  supportScope,
}: StructuredReviewFormProps) {
  if (form.taskType !== "structured_review") {
    return null;
  }

  const selectedDocumentType = form.documentType || "construction_org";
  const selectedTags = new Set(form.disciplineTags || []);
  const capabilityEntry = getCapabilityEntry(supportScope);
  const documentSupportMap = new Map(
    (supportScope?.documentTypes || []).map((item) => [item.documentType, item.readiness]),
  );
  const documentLabelMap = new Map(
    (supportScope?.documentTypes || []).map((item) => [item.documentType, item.label]),
  );
  const documentReadiness = documentSupportMap.get(selectedDocumentType);
  const selectedFamily =
    capabilityEntry?.families.find((family) => family.documentType === selectedDocumentType) || null;
  const crossCuttingModules =
    capabilityEntry?.crossCuttingModules.filter((module) => module.docTypes.includes(selectedDocumentType)) || [];
  const relevantPacks = (supportScope?.packs || []).filter((pack) => {
    if (pack.docTypes.includes(selectedDocumentType)) return true;
    return pack.disciplineTags.some((tag) => selectedTags.has(tag));
  });
  const readyPacks = relevantPacks.filter((pack) => pack.readiness === "ready");
  const placeholderPacks = relevantPacks.filter((pack) => pack.readiness === "placeholder");
  const documentOptions = supportScope?.documentTypes?.length
    ? supportScope.documentTypes.map((item) => ({
        value: item.documentType,
        label: item.label,
      }))
    : FALLBACK_DOCUMENT_OPTIONS;

  return (
    <section className="stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">结构化审查级联配置</p>
          <h3>正式审查参数</h3>
        </div>
        <p className="muted small">
          支持范围只以 `/api/tasks/support-scope` 为准；产品展示按“一级入口 → 二级方案大类 → 三级专项”组织。
        </p>
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
      {!documentReadiness ? (
        <div className="callout">网络域加载中：环境未同步之前，系统将默认阻断所有推理操作。</div>
      ) : null}

      <div className="form-grid review-profile-grid">
        <label className="field">
          <span>文档类型</span>
          <select
            value={selectedDocumentType}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                documentType: event.target.value as ReviewDocumentType,
                disciplineTags: sanitizeDisciplineTags(
                  event.target.value as ReviewDocumentType,
                  current.disciplineTags,
                  supportScope,
                ),
              }))
            }
          >
            {documentOptions.map((option) => (
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
        <span>专项方案能力树</span>
        {capabilityEntry ? (
          <div className="stack-md">
            <div className="callout">
              <strong>{capabilityEntry.label}</strong>
              <p className="muted small">
                一级是产品入口；二级是方案大类；三级是具体专项审查单元。横向风险模块不进入主树三级，但仍可按文档风险叠加执行。
              </p>
            </div>

            {selectedFamily ? (
              <div className="stack-sm">
                <strong>
                  二级方案大类：{selectedFamily.label} ·{" "}
                  {READINESS_MAP[selectedFamily.readiness] || selectedFamily.readiness}
                </strong>
                <div className="review-discipline-grid">
                  {selectedFamily.children.map((item) => (
                    <label className="checkbox-row inline-check" key={item.tag}>
                      <input
                        checked={selectedTags.has(item.tag)}
                        onChange={(event) =>
                          setForm((current) => {
                            const next = new Set(
                              sanitizeDisciplineTags(selectedDocumentType, current.disciplineTags, supportScope),
                            );
                            if (event.target.checked) {
                              next.add(item.tag);
                            } else {
                              next.delete(item.tag);
                            }
                            return {
                              ...current,
                              disciplineTags: Array.from(next),
                            };
                          })
                        }
                        type="checkbox"
                      />
                      <span>
                        {item.label}（三级，{READINESS_MAP[item.readiness] || item.readiness}）
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ) : (
              <div className="callout">
                当前文档类型不属于“专项方案审查”能力树的二级方案族。
              </div>
            )}

            {crossCuttingModules.length ? (
              <div className="stack-sm">
                <strong>附加风险模块</strong>
                <div className="review-discipline-grid">
                  {crossCuttingModules.map((item) => (
                    <label className="checkbox-row inline-check" key={item.tag}>
                      <input
                        checked={selectedTags.has(item.tag)}
                        onChange={(event) =>
                          setForm((current) => {
                            const next = new Set(
                              sanitizeDisciplineTags(selectedDocumentType, current.disciplineTags, supportScope),
                            );
                            if (event.target.checked) {
                              next.add(item.tag);
                            } else {
                              next.delete(item.tag);
                            }
                            return {
                              ...current,
                              disciplineTags: Array.from(next),
                            };
                          })
                        }
                        type="checkbox"
                      />
                      <span>
                        {item.label}（附属能力，{READINESS_MAP[item.readiness] || item.readiness}）
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="review-discipline-grid">
            {LEGACY_DISCIPLINE_OPTIONS.map((option) => (
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
        )}
        <small>
          对外展示以“二级方案大类 + 三级专项”为主；内部仍允许叠加横向风险模块，并继续支持自动补全所需策略包。
        </small>
      </div>

      {documentReadiness ? (
        <div className="callout">
          <strong>当前链路支持度</strong>
          <p>
            主文档可用性：
            {documentLabelMap.get(selectedDocumentType) || selectedDocumentType} ·{" "}
            {READINESS_MAP[(documentReadiness || "").trim().toLowerCase()] || documentReadiness}
          </p>
          {selectedFamily ? <p>主专项族：{selectedFamily.label}（二级基础 pack）</p> : null}
          <p>
            已就绪模块：
            {readyPacks.map((pack) => getChinesePackName(pack.packId, supportScope)).join("，") || "无"}
          </p>
          <p>
            排期中模块：
            {placeholderPacks.map((pack) => getChinesePackName(pack.packId, supportScope)).join("，") || "无"}
          </p>
          {relevantPacks.length ? (
            <div className="stack-sm">
              <strong>策略包晋升准入条件</strong>
              <ul className="source-list">
                {relevantPacks.map((pack) => (
                  <li key={pack.packId}>
                    <strong>
                      {getChinesePackName(pack.packId, supportScope)} ·{" "}
                      {READINESS_MAP[(pack.readiness || "").trim().toLowerCase()] || pack.readiness}
                    </strong>
                    <p className="muted small">{renderPromotionCriteria(pack.promotionCriteria || {})}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="muted small">
            说明：单项模块就绪仅代表该逻辑节点可独立流转，绝不意味着全局链路已达到官方安全验收基线标准。
          </p>
        </div>
      ) : null}
    </section>
  );
}
