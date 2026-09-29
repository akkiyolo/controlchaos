"""Pydantic schemas for datasets, trial balance, and generation jobs."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    id: str
    name: str
    seed: int
    params: Dict[str, Any]
    period_start: str
    period_end: str
    status: str
    created_by: str
    is_baseline: bool
    parent_dataset_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
    total: int


class TrialBalanceItem(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    normal_balance: str
    total_debit: float
    total_credit: float
    net_balance: float


class TrialBalanceResponse(BaseModel):
    dataset_id: str
    items: List[TrialBalanceItem]
    sum_debit: float
    sum_credit: float
    net_difference: float
    is_balanced: bool


class GLEntryResponse(BaseModel):
    id: str
    dataset_id: str
    entry_id: str
    posting_date: str
    period: str
    entity_id: str
    account_code: str
    debit: float
    credit: float
    currency: str
    fx_rate: float
    description: str
    source_system: str
    batch_id: str
    created_by: str
    approved_by: str

    class Config:
        from_attributes = True


class SubledgerEntryResponse(BaseModel):
    id: str
    dataset_id: str
    ref_id: str
    gl_entry_id: Optional[str] = None
    subledger_type: str
    counterparty: str
    amount: float
    currency: str
    value_date: str
    status: str

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    id: str
    type: str
    status: str
    progress: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
