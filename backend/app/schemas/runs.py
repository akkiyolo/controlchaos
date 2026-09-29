"""Schemas for Runs, Detection Matching, and Scorecards."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecuteRunRequest(BaseModel):
    dataset_id: str
    control_keys: Optional[List[str]] = Field(None, description="Subset of controls to execute, or None for all")
    match_mode: str = Field(default="strict_row", pattern="^(strict_row|account_period)$")


class DetectionDTO(BaseModel):
    mutation_id: str
    detected: bool
    detected_by: List[str]
    partial_credit: float
    time_to_detect_ms: Optional[int] = None


class MarginalValueDTO(BaseModel):
    control_id: str
    marginal_drop_count: int
    marginal_value_pct: float
    unique_catches: int
    is_critical: bool


class BlindSpotCellDTO(BaseModel):
    class_name: str
    stealth: str
    magnitude: str
    tested: int
    detected: int
    detection_rate_pct: float
    status: str


class ScorecardResponse(BaseModel):
    run_id: str
    dataset_id: str
    overall_detection_rate: float
    weighted_detection_rate: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    cost_of_misses: float
    by_class: Dict[str, Any]
    by_control: Dict[str, Any]
    detections: List[DetectionDTO]
    marginal_values: List[MarginalValueDTO]
    blindspot_map: List[BlindSpotCellDTO]


class RunListItemDTO(BaseModel):
    id: str
    dataset_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    overall_detection_rate: Optional[float] = None
    precision: Optional[float] = None
    cost_of_misses: Optional[float] = None
    total_findings: int


class RunListResponse(BaseModel):
    total: int
    runs: List[RunListItemDTO]
