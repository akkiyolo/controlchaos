"""Runs, Detection Matching, and Scorecards API Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db import get_db
from app.models.entities import Detection, Finding, Run, Score, User
from app.schemas.runs import (
    BlindSpotCellDTO,
    DetectionDTO,
    ExecuteRunRequest,
    MarginalValueDTO,
    RunListItemDTO,
    RunListResponse,
    ScorecardResponse,
)
from app.services.controls.runner import ControlRunner
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.matcher import DetectionMatcher

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunListResponse)
def list_runs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunListResponse:
    """List executed control runs with high-level score summaries."""
    query = select(Run).order_by(desc(Run.started_at)).limit(limit).offset(offset)
    runs = db.execute(query).scalars().all()

    # Pre-fetch scores and findings count
    run_ids = [r.id for r in runs]
    scores_by_run = {
        s.run_id: s
        for s in db.execute(select(Score).where(Score.run_id.in_(run_ids))).scalars().all()
    } if run_ids else {}

    items = []
    for r in runs:
        s = scores_by_run.get(r.id)
        findings_count = db.execute(
            select(Finding).where(Finding.run_id == r.id)
        ).scalars().all()

        items.append(
            RunListItemDTO(
                id=r.id,
                dataset_id=r.dataset_id,
                status=r.status,
                started_at=r.started_at,
                finished_at=r.finished_at,
                overall_detection_rate=s.overall_detection_rate if s else None,
                precision=s.precision if s else None,
                cost_of_misses=float(s.cost_of_misses) if s else None,
                total_findings=len(findings_count),
            )
        )

    return RunListResponse(total=len(items), runs=items)


@router.post("", response_model=ScorecardResponse)
def execute_run(
    req: ExecuteRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "control_owner", "analyst")),
) -> ScorecardResponse:
    """Execute controls suite, perform detection matching, score findings, and return full Scorecard."""
    try:
        # 1. Run control suite against dataset
        run = ControlRunner.run_suite(
            db=db,
            dataset_id=req.dataset_id,
            control_keys=req.control_keys,
            actor=current_user.email,
        )

        # 2. Match findings against ground truth mutations
        DetectionMatcher.match_run(
            db=db,
            run_id=run.id,
            dataset_id=req.dataset_id,
            match_mode=req.match_mode,
        )

        # 3. Score the run
        ScoringEngine.score_run(db=db, run_id=run.id)

        # 4. Return complete scorecard
        return get_run_scorecard(run.id, db=db, current_user=current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{run_id}/scorecard", response_model=ScorecardResponse)
def get_run_scorecard(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScorecardResponse:
    """Retrieve complete institutional Scorecard with marginal value and blind-spot heatmap."""
    run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found")

    score = db.execute(select(Score).where(Score.run_id == run_id)).scalar_one_or_none()
    if not score:
        # Re-score on the fly if missing
        score = ScoringEngine.score_run(db=db, run_id=run_id)

    detections = db.execute(select(Detection).where(Detection.run_id == run_id)).scalars().all()
    marginal_values = ScoringEngine.compute_marginal_values(db=db, run_id=run_id)
    blindspot_map = ScoringEngine.compute_blindspot_map(db=db, run_id=run_id)

    return ScorecardResponse(
        run_id=run.id,
        dataset_id=run.dataset_id,
        overall_detection_rate=score.overall_detection_rate,
        weighted_detection_rate=score.weighted_detection_rate,
        precision=score.precision,
        recall=score.recall,
        f1=score.f1,
        false_positive_rate=score.false_positive_rate,
        cost_of_misses=float(score.cost_of_misses),
        by_class=score.by_class,
        by_control=score.by_control,
        detections=[
            DetectionDTO(
                mutation_id=d.mutation_id,
                detected=d.detected,
                detected_by=d.detected_by,
                partial_credit=d.partial_credit,
                time_to_detect_ms=d.time_to_detect_ms,
            )
            for d in detections
        ],
        marginal_values=[
            MarginalValueDTO(
                control_id=m["control_id"],
                marginal_drop_count=m["marginal_drop_count"],
                marginal_value_pct=m["marginal_value_pct"],
                unique_catches=m["unique_catches"],
                is_critical=m["is_critical"],
            )
            for m in marginal_values
        ],
        blindspot_map=[
            BlindSpotCellDTO(
                class_name=b["class_name"],
                stealth=b["stealth"],
                magnitude=b["magnitude"],
                tested=b["tested"],
                detected=b["detected"],
                detection_rate_pct=b["detection_rate_pct"],
                status=b["status"],
            )
            for b in blindspot_map
        ],
    )
