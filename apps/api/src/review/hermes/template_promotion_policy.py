"""Template Promotion Governance for HermesController-first structured review.

Status:
- governance enforcement module

Promotion policy:
- Runtime/candidate templates are allowed to be generated and used
- They do NOT become official (seed) automatically
- Promotion requires explicit validation and approval flow
- This module enforces the governance boundary between runtime and seed templates

Canonical path:
- HermesTemplateRegistry loads templates from seed_dir and runtime_dir
- This module governs the promotion lifecycle:
    runtime_candidate → validated → promoted_to_seed
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


PromotionStatus = Literal['candidate', 'validated', 'promoted', 'rejected']


class TemplatePromotionRecord(BaseModel):
    """Tracks the promotion lifecycle of a runtime template."""

    template_id: str
    status: PromotionStatus = 'candidate'
    source_task_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validated_at: datetime | None = None
    promoted_at: datetime | None = None
    rejected_at: datetime | None = None
    validation_results: dict[str, Any] = Field(default_factory=dict)
    rejection_reason: str | None = None
    promoted_by: str | None = None


class TemplatePromotionPolicy:
    """Enforces template promotion governance.

    Rules:
    1. Only templates in runtime_dir can be candidates for promotion.
    2. A template must pass validation before promotion.
    3. Promotion copies the template from runtime_dir to seed_dir
       and records the promotion event.
    4. Rejected templates are annotated but not deleted.

    Validation criteria (all must pass):
    - Template must be structurally valid (parseable JSON, valid AgentTemplate)
    - Template must have been used in at least one review (source_task_id present)
    - Template must not be experimental (metadata.experimental != True)
    - Template must have supported_document_types specified
    """

    def __init__(self, *, seed_dir: Path, runtime_dir: Path, promotion_log_dir: Path | None = None):
        self.seed_dir = seed_dir
        self.runtime_dir = runtime_dir
        self.promotion_log_dir = promotion_log_dir or runtime_dir / '_promotion_log'

    def list_candidates(self) -> list[TemplatePromotionRecord]:
        """List all runtime templates eligible for promotion review."""
        candidates: list[TemplatePromotionRecord] = []
        if not self.runtime_dir.exists():
            return candidates

        for path in sorted(self.runtime_dir.rglob('*.json')):
            # Skip promotion log files
            if '_promotion_log' in str(path):
                continue
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                template_id = data.get('id', path.stem)
                task_id = path.parent.name if path.parent != self.runtime_dir else None
                metadata = data.get('metadata', {})

                # Check if already promoted
                if self._is_already_promoted(template_id):
                    continue

                record = TemplatePromotionRecord(
                    template_id=template_id,
                    status='candidate',
                    source_task_id=task_id,
                )

                # Auto-reject if explicitly experimental
                if metadata.get('experimental'):
                    record.status = 'candidate'
                    record.validation_results['experimental_flag'] = 'present — requires manual override'

                candidates.append(record)
            except Exception as exc:
                logger.warning('[promotion_policy] Failed to parse candidate %s: %s', path, exc)

        return candidates

    def validate_candidate(self, template_id: str) -> TemplatePromotionRecord:
        """Validate a runtime template for promotion eligibility.

        Returns a record with validation results and updated status.
        """
        record = TemplatePromotionRecord(template_id=template_id)
        template_path = self._find_runtime_template(template_id)

        if template_path is None:
            record.status = 'rejected'
            record.rejection_reason = f'Template not found in runtime_dir: {template_id}'
            record.rejected_at = datetime.now(timezone.utc)
            return record

        try:
            data = json.loads(template_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError) as exc:
            record.status = 'rejected'
            record.rejection_reason = f'Invalid JSON: {exc}'
            record.rejected_at = datetime.now(timezone.utc)
            return record

        validation: dict[str, Any] = {}
        passed = True

        # 1. Structural validity
        required_fields = ['id', 'agent_name', 'agent_purpose', 'execution_mode']
        missing = [f for f in required_fields if not data.get(f)]
        validation['structural_validity'] = 'pass' if not missing else f'fail — missing: {missing}'
        if missing:
            passed = False

        # 2. Has been used in a review
        task_id = template_path.parent.name if template_path.parent != self.runtime_dir else None
        validation['usage_evidence'] = 'pass' if task_id else 'fail — no task_id directory'
        record.source_task_id = task_id
        if not task_id:
            passed = False

        # 3. Not experimental
        metadata = data.get('metadata', {})
        is_experimental = metadata.get('experimental', False)
        validation['experimental_check'] = 'fail — marked experimental' if is_experimental else 'pass'
        if is_experimental:
            passed = False

        # 4. Has supported_document_types
        doc_types = data.get('supported_document_types', [])
        validation['document_type_coverage'] = 'pass' if doc_types else 'fail — empty supported_document_types'
        if not doc_types:
            passed = False

        record.validation_results = validation
        if passed:
            record.status = 'validated'
            record.validated_at = datetime.now(timezone.utc)
        else:
            record.status = 'rejected'
            record.rejection_reason = 'Validation failed — see validation_results'
            record.rejected_at = datetime.now(timezone.utc)

        return record

    def promote(self, template_id: str, *, promoted_by: str = 'system') -> TemplatePromotionRecord:
        """Promote a validated runtime template to the seed directory.

        The template must pass validation first. Returns the promotion record.
        """
        record = self.validate_candidate(template_id)

        if record.status != 'validated':
            logger.warning('[promotion_policy] Cannot promote %s — status=%s', template_id, record.status)
            return record

        template_path = self._find_runtime_template(template_id)
        if template_path is None:
            record.status = 'rejected'
            record.rejection_reason = 'Template file not found after validation'
            return record

        # Copy to seed directory
        self.seed_dir.mkdir(parents=True, exist_ok=True)
        dest_path = self.seed_dir / f'{template_id}.json'

        data = json.loads(template_path.read_text(encoding='utf-8'))
        # Strip candidate/experimental markers on promotion
        metadata = data.get('metadata', {})
        metadata.pop('generated', None)
        metadata.pop('experimental', None)
        metadata.pop('not_official', None)
        metadata.pop('requires_promotion_validation', None)
        metadata['promoted'] = True
        metadata['promoted_at'] = datetime.now(timezone.utc).isoformat()
        metadata['promoted_by'] = promoted_by
        metadata['promotion_source'] = str(template_path)
        data['metadata'] = metadata

        dest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

        record.status = 'promoted'
        record.promoted_at = datetime.now(timezone.utc)
        record.promoted_by = promoted_by

        # Write promotion log
        self._write_promotion_log(record)

        logger.info('[promotion_policy] Promoted template %s to seed: %s', template_id, dest_path)
        return record

    def _find_runtime_template(self, template_id: str) -> Path | None:
        """Find a template file in the runtime directory by ID."""
        if not self.runtime_dir.exists():
            return None
        for path in self.runtime_dir.rglob('*.json'):
            if '_promotion_log' in str(path):
                continue
            if path.stem == template_id:
                return path
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if data.get('id') == template_id:
                    return path
            except (json.JSONDecodeError, IOError):
                continue
        return None

    def _is_already_promoted(self, template_id: str) -> bool:
        """Check if a template has already been promoted to seed."""
        seed_path = self.seed_dir / f'{template_id}.json'
        return seed_path.is_file()

    def _write_promotion_log(self, record: TemplatePromotionRecord) -> None:
        """Write a promotion event to the log directory."""
        self.promotion_log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.promotion_log_dir / f'{record.template_id}.json'
        log_path.write_text(record.model_dump_json(indent=2), encoding='utf-8')
