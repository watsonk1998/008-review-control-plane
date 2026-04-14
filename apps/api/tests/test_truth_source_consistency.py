"""
测试类 1：真相源一致性测试

验证:
- 治理台读取的是 YAML 真相源（顶层结构，无 'mappings' 包裹）
- SQLite governance store 不是 runtime truth source
- Runtime published configuration 只读 YAML
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.admin.governance_service import GovernanceService
from src.repositories.governance_store import SQLiteGovernanceStore
from src.review.profile_resolver import _load_profile_mapping
from src.review.basis_pack_resolver import BasisPackResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

YAML_DIR = Path(__file__).resolve().parents[3] / "config" / "review_basis"
PROFILE_MAPPING_PATH = YAML_DIR / "profile_mapping.yaml"
BASIS_REGISTRY_PATH = YAML_DIR / "basis_registry.yaml"


@pytest.fixture
def real_yaml_data():
    """Load the actual profile_mapping.yaml for comparison."""
    assert PROFILE_MAPPING_PATH.exists(), (
        f"profile_mapping.yaml not found at {PROFILE_MAPPING_PATH}"
    )
    with open(PROFILE_MAPPING_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@pytest.fixture
def basis_registry_data():
    assert BASIS_REGISTRY_PATH.exists(), (
        f"basis_registry.yaml not found at {BASIS_REGISTRY_PATH}"
    )
    with open(BASIS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@pytest.fixture
def temp_store(tmp_path):
    db_path = tmp_path / "test_truth.sqlite"
    return SQLiteGovernanceStore(str(db_path))


@pytest.fixture
def gov_service(temp_store):
    return GovernanceService(temp_store)


# ---------------------------------------------------------------------------
# Test 1: Governance reads current YAML shape (top-level, no wrapper)
# ---------------------------------------------------------------------------

def test_governance_profile_mapping_reads_current_yaml_shape(gov_service, real_yaml_data):
    """治理台 get_profile_mapping() 必须返回与 YAML 文件完全一致的结构。

    profile_mapping.yaml 是顶层直接映射（hazardous_special_scheme: {...}），
    不存在 'mappings:' 包裹层。治理台必须直接传递原始 dict。
    """
    dto = gov_service.get_profile_mapping()
    mappings = dto.mappings

    # Must not be empty
    assert mappings, "Governance service returned empty mappings — likely reading wrong key"

    # Every top-level key in YAML must appear in governance output
    for key in real_yaml_data:
        assert key in mappings, (
            f"YAML key '{key}' missing from governance output. "
            f"Governance may still be using data.get('mappings', {{}})."
        )

    # Every key in governance output must exist in YAML
    for key in mappings:
        assert key in real_yaml_data, (
            f"Governance output contains key '{key}' not present in YAML."
        )

    # Spot-check a known profile's structure
    for profile_key, profile_data in real_yaml_data.items():
        gov_profile = mappings.get(profile_key)
        assert gov_profile is not None
        assert gov_profile.get("profile_id") == profile_data.get("profile_id"), (
            f"profile_id mismatch for '{profile_key}'"
        )


# ---------------------------------------------------------------------------
# Test 2: Runtime published configuration reads YAML only
# ---------------------------------------------------------------------------

def test_runtime_published_configuration_reads_yaml_only(real_yaml_data):
    """Runtime 端（profile_resolver, basis_pack_resolver）必须只读 YAML。

    验证 runtime 读到的 profile_mapping 与文件内容完全一致，
    且没有经过任何 SQLite 中间层。
    """
    # profile_resolver path
    resolver_data = _load_profile_mapping()
    assert resolver_data == real_yaml_data, (
        "profile_resolver._load_profile_mapping() does not match YAML file content"
    )

    # basis_pack_resolver path
    bpr = BasisPackResolver()
    assert bpr.profile_mapping == real_yaml_data, (
        "BasisPackResolver.profile_mapping does not match YAML file content"
    )


# ---------------------------------------------------------------------------
# Test 3: Governance store is NOT runtime truth source
# ---------------------------------------------------------------------------

def test_governance_store_is_not_runtime_truth_source(gov_service, real_yaml_data):
    """即使 governance store 中存在 draft / modified mapping，
    正式 runtime 行为也不应受影响。

    SQLite governance store 只用于 draft → approval → manual transcription 流程，
    不参与 runtime resolution。
    """
    # Create a governance draft that modifies a profile
    gov_service.create_draft(
        entity_type="profile_mapping",
        entity_id="hazardous_special_scheme",
        changes={
            "default_pack_ids": ["FAKE_PACK_INJECTED_BY_GOVERNANCE"],
            "rule_pack_ids": ["FAKE_RULE_PACK"],
        },
        created_by="test_truth_source",
    )

    # Runtime resolver must still reflect YAML, not the draft
    resolver_data = _load_profile_mapping()
    hazardous_entry = resolver_data.get("hazardous_special_scheme", {})
    assert "FAKE_PACK_INJECTED_BY_GOVERNANCE" not in hazardous_entry.get("default_pack_ids", []), (
        "Runtime profile_mapping is polluted by governance draft — truth source violation"
    )

    bpr = BasisPackResolver()
    bpr_mapping = bpr.profile_mapping.get("hazardous_special_scheme", {})
    assert "FAKE_PACK_INJECTED_BY_GOVERNANCE" not in bpr_mapping.get("default_pack_ids", []), (
        "BasisPackResolver profile_mapping is polluted by governance draft"
    )

    # Governance service itself still reads from YAML (not from its own store)
    dto = gov_service.get_profile_mapping()
    gov_hazardous = dto.mappings.get("hazardous_special_scheme", {})
    assert "FAKE_PACK_INJECTED_BY_GOVERNANCE" not in gov_hazardous.get("default_pack_ids", []), (
        "Governance get_profile_mapping() reads from store instead of YAML"
    )


def test_distribution_network_governed_basis_files_are_registered(basis_registry_data):
    expected_basis_ids = {
        "power-grid-《电网工程建设施工安全基准风险指南》（2012年版）",
        "power-grid-《工程建设标准强制性条文 电力工程部分》（2016年版）",
        "power-grid-《中国南方电网公司电网建设工程专项施工方案管理工作指引》（2022）",
        "power-grid-《中国南方电网基建施工方案全流程管控工作指引》",
    }
    for basis_id in expected_basis_ids:
        assert basis_id in basis_registry_data, f"missing governed basis: {basis_id}"
        entry = basis_registry_data[basis_id]
        refs = entry.get("file_refs", [])
        assert refs and all(str(ref).startswith("knowledge/review_basis/") for ref in refs), (
            f"{basis_id} still points outside knowledge/review_basis"
        )
        tags = set(entry.get("applicability_tags", []))
        assert {"distribution_network_special_scheme", "power_outage_work"} <= tags, (
            f"{basis_id} missing distribution-network applicability tags"
        )
