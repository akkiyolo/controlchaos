"""Datasets, synthetic ledger generation, and trial balance endpoints."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user
from app.db import SessionLocal, get_db
from app.models.entities import (
    Account,
    Dataset,
    GLEntry,
    Job,
    LegalEntity,
    SubledgerEntry,
    User,
)
from app.schemas.dataset import (
    DatasetListResponse,
    DatasetResponse,
    GLEntryResponse,
    JobStatusResponse,
    SubledgerEntryResponse,
    TrialBalanceItem,
    TrialBalanceResponse,
)
from app.services.generator.ledger_generator import SyntheticLedgerGenerator
from app.services.generator.models import GeneratorParams
from app.services.generator.writer import BulkDatasetWriter

router = APIRouter(prefix="/datasets", tags=["datasets"])


def run_generator_task(job_id: str, params: GeneratorParams, creator_email: str):
    """Background task executing synthetic ledger generation and database ingestion."""
    db = SessionLocal()
    job = db.get(Job, job_id)
    if not job:
        db.close()
        return

    try:
        job.status = "running"
        job.progress = 5
        db.commit()

        # Load available legal entities from DB
        entities_records = list(db.scalars(select(LegalEntity).limit(params.entities_count)).all())
        entities_data = [
            {"id": e.id, "code": e.code, "name": e.name, "currency": e.currency, "region": e.region}
            for e in entities_records
        ]
        if not entities_data:
            # Fallback default entities if DB empty
            entities_data = [
                {"id": str(uuid.uuid4()), "code": "LE-100", "name": "Global Markets Corp (London)", "currency": "GBP", "region": "EMEA"},
                {"id": str(uuid.uuid4()), "code": "LE-200", "name": "North America Prime Brokerage LLC", "currency": "USD", "region": "AMER"},
                {"id": str(uuid.uuid4()), "code": "LE-300", "name": "Asia Pacific Treasury Ltd", "currency": "INR", "region": "APAC"},
            ][:params.entities_count]

        # Generate all tables in memory
        generator = SyntheticLedgerGenerator(params, entities_data)
        generated = generator.generate_all()

        # Bulk write to database
        dataset = BulkDatasetWriter.write_dataset(
            db=db,
            generated=generated,
            params_dict=params.model_dump(),
            creator_email=creator_email,
            job_id=job_id,
        )

        job.status = "completed"
        job.progress = 100
        job.result = {
            "dataset_id": dataset.id,
            "name": dataset.name,
            "total_gl_entries": generated["total_gl_entries"],
            "total_subledger_entries": generated["total_subledger_entries"],
            "total_debits": generated["total_debits"],
            "total_credits": generated["total_credits"],
            "decoys_count": len(generated.get("decoys", [])),
        }
        db.commit()

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        db.commit()
    finally:
        db.close()


@router.post("/generate", response_model=JobStatusResponse)
def generate_dataset(
    params: GeneratorParams,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Spawns background job generating synthetic ledger, sub-ledgers, budget, and treasury data."""
    job = Job(
        type="dataset_generation",
        status="pending",
        progress=0,
        result=None,
        error=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_generator_task, job.id, params, current_user.email)
    return job


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    is_baseline: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists available synthetic datasets."""
    query = select(Dataset)
    if is_baseline is not None:
        query = query.where(Dataset.is_baseline == is_baseline)

    total = len(list(db.scalars(query).all()))
    datasets = list(db.scalars(query.order_by(desc(Dataset.created_at)).limit(limit).offset(offset)).all())
    return DatasetListResponse(
        datasets=[DatasetResponse.model_validate(d) for d in datasets],
        total=total,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves dataset details by ID."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    dataset_id: str,
    period: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Computes aggregated trial balance per account code."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Load chart of accounts
    accounts = {a.code: a for a in db.scalars(select(Account)).all()}

    # Aggregate GL entries debits and credits grouped by account_code
    query = (
        select(
            GLEntry.account_code,
            func.sum(GLEntry.debit).label("total_debit"),
            func.sum(GLEntry.credit).label("total_credit"),
        )
        .where(GLEntry.dataset_id == dataset_id)
        .group_by(GLEntry.account_code)
    )
    if period:
        query = query.where(GLEntry.period == period)
    if entity_id:
        query = query.where(GLEntry.entity_id == entity_id)

    results = db.execute(query).all()

    items: List[TrialBalanceItem] = []
    sum_dr = 0.0
    sum_cr = 0.0

    for row in results:
        acc_code = row.account_code
        dr = float(row.total_debit or 0.0)
        cr = float(row.total_credit or 0.0)
        sum_dr += dr
        sum_cr += cr

        acc = accounts.get(acc_code)
        acc_name = acc.name if acc else f"Account {acc_code}"
        acc_type = acc.type if acc else "unknown"
        norm_bal = acc.normal_balance if acc else "debit"

        # Net balance: for asset/expense accounts (Dr - Cr), for liability/equity/revenue (Cr - Dr)
        net = (dr - cr) if norm_bal == "debit" else (cr - dr)

        items.append(TrialBalanceItem(
            account_code=acc_code,
            account_name=acc_name,
            account_type=acc_type,
            normal_balance=norm_bal,
            total_debit=round(dr, 4),
            total_credit=round(cr, 4),
            net_balance=round(net, 4),
        ))

    items.sort(key=lambda x: x.account_code)
    net_diff = round(abs(sum_dr - sum_cr), 4)

    return TrialBalanceResponse(
        dataset_id=dataset_id,
        items=items,
        sum_debit=round(sum_dr, 4),
        sum_credit=round(sum_cr, 4),
        net_difference=net_diff,
        is_balanced=(net_diff < 0.01),
    )


@router.get("/{dataset_id}/gl-entries", response_model=List[GLEntryResponse])
def get_gl_entries(
    dataset_id: str,
    account_code: Optional[str] = Query(default=None),
    period: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves paginated general ledger entries."""
    query = select(GLEntry).where(GLEntry.dataset_id == dataset_id)
    if account_code:
        query = query.where(GLEntry.account_code == account_code)
    if period:
        query = query.where(GLEntry.period == period)

    entries = list(db.scalars(query.order_by(GLEntry.posting_date.asc(), GLEntry.entry_id.asc()).limit(limit).offset(offset)).all())
    return [GLEntryResponse.model_validate(e) for e in entries]


@router.get("/{dataset_id}/subledger-entries", response_model=List[SubledgerEntryResponse])
def get_subledger_entries(
    dataset_id: str,
    subledger_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves paginated sub-ledger entries."""
    query = select(SubledgerEntry).where(SubledgerEntry.dataset_id == dataset_id)
    if subledger_type:
        query = query.where(SubledgerEntry.subledger_type == subledger_type)

    entries = list(db.scalars(query.order_by(SubledgerEntry.value_date.asc()).limit(limit).offset(offset)).all())
    return [SubledgerEntryResponse.model_validate(e) for e in entries]


@router.get("/{dataset_id}/decoys")
def get_dataset_decoys(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns documented legitimate anomalies (decoys) embedded in the baseline dataset."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    decoys = dataset.params.get("decoys", [])
    return {"dataset_id": dataset_id, "decoys": decoys, "total": len(decoys)}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Polls background job execution progress and final result."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
