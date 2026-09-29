"""Mutation Campaign Runner and Copy-on-Write Dataset Cloner."""

from __future__ import annotations

import datetime
import random
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Budget,
    Dataset,
    GLEntry,
    MutationLedger,
    SubledgerEntry,
    TreasuryPosition,
)
from app.services.audit.service import AuditService
from app.services.mutators.base import (
    BaseMutator,
    MutableDatasetBundle,
    MutationRecordDTO,
)
from app.services.mutators.catalog import ALL_MUTATORS


class MutationRegistry:
    """Registry of all 20 financial mutator classes."""

    def __init__(self) -> None:
        self._mutators: Dict[str, BaseMutator] = {}
        for cls in ALL_MUTATORS:
            instance = cls()
            self._mutators[instance.key] = instance

    def get(self, key: str) -> Optional[BaseMutator]:
        return self._mutators.get(key)

    def list_all(self) -> List[BaseMutator]:
        return list(self._mutators.values())


mutator_registry = MutationRegistry()


class CampaignRunner:
    """Orchestrates mutation campaigns by cloning datasets and injecting ground-truth accounting errors."""

    @classmethod
    def clone_and_mutate(
        cls,
        db: Session,
        parent_dataset_id: str,
        campaign_name: str,
        mutations_config: List[Dict[str, Any]],
        seed: int = 42,
        actor: str = "system",
    ) -> tuple[Dataset, List[MutationRecordDTO]]:
        """Clone a baseline dataset, apply configured mutations, persist ground truth, and return."""
        parent = db.execute(select(Dataset).where(Dataset.id == parent_dataset_id)).scalar_one_or_none()
        if not parent:
            raise ValueError(f"Parent dataset '{parent_dataset_id}' not found")

        rng = random.Random(seed)

        # 1. Create child dataset record
        child_id = str(uuid.uuid4())
        child = Dataset(
            id=child_id,
            name=campaign_name or f"Mutated Copy of {parent.name}",
            seed=seed,
            params={**parent.params, "parent_dataset_id": parent_dataset_id, "is_mutated": True},
            period_start=parent.period_start,
            period_end=parent.period_end,
            status="ready",
            created_by=actor,
            is_baseline=False,
            parent_dataset_id=parent_dataset_id,
        )
        db.add(child)
        db.flush()

        # 2. Load parent entries into in-memory copy-on-write bundle
        parent_gls = db.execute(select(GLEntry).where(GLEntry.dataset_id == parent_dataset_id)).scalars().all()
        parent_subs = db.execute(select(SubledgerEntry).where(SubledgerEntry.dataset_id == parent_dataset_id)).scalars().all()
        parent_budgets = db.execute(select(Budget).where(Budget.dataset_id == parent_dataset_id)).scalars().all()
        parent_treasury = db.execute(select(TreasuryPosition).where(TreasuryPosition.dataset_id == parent_dataset_id)).scalars().all()

        # Construct new model instances with child_id
        cloned_gls = [
            GLEntry(
                dataset_id=child_id,
                entry_id=g.entry_id,
                posting_date=g.posting_date,
                period=g.period,
                entity_id=g.entity_id,
                account_code=g.account_code,
                debit=float(g.debit),
                credit=float(g.credit),
                currency=g.currency,
                fx_rate=float(g.fx_rate),
                description=g.description,
                source_system=g.source_system,
                batch_id=g.batch_id,
                created_by=g.created_by,
                approved_by=g.approved_by,
            )
            for g in parent_gls
        ]

        cloned_subs = [
            SubledgerEntry(
                dataset_id=child_id,
                ref_id=s.ref_id,
                gl_entry_id=s.gl_entry_id,
                subledger_type=s.subledger_type,
                counterparty=s.counterparty,
                amount=float(s.amount),
                currency=s.currency,
                value_date=s.value_date,
                status=s.status,
            )
            for s in parent_subs
        ]

        cloned_budgets = [
            Budget(
                dataset_id=child_id,
                period=b.period,
                entity_id=b.entity_id,
                account_code=b.account_code,
                amount=float(b.amount),
            )
            for b in parent_budgets
        ]

        cloned_treasury = [
            TreasuryPosition(
                dataset_id=child_id,
                as_of_date=t.as_of_date,
                entity_id=t.entity_id,
                currency=t.currency,
                cash_balance=float(t.cash_balance),
                hqla=float(t.hqla),
                outflows_30d=float(t.outflows_30d),
                inflows_30d=float(t.inflows_30d),
                funding_source=t.funding_source,
                funding_amount=float(t.funding_amount),
                maturity_bucket=t.maturity_bucket,
            )
            for t in parent_treasury
        ]

        bundle = MutableDatasetBundle(
            dataset_id=child_id,
            gl_entries=cloned_gls,
            subledger_entries=cloned_subs,
            budget_entries=cloned_budgets,
            treasury_positions=cloned_treasury,
        )

        # 3. Apply mutations
        applied_records: List[MutationRecordDTO] = []
        for cfg in mutations_config:
            c_name = str(cfg.get("class_name") or "")
            count = int(cfg.get("count", 1))
            params = {
                "magnitude": cfg.get("magnitude", "medium"),
                "stealth": cfg.get("stealth", "subtle"),
            }

            mutator = mutator_registry.get(c_name)
            if not mutator:
                continue

            for _ in range(count):
                rec = mutator.apply(bundle, rng, params)
                if rec:
                    applied_records.append(rec)

        # 4. Save mutated bundle in chunks of 500
        chunk_size = 500
        for i in range(0, len(bundle.gl_entries), chunk_size):
            db.bulk_save_objects(bundle.gl_entries[i : i + chunk_size])
            db.flush()

        for i in range(0, len(bundle.subledger_entries), chunk_size):
            db.bulk_save_objects(bundle.subledger_entries[i : i + chunk_size])
            db.flush()

        for i in range(0, len(bundle.budget_entries), chunk_size):
            db.bulk_save_objects(bundle.budget_entries[i : i + chunk_size])
            db.flush()

        for i in range(0, len(bundle.treasury_positions), chunk_size):
            db.bulk_save_objects(bundle.treasury_positions[i : i + chunk_size])
            db.flush()

        # 5. Write Ground Truth into mutation_ledger table
        ledger_objects = [
            MutationLedger(
                dataset_id=child_id,
                mutation_id=r.mutation_id,
                class_name=r.class_name,
                params={
                    "stealth": r.stealth,
                    "magnitude": r.magnitude,
                    "description": r.description,
                    "location_details": r.location_details,
                },
                affected_row_refs=r.affected_row_refs,
                expected_impact_amount=r.expected_impact_amount,
                injected_at=datetime.datetime.now(datetime.timezone.utc),
            )
            for r in applied_records
        ]
        db.bulk_save_objects(ledger_objects)

        AuditService.record(
            db=db,
            actor=actor,
            action="dataset.mutated",
            entity_type="dataset",
            entity_id=child_id,
            payload={
                "parent_dataset_id": parent_dataset_id,
                "mutations_applied": len(applied_records),
                "mutation_classes": list({r.class_name for r in applied_records}),
            },
        )

        db.commit()
        db.refresh(child)
        return child, applied_records
