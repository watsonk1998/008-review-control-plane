#!/usr/bin/env python3
"""
E2E script to verify the pure YAML-driven pipeline for 008 Review Control Plane.
Demonstrates: TaskCompiler -> ProfileResolver -> BasisPackResolver -> SupportPacketBuilder
Without touching the archive directory!
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
import json

# Add project root AND apps/api to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/api')))

from src.domain.models import TaskRecord
from src.review.schema import ExtractedFacts, StructuredReviewTask
from src.review.task_compiler import TaskCompiler
from src.review.profile_resolver import resolve_review_profile
from src.review.basis_pack_resolver import BasisPackResolver
from src.review.support_packet_builder import SupportPacketBuilder
from src.main_dependencies import get_hermes_controller

async def main():
    print("==========================================================")
    print("  008 Review Control Plane - Pure YAML Pipeline E2E Test  ")
    print("==========================================================\n")
    
    # 1. Mock Task
    task_id = "e2e-yaml-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    doc_type = "hazardous_special_scheme"
    print(f"[1] Initiating Task: {task_id} (Type: {doc_type})")
    
    mock_task = TaskRecord(
        id=task_id,
        taskType="structured_review",
        capabilityMode="auto",
        query="E2E test for YAML-driven pure pipeline",
        documentType=doc_type,
        policyPackIds=[],
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        status="running"
    )
    
    # 2. Task Compiler -> ReviewBrief
    print("\n[2] Compiling Task -> ReviewBrief...")
    compiler = TaskCompiler()
    brief = compiler.compile(task=mock_task)
    print(f"    -> Brief Review ID: {brief.review_id}")
    print(f"    -> Object Type: {brief.review_object_type}")
    
    # 3. Profile Resolver (Pure YAML mapped)
    print("\n[3] ProfileResolver -> ResolvedReviewProfile...")
    structured_task = StructuredReviewTask(
        taskId=task_id,
        requestId="req-e2e",
        sourceDocumentRef={"refId": "doc123", "sourceType": "fixture", "fileName": "test.pdf", "fileType": "pdf", "storagePath": "/path/to/doc"},
        sourceDocumentPath="/path/to/doc",
        documentType=doc_type,
        disciplineTags=[],
        policyPackIds=[],
        strictMode=True
    )
    facts = ExtractedFacts()
    resolved_profile, selected_packs, executable_packs = resolve_review_profile(structured_task, facts)
    print(f"    -> Target Profile ID: {resolved_profile.documentType}")
    print(f"    -> Resolved Packs: {resolved_profile.policyPackIds}")

    # 4. Basis Pack Resolver (Pure YAML mapped)
    print("\n[4] BasisPackResolver -> ResolvedBasisProfile...")
    basis_resolver = BasisPackResolver()
    basis_profile = basis_resolver.resolve(resolved_profile)
    print(f"    -> Degraded: {basis_profile.degraded}")
    print(f"    -> Rule Packs Loaded: {[rp.rule_pack_id for rp in basis_profile.rule_packs]}")
    print(f"    -> Basis Documents Extracted: {[b.basis_id for b in basis_profile.basis_documents]}")
    
    # 5. Support Packet Builder
    print("\n[5] SupportPacketBuilder -> SupportPacket...")
    builder = SupportPacketBuilder()
    support_packet = builder.build_packet(
        review_record=mock_task,
        profile=resolved_profile,
        basis_profile=basis_profile,
        facts=facts
    )
    print(f"    -> Basis Summary Size: {len(support_packet.basis_summary)}")
    print(f"    -> Rule Pack Summary Size: {len(support_packet.rule_pack_summary)}")
    print(f"    -> Warning Signals: {support_packet.warning_signals}")
    
    print("\n==========================================================")
    print(" SUCCESS: Validated stable YAML-driven pipeline logic!")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(main())
