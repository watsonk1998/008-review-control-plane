import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from ruamel.yaml import YAML
except ImportError:
    pass

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

    def _write_yaml(self, file_name: str, modifier_fn: Callable[[dict[str, Any]], None]):
        path = self.config_dir / file_name
        
        # Use ruamel.yaml to preserve comments if available
        try:
            yaml_parser = YAML()
            yaml_parser.preserve_quotes = True
            yaml_parser.indent(mapping=2, sequence=4, offset=2)
            with path.open("r", encoding="utf-8") as f:
                data = yaml_parser.load(f)
            if data is None:
                data = {}
            modifier_fn(data)
            with path.open("w", encoding="utf-8") as f:
                yaml_parser.dump(data, f)
        except NameError:
            # Fallback to PyYAML if ruamel is not installed yet
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            modifier_fn(data)
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

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
        data = self._read_yaml("profile_mapping.yaml")
        mappings = data.get("mappings", {})
        return ProfileMappingDTO(mappings=mappings)

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

    def approve_and_publish_draft(self, draft_id: str, user: str = "system") -> DraftRecord:
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft not found: {draft_id}")
        if draft.status != DraftStatus.pending_approval:
            raise ValueError(f"Draft is not in pending_approval state (current: {draft.status})")

        # 1. Apply changes to local files
        self._apply_draft_to_yaml(draft)

        # 2. Update status
        draft = self.store.update_draft(draft_id, status=DraftStatus.published)

        # 3. Create Audit Log
        now = datetime.now(timezone.utc)
        audit = AuditLogRecord(
            id=str(uuid.uuid4()),
            entity_type=draft.target_entity_type,
            entity_id=draft.target_entity_id,
            action=AuditAction.publish,
            changes=draft.proposed_changes,
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

    def _apply_draft_to_yaml(self, draft: DraftRecord):
        target_type = draft.target_entity_type
        target_id = draft.target_entity_id
        changes = draft.proposed_changes

        if target_type == GovernanceEntityType.basis:
            def mod_basis(data):
                if target_id not in data:
                    data[target_id] = {}
                data[target_id].update(changes)
            self._write_yaml("basis_registry.yaml", mod_basis)

        elif target_type == GovernanceEntityType.pack:
            def mod_pack(data):
                if "packs" not in data:
                    data["packs"] = {}
                if target_id not in data["packs"]:
                    data["packs"][target_id] = {}
                data["packs"][target_id].update(changes)
            self._write_yaml("pack_registry.yaml", mod_pack)

        elif target_type == GovernanceEntityType.rule_pack:
            def mod_rp(data):
                if "rule_packs" not in data:
                    data["rule_packs"] = {}
                if target_id not in data["rule_packs"]:
                    data["rule_packs"][target_id] = {}
                data["rule_packs"][target_id].update(changes)
            self._write_yaml("rule_pack_registry.yaml", mod_rp)

        elif target_type == GovernanceEntityType.profile_mapping:
            def mod_profile(data):
                if "mappings" not in data:
                    data["mappings"] = {}
                # Profile Mapping might treat target_id differently, 
                # but typically if target_id is global, changes replace everything
                data["mappings"].update(changes)
            self._write_yaml("profile_mapping.yaml", mod_profile)
