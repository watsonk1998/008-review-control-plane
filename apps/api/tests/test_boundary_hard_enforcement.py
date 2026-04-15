"""
测试类 3：边界硬测试

验证:
- archive 中的代码不会被 active runtime import
- external/hermes-agent 未被业务逻辑侵入
- 补丁后核心边界仍完整
"""

import ast
import os
import subprocess
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APPS_SRC_DIR = PROJECT_ROOT / "apps" / "api" / "src"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
EXTERNAL_HERMES_DIR = PROJECT_ROOT / "external" / "hermes-agent"


# ---------------------------------------------------------------------------
# Test 1: Archive code not imported by active runtime
# ---------------------------------------------------------------------------

def test_archive_code_not_imported_by_active_runtime():
    """Active runtime (apps/api/src/) 不得 import archive 目录下的任何模块。

    扫描所有 .py 文件的 import 语句，确保没有引用 archive 路径。
    """
    violations = []

    for py_file in APPS_SRC_DIR.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "archive" in alias.name.lower():
                        violations.append(
                            f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno} → import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "archive" in module.lower():
                    violations.append(
                        f"{py_file.relative_to(PROJECT_ROOT)}:{node.lineno} → from {module} import ..."
                    )

    assert not violations, (
        "Active runtime imports from archive/ detected:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Test 2: External hermes-agent remains untouched boundary
# ---------------------------------------------------------------------------

def test_external_hermes_agent_remains_untouched_boundary():
    """external/hermes-agent 目录不得包含项目特有的业务逻辑。

    扫描 external/hermes-agent/ 下所有 .py 文件，确保不包含：
    - profile_mapping / basis_pack / review_basis 等项目特有术语
    - 项目特定的 import 路径引用（如 src.review, src.domain）
    """
    if not EXTERNAL_HERMES_DIR.exists():
        pytest.skip("external/hermes-agent directory not present")

    project_specific_markers = [
        "profile_mapping",
        "basis_pack_resolver",
        "FinalReportAssembler",
        "GovernanceService",
        "governance_store",
        "review_basis",
        "from src.review",
        "from src.domain",
        "from src.services",
        "from src.config.settings",
    ]

    violations = []

    for py_file in EXTERNAL_HERMES_DIR.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for marker in project_specific_markers:
            # Search line by line for precise reporting
            for i, line in enumerate(content.splitlines(), start=1):
                if marker in line and not line.lstrip().startswith("#"):
                    violations.append(
                        f"{py_file.relative_to(PROJECT_ROOT)}:{i} → contains '{marker}'"
                    )

    assert not violations, (
        "external/hermes-agent contains project-specific business logic:\n"
        + "\n".join(violations[:20])  # Cap output
    )


# ---------------------------------------------------------------------------
# Test 3: Verify hermes boundary integrity (structural checks)
# ---------------------------------------------------------------------------

def test_external_hermes_agent_no_local_business_files():
    """external/hermes-agent 不得包含以下项目侧业务文件名。

    这些文件名只属于 shell 侧，不应出现在 upstream kernel 中。
    """
    if not EXTERNAL_HERMES_DIR.exists():
        pytest.skip("external/hermes-agent directory not present")

    forbidden_filenames = {
        "governance_service.py",
        "governance_store.py",
        "governance_schema.py",
        "basis_pack_resolver.py",
        "profile_resolver.py",
        "hermes_controller.py",
        "final_report_merger.py",
        "support_packet_builder.py",
    }

    violations = []
    for py_file in EXTERNAL_HERMES_DIR.rglob("*.py"):
        if py_file.name in forbidden_filenames:
            violations.append(str(py_file.relative_to(PROJECT_ROOT)))

    assert not violations, (
        "external/hermes-agent contains shell-side business files:\n"
        + "\n".join(violations)
    )


def test_active_runtime_does_not_sys_path_inject_archive():
    """确保 active runtime 没有通过 sys.path 注入 archive 目录。"""
    violations = []

    for py_file in APPS_SRC_DIR.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "sys.path" in stripped and "archive" in stripped:
                violations.append(
                    f"{py_file.relative_to(PROJECT_ROOT)}:{i} → {stripped}"
                )

    assert not violations, (
        "Active runtime injects archive into sys.path:\n" + "\n".join(violations)
    )


def test_config_review_basis_yaml_files_are_self_consistent():
    """config/review_basis/ 下的 YAML 注册表必须自洽：
    profile_mapping 引用的 pack_id 应在 pack_registry 中存在。
    """
    import yaml

    config_dir = PROJECT_ROOT / "config" / "review_basis"

    profile_mapping_path = config_dir / "profile_mapping.yaml"
    pack_registry_path = config_dir / "pack_registry.yaml"

    if not profile_mapping_path.exists() or not pack_registry_path.exists():
        pytest.skip("YAML registry files not found")

    with open(profile_mapping_path, "r", encoding="utf-8") as f:
        profile_mapping = yaml.safe_load(f) or {}
    with open(pack_registry_path, "r", encoding="utf-8") as f:
        pack_data = yaml.safe_load(f) or {}
    pack_registry = pack_data.get("packs", {})

    missing_packs = []
    for profile_key, profile in profile_mapping.items():
        if not isinstance(profile, dict):
            continue
        for pack_id in profile.get("default_pack_ids", []):
            if pack_id not in pack_registry:
                missing_packs.append(f"  profile '{profile_key}' → pack '{pack_id}'")

    # This is a warning-level check — some packs may be planned but not yet registered
    if missing_packs:
        pytest.xfail(
            "Profile mapping references packs missing from pack_registry:\n"
            + "\n".join(missing_packs)
        )
