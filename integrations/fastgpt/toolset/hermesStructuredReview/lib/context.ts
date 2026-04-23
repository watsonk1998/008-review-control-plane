import { getAssets } from './assets.js';
import { parseReviewFile } from './parser.js';
import type { Candidate, ParseResult, ResolvedBasisProfile, ReviewContextInput, ReviewContextResult, RuleHit } from './contracts.js';
import { unique } from './utils.js';

const coreSectionKeywords: Record<string, Array<{ itemKey: string; keywords: string[] }>> = {
  construction_org: [
    { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
    { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
    { itemKey: 'constructionDeployment', keywords: ['施工部署'] },
    { itemKey: 'schedulePlan', keywords: ['施工进度', '进度计划'] },
    { itemKey: 'resourcePlan', keywords: ['资源配置', '人员计划'] },
    { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] },
    { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
    { itemKey: 'siteLayout', keywords: ['平面布置', '施工总平面'] }
  ],
  construction_scheme: [
    { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
    { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
    { itemKey: 'processMethod', keywords: ['施工方法', '工艺流程'] },
    { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] }
  ],
  hazardous_special_scheme: [
    { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
    { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
    { itemKey: 'constructionPlan', keywords: ['施工计划', '施工方案'] },
    { itemKey: 'processMethod', keywords: ['工艺流程', '施工工艺'] },
    { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] },
    { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
    { itemKey: 'calculationBook', keywords: ['计算书', '验算'] },
    { itemKey: 'staffingAndRoles', keywords: ['人员配备', '岗位职责'] },
    { itemKey: 'acceptanceRequirements', keywords: ['验收要求', '验收标准'] }
  ],
  distribution_network_special_scheme: [
    { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
    { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
    { itemKey: 'riskIdentification', keywords: ['风险辨识', '风险分级'] },
    { itemKey: 'safetyMeasures', keywords: ['安全措施', '停电', '验电', '接地'] },
    { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
    { itemKey: 'ticketChain', keywords: ['工作票', '操作票', '现场勘察'] }
  ],
  supervision_plan: [
    { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
    { itemKey: 'monitoringPlan', keywords: ['监测监控', '旁站', '巡视'] },
    { itemKey: 'safetyMeasures', keywords: ['安全监理', '安全控制'] }
  ],
  review_support_material: [
    { itemKey: 'materialScope', keywords: ['审查支持材料', '支持材料'] }
  ]
};

const structureRuleMap: Record<string, string> = {
  construction_org: 'construction_org_structure_completeness',
  construction_scheme: 'construction_scheme_structure_completeness',
  hazardous_special_scheme: 'hazardous_special_scheme_core_sections',
  distribution_network_special_scheme: 'distribution_network_special_scheme_structure_completeness',
  supervision_plan: 'supervision_plan_structure_completeness',
  review_support_material: 'review_support_material_context_only'
};

function hasAnyKeyword(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => text.includes(keyword));
}

function buildFacts(parseResult: ParseResult, documentType: string) {
  const text = parseResult.normalizedText;
  const sectionPresence = Object.fromEntries((coreSectionKeywords[documentType] || []).map((item) => [item.itemKey, hasAnyKeyword(text, item.keywords)]));
  const structureCompleteness = (coreSectionKeywords[documentType] || []).map((item) => ({ itemKey: item.itemKey, scope: 'common', status: sectionPresence[item.itemKey] ? 'complete' : 'missing' }));
  const hazardKeywords: Record<string, string[]> = {
    lifting_operations: ['吊装', '起重'],
    temporary_power: ['临时用电', '停送电'],
    hot_work: ['动火'],
    gas_area_ops: ['煤气', '有毒有害气体']
  };
  const highRiskCategories = Object.entries(hazardKeywords).flatMap(([key, keywords]) => hasAnyKeyword(text, keywords) ? [key] : []);
  const emergencyPlanCount = (text.match(/应急预案|应急处置/g) || []).length;
  const shutdownWindowDays = Number(text.match(/(\d+)\s*天/)?.[1] || 0) || null;
  const laborTotal = Number(text.match(/(\d+)\s*人/)?.[1] || 0) || null;
  return {
    projectFacts: { sectionPresence, structureCompleteness, duplicateSections: parseResult.visibility.duplicateSectionTitles },
    attachmentFacts: { attachments: parseResult.attachments },
    hazardFacts: { highRiskCategories, specialSchemePlanStatus: hasAnyKeyword(text, ['专项方案']) ? 'explicit_section' : highRiskCategories.length ? 'generic_mention_only' : 'not_applicable' },
    emergencyFacts: { targetedPlanCount: emergencyPlanCount, planTitles: emergencyPlanCount ? ['应急预案'] : [] },
    scheduleFacts: { shutdownWindowDays },
    resourceFacts: { laborTotal }
  };
}

function resolveBasisProfile(documentType: string, requestedPackIds: string[] = [], requestedRulePackIds: string[] = []): ResolvedBasisProfile {
  const assets = getAssets() as any;
  const mapping = assets.profileMapping[documentType];
  if (!mapping) {
    return { profile_id: documentType, level1_classification: 'Unknown', level2_classification: 'Unknown', level3_classification: null, packs: [], rule_packs: [], basis_documents: [], degraded: true, degradation_reasons: [`profile_mapping.json missing documentType=${documentType}`] };
  }
  const packRegistry = assets.packRegistry.packs || assets.packRegistry;
  const rulePackRegistry = assets.rulePackRegistry.rule_packs || assets.rulePackRegistry;
  const basisRegistry = assets.basisRegistry;
  const allPackIds = unique([...(mapping.default_pack_ids || []), ...requestedPackIds]);
  const packIds = new Set(allPackIds);
  const resolvedPacks: any[] = [];
  const rulePacks: any[] = [];
  const degradation_reasons: string[] = [];
  let degraded = false;
  const basisIds: string[] = [];

  for (const packId of allPackIds) {
    const pack = packRegistry[packId];
    if (!pack) { degraded = true; degradation_reasons.push(`missing pack: ${packId}`); continue; }
    resolvedPacks.push({ pack_id: packId, status: pack.status || 'unknown', role: pack.role || 'unknown', family: pack.family || 'unknown', basis_ids: pack.basis_ids || [] });
    basisIds.push(...(pack.basis_ids || []));
  }

  const allRulePackIds = unique([...(mapping.rule_pack_ids || []), ...requestedRulePackIds]);
  for (const rulePackId of allRulePackIds) {
    const rp = rulePackRegistry[rulePackId];
    if (!rp) { degraded = true; degradation_reasons.push(`missing rule pack: ${rulePackId}`); continue; }
    rulePacks.push({ rule_pack_id: rulePackId, scope: rp.scope || '', related_pack_ids: rp.related_pack_ids || [], evidence_requirements: rp.evidence_requirements || [] });
    for (const relatedPackId of rp.related_pack_ids || []) {
      if (!packIds.has(relatedPackId) && packRegistry[relatedPackId]) {
        packIds.add(relatedPackId);
        const related = packRegistry[relatedPackId];
        resolvedPacks.push({ pack_id: relatedPackId, status: related.status || 'unknown', role: related.role || 'unknown', family: related.family || 'unknown', basis_ids: related.basis_ids || [] });
        basisIds.push(...(related.basis_ids || []));
      }
    }
  }

  const basisDocuments = unique(basisIds).map((basisId) => {
    const basis = basisRegistry[basisId];
    if (!basis) { degraded = true; degradation_reasons.push(`missing basis: ${basisId}`); return { basis_id: basisId, title: basisId, degraded: true, degradation_reason: `missing basis ${basisId}` }; }
    return { basis_id: basisId, title: basis.title || basisId, source_type: basis.source_type || 'unknown', effective_status: basis.effective_status || 'unknown', jurisdiction: basis.jurisdiction || 'unknown', file_refs: basis.file_refs || [] };
  });

  return { profile_id: mapping.profile_id || documentType, level1_classification: mapping.classification?.level1 || 'Unknown', level2_classification: mapping.classification?.level2 || 'Unknown', level3_classification: mapping.classification?.level3 || null, packs: resolvedPacks, rule_packs: rulePacks, basis_documents: basisDocuments, degraded, degradation_reasons };
}

function buildRuleHits(documentType: string, facts: any, parseResult: ParseResult, resolvedBasisProfile: ResolvedBasisProfile): RuleHit[] {
  const hits: RuleHit[] = [];
  const basePackId = String(resolvedBasisProfile.packs[0]?.pack_id || `${documentType}.base`);
  const missing = (facts.projectFacts.structureCompleteness || []).filter((item: any) => item.status !== 'complete');
  hits.push({ ruleId: structureRuleMap[documentType] || `${documentType}_structure_completeness`, packId: basePackId, packReadiness: 'ready', matchType: 'direct_hit', status: missing.length ? 'hit' : 'pass', layerHint: 'L1', severityHint: missing.length >= 2 ? 'high' : 'medium', factRefs: missing.map((item: any) => `project.structureCompleteness.${item.itemKey}`), evidenceRefs: ['policy:structure'], rationale: '核心章节缺失或结构不完整。' });
  if (parseResult.visibility.manualReviewNeeded) {
    hits.push({ ruleId: documentType === 'construction_scheme' ? 'construction_scheme_attachment_visibility' : documentType === 'hazardous_special_scheme' ? 'hazardous_special_scheme_attachment_visibility' : documentType === 'supervision_plan' ? 'supervision_plan_attachment_visibility' : 'construction_org_attachment_visibility', packId: basePackId, packReadiness: 'ready', matchType: 'visibility_gap', status: 'manual_review_needed', layerHint: 'L1', severityHint: 'medium', factRefs: ['attachments.visibility'], evidenceRefs: ['policy:review_visibility_gap'], rationale: '附件或图纸存在可视域缺口。', applicabilityState: 'blocked_by_visibility', blockingReasons: ['visibility_gap'] });
  }
  if ((facts.hazardFacts.highRiskCategories || []).length && (facts.emergencyFacts.targetedPlanCount || 0) < 2) {
    hits.push({ ruleId: documentType === 'distribution_network_special_scheme' ? 'distribution_network_special_scheme_emergency_targeted' : 'construction_org_emergency_plan_targeted', packId: basePackId, packReadiness: 'ready', matchType: 'direct_hit', status: 'hit', layerHint: 'L2', severityHint: 'medium', factRefs: ['emergency.planTitles'], evidenceRefs: ['policy:emergency_plan_targeted'], rationale: '高风险场景下应急安排针对性不足。' });
  }
  return hits;
}

function buildCandidates(ruleHits: RuleHit[]): Candidate[] {
  const assets = getAssets() as any;
  return ruleHits.filter((hit) => hit.status === 'hit' || hit.status === 'manual_review_needed').map((hit) => ({ candidateId: hit.ruleId, title: assets.evidenceTitles[hit.ruleId] || hit.ruleId, layerHint: hit.layerHint, severityHint: hit.severityHint, findingType: assets.evidenceFindingTypes[hit.ruleId] || (hit.status === 'manual_review_needed' ? 'visibility_gap' : 'hard_evidence'), ruleHits: [hit], evidenceMissing: hit.status === 'manual_review_needed', manualReviewNeeded: hit.status === 'manual_review_needed', manualReviewReason: assets.evidenceManualReviewReasons[hit.ruleId] || (hit.status === 'manual_review_needed' ? 'visibility_gap' : undefined), blockingReasons: hit.blockingReasons || [] }));
}

export async function buildReviewContext(input: ReviewContextInput): Promise<ReviewContextResult> {
  const parseResult = await parseReviewFile(input.targetFiles[0]);
  const facts = buildFacts(parseResult, input.documentType);
  const requestedPackIds = unique((input.focusRequirements || []).filter((item) => item.endsWith('.base')));
  const requestedRulePackIds = unique((input.focusRequirements || []).filter((item) => item.includes('.v1')));
  const resolvedBasisProfile = resolveBasisProfile(input.documentType, requestedPackIds, requestedRulePackIds);
  const ruleHits = buildRuleHits(input.documentType, facts, parseResult, resolvedBasisProfile);
  const candidates = buildCandidates(ruleHits);
  const resolvedProfile = { profileId: resolvedBasisProfile.profile_id, documentType: input.documentType, disciplineTags: input.disciplineTags || [], policyPackIds: requestedPackIds, rulePackIds: requestedRulePackIds, strictMode: input.strictMode !== false };
  const governedSupportPacket = {
    document_type: input.documentType,
    profile: resolvedBasisProfile,
    facts,
    basis_summary: resolvedBasisProfile.basis_documents.map((item: any) => ({ basis_id: item.basis_id, title: item.title, effective_status: item.effective_status || 'unknown' })),
    rule_pack_summary: resolvedBasisProfile.rule_packs,
    priority_focus_axes: input.documentType === 'distribution_network_special_scheme' ? ['停电范围与停复电关键信息', '停电申请审批与用户告知', '停电五步法安全动作闭环', '工作票/操作票/现场勘察证据链', '防反送电与双电源风险控制', '完工送电、资料归档与整改闭环'] : [],
    warning_signals: resolvedBasisProfile.degradation_reasons,
    degraded: resolvedBasisProfile.degraded
  };
  return { parseResult, docTextPreview: parseResult.preview, facts, ruleHits, candidates, resolvedProfile, resolvedBasisProfile, governedSupportPacket };
}
