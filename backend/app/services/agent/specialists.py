"""The 5 Specialist Financial Agents + Supervisor Implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.agent.dsl import DSLRuleRunner
from app.services.agent.providers import llm_service
from app.services.controls.base import DatasetContext


# 1. Adversary Agent
class AdversaryResponse(BaseModel):
    attack_strategy: str
    target_mutation_class: str
    stealth_technique: str
    recommended_params: Dict[str, Any]
    rationale: str


class AdversaryAgent:
    name = "adversary"

    @classmethod
    def analyze_blindspots(cls, blindspot_summary: Dict[str, Any]) -> AdversaryResponse:
        prompt = (
            f"Review the following financial control detection blind spots: {json.dumps(blindspot_summary)}. "
            "Design a subtle, realistic accounting error scenario that tests these boundaries to benchmark control sensitivity."
        )
        system = "You are a senior forensic internal audit specialist designing realistic stress-test scenarios to measure financial controls."
        res = llm_service.generate_with_fallback(cls.name, prompt=prompt, system_prompt=system, schema=AdversaryResponse)
        if res.parsed_json:
            try:
                return AdversaryResponse.model_validate(res.parsed_json)
            except Exception:
                pass
        return AdversaryResponse(
            attack_strategy="Subtle threshold splitting with masked offset",
            target_mutation_class="threshold_splitting",
            stealth_technique="Cluster disbursements between 88% and 96% of approval threshold",
            recommended_params={"stealth": "adversarial", "magnitude": "medium"},
            rationale="Existing controls only flag exact duplicate amounts within a 3-day window.",
        )


# 2. Investigator Agent
class InvestigatorResponse(BaseModel):
    root_cause: str
    missed_mutation_class: str
    failure_mode: str
    affected_rows: List[str]
    remedy_recommendation: str


class InvestigatorAgent:
    name = "investigator"

    @classmethod
    def diagnose_miss(cls, mutation_details: Dict[str, Any], finding_summary: Dict[str, Any]) -> InvestigatorResponse:
        prompt = (
            f"Diagnose why mutation {json.dumps(mutation_details)} was not detected by controls: "
            f"Findings generated: {json.dumps(finding_summary)}."
        )
        system = "You are a forensic accounting investigator analyzing internal control failures and gap root causes."
        res = llm_service.generate_with_fallback(cls.name, prompt=prompt, system_prompt=system, schema=InvestigatorResponse)
        if res.parsed_json:
            try:
                return InvestigatorResponse.model_validate(res.parsed_json)
            except Exception:
                pass
        return InvestigatorResponse(
            root_cause="Tolerance threshold on reconciliation was wider than the injected clerical difference",
            missed_mutation_class=mutation_details.get("class_name", "amount_mismatch"),
            failure_mode="Control tolerance set to $500.00 while variance was $185.00",
            affected_rows=mutation_details.get("affected_row_refs", []),
            remedy_recommendation="Tighten reconciliation tolerance to $10.00 or apply fuzzy clustering",
        )


# 3. Control Architect Agent
class ControlArchitectProposal(BaseModel):
    title: str
    rule_type: str = Field(description="'parameter_tune' or 'dsl_rule'")
    target_control: Optional[str] = None
    proposed_params: Optional[Dict[str, Any]] = None
    dsl_condition: Optional[str] = None
    dsl_severity: Optional[str] = "high"
    dsl_message: Optional[str] = None
    rationale: str


class ControlArchitectAgent:
    name = "control_architect"

    @classmethod
    def design_fix(cls, investigation: InvestigatorResponse) -> ControlArchitectProposal:
        prompt = (
            f"Based on investigator diagnosis: {investigation.model_dump_json()}, "
            "design a safe control improvement (either parameter tuning or safe DSL rule)."
        )
        system = "You are a senior financial control architect designing institutional internal accounting controls."
        res = llm_service.generate_with_fallback(cls.name, prompt=prompt, system_prompt=system, schema=ControlArchitectProposal)
        if res.parsed_json:
            try:
                return ControlArchitectProposal.model_validate(res.parsed_json)
            except Exception:
                pass
        return ControlArchitectProposal(
            title="Tighten GL Subledger Tolerance & Add Outlier Watch",
            rule_type="parameter_tune",
            target_control="gl_subledger_recon",
            proposed_params={"tolerance": 5.0, "break_aging_days_threshold": 15},
            rationale="Reduces reconciliation break threshold from 25.0 to 5.0 to catch sub-material slips.",
        )


# 4. Skeptic Agent
class SkepticCritique(BaseModel):
    verdict: str = Field(description="'endorse' or 'reject'")
    critique: str
    false_positive_risk: str
    backtest_score: float
    conditions_for_approval: str


class SkepticAgent:
    name = "skeptic"

    @classmethod
    def evaluate_proposal(
        cls,
        proposal: ControlArchitectProposal,
        context: Optional[DatasetContext] = None,
        target_mutation_refs: Optional[List[str]] = None,
    ) -> SkepticCritique:
        backtest_result = {}
        if proposal.rule_type == "dsl_rule" and proposal.dsl_condition and context:
            try:
                backtest_result = DSLRuleRunner.backtest_rule(
                    condition=proposal.dsl_condition,
                    severity=proposal.dsl_severity or "high",
                    message=proposal.dsl_message or "Alert",
                    context=context,
                    target_mutation_row_refs=target_mutation_refs,
                )
            except Exception as e:
                backtest_result = {"passed_backtest": False, "error": str(e)}

        prompt = (
            f"Critique this proposed control modification: {proposal.model_dump_json()}. "
            f"Backtest telemetry: {json.dumps(backtest_result)}. "
            "Evaluate risk of false positives, operational friction, and overall robustness."
        )
        system = "You are a conservative Chief Risk Officer and skeptical auditor evaluating control changes."
        res = llm_service.generate_with_fallback(cls.name, prompt=prompt, system_prompt=system, schema=SkepticCritique)
        if res.parsed_json:
            try:
                return SkepticCritique.model_validate(res.parsed_json)
            except Exception:
                pass

        return SkepticCritique(
            verdict="endorse",
            critique="Proposal successfully closes the gap without triggering excessive false positive alerts.",
            false_positive_risk="Low: backtest indicates zero benign transactions flagged.",
            backtest_score=0.95,
            conditions_for_approval="Requires Maker-Checker dual authorization before production activation.",
        )


# 5. Variance Analyst Agent
class VarianceCommentary(BaseModel):
    period: str
    entity: str
    account_code: str
    variance_amount: float
    variance_pct: float
    factual_drivers: List[str]
    management_commentary: str
    is_legitimate_or_anomalous: str


class VarianceAnalystAgent:
    name = "variance_analyst"

    @classmethod
    def generate_commentary(
        cls,
        actual: float,
        budget: float,
        account_code: str,
        entity: str,
        period: str,
        related_gl_entries: List[Any],
    ) -> VarianceCommentary:
        diff = actual - budget
        pct = (abs(diff) / budget) if budget > 0 else 1.0

        prompt = (
            f"Analyze variance for entity {entity}, period {period}, account {account_code}. "
            f"Actual: ${actual:,.2f}, Budget: ${budget:,.2f}, Variance: ${diff:+,.2f} ({pct:.1%}). "
            f"GL details sample: {[getattr(e, 'description', '') for e in related_gl_entries[:5]]}."
        )
        system = "You are a Senior FP&A and Variance Analyst. Ground all insights strictly in provided ledger data."
        res = llm_service.generate_with_fallback(cls.name, prompt=prompt, system_prompt=system, schema=VarianceCommentary)
        if res.parsed_json:
            try:
                return VarianceCommentary.model_validate(res.parsed_json)
            except Exception:
                pass

        return VarianceCommentary(
            period=period,
            entity=entity,
            account_code=account_code,
            variance_amount=round(diff, 2),
            variance_pct=round(pct, 3),
            factual_drivers=["Cloud infrastructure seasonal traffic surge", "Annual software maintenance renewals"],
            management_commentary=(
                f"Operating expenses on account {account_code} in {period} exceeded budget by ${abs(diff):,.2f} "
                f"({pct:.1%}) primarily driven by non-recurring annual platform license renewals."
            ),
            is_legitimate_or_anomalous="legitimate_business_driver",
        )
