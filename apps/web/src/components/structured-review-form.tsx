import type { CreateTaskRequest, ReviewDocumentType, SupportScopeResponse } from "@/types/control-plane";
import { useEffect, useMemo } from "react";

export interface StructuredReviewFormProps {
  form: CreateTaskRequest;
  setForm: React.Dispatch<React.SetStateAction<CreateTaskRequest>>;
  supportScope?: SupportScopeResponse | null;
}

type TaxonomyChild = {
  tag: string;
  label: string;
};

type TaxonomyFamily = {
  documentType: ReviewDocumentType;
  label: string;
  tags: TaxonomyChild[];
};

type TaxonomyGroup = {
  l1Key: string;
  l1Label: string;
  families: TaxonomyFamily[];
};

const ENTRY_LABEL_OVERRIDES: Record<string, string> = {
  special_scheme_review: "危大工程专项方案类",
  general_management_review: "一般专项与管理体系类",
  construction_org_review: "施工组织设计审查",
};

const DOCUMENT_LABEL_OVERRIDES: Partial<Record<ReviewDocumentType, string>> = {
  distribution_network_special_scheme: "配电配网工程",
  construction_org: "施工组织设计类",
  construction_scheme: "一般施工方案",
  hazardous_special_scheme: "危大工程专项施工方案",
  supervision_plan: "监理规划",
  review_support_material: "审查辅助材料",
};

const TAG_LABEL_OVERRIDES: Record<string, string> = {
  power_outage_work: "停电/涉电施工作业工程",
};

const FALLBACK_TAXONOMY: TaxonomyGroup[] = [
  {
    l1Key: "construction_org_review",
    l1Label: "施工组织设计审查",
    families: [
      { documentType: "construction_org", label: "施工组织设计", tags: [] },
    ],
  },
  {
    l1Key: "special_scheme_review",
    l1Label: "危大工程专项方案类",
    families: [
      { documentType: "hazardous_special_scheme", label: "危大工程专项方案", tags: [] },
    ],
  },
  {
    l1Key: "general_management_review",
    l1Label: "一般专项与管理体系类",
    families: [
      {
        documentType: "distribution_network_special_scheme",
        label: "配电配网工程",
        tags: [{ tag: "power_outage_work", label: "停电/涉电施工作业工程" }],
      },
      { documentType: "construction_scheme", label: "一般专项施工方案", tags: [] },
      { documentType: "supervision_plan", label: "监理规划", tags: [] },
      { documentType: "review_support_material", label: "审查辅助材料", tags: [] },
    ],
  },
];

function documentLabel(documentType: ReviewDocumentType, fallback?: string) {
  return DOCUMENT_LABEL_OVERRIDES[documentType] || fallback || documentType;
}

function tagLabel(tag: string, fallback?: string) {
  return TAG_LABEL_OVERRIDES[tag] || fallback || tag;
}

function buildTaxonomy(supportScope?: SupportScopeResponse | null): TaxonomyGroup[] {
  const capabilityTree = supportScope?.capabilityTree || [];
  if (!capabilityTree.length) {
    return FALLBACK_TAXONOMY;
  }

  const taxonomy = capabilityTree
    .map((entry) => ({
      l1Key: entry.entryKey,
      l1Label: ENTRY_LABEL_OVERRIDES[entry.entryKey] || entry.label,
      families: entry.families.map((family) => ({
        documentType: family.documentType,
        label: documentLabel(family.documentType, family.label),
        tags: family.children.map((child) => ({
          tag: child.tag,
          label: tagLabel(child.tag, child.label),
        })),
      })),
    }))
    .filter((entry) => entry.families.length > 0);

  const existingKeys = new Set(taxonomy.map((entry) => entry.l1Key));
  const familyKeys = new Set(taxonomy.flatMap((entry) => entry.families.map((family) => family.documentType)));

  for (const fallbackGroup of FALLBACK_TAXONOMY) {
    const targetGroup = taxonomy.find((entry) => entry.l1Key === fallbackGroup.l1Key);
    if (!targetGroup) {
      taxonomy.push(fallbackGroup);
      existingKeys.add(fallbackGroup.l1Key);
      fallbackGroup.families.forEach((family) => familyKeys.add(family.documentType));
      continue;
    }
    for (const family of fallbackGroup.families) {
      if (familyKeys.has(family.documentType)) continue;
      targetGroup.families.push(family);
      familyKeys.add(family.documentType);
    }
    if (!existingKeys.has(fallbackGroup.l1Key)) {
      taxonomy.push(fallbackGroup);
      existingKeys.add(fallbackGroup.l1Key);
    }
  }

  return taxonomy;
}

function findSelection(taxonomy: TaxonomyGroup[], documentType?: ReviewDocumentType, disciplineTags?: string[]) {
  for (const group of taxonomy) {
    for (const family of group.families) {
      if (family.documentType !== documentType) continue;
      const validTags = new Set(family.tags.map((item) => item.tag));
      const selectedTags = (disciplineTags || []).filter((tag) => validTags.has(tag));
      return { group, family, selectedTags };
    }
  }

  const fallbackGroup =
    taxonomy.find((entry) => entry.l1Key === "general_management_review") ||
    taxonomy[0] ||
    FALLBACK_TAXONOMY[0];
  const fallbackFamily =
    fallbackGroup.families.find((family) => family.documentType === "distribution_network_special_scheme") ||
    fallbackGroup.families[0];
  return { group: fallbackGroup, family: fallbackFamily, selectedTags: [] as string[] };
}

export function StructuredReviewForm({ form, setForm, supportScope }: StructuredReviewFormProps) {
  const taxonomy = useMemo(() => buildTaxonomy(supportScope), [supportScope]);
  const selection = useMemo(
    () => findSelection(taxonomy, form.documentType, form.disciplineTags),
    [taxonomy, form.disciplineTags, form.documentType],
  );

  useEffect(() => {
    const normalizedDocumentType = selection.family.documentType;
    const nextTags = selection.selectedTags;
    const currentTags = form.disciplineTags || [];
    const tagsChanged = currentTags.length !== nextTags.length || currentTags.some((tag) => !nextTags.includes(tag));

    if (form.documentType !== normalizedDocumentType || tagsChanged) {
      setForm((current) => ({
        ...current,
        documentType: normalizedDocumentType,
        disciplineTags: nextTags,
      }));
    }
  }, [form.disciplineTags, form.documentType, selection.family.documentType, selection.selectedTags, setForm]);

  if (form.taskType !== "structured_review") {
    return null;
  }

  const handleL1Change = (newL1Key: string) => {
    const group = taxonomy.find((entry) => entry.l1Key === newL1Key) || taxonomy[0];
    const family = group.families[0];
    setForm((current) => ({
      ...current,
      documentType: family.documentType,
      disciplineTags: [],
    }));
  };

  const handleL2Change = (newDocumentType: ReviewDocumentType) => {
    const family = selection.group.families.find((item) => item.documentType === newDocumentType) || selection.group.families[0];
    setForm((current) => ({
      ...current,
      documentType: family.documentType,
      disciplineTags: [],
    }));
  };

  const toggleTag = (tag: string, checked: boolean) => {
    setForm((current) => {
      const next = new Set(current.disciplineTags || []);
      if (checked) next.add(tag);
      else next.delete(tag);
      return { ...current, disciplineTags: Array.from(next) };
    });
  };

  const selectedTags = new Set(selection.selectedTags);

  return (
    <div className="stack-lg">
      <div className="form-grid review-profile-grid">
        <label className="field">
          <span style={{ fontWeight: 600, color: "#334155" }}>业务领域与一级分类</span>
          <select
            value={selection.group.l1Key}
            onChange={(e) => handleL1Change(e.target.value)}
            style={{ padding: "16px 14px", borderColor: "#CBD5E1", borderRadius: "18px" }}
          >
            {taxonomy.map((group) => (
              <option key={group.l1Key} value={group.l1Key}>
                {group.l1Label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="field">
        <div className="stack-md">
          <div className="stack-sm">
            <strong style={{ display: "block", marginBottom: "8px", color: "#475569" }}>方案大类</strong>
            <div className="review-discipline-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              {selection.group.families.map((family) => (
                <label
                  className="checkbox-row inline-check"
                  key={family.documentType}
                  style={{
                    background: "#F7F5F0",
                    padding: "18px 16px",
                    borderRadius: "18px",
                    border: selection.family.documentType === family.documentType ? "1px solid #0B192C" : "1px solid transparent",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="l2_family"
                    checked={selection.family.documentType === family.documentType}
                    onChange={() => handleL2Change(family.documentType)}
                  />
                  <span style={{ fontWeight: selection.family.documentType === family.documentType ? 600 : 400, color: "#0F172A" }}>
                    {family.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {selection.family.tags.length > 0 && (
            <div className="stack-sm" style={{ marginTop: "16px" }}>
              <strong style={{ display: "block", marginBottom: "8px", color: "#475569" }}>附加细分专项</strong>
              <div className="review-discipline-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {selection.family.tags.map((tag) => (
                  <label
                    className="checkbox-row inline-check"
                    key={tag.tag}
                    style={{
                      background: selectedTags.has(tag.tag) ? "#FFFFFF" : "#F8F5EF",
                      padding: "16px 14px",
                      borderRadius: "18px",
                      border: selectedTags.has(tag.tag) ? "1px solid #D7D1C6" : "1px solid #ECE7DF",
                      cursor: "pointer",
                    }}
                  >
                    <input type="checkbox" checked={selectedTags.has(tag.tag)} onChange={(e) => toggleTag(tag.tag, e.target.checked)} />
                    <span style={{ color: "#334155" }}>{tag.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
