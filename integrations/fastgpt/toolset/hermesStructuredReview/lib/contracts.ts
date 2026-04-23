export type ReviewDocumentType =
  | 'construction_org'
  | 'construction_scheme'
  | 'hazardous_special_scheme'
  | 'distribution_network_special_scheme'
  | 'supervision_plan'
  | 'review_support_material';

export type Severity = 'high' | 'medium' | 'low' | 'info';
export type EvidenceStatus = 'grounded' | 'inferred' | 'evidence_gap' | 'visibility_gap';
export type FindingType = 'hard_evidence' | 'engineering_inference' | 'visibility_gap' | 'suggestion_enhancement' | string;

export interface ReviewFileRef { fileName?: string; fileType?: string; path?: string; url?: string; content?: string; }
export interface ReviewContextInput { query: string; documentType: ReviewDocumentType; disciplineTags?: string[]; enabledModules?: string[]; disabledModules?: string[]; focusRequirements?: string[]; strictMode?: boolean; targetFiles: ReviewFileRef[]; basisFiles?: ReviewFileRef[]; contextFiles?: ReviewFileRef[]; }
export interface ParseSection { id: string; title: string; key: string; level: number; parentId?: string | null; blockId: string; position: number; }
export interface ParseBlock { id: string; type: string; text: string; sectionId?: string | null; headingLevel?: number | null; position: number; }
export interface ParseVisibility { attachmentCount: number; counts: Record<string, number>; reasonCounts: Record<string, number>; duplicateSectionTitles: string[]; parseWarnings: string[]; manualReviewNeeded: boolean; manualReviewReason?: string | null; }
export interface ParseResult { documentId: string; filePath?: string; fileType: string; parseMode: string; parserLimited: boolean; sections: ParseSection[]; blocks: ParseBlock[]; attachments: Array<Record<string, unknown>>; normalizedText: string; preview: string; visibility: ParseVisibility; parseWarnings: string[]; }
export interface RuleHit { ruleId: string; packId: string; packReadiness: string; matchType: string; status: string; layerHint: string; severityHint: Severity; factRefs: string[]; evidenceRefs: string[]; rationale: string; applicabilityState?: string; blockingReasons?: string[]; missingFactKeys?: string[]; }
export interface Candidate { candidateId: string; title: string; layerHint: string; severityHint: Severity; findingType: FindingType; ruleHits: RuleHit[]; evidenceMissing: boolean; manualReviewNeeded: boolean; manualReviewReason?: string; blockingReasons: string[]; }
export interface ResolvedBasisProfile { profile_id: string; level1_classification: string; level2_classification: string; level3_classification?: string | null; packs: Array<Record<string, unknown>>; rule_packs: Array<Record<string, unknown>>; basis_documents: Array<Record<string, unknown>>; degraded: boolean; degradation_reasons: string[]; }
export interface ReviewContextResult { parseResult: ParseResult; docTextPreview: string; facts: Record<string, unknown>; ruleHits: RuleHit[]; candidates: Candidate[]; resolvedProfile: Record<string, unknown>; resolvedBasisProfile: ResolvedBasisProfile; governedSupportPacket: Record<string, unknown>; }
export interface Finding { id: string; title: string; severity: Severity; category: string; summary: string; suggestion?: string; evidence_status?: EvidenceStatus; source_engine?: string; finding_type?: FindingType; raw_data?: Record<string, unknown>; manual_review_needed?: boolean; }
export interface FactPacket { review_id: string; engine: string; findings: Finding[]; overall_assessment: string; degraded?: boolean; error?: string; metadata: Record<string, unknown>; raw_result?: Record<string, unknown>; }
export interface SupportReviewResult { supportResult008: Record<string, unknown>; supportPacket008: FactPacket; artifactIndex: Array<Record<string, unknown>>; supportLayerContext: Record<string, unknown>; }
export interface FinalReportPacket { title: string; verdict: 'conditional_pass' | 'needs_revision' | 'fail'; summary: string; top_risks: string[]; key_findings: Finding[]; supplemental_findings: Finding[]; traceability: Array<Record<string, unknown>>; report_markdown: string; metadata: Record<string, unknown>; }
