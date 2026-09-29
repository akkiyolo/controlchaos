"""Controls, Versioning, Maker-Checker, and Suite Execution API Endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db import get_db
from app.models.entities import ControlDefinition, ControlVersion, Finding, Run, User
from app.schemas.controls import (
    ControlApprovalRequest,
    ControlDefinitionDTO,
    ControlEditRequest,
    ControlListResponse,
    ControlRunRequest,
    ControlVersionDTO,
    FindingSummaryDTO,
    RunSummaryDTO,
)
from app.services.controls.registry import registry
from app.services.controls.runner import ControlRunner

router = APIRouter(prefix="/controls", tags=["controls"])


@router.get("", response_model=ControlListResponse)
def list_controls(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ControlListResponse:
    """List all registered controls with their active version, parameters, and pending drafts."""
    # Ensure all 15 controls are seeded in database
    registry.seed_defaults(db, audit_actor=current_user.email)

    query = select(ControlDefinition).order_by(ControlDefinition.key)
    if category:
        query = query.where(ControlDefinition.category == category)

    c_defs = db.execute(query).scalars().all()

    # Pre-fetch pending versions (approved_by is None)
    pending_versions = {
        v.control_id: v
        for v in db.execute(
            select(ControlVersion).where(ControlVersion.approved_by.is_(None))
        ).scalars().all()
    }

    result = []
    for c in c_defs:
        ctrl_impl = registry.get(c.key)
        intended_errors = ctrl_impl.intended_error_classes if ctrl_impl else []

        pending_v = pending_versions.get(c.id)
        pending_dto = (
            ControlVersionDTO(
                id=pending_v.id,
                control_id=pending_v.control_id,
                version=pending_v.version,
                params=pending_v.params,
                created_by=pending_v.created_by,
                approved_by=pending_v.approved_by,
                created_at=pending_v.created_at,
                diff=pending_v.diff,
            )
            if pending_v
            else None
        )

        result.append(
            ControlDefinitionDTO(
                id=c.id,
                key=c.key,
                name=c.name,
                category=c.category,
                description=c.description,
                params=c.params,
                version=c.version,
                status=c.status,
                owner=c.owner,
                created_at=c.created_at,
                intended_error_classes=intended_errors,
                pending_version=pending_dto,
            )
        )

    return ControlListResponse(total=len(result), controls=result)


@router.get("/{key}", response_model=Dict[str, Any])
def get_control_detail(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get control definition and complete version audit history."""
    c_def = db.execute(select(ControlDefinition).where(ControlDefinition.key == key)).scalar_one_or_none()
    if not c_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Control '{key}' not found")

    versions = db.execute(
        select(ControlVersion).where(ControlVersion.control_id == c_def.id).order_by(desc(ControlVersion.version))
    ).scalars().all()

    ctrl_impl = registry.get(key)
    intended_errors = ctrl_impl.intended_error_classes if ctrl_impl else []

    return {
        "control": ControlDefinitionDTO(
            id=c_def.id,
            key=c_def.key,
            name=c_def.name,
            category=c_def.category,
            description=c_def.description,
            params=c_def.params,
            version=c_def.version,
            status=c_def.status,
            owner=c_def.owner,
            created_at=c_def.created_at,
            intended_error_classes=intended_errors,
        ),
        "versions": [
            ControlVersionDTO(
                id=v.id,
                control_id=v.control_id,
                version=v.version,
                params=v.params,
                created_by=v.created_by,
                approved_by=v.approved_by,
                created_at=v.created_at,
                diff=v.diff,
            )
            for v in versions
        ],
    }


@router.post("/{key}/edit", response_model=ControlVersionDTO)
def propose_control_edit(
    key: str,
    req: ControlEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("control_owner", "admin")),
) -> ControlVersionDTO:
    """Propose changes to a control's parameters (Maker step). Creates a draft version pending review."""
    registry.seed_defaults(db, audit_actor=current_user.email)
    try:
        draft = registry.propose_edit(
            db=db,
            control_key=key,
            new_params=req.params,
            maker=current_user.email,
            rationale=req.rationale,
        )
        return ControlVersionDTO(
            id=draft.id,
            control_id=draft.control_id,
            version=draft.version,
            params=draft.params,
            created_by=draft.created_by,
            approved_by=draft.approved_by,
            created_at=draft.created_at,
            diff=draft.diff,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{key}/versions/{version_id}/decide", response_model=Dict[str, Any])
def decide_control_edit(
    key: str,
    version_id: str,
    req: ControlApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
) -> Dict[str, Any]:
    """Approve or reject a proposed control parameter change (Checker step).

    Enforces maker != checker segregation of duties.
    """
    try:
        if req.action == "approve":
            c_def = registry.approve_edit(
                db=db,
                control_key=key,
                version_id=version_id,
                checker=current_user.email,
                comment=req.comment,
            )
            return {
                "status": "approved",
                "control_key": key,
                "active_version": c_def.version,
                "params": c_def.params,
            }
        else:
            registry.reject_edit(
                db=db,
                control_key=key,
                version_id=version_id,
                checker=current_user.email,
                comment=req.comment,
            )
            return {"status": "rejected", "control_key": key, "version_id": version_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/run", response_model=RunSummaryDTO)
def run_controls_suite(
    req: ControlRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunSummaryDTO:
    """Execute financial controls suite against a synthetic dataset."""
    try:
        run = ControlRunner.run_suite(
            db=db,
            dataset_id=req.dataset_id,
            control_keys=req.control_keys,
            custom_params=req.custom_params,
            actor=current_user.email,
        )
        return get_run_summary(run.id, db=db, current_user=current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/runs/{run_id}", response_model=RunSummaryDTO)
def get_run_summary(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunSummaryDTO:
    """Retrieve run execution summary with categorized findings."""
    run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found")

    findings = db.execute(select(Finding).where(Finding.run_id == run_id)).scalars().all()

    by_severity: Dict[str, int] = {}
    by_control: Dict[str, int] = {}
    finding_dtos: List[FindingSummaryDTO] = []

    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_control[f.control_id] = by_control.get(f.control_id, 0) + 1
        finding_dtos.append(
            FindingSummaryDTO(
                id=f.id,
                run_id=f.run_id,
                control_id=f.control_id,
                finding_id=f.finding_id,
                severity=f.severity,
                description=f.description,
                affected_row_refs=f.affected_row_refs,
                amount=float(f.amount) if f.amount is not None else None,
                detected_at=f.detected_at,
            )
        )

    duration_ms = run.config.get("duration_ms") if run.config else None

    return RunSummaryDTO(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        total_findings=len(findings),
        findings_by_severity=by_severity,
        findings_by_control=by_control,
        duration_ms=duration_ms,
        findings=finding_dtos,
    )
