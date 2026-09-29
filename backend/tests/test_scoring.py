"""Integration tests for Runs, Detection Matching, and Scoring Engine."""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.models.entities import Dataset, GLEntry, MutationLedger
from app.services.controls.runner import ControlRunner
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.matcher import DetectionMatcher


def test_end_to_end_run_matching_and_scoring(db_session: Session):
    # 1. Create a mutated test dataset
    ds = Dataset(
        id="ds-scoring-test",
        name="Scoring Test Dataset",
        seed=42,
        period_start="2025-01",
        period_end="2025-01",
        created_by="admin@controlchaos.local",
        is_baseline=False,
    )
    db_session.add(ds)

    # 2. Add an unbalanced journal entry batch (mutation)
    gl1 = GLEntry(
        dataset_id=ds.id,
        entry_id="GL-UNBAL-1",
        posting_date="2025-01-10",
        period="2025-01",
        entity_id="ENT-01",
        account_code="1100",
        debit=1500.0,
        credit=0.0,
        currency="USD",
        fx_rate=1.0,
        description="Unbalanced cash debit",
        source_system="ERP",
        batch_id="BATCH-ERR-1",
        created_by="maker@local",
        approved_by="checker@local",
    )
    gl2 = GLEntry(
        dataset_id=ds.id,
        entry_id="GL-UNBAL-2",
        posting_date="2025-01-10",
        period="2025-01",
        entity_id="ENT-01",
        account_code="2000",
        debit=0.0,
        credit=1000.0,  # 500 imbalance!
        currency="USD",
        fx_rate=1.0,
        description="Unbalanced AP credit",
        source_system="ERP",
        batch_id="BATCH-ERR-1",
        created_by="maker@local",
        approved_by="checker@local",
    )
    db_session.add_all([gl1, gl2])

    # 3. Add ground truth mutation record in mutation_ledger
    mut = MutationLedger(
        dataset_id=ds.id,
        mutation_id="MUT-TEST-UNBAL",
        class_name="unbalanced_batch",
        params={"severity": "critical", "magnitude": "medium", "stealth": "obvious"},
        affected_row_refs=["gl:GL-UNBAL-1", "gl:GL-UNBAL-2"],
        expected_impact_amount=500.0,
        injected_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db_session.add(mut)
    db_session.commit()

    # 4. Execute Control Suite against the dataset
    run = ControlRunner.run_suite(
        db=db_session,
        dataset_id=ds.id,
        control_keys=["tb_integrity"],
        actor="admin@controlchaos.local",
    )
    assert run.status == "completed"

    # 5. Execute Detection Matching
    detections = DetectionMatcher.match_run(
        db=db_session,
        run_id=run.id,
        dataset_id=ds.id,
        match_mode="strict_row",
    )
    assert len(detections) == 1
    assert detections[0].detected is True
    assert "tb_integrity" in detections[0].detected_by

    # 6. Execute Scoring Engine
    score = ScoringEngine.score_run(db=db_session, run_id=run.id)
    assert score.overall_detection_rate == 1.0
    assert score.cost_of_misses == 0.0
    assert "unbalanced_batch" in score.by_class
    assert score.by_class["unbalanced_batch"]["rate"] == 1.0

    # 7. Marginal values (Leave-one-out)
    marginal = ScoringEngine.compute_marginal_values(db=db_session, run_id=run.id)
    assert len(marginal) == 1
    assert marginal[0]["control_id"] == "tb_integrity"
    assert marginal[0]["marginal_value_pct"] == 100.0

    # 8. Blind-spot map
    blindspot = ScoringEngine.compute_blindspot_map(db=db_session, run_id=run.id)
    assert len(blindspot) >= 1
    assert blindspot[0]["class_name"] == "unbalanced_batch"
    assert blindspot[0]["status"] == "caught"
