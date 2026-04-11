from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HermesReviewDecisionInputs(BaseModel):
    support_packet_008: dict[str, Any] | None = None
    support_result_008: dict[str, Any] | None = None
    hermes_review_packets: list[dict[str, Any]] = Field(default_factory=list)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
