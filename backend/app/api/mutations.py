"""Mutation Catalog and Campaign API Endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db import get_db
from app.models.entities import MutationLedger, User
from app.schemas.mutation import (
    CreateCampaignRequest,
    MutationLedgerItemDTO,
    MutationLedgerResponse,
    MutatorCatalogResponse,
    MutatorInfoDTO,
)
from app.services.mutators.campaign import CampaignRunner, mutator_registry

router = APIRouter(prefix="/mutations", tags=["mutations"])


@router.get("/catalog", response_model=MutatorCatalogResponse)
def get_mutation_catalog(current_user: User = Depends(get_current_user)) -> MutatorCatalogResponse:
    """List all 20 available accounting error mutator classes."""
    mutators = mutator_registry.list_all()
    items = [
        MutatorInfoDTO(
            key=m.key,
            name=m.name,
            description=m.description,
            default_severity=m.default_severity,
        )
        for m in mutators
    ]
    return MutatorCatalogResponse(total=len(items), mutators=items)


@router.post("/campaign", response_model=Dict[str, Any])
def create_mutation_campaign(
    req: CreateCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "control_owner", "analyst")),
) -> Dict[str, Any]:
    """Execute a mutation campaign: clone parent dataset and inject accounting errors."""
    try:
        mutations_config = [m.model_dump() for m in req.mutations]
        child_dataset, applied_records = CampaignRunner.clone_and_mutate(
            db=db,
            parent_dataset_id=req.parent_dataset_id,
            campaign_name=req.campaign_name,
            mutations_config=mutations_config,
            seed=req.seed,
            actor=current_user.email,
        )
        return {
            "dataset_id": child_dataset.id,
            "dataset_name": child_dataset.name,
            "parent_dataset_id": req.parent_dataset_id,
            "mutations_injected": len(applied_records),
            "total_expected_impact": sum(r.expected_impact_amount for r in applied_records),
            "injected_mutations": [r.to_dict() for r in applied_records],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/datasets/{dataset_id}/ledger", response_model=MutationLedgerResponse)
def get_dataset_mutation_ledger(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MutationLedgerResponse:
    """Retrieve ground-truth injected mutations from the mutation_ledger for a dataset."""
    records = db.execute(
        select(MutationLedger).where(MutationLedger.dataset_id == dataset_id).order_by(MutationLedger.injected_at.asc())
    ).scalars().all()

    items = [
        MutationLedgerItemDTO(
            id=r.id,
            dataset_id=r.dataset_id,
            mutation_id=r.mutation_id,
            class_name=r.class_name,
            params=r.params,
            affected_row_refs=r.affected_row_refs,
            expected_impact_amount=float(r.expected_impact_amount),
            injected_at=r.injected_at,
        )
        for r in records
    ]
    return MutationLedgerResponse(total=len(items), mutations=items)
