"""Autonomous Multi-Agent Orchestrator and Workflow Loop."""

from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Detection, MutationLedger, Proposal, Run
from app.services.agent.specialists import (
    ControlArchitectAgent,
    InvestigatorAgent,
    SkepticAgent,
)
from app.services.audit.service import AuditService
from app.services.controls.runner import ControlRunner


class AgentSupervisor:
    """Coordinates specialist agents in an autonomous gap-closing cycle."""

    @classmethod
    def execute_closed_loop(
        cls,
        db: Session,
        run_id: str,
        actor: str = "agent_supervisor@controlchaos.local",
    ) -> List[Proposal]:
        """Runs the autonomous gap closure workflow for any undetected mutations in a run."""
        run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Run '{run_id}' not found")

        # Find undetected mutations
        missed_detections = db.execute(
            select(Detection).where(Detection.run_id == run_id, Detection.detected.is_(False))
        ).scalars().all()

        if not missed_detections:
            return []

        # Load context
        context = ControlRunner.load_dataset_context(db, run.dataset_id)
        created_proposals: List[Proposal] = []

        for det in missed_detections[:3]:  # Top 3 gaps per run
            mut = db.execute(
                select(MutationLedger).where(
                    MutationLedger.dataset_id == run.dataset_id,
                    MutationLedger.mutation_id == det.mutation_id,
                )
            ).scalar_one_or_none()

            if not mut:
                continue

            mut_dict = {
                "class_name": mut.class_name,
                "expected_impact": float(mut.expected_impact_amount),
                "affected_row_refs": mut.affected_row_refs,
                "params": mut.params,
            }

            # Step 1: Investigator Agent
            investigation = InvestigatorAgent.diagnose_miss(
                mutation_details=mut_dict,
                finding_summary={"run_id": run_id, "findings_count": 0},
            )

            # Step 2: Control Architect Agent
            proposal_plan = ControlArchitectAgent.design_fix(investigation)

            # Step 3: Skeptic Agent
            critique = SkepticAgent.evaluate_proposal(
                proposal=proposal_plan,
                context=context,
                target_mutation_refs=mut.affected_row_refs,
            )

            # Step 4: Persist proposal with maker-checker pending status
            proposal_entity = Proposal(
                run_id=run.id,
                gap_class=mut.class_name,
                proposed_rule=proposal_plan.model_dump(),
                rationale=(
                    f"Root Cause: {investigation.root_cause}. "
                    f"Architect Remedy: {proposal_plan.rationale}. "
                    f"Skeptic Critique ({critique.verdict.upper()}): {critique.critique} "
                    f"[False Positive Risk: {critique.false_positive_risk}]."
                ),
                backtest={
                    "backtest_score": critique.backtest_score,
                    "verdict": critique.verdict,
                    "conditions": critique.conditions_for_approval,
                },
                status="pending",
                maker=actor,
            )
            db.add(proposal_entity)
            db.flush()

            AuditService.record(
                db=db,
                actor=actor,
                action="proposal.created",
                entity_type="proposal",
                entity_id=proposal_entity.id,
                payload={
                    "gap_class": mut.class_name,
                    "proposed_title": proposal_plan.title,
                    "rule_type": proposal_plan.rule_type,
                    "skeptic_verdict": critique.verdict,
                },
            )
            created_proposals.append(proposal_entity)

        db.commit()
        return created_proposals
