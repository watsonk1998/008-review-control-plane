import pytest
from pathlib import Path
from typing import Any
import tempfile
import json
import uuid

from src.review.hermes.template_registry import HermesTemplateRegistry
from src.review.hermes.template_models import AgentTemplate
from src.domain.models import TaskRecord, SourceDocumentRef
from src.review.basis_pack_resolver import BasisPackResolver
from src.review.schema import ResolvedReviewProfile


@pytest.fixture
def temp_dirs():
    with (
        tempfile.TemporaryDirectory() as seed_dir,
        tempfile.TemporaryDirectory() as runtime_dir,
    ):
        yield Path(seed_dir), Path(runtime_dir)


def test_online_main_chain_does_not_save_runtime_templates(temp_dirs):
    """
    Test 1: Formal main chain MUST NOT save runtime templates to disk.
    Ensures HermesTemplateRegistry(formal_mode=True) raises error on save.
    """
    seed_dir, runtime_dir = temp_dirs
    registry = HermesTemplateRegistry(
        seed_dir=seed_dir, runtime_dir=runtime_dir, formal_mode=True
    )

    template = AgentTemplate(
        id="test_candidate",
        role="assistant",
        agent_name="Test Agent",
        agent_purpose="Testing",
        agent_scope="Testing Scope",
        prompt="test prompt",
        schemaVersion="1.0",
    )

    with pytest.raises(RuntimeError) as exc_info:
        registry.save_runtime_template(template, task_id="task_123")

    assert "save_runtime_template is FORBIDDEN in formal_mode" in str(exc_info.value)
    assert not (runtime_dir / "task_123").exists()


def test_basis_pack_resolver_does_not_use_sqlite(monkeypatch):
    """
    Test 2: BasisPackResolver strictly operates on YAML registries and never queries SQLite.
    We assert that it doesn't have any SQLite dependencies or database sessions injected.
    """
    resolver = BasisPackResolver()

    # Prove that the class has exactly the configured YAML dictionaries and no db.
    assert hasattr(resolver, "profile_mapping")
    assert hasattr(resolver, "pack_registry")
    assert hasattr(resolver, "rule_pack_registry")
    assert hasattr(resolver, "basis_registry")
    assert not hasattr(resolver, "db")
    assert not hasattr(resolver, "session")
    assert not hasattr(resolver, "store")


def test_basis_pack_resolver_closed_loop():
    """
    Test 3: BasisPackResolver should recursively pull basis_ids from rule_packs' related_pack_ids.
    """
    resolver = BasisPackResolver()
    # Mocking internal YAML dicts for consistent testing
    resolver.profile_mapping = {
        "construction_org": {
            "profile_id": "test_profile",
            "rule_pack_ids": ["test_rule_pack"],
        }
    }
    resolver.rule_pack_registry = {
        "test_rule_pack": {"related_pack_ids": ["related_pack_1"]}
    }
    resolver.pack_registry = {"related_pack_1": {"basis_ids": ["basis_a", "basis_b"]}}
    resolver.basis_registry = {
        "basis_a": {"title": "Basis A"},
        "basis_b": {"title": "Basis B"},
    }
    resolver._tag_to_basis_ids = {}

    profile = ResolvedReviewProfile(
        documentType="construction_org",
        requestedPolicyPackIds=[],
        requestedDisciplineTags=[],
    )
    resolved = resolver.resolve(profile)

    assert resolved.degraded is False
    assert len(resolved.basis_documents) == 2
    basis_ids = [b.basis_id for b in resolved.basis_documents]
    assert "basis_a" in basis_ids
    assert "basis_b" in basis_ids


def test_simulation_allows_runtime_template_save(temp_dirs):
    """
    Test 4: Simulation/Learning mode allows writing templates to runtime_dir.
    """
    seed_dir, runtime_dir = temp_dirs
    registry = HermesTemplateRegistry(
        seed_dir=seed_dir, runtime_dir=runtime_dir, formal_mode=False
    )

    template = AgentTemplate(
        id="sim_candidate",
        role="assistant",
        agent_name="Sim Agent",
        agent_purpose="Simulating",
        agent_scope="Simulation Scope",
        prompt="sim prompt",
        schemaVersion="1.0",
    )

    res = registry.save_runtime_template(template, task_id="sim_task")
    assert res.exists()

    loaded = registry.load_templates()
    assert any(t.id == "sim_candidate" for t in loaded)
