import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.domain.governance_schema import (
    BasisDTO,
    DraftRecord,
    PackDTO,
    ProfileMappingDTO,
    RulePackDTO,
    CandidateArtifactDTO,
    CreateCandidateRequest,
    UpdateCandidateRequest,
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

# --- Candidates ---

@router.post("/candidates", response_model=CandidateArtifactDTO)
async def create_candidate(request: CreateCandidateRequest):
    service = get_governance_service()
    return service.create_candidate(request)

@router.get("/candidates", response_model=list[CandidateArtifactDTO])
async def list_candidates(profile_id: str | None = None, status: str | None = None):
    service = get_governance_service()
    return service.list_candidates(profile_id=profile_id, status=status)

@router.patch("/candidates/{candidate_id}", response_model=CandidateArtifactDTO)
async def update_candidate(candidate_id: str, request: UpdateCandidateRequest):
    service = get_governance_service()
    try:
        return service.update_candidate(candidate_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

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
    """模拟运行：独立隔离舱，不写正式 task store / artifacts / governance state。"""
    import uuid
    from datetime import datetime, timezone
    
    compiler = get_task_compiler()
    controller = get_hermes_controller()
    
    # Simulation task ID has explicit prefix — never collides with production
    task_id = f"simulation-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    
    # Mock TaskRecord — NOT persisted to SQLite task store
    mock_task = TaskRecord(
        id=task_id,
        taskType="structured_review",
        capabilityMode="auto",
        query="[SIMULATION] 模拟运行",
        documentType=request.document_type,
        policyPackIds=request.pack_ids,
        createdAt=now,
        updatedAt=now,
        status="simulation"
    )
    
    # Simulation uses a temp path — never touches real document storage
    mock_doc_path = f"/tmp/simulation-sandbox/{task_id}/{request.target_file_id}"
    
    plan = {
        "reviewProfile": {"documentTypeHint": request.document_type},
        "hermesInput": {
            "focusRequirements": request.rule_pack_ids
        },
        "simulation_mode": True,  # Always forced True regardless of request
        "learning_mode": request.learning_mode
    }
    
    # --- SIMULATION ISOLATION GUARDS ---
    # All artifact callbacks are no-op: simulation NEVER writes formal artifacts
    def _noop_json(name, content): pass  # noqa: E704
    def _noop_text(name, content, ext): pass  # noqa: E704
    def _noop_binary(name, content, ext): pass  # noqa: E704
    
    try:
        result = await controller.run(
            task=mock_task,
            plan=plan,
            source_document_ref=None,
            source_document_path=mock_doc_path,
            fixture=None,
            emit=None,
            write_json_artifact=_noop_json,
            write_text_artifact=_noop_text,
            write_binary_artifact=_noop_binary,
        )
        
        # Build response from decision inputs
        decision_inputs = result.get('hermesController', {}).get('decisionInputs', {})
        support_packet = decision_inputs.get('support_packet_008')
        hermes_packets = decision_inputs.get('hermes_review_packets', [])
        
        # Collect and store generated candidates if in learning mode
        generated_candidates = result.get('hermesController', {}).get('learningGeneratedCandidates', [])
        saved_candidates = []
        if request.learning_mode and generated_candidates:
            gov_service = get_governance_service()
            from src.domain.governance_schema import CreateCandidateRequest
            profile_id = request.document_type # mapping hint
            for cand in generated_candidates:
                req = CreateCandidateRequest(
                    profile_id=profile_id,
                    candidate_type=cand.get("type", "template_hint"),
                    content=cand.get("content", ""),
                    source="simulation"
                )
                saved = gov_service.create_candidate(req)
                saved_candidates.append(saved.model_dump())

        return SimulationRunResponse(
            result_class="simulation_preview",
            user_visible_title="⚠️ 模拟环境隔离舱结果",
            user_visible_notice="当前运行在独立验证舱，不影响生产数据，不会改变任何持久化事实基线。",
            support_packet=support_packet,
            hermes_review_packets=hermes_packets,
            generated_candidates=saved_candidates if saved_candidates else None
        )
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
