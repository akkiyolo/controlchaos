"""Pydantic schemas for controls, versioning, maker-checker, and runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ControlVersionDTO(BaseModel):
    id: str
    control_id: str
    version: int
    params: Dict[str, Any]
    created_by: str
    approved_by: Optional[str] = None
    created_at: datetime
    diff: Optional[Dict[str, Any]] = None


class ControlDefinitionDTO(BaseModel):
    id: str
    key: str
    name: str
    category: str
    description: str
    params: Dict[str, Any]
    version: int
    status: str
    owner: str
    created_at: datetime
    intended_error_classes: List[str] = Field(default_factory=list)
    pending_version: Optional[ControlVersionDTO] = None


class ControlListResponse(BaseModel):
    total: int
    controls: List[ControlDefinitionDTO]


class ControlEditRequest(BaseModel):
    params: Dict[str, Any] = Field(..., description="Proposed new parameters")
    rationale: str = Field(..., min_length=5, description="Business rationale for changing control parameters")


class ControlApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = Field(None, description="Optional reviewer feedback")


class ControlRunRequest(BaseModel):
    dataset_id: str
    control_keys: Optional[List[str]] = Field(None, description="Subset of controls to run, or None for all")
    custom_params: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description="Optional per-control parameter overrides for ad-hoc sensitivity analysis"
    )


class FindingSummaryDTO(BaseModel):
    id: str
    run_id: str
    control_id: str
    finding_id: str
    severity: str
    description: str
    affected_row_refs: List[str]
    amount: Optional[float] = None
    detected_at: datetime


class RunSummaryDTO(BaseModel):
    id: str
    dataset_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_findings: int
    findings_by_severity: Dict[str, int]
    findings_by_control: Dict[str, int]
    duration_ms: Optional[int] = None
    findings: List[FindingSummaryDTO] = Field(default_factory=list)
