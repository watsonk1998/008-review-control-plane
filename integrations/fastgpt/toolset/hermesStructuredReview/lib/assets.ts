import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const generatedDir = path.resolve(__dirname, '../assets/generated');
const readJson = (name: string) => JSON.parse(fs.readFileSync(path.join(generatedDir, name), 'utf8'));
let cache: Record<string, unknown> | null = null;
export function getAssets() {
  if (cache) return cache;
  cache = {
    moduleBindings: readJson('module_bindings.json'),
    moduleTitles: readJson('module_titles.json'),
    docTypeLabels: readJson('doc_type_labels.json'),
    templates: readJson('template_manifest.json'),
    profileMapping: readJson('profile_mapping.json'),
    packRegistry: readJson('pack_registry.json'),
    rulePackRegistry: readJson('rule_pack_registry.json'),
    basisRegistry: readJson('basis_registry.json'),
    evidenceTitles: readJson('evidence_titles.json'),
    evidenceFindingTypes: readJson('evidence_finding_types.json'),
    evidenceManualReviewReasons: readJson('evidence_manual_review_reasons.json')
  };
  return cache;
}
