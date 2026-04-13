from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.config.settings import get_settings
from src.domain.governance_schema import (
    AuditAction,
    AuditLogRecord,
    BasisDTO,
    DraftRecord,
    DraftStatus,
    GovernanceEntityType,
    PackDTO,
    ProfileMappingDTO,
    RulePackDTO,
    CandidateArtifact,
    CandidateType,
    CandidateStatus,
    CreateCandidateRequest,
    UpdateCandidateRequest,
)
from src.repositories.governance_store import SQLiteGovernanceStore

logger = logging.getLogger(__name__)

class GovernanceService:
    def __init__(self, store: SQLiteGovernanceStore):
        self.store = store
        self.settings = get_settings()
        self.config_dir = self.settings.project_root / "config" / "review_basis"
        
    def _read_yaml(self, file_name: str) -> dict[str, Any]:
        path = self.config_dir / file_name
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error(f"Failed to read {file_name}: {exc}")
            return {}

    def _write_yaml(self, file_name: str, data: dict[str, Any], user: str = "admin") -> None:
        path = self.config_dir / file_name
        history_dir = self.config_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Backup existing
        if path.exists():
            timestamp = datetime.now(timezone.utc).strftime('%Y%md%H%M%S')
            backup_path = history_dir / f"{file_name}.{timestamp}.bak"
            import shutil
            shutil.copy2(path, backup_path)
            
            # Record audit log for the backup action implicitly
            audit = AuditLogRecord(
                id=str(uuid.uuid4()),
                entity_type=GovernanceEntityType.pack, # Will be generic
                entity_id=file_name,
                action=AuditAction.update,
                changes={"backup_file": str(backup_path.name)},
                created_by=user,
                created_at=datetime.now(timezone.utc),
            )
            self.store.create_audit_log(audit)

        # 2. Write new dict to YAML
        # We use sort_keys=False and safe_dump to maintain clean formatting
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def save_bases(self, data: dict[str, Any], user: str = "admin") -> None:
        self._write_yaml("basis_registry.yaml", data, user)

    def save_packs(self, data: dict[str, Any], user: str = "admin") -> None:
        self._write_yaml("pack_registry.yaml", {"packs": data}, user)

    def save_rule_packs(self, data: dict[str, Any], user: str = "admin") -> None:
        self._write_yaml("rule_pack_registry.yaml", {"rule_packs": data}, user)

    def save_profile_mapping(self, data: dict[str, Any], user: str = "admin") -> None:
        self._write_yaml("profile_mapping.yaml", data, user)

    def list_bases(self) -> list[BasisDTO]:
        data = self._read_yaml("basis_registry.yaml")
        results = []
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            results.append(BasisDTO(
                basis_id=value.get("basis_id", key),
                title=value.get("title", ""),
                source_type=value.get("source_type", ""),
                version=value.get("version", ""),
                effective_status=value.get("effective_status", ""),
                jurisdiction=value.get("jurisdiction", ""),
                file_refs=value.get("file_refs", []),
                applicability_tags=value.get("applicability_tags", []),
                owner=value.get("owner", ""),
                freshness_rule=value.get("freshness_rule", ""),
            ))
        return results

    def list_packs(self) -> list[PackDTO]:
        data = self._read_yaml("pack_registry.yaml")
        packs = data.get("packs", {})
        results = []
        for key, value in packs.items():
            if not isinstance(value, dict):
                continue
            results.append(PackDTO(
                pack_id=value.get("pack_id", key),
                display_name=value.get("display_name", ""),
                basis_ids=value.get("basis_ids", []),
                status=value.get("status", ""),
                default_profiles=value.get("default_profiles", []),
                priority=value.get("priority", ""),
                promotion_state=value.get("promotion_state", ""),
                role=value.get("role", ""),
                family=value.get("family", ""),
            ))
        return results

    def list_rule_packs(self) -> list[RulePackDTO]:
        data = self._read_yaml("rule_pack_registry.yaml")
        rule_packs = data.get("rule_packs", {})
        results = []
        for key, value in rule_packs.items():
            if not isinstance(value, dict):
                continue
            results.append(RulePackDTO(
                rule_pack_id=value.get("rule_pack_id", key),
                display_name=value.get("display_name", ""),
                description=value.get("description"),
                trigger_conditions=value.get("trigger_conditions", []),
                checks=value.get("checks", []),
                status=value.get("status", ""),
            ))
        return results

    def get_profile_mapping(self) -> ProfileMappingDTO:
        """Read profile_mapping.yaml — the ONLY truth source for profile resolution.

        The YAML is a top-level dict of profile keys (no 'mappings' wrapper).
        This must stay aligned with the runtime read paths in
        profile_resolver._load_profile_mapping() and BasisPackResolver.__init__().
        """
        data = self._read_yaml("profile_mapping.yaml")
        # The YAML structure is top-level keyed (e.g. hazardous_special_scheme: {...}).
        # Do NOT wrap with data.get("mappings") — that key does not exist.
        return ProfileMappingDTO(mappings=data)

    # --- Candidates ---

    def create_candidate(self, request: CreateCandidateRequest, created_by: str = "system") -> CandidateArtifact:
        now = datetime.now(timezone.utc)
        candidate = CandidateArtifact(
            id=str(uuid.uuid4()),
            profile_id=request.profile_id,
            candidate_type=CandidateType(request.candidate_type),
            content=request.content,
            source=request.source,
            status=CandidateStatus.draft,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        return self.store.create_candidate(candidate)

    def list_candidates(self, profile_id: str | None = None, status: str | None = None) -> list[CandidateArtifact]:
        return self.store.list_candidates(profile_id=profile_id, status=status)

    def update_candidate(self, candidate_id: str, request: UpdateCandidateRequest) -> CandidateArtifact:
        update_fields: dict[str, Any] = {}
        if request.status is not None:
            update_fields["status"] = CandidateStatus(request.status)
        if request.reviewer_notes is not None:
            update_fields["reviewer_notes"] = request.reviewer_notes

        if not update_fields:
            raise ValueError("No valid fields provided for update")

        return self.store.update_candidate(candidate_id, **update_fields)

    # --- Draft & Publish State Machine ---

    def create_draft(self, entity_type: str, entity_id: str, changes: dict[str, Any], created_by: str = "system") -> DraftRecord:
        now = datetime.now(timezone.utc)
        draft = DraftRecord(
            id=str(uuid.uuid4()),
            target_entity_type=GovernanceEntityType(entity_type),
            target_entity_id=entity_id,
            proposed_changes=changes,
            status=DraftStatus.pending_approval,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        return self.store.create_draft(draft)

    def approve_draft(self, draft_id: str, user: str = "system") -> DraftRecord:
        """Approve a governance draft.

        HARD CONSTRAINT: This method only transitions the draft to
        'approved' status.  It does NOT automatically rewrite YAML files.
        The actual YAML modification must be performed manually by an
        administrator.  This is the only formally recognized path.

        After manual transcription, an admin should call
        ``mark_draft_transcribed`` to close the lifecycle.
        """
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")
        if draft.status != DraftStatus.pending_approval:
            raise ValueError(f"Draft is not in pending_approval state (current: {draft.status})")

        # Update status to approved (NOT published — no YAML is touched)
        draft = self.store.update_draft(draft_id, status=DraftStatus.approved)

        # Audit log
        now = datetime.now(timezone.utc)
        audit = AuditLogRecord(
            id=str(uuid.uuid4()),
            entity_type=draft.target_entity_type,
            entity_id=draft.target_entity_id,
            action=AuditAction.update,
            changes={**draft.proposed_changes, '_governance_action': 'approved_pending_manual_transcription'},
            created_by=user,
            created_at=now,
        )
        self.store.create_audit_log(audit)

        return draft

    def mark_draft_transcribed(self, draft_id: str, user: str = "system") -> DraftRecord:
        """Mark an approved draft as transcribed after manual YAML update.

        This is called by an administrator AFTER they have manually
        edited the corresponding YAML file.  It transitions the draft
        to 'published' status for audit completeness.
        """
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")
        if draft.status != DraftStatus.approved:
            raise ValueError(
                f"Draft must be in 'approved' state before marking as transcribed "
                f"(current: {draft.status}).  Automated publish is forbidden."
            )

        draft = self.store.update_draft(draft_id, status=DraftStatus.published)

        now = datetime.now(timezone.utc)
        audit = AuditLogRecord(
            id=str(uuid.uuid4()),
            entity_type=draft.target_entity_type,
            entity_id=draft.target_entity_id,
            action=AuditAction.publish,
            changes={'_governance_action': 'manual_transcription_confirmed'},
            created_by=user,
            created_at=now,
        )
        self.store.create_audit_log(audit)

        return draft

    def reject_draft(self, draft_id: str, notes: str = "", user: str = "system") -> DraftRecord:
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")
        return self.store.update_draft(draft_id, status=DraftStatus.rejected, reviewer_notes=notes)

    def list_drafts(self, status: str | None = None) -> list[DraftRecord]:
        return self.store.list_drafts(status)

    # NOTE: _apply_draft_to_yaml has been REMOVED.
    # Automated YAML rewriting is FORBIDDEN in the governance pipeline.
    # All formal YAML changes must be performed manually by administrators
    # and then confirmed via mark_draft_transcribed().
