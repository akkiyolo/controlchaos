"""Audit log endpoints and chain verification."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.rbac import Role, require_roles
from app.db import get_db
from app.models.entities import User
from app.schemas.audit import AuditEntryResponse, AuditListResponse, AuditVerifyResponse
from app.services.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/list", response_model=AuditListResponse)
def list_audit_entries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        Role.ADMIN.value,
        Role.AUDITOR.value,
        Role.CONTROL_OWNER.value,
        Role.REVIEWER.value,
        Role.ANALYST.value,
    )),
):
    offset = (page - 1) * page_size
    entries, total = AuditService.list_entries(
        db=db, limit=page_size, offset=offset, action=action, entity_type=entity_type
    )
    return AuditListResponse(
        entries=[AuditEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/verify", response_model=AuditVerifyResponse)
def verify_audit_chain(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        Role.ADMIN.value,
        Role.AUDITOR.value,
        Role.CONTROL_OWNER.value,
        Role.REVIEWER.value,
        Role.ANALYST.value,
    )),
):
    start = time.perf_counter()
    is_intact, count, broken_info = AuditService.verify_chain(db)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return AuditVerifyResponse(
        is_intact=is_intact,
        total_entries_verified=count,
        broken_link=broken_info,
        verification_time_ms=round(elapsed_ms, 2),
    )
