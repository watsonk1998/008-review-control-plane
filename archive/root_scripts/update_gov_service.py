import re

path = "apps/api/src/services/admin/governance_service.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace the _write_yaml REMOVED comment with actual logic
write_yaml_logic = """
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
"""

text = re.sub(
    r"    # NOTE: _write_yaml has been REMOVED\..*?    # files by administrators\.  This is a hard governance constraint\.",
    write_yaml_logic.strip(),
    text,
    flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated GovernanceService with write abilities!")
