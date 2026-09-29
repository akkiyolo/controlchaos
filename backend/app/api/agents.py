"""Multi-Agent Governance, Proposals, and Agent Console API Router."""

from __future__ import annotations

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.rbac import assert_maker_checker, get_current_user, require_roles
from app.db import get_db
from app.models.entities import Proposal, User
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentProposalDTO,
    DecideProposalRequest,
    ProposalListResponse,
)
from app.services.agent.providers import get_provider
from app.services.agent.workflow import AgentSupervisor
from app.services.audit.service import AuditService
from app.services.controls.registry import registry

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/proposals", response_model=ProposalListResponse)
def list_proposals(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposalListResponse:
    """List AI-generated control improvement proposals pending maker-checker review."""
    query = select(Proposal).order_by(desc(Proposal.id))
    if status_filter:
        query = query.where(Proposal.status == status_filter)

    items = db.execute(query).scalars().all()
    dtos = [
        AgentProposalDTO(
            id=p.id,
            run_id=p.run_id,
            gap_class=p.gap_class,
            proposed_rule=p.proposed_rule,
            rationale=p.rationale,
            backtest=p.backtest,
            status=p.status,
            maker=p.maker,
            checker=p.checker,
            decided_at=p.decided_at,
            comments=p.comments,
        )
        for p in items
    ]
    return ProposalListResponse(total=len(dtos), proposals=dtos)


@router.post("/runs/{run_id}/trigger-loop", response_model=ProposalListResponse)
def trigger_agent_loop(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "control_owner")),
) -> ProposalListResponse:
    """Triggers the autonomous multi-agent closed loop (Adversary -> Investigator -> Architect -> Skeptic)."""
    try:
        created = AgentSupervisor.execute_closed_loop(
            db=db,
            run_id=run_id,
            actor=current_user.email,
        )
        dtos = [
            AgentProposalDTO(
                id=p.id,
                run_id=p.run_id,
                gap_class=p.gap_class,
                proposed_rule=p.proposed_rule,
                rationale=p.rationale,
                backtest=p.backtest,
                status=p.status,
                maker=p.maker,
                checker=p.checker,
                decided_at=p.decided_at,
                comments=p.comments,
            )
            for p in created
        ]
        return ProposalListResponse(total=len(dtos), proposals=dtos)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/proposals/{proposal_id}/decide", response_model=AgentProposalDTO)
def decide_proposal(
    proposal_id: str,
    req: DecideProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
) -> AgentProposalDTO:
    """Checker review: approve or reject an AI-generated control enhancement proposal."""
    proposal = db.execute(select(Proposal).where(Proposal.id == proposal_id)).scalar_one_or_none()
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Proposal is already {proposal.status}")

    # Enforce maker-checker: maker cannot approve own proposal
    assert_maker_checker(proposal.maker, current_user.email)

    proposal.status = "approved" if req.action == "approve" else "rejected"
    proposal.checker = current_user.email
    proposal.decided_at = datetime.datetime.now(datetime.timezone.utc)
    proposal.comments = req.comments

    # If approved and it is a parameter tuning proposal, apply it to the control definition
    if req.action == "approve":
        rule = proposal.proposed_rule or {}
        if rule.get("rule_type") == "parameter_tune" and rule.get("target_control") and rule.get("proposed_params"):
            ctrl_key = rule["target_control"]
            ctrl = registry.get(ctrl_key)
            if ctrl:
                # Propose and immediately approve new version under checker identity
                v = registry.propose_edit(
                    db=db,
                    control_key=ctrl_key,
                    new_params=rule["proposed_params"],
                    maker=proposal.maker,
                    rationale=f"Automated AI gap closure: {proposal.rationale}",
                )
                registry.approve_edit(
                    db=db,
                    control_key=ctrl_key,
                    version_id=v.id,
                    checker=current_user.email,
                    comment="Approved AI proposal",
                )

    AuditService.record(
        db=db,
        actor=current_user.email,
        action=f"proposal.{req.action}d",
        entity_type="proposal",
        entity_id=proposal.id,
        payload={
            "action": req.action,
            "checker": current_user.email,
            "maker": proposal.maker,
            "comments": req.comments,
        },
    )

    db.commit()
    db.refresh(proposal)
    return AgentProposalDTO(
        id=proposal.id,
        run_id=proposal.run_id,
        gap_class=proposal.gap_class,
        proposed_rule=proposal.proposed_rule,
        rationale=proposal.rationale,
        backtest=proposal.backtest,
        status=proposal.status,
        maker=proposal.maker,
        checker=proposal.checker,
        decided_at=proposal.decided_at,
        comments=proposal.comments,
    )


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    req: AgentChatRequest,
    current_user: User = Depends(get_current_user),
) -> AgentChatResponse:
    """Conversational interaction with any of the 5 specialist agents."""
    provider = get_provider(req.agent_name)
    system_prompts = {
        "adversary": "You are the Adversary Agent. You specialize in red-teaming financial controls and inventing stealthy accounting evasions.",
        "investigator": "You are the Investigator Agent. You diagnose control failures, root causes, and false positives.",
        "control_architect": "You are the Control Architect Agent. You design robust internal accounting controls, parameter thresholds, and rules.",
        "skeptic": "You are the Skeptic Agent. You challenge proposals, stress-test rules, and minimize false positive operational burdens.",
        "variance_analyst": "You are the Variance Analyst Agent. You draft verified financial commentary grounded strictly in General Ledger facts.",
    }

    system_prompt = system_prompts.get(req.agent_name, "You are an expert financial controls AI assistant.")
    prompt = f"User query from {current_user.name}: {req.message}"
    if req.context_data:
        prompt += f"\nContext telemetry: {req.context_data}"

    res = provider.generate(prompt=prompt, system_prompt=system_prompt)

    return AgentChatResponse(
        agent_name=req.agent_name,
        reply=res.content,
        structured_output=res.parsed_json,
        provider_used=res.provider,
        latency_ms=res.usage.latency_ms,
    )
