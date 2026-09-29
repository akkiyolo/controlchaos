"""Control Suite Execution Runner."""

from __future__ import annotations

import datetime
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Budget,
    ControlDefinition,
    Dataset,
    Finding,
    GLEntry,
    Run,
    SubledgerEntry,
    TreasuryPosition,
)
from app.services.audit.service import AuditService
from app.services.controls.base import DatasetContext, FindingDTO
from app.services.controls.registry import registry


class ControlRunner:
    """Executes financial controls suite against a given dataset and persists findings."""

    @staticmethod
    def load_dataset_context(db: Session, dataset_id: str) -> DatasetContext:
        """Load all entries associated with a dataset into memory for rapid evaluation."""
        gl_entries = db.execute(select(GLEntry).where(GLEntry.dataset_id == dataset_id)).scalars().all()
        sub_entries = db.execute(select(SubledgerEntry).where(SubledgerEntry.dataset_id == dataset_id)).scalars().all()
        budget_entries = db.execute(select(Budget).where(Budget.dataset_id == dataset_id)).scalars().all()
        treasury_pos = db.execute(select(TreasuryPosition).where(TreasuryPosition.dataset_id == dataset_id)).scalars().all()

        # Build FX rate map from GL entries: date -> {CURR/USD: rate}
        fx_rates: Dict[str, Dict[str, float]] = defaultdict(dict)
        for gl in gl_entries:
            curr = gl.currency
            d = gl.posting_date
            rate = float(gl.fx_rate)
            if curr and d:
                fx_rates[d][f"{curr}/USD"] = rate

        return DatasetContext(
            dataset_id=dataset_id,
            gl_entries=list(gl_entries),
            subledger_entries=list(sub_entries),
            budget_entries=list(budget_entries),
            treasury_positions=list(treasury_pos),
            fx_rates=dict(fx_rates),
            db_session=db,
        )

    @classmethod
    def run_suite(
        cls,
        db: Session,
        dataset_id: str,
        control_keys: Optional[List[str]] = None,
        custom_params: Optional[Dict[str, Dict[str, Any]]] = None,
        actor: str = "system",
    ) -> Run:
        """Execute controls suite against a dataset, persist findings, and return Run summary."""
        dataset = db.execute(select(Dataset).where(Dataset.id == dataset_id)).scalar_one_or_none()
        if not dataset:
            raise ValueError(f"Dataset with ID '{dataset_id}' not found")

        # 1. Determine active parameters from ControlDefinition table
        active_defs = {
            c.key: c.params
            for c in db.execute(select(ControlDefinition).where(ControlDefinition.status == "active")).scalars().all()
        }

        # 2. Filter controls to run
        all_ctrls = registry.list_all()
        if control_keys:
            ctrls_to_run = [c for c in all_ctrls if c.key in control_keys]
        else:
            ctrls_to_run = all_ctrls

        # 3. Create Run entity
        control_snapshot: Dict[str, Any] = {}
        for c in ctrls_to_run:
            p = dict(active_defs.get(c.key, c.get_default_params()))
            if custom_params and c.key in custom_params:
                p.update(custom_params[c.key])
            control_snapshot[c.key] = p

        run = Run(
            dataset_id=dataset_id,
            control_set_snapshot=control_snapshot,
            status="running",
            started_at=datetime.datetime.now(datetime.timezone.utc),
            config={"actor": actor, "control_count": len(ctrls_to_run)},
        )
        db.add(run)
        db.flush()

        # 4. Load dataset context
        start_time = time.perf_counter()
        context = cls.load_dataset_context(db, dataset_id)

        # 5. Execute each control
        all_findings: List[FindingDTO] = []
        for ctrl in ctrls_to_run:
            params = control_snapshot.get(ctrl.key, {})
            try:
                findings = ctrl.run(context, params)
                all_findings.extend(findings)
            except Exception as e:
                # Add a finding indicating control execution error
                all_findings.append(
                    FindingDTO(
                        finding_id=f"ERR-{ctrl.key}",
                        control_id=ctrl.key,
                        severity="critical",
                        description=f"Error executing control {ctrl.key}: {str(e)}",
                        affected_row_refs=[],
                    )
                )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 6. Persist findings to database in chunks
        chunk_size = 500
        for i in range(0, len(all_findings), chunk_size):
            chunk = all_findings[i : i + chunk_size]
            db.bulk_save_objects(
                [
                    Finding(
                        run_id=run.id,
                        control_id=f.control_id,
                        finding_id=f.finding_id,
                        severity=f.severity,
                        description=f.description,
                        affected_row_refs=f.affected_row_refs,
                        amount=f.amount,
                        detected_at=datetime.datetime.now(datetime.timezone.utc),
                    )
                    for f in chunk
                ]
            )
            db.flush()

        # 7. Complete run
        run.status = "completed"
        run.finished_at = datetime.datetime.now(datetime.timezone.utc)
        run.config = {
            "actor": actor,
            "control_count": len(ctrls_to_run),
            "findings_count": len(all_findings),
            "duration_ms": duration_ms,
        }

        AuditService.record(
            db=db,
            actor=actor,
            action="run.completed",
            entity_type="run",
            entity_id=run.id,
            payload={
                "dataset_id": dataset_id,
                "control_count": len(ctrls_to_run),
                "total_findings": len(all_findings),
                "duration_ms": duration_ms,
            },
        )
        db.commit()
        db.refresh(run)
        return run
