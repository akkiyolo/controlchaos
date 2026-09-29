"""Pydantic schemas for audit logs and chain verification."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditEntryResponse(BaseModel):
    id: int
    ts: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]
    prev_hash: str
    hash: str

    class Config:
        from_attributes = True


class AuditListResponse(BaseModel):
    entries: List[AuditEntryResponse]
    total: int
    page: int
    page_size: int


class AuditVerifyResponse(BaseModel):
    is_intact: bool
    total_entries_verified: int
    broken_link: Optional[Dict[str, Any]] = None
    verification_time_ms: float
