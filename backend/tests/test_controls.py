"""Unit and integration tests for the 15 Financial Controls, Versioning, Maker-Checker, and Runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.services.audit.service import AuditService
from app.services.controls.base import DatasetContext
from app.services.controls.registry import registry
from app.services.controls.suite import (
    AccountClassificationControl,
    AccrualCompletenessControl,
    BenfordAnalysisControl,
    CutoffCheckControl,
    DuplicateDetectionControl,
    FXValidationControl,
    GLSubledgerReconControl,
    IntercompanyEliminationControl,
    JournalRiskScoreControl,
    SegregationOfDutiesControl,
    StatisticalOutliersControl,
    ThresholdSplittingControl,
    TreasuryControls,
    TrialBalanceIntegrityControl,
    VarianceThresholdControl,
)


def make_gl(
    entry_id: str,
    account_code: str,
    debit: float = 0.0,
    credit: float = 0.0,
    entity_id: str = "ENT-01",
    period: str = "2025-01",
    posting_date: str = "2025-01-15",
    batch_id: str = "BATCH-01",
    currency: str = "USD",
    fx_rate: float = 1.0,
    description: str = "Standard operating entry",
    source_system: str = "SAP_ERP",
    created_by: str = "analyst@controlchaos.local",
    approved_by: str = "reviewer@controlchaos.local",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"uuid-{entry_id}",
        entry_id=entry_id,
        account_code=account_code,
        debit=debit,
        credit=credit,
        entity_id=entity_id,
        period=period,
        posting_date=posting_date,
        batch_id=batch_id,
        currency=currency,
        fx_rate=fx_rate,
        description=description,
        source_system=source_system,
        created_by=created_by,
        approved_by=approved_by,
    )


def make_sub(
    ref_id: str,
    subledger_type: str,
    amount: float,
    gl_entry_id: str = "",
    counterparty: str = "Vendor ABC",
    value_date: str = "2025-01-15",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"uuid-{ref_id}",
        ref_id=ref_id,
        subledger_type=subledger_type,
        amount=amount,
        gl_entry_id=gl_entry_id,
        counterparty=counterparty,
        value_date=value_date,
    )


# ---------------------------------------------------------
# 1. GL-to-Subledger Reconciliation
# ---------------------------------------------------------
def test_gl_subledger_recon():
    ctrl = GLSubledgerReconControl()

    # GL has 1200 (AR) of 1,000; Subledger has 1,000 -> Balanced
    gl1 = make_gl("GL-1", "1200", debit=1000.0)
    sub1 = make_sub("SUB-1", "AR", 1000.0, gl_entry_id="GL-1")

    # GL has 2000 (AP) of 5,000; Subledger missing -> Orphan GL
    gl2 = make_gl("GL-2", "2000", credit=5000.0)

    # Subledger has AP 2,500; GL missing -> Orphan Subledger
    sub2 = make_sub("SUB-2", "AP", 2500.0, gl_entry_id="GL-MISSING")

    # GL has 1100 (Cash) of 3,000; Subledger has 3,050 -> Mismatch
    gl3 = make_gl("GL-3", "1100", debit=3000.0)
    sub3 = make_sub("SUB-3", "cash", 3050.0, gl_entry_id="GL-3")

    ctx = DatasetContext(
        dataset_id="test-ds",
        gl_entries=[gl1, gl2, gl3],
        subledger_entries=[sub1, sub2, sub3],
    )

    findings = ctrl.run(ctx)
    finding_types = [f.metadata.get("type") or "mismatch" for f in findings]

    assert "gl_orphan" in finding_types
    assert "subledger_orphan" in finding_types
    assert any("mismatch" in f.finding_id.lower() for f in findings)


# ---------------------------------------------------------
# 2. Trial Balance Integrity
# ---------------------------------------------------------
def test_tb_integrity():
    ctrl = TrialBalanceIntegrityControl()

    # Balanced batch
    gl1 = make_gl("GL-1", "1100", debit=100.0, batch_id="B-1")
    gl2 = make_gl("GL-2", "2000", credit=100.0, batch_id="B-1")

    # Unbalanced batch
    gl3 = make_gl("GL-3", "5000", debit=500.0, batch_id="B-2")
    gl4 = make_gl("GL-4", "1100", credit=450.0, batch_id="B-2")  # 50 difference

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2, gl3, gl4])
    findings = ctrl.run(ctx)

    unbalanced = [f for f in findings if "B-2" in f.finding_id]
    assert len(unbalanced) == 1
    assert unbalanced[0].amount == pytest.approx(50.0)


# ---------------------------------------------------------
# 3. Duplicate Detection
# ---------------------------------------------------------
def test_duplicate_detection():
    ctrl = DuplicateDetectionControl()

    # Two identical postings 1 day apart
    gl1 = make_gl("GL-1", "5000", debit=1234.56, posting_date="2025-01-10", description="Invoice 999")
    gl2 = make_gl("GL-2", "5000", debit=1234.56, posting_date="2025-01-11", description="Invoice 999")

    # Legitimate non-duplicate
    gl3 = make_gl("GL-3", "5000", debit=999.00, posting_date="2025-01-10")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2, gl3])
    findings = ctrl.run(ctx, {"window_days": 2, "amount_tolerance": 0.0})

    assert len(findings) == 1
    assert "GL-1" in findings[0].affected_row_refs[0]
    assert "GL-2" in findings[0].affected_row_refs[1]


# ---------------------------------------------------------
# 4. Period Cutoff Check
# ---------------------------------------------------------
def test_cutoff_check():
    ctrl = CutoffCheckControl()

    # GL posted on 2025-02-02, but period was tagged as 2025-01
    gl1 = make_gl("GL-1", "5000", debit=5000.0, period="2025-01", posting_date="2025-02-02")

    # GL posted in 2025-01, but subledger value_date was 2024-12-31
    gl2 = make_gl("GL-2", "2000", credit=3000.0, period="2025-01", posting_date="2025-01-02")
    sub2 = make_sub("SUB-2", "AP", 3000.0, gl_entry_id="GL-2", value_date="2024-12-31")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2], subledger_entries=[sub2])
    findings = ctrl.run(ctx)

    assert len(findings) >= 2
    assert any("GL-1" in f.finding_id for f in findings)
    assert any("GL-2" in f.finding_id for f in findings)


# ---------------------------------------------------------
# 5. Variance Threshold Control
# ---------------------------------------------------------
def test_variance_threshold():
    ctrl = VarianceThresholdControl()

    # Actual expense: $100,000 on account 5000 in 2025-01
    gl1 = make_gl("GL-1", "5000", debit=100000.0, period="2025-01", entity_id="ENT-01")

    # Approved Budget: $50,000 -> Variance is +$50,000 (+100%)
    budget_entry = SimpleNamespace(
        period="2025-01",
        entity_id="ENT-01",
        account_code="5000",
        amount=50000.0,
    )

    ctx = DatasetContext(
        dataset_id="test-ds",
        gl_entries=[gl1],
        budget_entries=[budget_entry],
    )

    findings = ctrl.run(ctx, {"abs_threshold": 25000.0, "pct_threshold": 0.20})
    assert len(findings) >= 1
    assert findings[0].amount == pytest.approx(50000.0)


# ---------------------------------------------------------
# 6. Accrual Completeness Control
# ---------------------------------------------------------
def test_accrual_completeness():
    ctrl = AccrualCompletenessControl()

    # Period 2025-01 has 5000 (Rent), but missing mandatory 5100 (Payroll)
    gl1 = make_gl("GL-1", "5000", debit=10000.0, period="2025-01", entity_id="ENT-01")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1])
    findings = ctrl.run(ctx, {"required_accounts": ["5000", "5100"]})

    assert len(findings) == 1
    assert findings[0].account_code == "5100"
    assert "Missing" in findings[0].description


# ---------------------------------------------------------
# 7. FX Validation Control
# ---------------------------------------------------------
def test_fx_validation():
    ctrl = FXValidationControl()

    # EUR/USD reference rate is 1.08
    # GL-1 applies 1.25 (+15.7% drift)
    gl1 = make_gl("GL-1", "1200", debit=1000.0, currency="EUR", fx_rate=1.25, posting_date="2025-01-10")

    # GL-2 applies inverted quote: 0.9259 (1 / 1.08)
    gl2 = make_gl("GL-2", "1200", debit=1000.0, currency="EUR", fx_rate=0.9259, posting_date="2025-01-10")

    ctx = DatasetContext(
        dataset_id="test-ds",
        gl_entries=[gl1, gl2],
        fx_rates={"2025-01-10": {"EUR/USD": 1.08}},
    )

    findings = ctrl.run(ctx)
    assert len(findings) == 2
    assert any("inverted" in f.description.lower() for f in findings)
    assert any("drift" in f.description.lower() for f in findings)


# ---------------------------------------------------------
# 8. Threshold Splitting Control
# ---------------------------------------------------------
def test_threshold_splitting():
    ctrl = ThresholdSplittingControl()

    # Single-item limit is 50,000.
    # User posts 3 items of 48,000 on consecutive days -> Structuring!
    gl1 = make_gl("GL-1", "5000", debit=48000.0, posting_date="2025-01-10", created_by="maker@local")
    gl2 = make_gl("GL-2", "5000", debit=49000.0, posting_date="2025-01-11", created_by="maker@local")
    gl3 = make_gl("GL-3", "5000", debit=48500.0, posting_date="2025-01-12", created_by="maker@local")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2, gl3])
    findings = ctrl.run(ctx, {"approval_limit": 50000.0, "window_days": 3, "min_cluster_count": 2})

    assert len(findings) == 1
    assert "structuring" in findings[0].description.lower()
    assert findings[0].amount == pytest.approx(48000.0 + 49000.0 + 48500.0)


# ---------------------------------------------------------
# 9. Segregation of Duties Control
# ---------------------------------------------------------
def test_segregation_of_duties():
    ctrl = SegregationOfDutiesControl()

    # Maker approved own entry
    gl1 = make_gl("GL-1", "1100", debit=25000.0, created_by="analyst@local", approved_by="analyst@local")

    # Segregated entry (different users)
    gl2 = make_gl("GL-2", "1100", debit=25000.0, created_by="maker@local", approved_by="checker@local")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2])
    findings = ctrl.run(ctx)

    assert len(findings) == 1
    assert "analyst@local" in findings[0].description


# ---------------------------------------------------------
# 10. Journal Entry Risk Scoring Control
# ---------------------------------------------------------
def test_journal_risk_score():
    ctrl = JournalRiskScoreControl()

    # Saturday 2025-01-11 + Round 50,000 + Manual source
    gl1 = make_gl(
        "GL-1",
        "5000",
        debit=50000.0,
        posting_date="2025-01-11",
        source_system="manual_excel_upload",
    )

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1])
    findings = ctrl.run(ctx, {"risk_threshold": 0.60})

    assert len(findings) == 1
    assert "risk score" in findings[0].description.lower()


# ---------------------------------------------------------
# 11. Benford's Law Analysis Control
# ---------------------------------------------------------
def test_benford_analysis():
    ctrl = BenfordAnalysisControl()

    # Generate 100 entries all artificially starting with digit 9
    fabricated_entries = [
        make_gl(f"GL-{i}", "5000", debit=float(f"9{i:03d}.50"))
        for i in range(100)
    ]

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=fabricated_entries)
    findings = ctrl.run(ctx, {"min_sample_size": 50, "critical_chi2": 15.51})

    assert len(findings) >= 1
    assert "benford" in findings[0].description.lower()


# ---------------------------------------------------------
# 12. Intercompany Elimination Control
# ---------------------------------------------------------
def test_intercompany_elimination():
    ctrl = IntercompanyEliminationControl()

    # Group IC Receivable (1300): 100,000
    # Group IC Payable (2300): 80,000 -> 20,000 break!
    gl1 = make_gl("GL-1", "1300", debit=100000.0, period="2025-01")
    gl2 = make_gl("GL-2", "2300", credit=80000.0, period="2025-01")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2])
    findings = ctrl.run(ctx, {"tolerance": 1.0})

    assert len(findings) == 1
    assert findings[0].amount == pytest.approx(20000.0)


# ---------------------------------------------------------
# 13. Account Classification Control
# ---------------------------------------------------------
def test_account_classification():
    ctrl = AccountClassificationControl()

    # OPEX narrative ("consulting fee") booked into Fixed Assets (1500)
    gl1 = make_gl("GL-1", "1500", debit=15000.0, description="Monthly management consulting advisory fee")

    # Normal asset entry
    gl2 = make_gl("GL-2", "1500", debit=50000.0, description="Office building purchase")

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=[gl1, gl2])
    findings = ctrl.run(ctx)

    assert len(findings) == 1
    assert "consulting" in findings[0].description


# ---------------------------------------------------------
# 14. Treasury Controls (LCR and Staleness)
# ---------------------------------------------------------
def test_treasury_controls():
    ctrl = TreasuryControls()

    # Day 1: LCR = 80% (Breach < 100%)
    pos1 = SimpleNamespace(
        id="T-1",
        entity_id="ENT-01",
        as_of_date="2025-01-01",
        cash_balance=100000.0,
        hqla=80000.0,
        net_outflow_30d=100000.0,
        lcr_ratio=80.0,
    )

    # Days 2-7: Static cash balance of 100,000 for 6 days -> Stale balance!
    stale_positions = [
        SimpleNamespace(
            id=f"T-{i}",
            entity_id="ENT-01",
            as_of_date=f"2025-01-{i:02d}",
            cash_balance=100000.0,
            hqla=120000.0,
            net_outflow_30d=100000.0,
            lcr_ratio=120.0,
        )
        for i in range(2, 8)
    ]

    ctx = DatasetContext(dataset_id="test-ds", treasury_positions=[pos1] + stale_positions)
    findings = ctrl.run(ctx, {"lcr_floor_pct": 100.0, "staleness_max_days": 5})

    assert any("LCR" in f.finding_id for f in findings)
    assert any("STALE" in f.finding_id for f in findings)


# ---------------------------------------------------------
# 15. Statistical Outliers Control
# ---------------------------------------------------------
def test_statistical_outliers():
    ctrl = StatisticalOutliersControl()

    # 30 entries of typical expenses around ~1,000
    normal_entries = [make_gl(f"GL-{i}", "5000", debit=1000.0 + (i * 10)) for i in range(30)]

    # 1 massive outlier: 150,000
    outlier = make_gl("GL-999", "5000", debit=150000.0)

    ctx = DatasetContext(dataset_id="test-ds", gl_entries=normal_entries + [outlier])
    findings = ctrl.run(ctx, {"multiplier": 3.0, "min_sample_size": 20})

    assert len(findings) == 1
    assert "GL-999" in findings[0].affected_row_refs[0]


# ---------------------------------------------------------
# Maker-Checker Workflow and Control Versioning
# ---------------------------------------------------------
def test_maker_checker_control_versioning(db_session: Session):
    registry.seed_defaults(db_session, audit_actor="system@local")

    maker = "owner@controlchaos.local"
    checker = "reviewer@controlchaos.local"

    # Step 1: Maker proposes edit
    draft = registry.propose_edit(
        db=db_session,
        control_key="duplicate_detection",
        new_params={"window_days": 7, "amount_tolerance": 5.0, "enabled": True},
        maker=maker,
        rationale="Widen duplicate search window from 3 to 7 days for month-end close",
    )
    assert draft.version == 2
    assert draft.approved_by is None
    assert draft.diff["window_days"]["new"] == 7

    # Step 2: Maker tries to approve own edit -> Must fail!
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        registry.approve_edit(
            db=db_session,
            control_key="duplicate_detection",
            version_id=draft.id,
            checker=maker,  # Same user!
        )
    assert "Maker-checker violation" in str(exc_info.value.detail)

    # Step 3: Checker approves edit -> Version 2 activated
    c_def = registry.approve_edit(
        db=db_session,
        control_key="duplicate_detection",
        version_id=draft.id,
        checker=checker,
        comment="Approved as per quarterly control review",
    )
    assert c_def.version == 2
    assert c_def.params["window_days"] == 7

    # Step 4: Verify audit log entries
    audit_chain, _ = AuditService.list_entries(db_session, limit=10)
    actions = [r.action for r in audit_chain]
    assert "control.edit_proposed" in actions
    assert "control.edit_approved" in actions
