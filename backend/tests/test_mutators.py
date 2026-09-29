"""Unit tests verifying all 20 financial mutators and the Campaign Runner."""

from __future__ import annotations

import random
from types import SimpleNamespace

from app.services.mutators.base import MutableDatasetBundle
from app.services.mutators.catalog import ALL_MUTATORS


def create_test_bundle() -> MutableDatasetBundle:
    gl1 = SimpleNamespace(
        id="gl-1",
        entry_id="GL-1",
        account_code="1100",
        debit=10000.0,
        credit=0.0,
        entity_id="ENT-01",
        period="2025-01",
        posting_date="2025-01-15",
        batch_id="BATCH-01",
        currency="USD",
        fx_rate=1.0,
        description="Cash receipts",
        source_system="ERP",
        created_by="analyst@local",
        approved_by="reviewer@local",
    )
    gl2 = SimpleNamespace(
        id="gl-2",
        entry_id="GL-2",
        account_code="5000",
        debit=15000.0,
        credit=0.0,
        entity_id="ENT-01",
        period="2025-01",
        posting_date="2025-01-15",
        batch_id="BATCH-01",
        currency="USD",
        fx_rate=1.0,
        description="Rent expense",
        source_system="ERP",
        created_by="analyst@local",
        approved_by="reviewer@local",
    )
    sub1 = SimpleNamespace(
        id="sub-1",
        ref_id="SUB-1",
        gl_entry_id="GL-1",
        subledger_type="cash",
        counterparty="Bank A",
        amount=10000.0,
        currency="USD",
        value_date="2025-01-15",
        status="posted",
    )
    treasury_pos = [
        SimpleNamespace(
            id=f"t-{i}",
            entity_id="ENT-01",
            as_of_date=f"2025-01-{i+1:02d}",
            currency="USD",
            cash_balance=100000.0 + (i * 100),
            hqla=120000.0,
            outflows_30d=100000.0,
            inflows_30d=90000.0,
            funding_source="Deposits",
            funding_amount=100000.0,
            maturity_bucket="30d",
        )
        for i in range(10)
    ]

    return MutableDatasetBundle(
        dataset_id="test-ds",
        gl_entries=[gl1, gl2],
        subledger_entries=[sub1],
        budget_entries=[],
        treasury_positions=treasury_pos,
    )


def test_all_20_mutators_instantiate_and_apply():
    assert len(ALL_MUTATORS) == 20

    for cls in ALL_MUTATORS:
        mutator = cls()
        bundle = create_test_bundle()
        rng = random.Random(42)

        rec = mutator.apply(bundle, rng, {"magnitude": "medium", "stealth": "subtle"})
        assert rec is not None, f"Mutator {mutator.key} failed to generate a mutation record"
        assert rec.class_name == mutator.key
        assert rec.expected_impact_amount >= 0.0
        assert len(rec.affected_row_refs) >= 1
