import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.domain.governance_schema import (
    BasisDTO,
    DraftRecord,
    PackDTO,
    ProfileMappingDTO,
    RulePackDTO,
    SimulationRunRequest,
    SimulationRunResponse,
)

from src.main_dependencies import get_governance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/governance", tags=["Admin Governance Workbench"])

@router.get("/bases", response_model=list[BasisDTO])
async def list_bases():
    service = get_governance_service()
    return service.list_bases()

@router.get("/packs", response_model=list[PackDTO])
async def list_packs():
    service = get_governance_service()
    return service.list_packs()

@router.get("/rule-packs", response_model=list[RulePackDTO])
async def list_rule_packs():
    service = get_governance_service()
    return service.list_rule_packs()

@router.get("/profiles", response_model=ProfileMappingDTO)
async def get_profile_mapping():
    service = get_governance_service()
    return service.get_profile_mapping()

from pydantic import BaseModel

class CreateDraftRequest(BaseModel):
    entity_type: str
    entity_id: str
    changes: dict[str, Any]

class ModifyDraftRequest(BaseModel):
    notes: str = ""

@router.post("/drafts", response_model=DraftRecord)
async def create_draft(request: CreateDraftRequest):
    service = get_governance_service()
    return service.create_draft(request.entity_type, request.entity_id, request.changes)

@router.get("/drafts", response_model=list[DraftRecord])
async def list_drafts(status: str | None = None):
    service = get_governance_service()
    return service.list_drafts(status)

@router.post("/drafts/{draft_id}/publish", response_model=DraftRecord)
async def publish_draft(draft_id: str, request: ModifyDraftRequest | None = None):
    service = get_governance_service()
    try:
        return service.approve_and_publish_draft(draft_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/drafts/{draft_id}/reject", response_model=DraftRecord)
async def reject_draft(draft_id: str, request: ModifyDraftRequest):
    service = get_governance_service()
    try:
        return service.reject_draft(draft_id, notes=request.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

from src.main_dependencies import (
    get_governance_service,
    get_hermes_controller,
    get_task_compiler,
    get_fixture_service
)
from src.domain.models import TaskRecord, SourceDocumentRef

@router.post("/simulation/run", response_model=SimulationRunResponse)
async def run_simulation(request: SimulationRunRequest):
    import uuid
    from datetime import datetime, timezone
    
    compiler = get_task_compiler()
    controller = get_hermes_controller()
    
    task_id = f"sim-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    
    # We construct a mock TaskRecord for simulation
    mock_task = TaskRecord(
        id=task_id,
        taskType="structured_review",
        capabilityMode="auto",
        query="Simulation Run",
        documentType=request.document_type,
        policyPackIds=request.pack_ids,
        createdAt=now,
        updatedAt=now,
        status="running"
    )
    
    # Normally we'd use source Document Ref. For simulation, assume the target_file_id is a valid fake path or fixture
    mock_doc_path = f"/tmp/simulation/{request.target_file_id}"
    
    plan = {
        "reviewProfile": {"documentTypeHint": request.document_type},
        "hermesInput": {
            "focusRequirements": request.rule_pack_ids
        },
        "simulation_mode": request.simulation_mode
    }
    
    try:
        # Call controller
        result = await controller.run(
            task=mock_task,
            plan=plan,
            source_document_ref=None,
            source_document_path=mock_doc_path,
            fixture=None,
            emit=None,
            write_json_artifact=lambda name, content: None,
            write_text_artifact=lambda name, content, ext: None,
            write_binary_artifact=lambda name, content, ext: None,
        )
        
        # Build response
        decision_inputs = result.get('hermesController', {}).get('decisionInputs', {})
        support_packet = decision_inputs.get('support_packet_008')
        hermes_packets = decision_inputs.get('hermes_review_packets', [])
        
        return SimulationRunResponse(
            result_class="simulation_preview",
            user_visible_title="⚠️ 模拟环境隔离舱结果",
            user_visible_notice="当前运行在独立验证舱，不影响生产数据，不会改变任何持久化事实基线。",
            support_packet=support_packet,
            hermes_review_packets=hermes_packets
        )
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
