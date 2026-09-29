"""Unit and integration tests for Safe DSL and Multi-Agent system."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Proposal, Run
from app.services.agent.dsl import SafeDSLEvaluator
from app.services.agent.specialists import (
    AdversaryAgent,
    ControlArchitectAgent,
    InvestigatorAgent,
    SkepticAgent,
    VarianceAnalystAgent,
)


def test_safe_dsl_evaluator():
    # 1. Valid expressions
    assert SafeDSLEvaluator.evaluate("amount > 1000 and account_code == '1500'", {"amount": 2500, "account_code": "1500"}) is True
    assert SafeDSLEvaluator.evaluate("currency in ['USD', 'EUR']", {"currency": "USD"}) is True
    assert SafeDSLEvaluator.evaluate("debit == 0.0 or credit > 5000", {"debit": 100.0, "credit": 200.0}) is False

    # 2. Blocked unsafe expressions
    import pytest
    with pytest.raises(ValueError):
        SafeDSLEvaluator.evaluate("__import__('os').system('echo pwned')", {})


def test_specialist_agents_generate():
    # 1. Adversary Agent
    adv = AdversaryAgent.analyze_blindspots({"amount_mismatch": 0.4})
    assert adv.target_mutation_class is not None
    assert adv.attack_strategy is not None

    # 2. Investigator Agent
    inv = InvestigatorAgent.diagnose_miss(
        {"class_name": "subledger_orphan", "expected_impact": 5000.0, "affected_row_refs": ["gl:1"]},
        {"run_id": "r-1", "findings_count": 0},
    )
    assert inv.root_cause is not None

    # 3. Control Architect Agent
    arch = ControlArchitectAgent.design_fix(inv)
    assert arch.title is not None
    assert arch.rule_type in ("parameter_tune", "dsl_rule")

    # 4. Skeptic Agent
    skep = SkepticAgent.evaluate_proposal(arch)
    assert skep.verdict in ("endorse", "reject")

    # 5. Variance Analyst Agent
    var = VarianceAnalystAgent.generate_commentary(
        actual=120000.0,
        budget=100000.0,
        account_code="5000",
        entity="ENT-01",
        period="2025-01",
        related_gl_entries=[],
    )
    assert var.variance_amount == 20000.0
    assert len(var.management_commentary) > 10


def test_agent_supervisor_and_proposals(db_session: Session):
    # Create test run
    run = Run(
        dataset_id="test-agent-ds",
        control_set_snapshot={},
        status="completed",
        config={},
    )
    db_session.add(run)
    db_session.commit()

    # Create dummy proposal
    prop = Proposal(
        run_id=run.id,
        gap_class="amount_mismatch",
        proposed_rule={"rule_type": "parameter_tune", "target_control": "gl_subledger_recon", "proposed_params": {"tolerance": 5.0}},
        rationale="Automated gap closing",
        backtest={"backtest_score": 0.9},
        status="pending",
        maker="agent_supervisor@local",
    )
    db_session.add(prop)
    db_session.commit()

    assert prop.id is not None
    assert prop.status == "pending"
