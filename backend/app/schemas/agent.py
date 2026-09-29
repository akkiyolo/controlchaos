"""Schemas for the Multi-Agent System and Maker-Checker Proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentProposalDTO(BaseModel):
    id: str
    run_id: str
    gap_class: str
    proposed_rule: Dict[str, Any]
    rationale: str
    backtest: Dict[str, Any]
    status: str
    maker: str
    checker: Optional[str] = None
    decided_at: Optional[datetime] = None
    comments: Optional[str] = None


class ProposalListResponse(BaseModel):
    total: int
    proposals: List[AgentProposalDTO]


class DecideProposalRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    comments: Optional[str] = Field(None, description="Checker review feedback")


class AgentChatRequest(BaseModel):
    agent_name: str = Field(..., pattern="^(adversary|investigator|control_architect|skeptic|variance_analyst)$")
    message: str = Field(..., min_length=2)
    context_data: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    agent_name: str
    reply: str
    structured_output: Optional[Dict[str, Any]] = None
    provider_used: str
    latency_ms: float
