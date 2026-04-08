"use client";

import type {
  CreateTaskRequest,
  ReviewDocumentType,
  SupportScopeResponse,
} from "@/types/control-plane";

const FALLBACK_DOCUMENT_OPTIONS: Array<{ value: ReviewDocumentType; label: string }> = [
  { value: "construction_org", label: "施工组织设计" },
  { value: "hazardous_special_scheme", label: "危大工程专项施工方案" },
  { value: "distribution_network_special_scheme", label: "配网工程专项施工方案" },
  { value: "construction_scheme", label: "一般施工方案" },
  { value: "supervision_plan", label: "监理规划" },
  { value: "review_support_material", label: "审查辅助材料" },
];

type ReviewCategoryKey = 
  | "construction_org" 
  | "construction_scheme" 
  | "special_scheme_review" 
  | "supervision_plan" 
  | "review_support_material";

const CATEGORY_OPTIONS: Array<{ value: ReviewCategoryKey; label: string }> = [
  { value: "construction_org", label: "施工组织设计审查" },
  { value: "construction_scheme", label: "一般施工方案审查" },
  { value: "special_scheme_review", label: "专项方案审查" },
  { value: "supervision_plan", label: "监理规划审查" },
  { value: "review_support_material", label: "审查辅助材料" },
];

function getCategoryForDocumentType(docType: ReviewDocumentType): ReviewCategoryKey {
  if (docType === "hazardous_special_scheme" || docType === "distribution_network_special_scheme") {
    return "special_scheme_review";
  }
  return docType as ReviewCategoryKey;
}

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

function getDefaultSpecialFamily(
  capabilityEntry: ReturnType<typeof getCapabilityEntry>
): ReviewDocumentType {
  return capabilityEntry?.families[0]?.documentType || "hazardous_special_scheme";
}

function getSelectedFamily(
  documentType: ReviewDocumentType,
  capabilityEntry: ReturnType<typeof getCapabilityEntry>
) {
  return capabilityEntry?.families.find((family) => family.documentType === documentType) || null;
}

function getCrossCuttingModules(
  documentType: ReviewDocumentType,
  capabilityEntry: ReturnType<typeof getCapabilityEntry>
) {
  return capabilityEntry?.crossCuttingModules.filter((module) => module.docTypes.includes(documentType)) || [];
}

function getAllowedTags(
  documentType: ReviewDocumentType,
  supportScope?: SupportScopeResponse | null,
) {
  const capabilityEntry = getCapabilityEntry(supportScope);
  const family = getSelectedFamily(documentType, capabilityEntry);
  const familyTags = family?.children.map((item) => item.tag) || [];
  const crossCuttingTags = getCrossCuttingModules(documentType, capabilityEntry).map((item) => item.tag) || [];
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

function getRelevantPacks(
  documentType: ReviewDocumentType,
  selectedTags: Set<string>,
  supportScope?: SupportScopeResponse | null,
) {
  return (supportScope?.packs || []).filter((pack) => {
    if (pack.docTypes.includes(documentType)) return true;
    return pack.disciplineTags.some((tag) => selectedTags.has(tag));
  });
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
  const currentCategory = getCategoryForDocumentType(selectedDocumentType);
  const capabilityEntry = getCapabilityEntry(supportScope);
  
  const documentSupportMap = new Map(
    (supportScope?.documentTypes || []).map((item) => [item.documentType, item.readiness]),
  );
  const documentLabelMap = new Map(
    (supportScope?.documentTypes || []).map((item) => [item.documentType, item.label]),
  );
  
  const documentReadiness = documentSupportMap.get(selectedDocumentType);
  const selectedFamily = getSelectedFamily(selectedDocumentType, capabilityEntry);
  const crossCuttingModules = getCrossCuttingModules(selectedDocumentType, capabilityEntry);
    
  const relevantPacks = getRelevantPacks(selectedDocumentType, selectedTags, supportScope);
  const readyPacks = relevantPacks.filter((pack) => pack.readiness === "ready");
  const placeholderPacks = relevantPacks.filter((pack) => pack.readiness === "placeholder");

  const handleCategoryChange = (category: ReviewCategoryKey) => {
    let nextDocType: ReviewDocumentType;
    if (category === "special_scheme_review") {
      nextDocType = getDefaultSpecialFamily(capabilityEntry);
    } else {
      nextDocType = category as ReviewDocumentType;
    }
    
    setForm((current) => ({
      ...current,
      documentType: nextDocType,
      disciplineTags: sanitizeDisciplineTags(nextDocType, current.disciplineTags, supportScope),
    }));
  };

  const handleFamilyChange = (nextDocType: ReviewDocumentType) => {
    setForm((current) => ({
      ...current,
      documentType: nextDocType,
      disciplineTags: sanitizeDisciplineTags(nextDocType, current.disciplineTags, supportScope),
    }));
  };

  const toggleDisciplineTag = (tag: string, checked: boolean) => {
    setForm((current) => {
      const next = new Set(sanitizeDisciplineTags(selectedDocumentType, current.disciplineTags, supportScope));
      if (checked) {
        next.add(tag);
      } else {
        next.delete(tag);
      }
      return {
        ...current,
        disciplineTags: Array.from(next),
      };
    });
  };

  return (
    <section className="stack-lg">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">结构化审查级联配置</p>
          <h3>正式审查参数</h3>
        </div>
        <p className="muted small">
          支持范围只以 `/api/tasks/support-scope` 为准；产品展示按“一级审查类别 → 二级方案大类 → 三级专项”选择审查范围。
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
          <span>一级审查类别</span>
          <select
            value={currentCategory}
            onChange={(event) => handleCategoryChange(event.target.value as ReviewCategoryKey)}
          >
            {CATEGORY_OPTIONS.map((option) => (
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
        {capabilityEntry ? (
          <div className="stack-md">
            {currentCategory === "special_scheme_review" ? (
              <>
                <div className="stack-sm">
                  <strong>二级方案大类</strong>
                  {capabilityEntry.families.length > 0 ? (
                    <div className="review-discipline-grid">
                      {capabilityEntry.families.map((family) => (
                        <label className="checkbox-row inline-check" key={family.familyKey}>
                          <input
                            type="radio"
                            name="secondary_family"
                            value={family.documentType}
                            checked={selectedDocumentType === family.documentType}
                            onChange={() => handleFamilyChange(family.documentType)}
                          />
                          <span>
                            {family.label}（{READINESS_MAP[family.readiness] || family.readiness}）
                          </span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="callout">能力树加载中或不可用。</div>
                  )}
                </div>

                {selectedFamily ? (
                  <div className="stack-sm">
                    <strong>三级专项（按所选专项叠加审查）</strong>
                    <div className="review-discipline-grid">
                      {selectedFamily.children.map((item) => (
                        <label className="checkbox-row inline-check" key={item.tag}>
                          <input
                            checked={selectedTags.has(item.tag)}
                            onChange={(e) => toggleDisciplineTag(item.tag, e.target.checked)}
                            type="checkbox"
                          />
                          <span>
                            {item.label}（{READINESS_MAP[item.readiness] || item.readiness}）
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="callout">
                该类文档按主审查对象基础模块与附加风险模块执行。
              </div>
            )}

            {crossCuttingModules.length > 0 ? (
              <div className="stack-sm">
                <strong>附加风险模块</strong>
                <div className="review-discipline-grid">
                  {crossCuttingModules.map((item) => (
                    <label className="checkbox-row inline-check" key={item.tag}>
                      <input
                        checked={selectedTags.has(item.tag)}
                        onChange={(e) => toggleDisciplineTag(item.tag, e.target.checked)}
                        type="checkbox"
                      />
                      <span>
                        {item.label}（{READINESS_MAP[item.readiness] || item.readiness}）
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="stack-md">
            <span className="muted small">专项能力树暂不可用，请稍后重试</span>
          </div>
        )}
      </div>

      {documentReadiness ? (
        <div className="callout">
          <strong>当前链路支持度</strong>
          <p>
            主文档可用性：
            {documentLabelMap.get(selectedDocumentType) || selectedDocumentType} ·{" "}
            {READINESS_MAP[(documentReadiness || "").trim().toLowerCase()] || documentReadiness}
          </p>
          {selectedFamily && currentCategory === "special_scheme_review" ? (
            <p>主专项族：{selectedFamily.label}（二级基础 pack）</p>
          ) : null}
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

