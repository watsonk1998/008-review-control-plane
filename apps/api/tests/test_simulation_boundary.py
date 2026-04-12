import pytest
from src.domain.models import TaskRecord
from src.review.task_compiler import TaskCompiler
from datetime import datetime, timezone
import uuid

def test_task_compiler_simulation_mode_injection():
    compiler = TaskCompiler()
    mock_task = TaskRecord(
        id=str(uuid.uuid4()),
        taskType="structured_review",
        capabilityMode="auto",
        query="Simulation",
        documentType="construction_org",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status="running"
    )
    
    brief = compiler.compile(
        task=mock_task,
        simulation_mode=True
    )
    
    # Verify simulation mode flag is injected into the metadata
    assert brief.metadata.get("simulation_mode") is True
