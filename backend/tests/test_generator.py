"""Property-based and unit tests for the Synthetic Ledger Generator."""

import hypothesis.strategies as st
from hypothesis import given, settings

from app.services.generator.benford import calculate_benford_distribution, sample_lognormal_amount
from app.services.generator.ledger_generator import SyntheticLedgerGenerator
from app.services.generator.models import GeneratorParams, TransactionVolume
from app.services.generator.subledgers import SUBLEDGER_GL_MAPPING

MOCK_ENTITIES = [
    {"id": "ent-1", "code": "LE-100", "name": "Entity 1", "currency": "USD", "region": "AMER"},
    {"id": "ent-2", "code": "LE-200", "name": "Entity 2", "currency": "EUR", "region": "EMEA"},
    {"id": "ent-3", "code": "LE-300", "name": "Entity 3", "currency": "GBP", "region": "EMEA"},
]


@given(
    seed=st.integers(min_value=1, max_value=999999),
    months=st.integers(min_value=3, max_value=6),
)
@settings(max_examples=8, deadline=15000)
def test_double_entry_balance_invariant(seed, months):
    """
    Hypothesis Property Test:
    For any valid seed and duration, the generated general ledger MUST be strictly balanced.
    Total Debits == Total Credits, and every batch must balance individually.
    """
    params = GeneratorParams(
        name=f"Property Test {seed}",
        seed=seed,
        entities_count=3,
        months=months,
        volume=TransactionVolume.LOW,
        include_decoys=True,
    )
    generator = SyntheticLedgerGenerator(params, MOCK_ENTITIES)
    generated = generator.generate_all()

    gl_rows = generated["gl_rows"]
    assert len(gl_rows) > 0

    # 1. Overall Ledger Balance
    total_debits = sum(r["debit"] for r in gl_rows)
    total_credits = sum(r["credit"] for r in gl_rows)
    assert abs(total_debits - total_credits) < 0.001

    # 2. Batch-level Invariant
    batches = {}
    for r in gl_rows:
        b_id = r["batch_id"]
        batches.setdefault(b_id, {"debit": 0.0, "credit": 0.0})
        batches[b_id]["debit"] += r["debit"]
        batches[b_id]["credit"] += r["credit"]

    for b_id, totals in batches.items():
        batch_diff = abs(totals["debit"] - totals["credit"])
        assert batch_diff < 0.001, f"Batch {b_id} is out of balance: {totals}"


def test_subledger_reconciliation_invariant():
    """
    Verifies that subledgers (AR, AP, FA, payroll, cash) tie to GL control accounts.
    """
    params = GeneratorParams(seed=101, months=3, volume=TransactionVolume.LOW)
    generator = SyntheticLedgerGenerator(params, MOCK_ENTITIES)
    generated = generator.generate_all()

    gl_entries = {r["entry_id"]: r for r in generated["gl_rows"]}
    subledger_entries = generated["subledger_rows"]

    for sl in subledger_entries:
        gl_id = sl["gl_entry_id"]
        assert gl_id in gl_entries, f"Subledger ref {sl['ref_id']} links to non-existent GL entry {gl_id}"
        gl_row = gl_entries[gl_id]

        expected_acc = SUBLEDGER_GL_MAPPING.get(sl["subledger_type"])
        assert expected_acc == gl_row["account_code"]
        assert abs(sl["amount"] - max(gl_row["debit"], gl_row["credit"])) < 0.001


def test_treasury_lcr_baseline_above_100():
    """
    Verifies that daily Liquidity Coverage Ratio (LCR) is strictly above 100% in baseline.
    """
    params = GeneratorParams(seed=202, months=3, volume=TransactionVolume.LOW)
    generator = SyntheticLedgerGenerator(params, MOCK_ENTITIES)
    generated = generator.generate_all()

    for pos in generated["treasury_rows"]:
        hqla = pos["hqla"]
        outflows = pos["outflows_30d"]
        inflows = pos["inflows_30d"]
        net_outflows = outflows - min(inflows, 0.75 * outflows)
        lcr = hqla / net_outflows
        assert lcr >= 1.0, f"Baseline LCR dropped below 100%: {lcr:.2f} on {pos['as_of_date']}"


def test_benford_distribution_conformity():
    """
    Verifies that financial amounts sampled follow a Benford distribution with low MAD.
    """
    import numpy as np
    rng = np.random.default_rng(42)
    amounts = [sample_lognormal_amount(rng) for _ in range(5000)]
    stats = calculate_benford_distribution(amounts)

    # In finance, MAD <= 0.035 indicates strong conformity to Benford's Law
    assert stats["mad"] < 0.035, f"High Benford MAD: {stats['mad']}"
    assert stats["observed"][1] > 0.25  # Digit 1 should appear ~30% of the time


def test_decoy_anomalies_present():
    """
    Verifies that legitimate decoy anomalies are embedded with documented reasons.
    """
    params = GeneratorParams(seed=303, months=6, volume=TransactionVolume.LOW, include_decoys=True)
    generator = SyntheticLedgerGenerator(params, MOCK_ENTITIES)
    generated = generator.generate_all()

    decoys = generated["decoys"]
    assert len(decoys) > 0
    for d in decoys:
        assert d["amount"] >= 400000.0
        assert "DECOY-" in d["decoy_id"]
        assert len(d["reason_valid"]) > 10
