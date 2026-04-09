"""
Task Compiler: converts raw task inputs into a unified ReviewBrief.

Design intent:
- Review engines should NOT receive scattered raw inputs
- All task parameters are compiled into a single ReviewBrief
- This is the boundary between "task management" and "review execution"
- basis_files / project_context_files are placeholder-ready for future expansion
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.domain.models import SourceDocumentRef, TaskRecord
from src.review.contracts import ReviewBrief

logger = logging.getLogger(__name__)


class TaskCompiler:
    """Compile task inputs into a unified ReviewBrief."""

    def compile(
        self,
        task: TaskRecord,
        *,
        source_document_ref: SourceDocumentRef | None = None,
        source_document_path: str | None = None,
        plan: dict[str, Any] | None = None,
    ) -> ReviewBrief:
        """Compile a TaskRecord into a ReviewBrief.

        This method normalises the scattered task fields into a single
        structured brief that both 008 and Hermes can consume.
        """
        logger.info('[task_compiler] Compiling review brief for task %s', task.id)

        plan = plan or {}
        plan_profile = dict(plan.get('reviewProfile') or {})

        # --- target files ---
        target_files: list[dict[str, Any]] = []
        if source_document_path:
            entry: dict[str, Any] = {
                'path': source_document_path,
                'type': Path(source_document_path).suffix.lstrip('.'),
                'name': Path(source_document_path).name,
            }
            if source_document_ref:
                entry.update({
                    'ref_id': source_document_ref.refId,
                    'source_type': source_document_ref.sourceType,
                    'display_name': source_document_ref.displayName,
                })
            target_files.append(entry)
        elif source_document_ref:
            target_files.append({
                'path': source_document_ref.storagePath,
                'type': source_document_ref.fileType,
                'name': source_document_ref.fileName,
                'ref_id': source_document_ref.refId,
                'source_type': source_document_ref.sourceType,
                'display_name': source_document_ref.displayName,
            })

        # --- focus pack ---
        focus_pack = {
            'discipline_tags': list(
                task.disciplineTags
                or plan_profile.get('disciplineTagHints')
                or []
            ),
            'policy_pack_ids': list(
                task.policyPackIds
                or plan_profile.get('policyPackHints')
                or []
            ),
        }

        # --- review policy ---
        review_policy = {
            'strict_mode': task.strictMode if task.strictMode is not None else True,
        }

        review_brief = ReviewBrief(
            review_id=task.id,
            review_object_type=(
                task.documentType
                or plan_profile.get('documentTypeHint')
                or 'construction_org'
            ),
            target_files=target_files,
            basis_files=[],  # future: populated from policy packs / attached standards
            project_context_files=[],  # future: populated for multi-file review
            focus_pack=focus_pack,
            review_policy=review_policy,
            report_type='structured_review',
            query=task.query,
            compiled_at=datetime.now(timezone.utc),
            metadata={
                'task_type': task.taskType,
                'capability_mode': task.capabilityMode,
                'fixture_id': task.fixtureId,
                'plan_authority': plan_profile.get('authority'),
            },
        )

        logger.info(
            '[task_compiler] Brief compiled: review_id=%s, doc_type=%s, targets=%d, focus_tags=%s',
            review_brief.review_id,
            review_brief.review_object_type,
            len(review_brief.target_files),
            focus_pack.get('discipline_tags'),
        )
        return review_brief
