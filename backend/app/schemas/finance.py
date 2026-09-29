"""Pydantic schemas for Finance Views (Variance Studio, Treasury, and Reconciliation)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VarianceRowDTO(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    actual: float
    budget: float
    variance_amount: float
    variance_pct: float
    is_adverse: bool
    status: str  # on_target, watch, breach


class VarianceStudioResponse(BaseModel):
    dataset_id: str
    period: str
    entity_id: Optional[str] = None
    total_actual_revenue: float
    total_budget_revenue: float
    total_actual_expense: float
    total_budget_expense: float
    net_income_variance: float
    rows: List[VarianceRowDTO]


class AICommentaryRequest(BaseModel):
    dataset_id: str
    account_code: str
    period: str
    entity_id: Optional[str] = None
    actual: float
    budget: float


class AICommentaryResponse(BaseModel):
    account_code: str
    period: str
    entity: str
    variance_amount: float
    variance_pct: float
    factual_drivers: List[str]
    management_commentary: str
    is_legitimate_or_anomalous: str


class TreasuryMetricsDTO(BaseModel):
    dataset_id: str
    as_of_date: str
    total_cash_usd: float
    total_hqla_usd: float
    total_inflows_30d_usd: float
    total_outflows_30d_usd: float
    net_30d_outflow_usd: float
    lcr_ratio: float
    lcr_status: str  # Compliant, Warning, Deficit
    by_currency: List[Dict[str, Any]]
    maturity_ladder: List[Dict[str, Any]]
    funding_sources: List[Dict[str, Any]]


class ReconciliationBreakDTO(BaseModel):
    break_id: str
    subledger_type: str
    ref_id: str
    gl_entry_id: Optional[str] = None
    counterparty: str
    gl_amount: Optional[float] = None
    subledger_amount: float
    variance: float
    value_date: str
    aging_days: int
    aging_bucket: str  # <15d, 15-30d, 30-60d, >60d
    status: str        # open, resolved, under_investigation
    resolution_notes: Optional[str] = None


class ReconciliationSummaryResponse(BaseModel):
    dataset_id: str
    subledgers: List[Dict[str, Any]]
    total_breaks: int
    total_break_amount: float
    aging_breakdown: Dict[str, int]
    breaks: List[ReconciliationBreakDTO]


class ReconciliationResolveRequest(BaseModel):
    break_id: str
    action: str = Field(description="'resolve', 'investigate', or 'write_off'")
    resolution_notes: str
