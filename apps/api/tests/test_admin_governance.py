import pytest
from src.domain.governance_schema import DraftStatus
from src.repositories.governance_store import SQLiteGovernanceStore
from src.services.admin.governance_service import GovernanceService

@pytest.fixture
def temp_store(tmp_path):
    db_path = tmp_path / "test_gov.sqlite"
    return SQLiteGovernanceStore(str(db_path))

@pytest.fixture
def gov_service(temp_store):
    return GovernanceService(temp_store)

def test_create_and_reject_draft(gov_service):
    # Test creation
    draft = gov_service.create_draft(
        entity_type="basis",
        entity_id="test_basis_001",
        changes={"title": "Test Title"},
        created_by="tester"
    )
    assert draft.status == DraftStatus.pending_approval
    assert draft.target_entity_id == "test_basis_001"
    
    # Test reject
    rejected = gov_service.reject_draft(draft.id, notes="Not ready")
    assert rejected.status == DraftStatus.rejected
    assert rejected.reviewer_notes == "Not ready"

def test_list_drafts(gov_service):
    gov_service.create_draft("pack", "pack_123", {"status": "inactive"})
    drafts = gov_service.list_drafts()
    assert len(drafts) == 1
    assert drafts[0].target_entity_type == "pack"
