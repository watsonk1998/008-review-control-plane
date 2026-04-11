from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.review.contracts import ReviewBrief
from src.review.hermes.module_bindings import template_review_modules
from src.review.hermes.constants import normalize_template_id
from src.review.hermes.template_models import AgentTemplate, AgentTemplateMatch

logger = logging.getLogger(__name__)


class HermesTemplateRegistry:
    def __init__(self, *, seed_dir: Path, runtime_dir: Path):
        self.seed_dir = seed_dir
        self.runtime_dir = runtime_dir

    def load_templates(self) -> list[AgentTemplate]:
        templates: list[AgentTemplate] = []
        for directory in (self.seed_dir, self.runtime_dir):
            if not directory.exists():
                continue
            for path in sorted(directory.rglob('*.json')):
                try:
                    template = AgentTemplate.model_validate_json(path.read_text(encoding='utf-8'))
                    template.id = normalize_template_id(template.id) or template.id
                    template.metadata = {
                        **template.metadata,
                        'review_modules': template.metadata.get('review_modules') or template_review_modules(template.id),
                    }
                    templates.append(template)
                except Exception as exc:
                    logger.warning('[hermes_template_registry] Failed to load %s: %s', path, exc)
        unique_templates: dict[str, AgentTemplate] = {}
        for template in templates:
            unique_templates[template.id] = template
        return list(unique_templates.values())

    def select_templates(self, *, brief: ReviewBrief, hermes_input: dict[str, Any]) -> list[AgentTemplateMatch]:
        matches: list[AgentTemplateMatch] = []
        enabled = {normalize_template_id(item) or item for item in set(hermes_input.get('enabledAgents') or [])}
        disabled = {normalize_template_id(item) or item for item in set(hermes_input.get('disabledAgents') or [])}
        focus_text = ' '.join(self._focus_terms(brief, hermes_input))
        pack_ids = set(((brief.focus_pack or {}).get('policy_pack_ids') or []))
        for template in self.load_templates():
            if template.id in disabled:
                continue
            score = 0
            reasons: list[str] = []
            if enabled:
                if template.id in enabled:
                    score += 100
                    reasons.append('explicitly_enabled')
                else:
                    continue
            if not template.supported_document_types or str(brief.review_object_type) in template.supported_document_types:
                score += 5
                reasons.append('document_type_match')
            for keyword in template.focus_keywords:
                if keyword and keyword in focus_text:
                    score += 5
                    reasons.append(f'focus:{keyword}')
            if pack_ids and any(pack_id in pack_ids for pack_id in template.metadata.get('preferred_pack_ids', [])):
                score += 3
                reasons.append('preferred_pack_match')
            if template.default_enabled:
                score += 1
                reasons.append('default_enabled')
            if score > 0:
                matches.append(AgentTemplateMatch(template=template, score=score, reasons=reasons))
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches

    def focus_gaps(self, *, selected_templates: list[AgentTemplateMatch], brief: ReviewBrief, hermes_input: dict[str, Any]) -> list[str]:
        selected_keywords = {keyword for match in selected_templates for keyword in match.template.focus_keywords}
        gaps: list[str] = []
        for term in self._focus_terms(brief, hermes_input):
            if term and not any(term == keyword or term in keyword or keyword in term for keyword in selected_keywords):
                gaps.append(term)
        return list(dict.fromkeys(gaps))

    def save_runtime_template(self, template: AgentTemplate, *, task_id: str | None = None) -> Path:
        runtime_dir = self.runtime_dir / task_id if task_id else self.runtime_dir
        runtime_dir.mkdir(parents=True, exist_ok=True)
        path = runtime_dir / f'{template.id}.json'
        path.write_text(template.model_dump_json(indent=2), encoding='utf-8')
        return path

    def _focus_terms(self, brief: ReviewBrief, hermes_input: dict[str, Any]) -> list[str]:
        raw_focus = hermes_input.get('focusRequirements') or []
        if isinstance(raw_focus, str):
            terms = [part.strip() for part in raw_focus.replace('；', '，').split('，') if part.strip()]
        else:
            terms = [str(item).strip() for item in raw_focus if str(item).strip()]
        terms.extend(str(tag).strip() for tag in ((brief.focus_pack or {}).get('discipline_tags') or []) if str(tag).strip())
        if brief.query:
            terms.append(str(brief.query).strip())
        return list(dict.fromkeys(terms))
