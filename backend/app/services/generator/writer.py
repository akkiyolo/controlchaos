"""High-performance batched bulk writer for remote Render PostgreSQL."""

import logging
from typing import Any, Dict, List

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.entities import (
    Budget,
    Dataset,
    FXRate,
    GLEntry,
    Job,
    SubledgerEntry,
    TreasuryPosition,
)
from app.services.audit.service import AuditService

logger = logging.getLogger(__name__)


def chunk_list(data: List[Any], chunk_size: int = 500):
    """Splits a list into chunks for batched bulk insertion."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


class BulkDatasetWriter:
    """Writes generated dataset records in optimized batches with progress updates."""

    @staticmethod
    def write_dataset(
        db: Session,
        generated: Dict[str, Any],
        params_dict: Dict[str, Any],
        creator_email: str,
        job_id: str | None = None,
    ) -> Dataset:
        dataset_id = generated["dataset_id"]

        def update_job_progress(progress_pct: int):
            if job_id:
                job = db.get(Job, job_id)
                if job:
                    job.progress = progress_pct
                    db.commit()

        # 1. Create Dataset record
        dataset = Dataset(
            id=dataset_id,
            name=params_dict.get("name", "Baseline Ledger"),
            seed=params_dict.get("seed", 42),
            params={
                **params_dict,
                "decoys": generated.get("decoys", []),
                "summary": {
                    "total_gl_entries": generated["total_gl_entries"],
                    "total_subledger_entries": generated["total_subledger_entries"],
                    "total_debits": generated["total_debits"],
                    "total_credits": generated["total_credits"],
                },
            },
            period_start=generated["period_start"],
            period_end=generated["period_end"],
            status="pending",
            created_by=creator_email,
            is_baseline=True,
            parent_dataset_id=None,
        )
        db.add(dataset)
        db.commit()
        update_job_progress(10)

        # 2. Batch insert GL Entries
        gl_rows = generated["gl_rows"]
        for chunk in chunk_list(gl_rows, chunk_size=500):
            db.execute(insert(GLEntry), chunk)
            db.commit()
        update_job_progress(45)

        # 3. Batch insert Sub-ledger Entries
        subledger_rows = generated["subledger_rows"]
        for chunk in chunk_list(subledger_rows, chunk_size=500):
            db.execute(insert(SubledgerEntry), chunk)
            db.commit()
        update_job_progress(65)

        # 4. Batch insert Budget Targets
        budget_rows = generated["budget_rows"]
        for chunk in chunk_list(budget_rows, chunk_size=500):
            db.execute(insert(Budget), chunk)
            db.commit()
        update_job_progress(75)

        # 5. Batch insert Treasury Positions
        treasury_rows = generated["treasury_rows"]
        for chunk in chunk_list(treasury_rows, chunk_size=500):
            db.execute(insert(TreasuryPosition), chunk)
            db.commit()
        update_job_progress(85)

        # 6. Batch insert FX Rates
        fx_rows = generated["fx_rows"]
        for chunk in chunk_list(fx_rows, chunk_size=500):
            db.execute(insert(FXRate), chunk)
            db.commit()
        update_job_progress(95)

        # Mark dataset ready and record audit log
        dataset.status = "ready"
        db.commit()

        AuditService.record(
            db=db,
            actor=creator_email,
            action="DATASET_GENERATE",
            entity_type="dataset",
            entity_id=dataset_id,
            payload={
                "name": dataset.name,
                "seed": dataset.seed,
                "gl_entries_count": generated["total_gl_entries"],
                "subledger_entries_count": generated["total_subledger_entries"],
                "total_debits": generated["total_debits"],
            },
        )
        update_job_progress(100)

        return dataset
