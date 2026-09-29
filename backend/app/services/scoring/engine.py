"""Scoring Engine: Computes institutional scorecards, leave-one-out marginal value, and blind-spot maps."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Detection, Finding, MutationLedger, Run, Score


class ScoringEngine:
    """Calculates detection metrics, marginal values, and blind-spot heatmaps for runs."""

    SEVERITY_WEIGHTS = {
        "critical": 1.5,
        "high": 1.2,
        "medium": 1.0,
        "low": 0.5,
    }

    @classmethod
    def score_run(cls, db: Session, run_id: str) -> Score:
        """Compute full scorecard metrics for a completed run and persist to the database."""
        run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Run '{run_id}' not found")

        mutations = db.execute(
            select(MutationLedger).where(MutationLedger.dataset_id == run.dataset_id)
        ).scalars().all()

        detections = db.execute(
            select(Detection).where(Detection.run_id == run_id)
        ).scalars().all()

        findings = db.execute(
            select(Finding).where(Finding.run_id == run_id)
        ).scalars().all()

        det_by_id = {d.mutation_id: d for d in detections}

        total_mutations = len(mutations)
        if total_mutations == 0:
            # Baseline or clean dataset run
            score = Score(
                run_id=run_id,
                overall_detection_rate=1.0,
                weighted_detection_rate=1.0,
                by_class={},
                by_control={},
                false_positive_rate=0.0,
                precision=1.0 if not findings else 0.0,
                recall=1.0,
                f1=1.0,
                cost_of_misses=0.0,
            )
            db.add(score)
            db.commit()
            return score

        # 1. Overall & Weighted Detection Rates
        detected_count = sum(1 for d in detections if d.detected)
        overall_detection_rate = detected_count / total_mutations if total_mutations > 0 else 0.0

        total_weight = 0.0
        detected_weight = 0.0
        cost_of_misses = 0.0

        # Breakdown by mutation class
        by_class: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "detected": 0, "rate": 0.0})
        # Breakdown by control
        by_control: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"detections_count": 0, "unique_catches": 0})

        for mut in mutations:
            c_name = mut.class_name
            w = cls.SEVERITY_WEIGHTS.get(mut.params.get("severity", "high"), 1.0)
            total_weight += w
            by_class[c_name]["total"] += 1

            det = det_by_id.get(mut.mutation_id)
            if det and det.detected:
                detected_weight += w * (det.partial_credit or 1.0)
                by_class[c_name]["detected"] += 1

                for ctrl in det.detected_by:
                    by_control[ctrl]["detections_count"] += 1
                if len(det.detected_by) == 1:
                    by_control[det.detected_by[0]]["unique_catches"] += 1
            else:
                cost_of_misses += float(mut.expected_impact_amount)

        weighted_detection_rate = detected_weight / total_weight if total_weight > 0 else 0.0

        for c_data in by_class.values():
            if c_data["total"] > 0:
                c_data["rate"] = round(c_data["detected"] / c_data["total"], 3)

        # 2. Precision, Recall, F1
        # In financial mutation testing:
        # True Positives = detected mutations
        # False Positives = findings that did not match any mutation
        matched_finding_count = sum(len(d.detected_by) for d in detections if d.detected)
        total_findings = len(findings)
        false_positives = max(0, total_findings - matched_finding_count)

        precision = (detected_count / (detected_count + false_positives)) if (detected_count + false_positives) > 0 else 1.0
        recall = overall_detection_rate
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        false_positive_rate = false_positives / total_findings if total_findings > 0 else 0.0

        # Check if score already exists for run
        existing_score = db.execute(select(Score).where(Score.run_id == run_id)).scalar_one_or_none()
        if not existing_score:
            final_score = Score(
                run_id=run_id,
                overall_detection_rate=round(overall_detection_rate, 4),
                weighted_detection_rate=round(weighted_detection_rate, 4),
                by_class=dict(by_class),
                by_control=dict(by_control),
                false_positive_rate=round(false_positive_rate, 4),
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1=round(f1, 4),
                cost_of_misses=round(cost_of_misses, 2),
            )
            db.add(final_score)
        else:
            final_score = existing_score
            final_score.overall_detection_rate = round(overall_detection_rate, 4)
            final_score.weighted_detection_rate = round(weighted_detection_rate, 4)
            final_score.by_class = dict(by_class)
            final_score.by_control = dict(by_control)
            final_score.false_positive_rate = round(false_positive_rate, 4)
            final_score.precision = round(precision, 4)
            final_score.recall = round(recall, 4)
            final_score.f1 = round(f1, 4)
            final_score.cost_of_misses = round(cost_of_misses, 2)

        db.commit()
        db.refresh(final_score)
        return final_score

    @classmethod
    def compute_marginal_values(cls, db: Session, run_id: str) -> List[Dict[str, Any]]:
        """Leave-one-out analysis: Computes how much detection rate drops if each control is removed."""
        score = db.execute(select(Score).where(Score.run_id == run_id)).scalar_one_or_none()
        if not score:
            return []

        detections = db.execute(select(Detection).where(Detection.run_id == run_id)).scalars().all()
        if not detections:
            return []

        total_mutations = len(detections)
        all_controls = set()
        for d in detections:
            all_controls.update(d.detected_by)

        marginal_results: List[Dict[str, Any]] = []

        baseline_detected = sum(1 for d in detections if d.detected)

        for ctrl in sorted(all_controls):
            # Recalculate detection count if 'ctrl' were removed
            detected_without_ctrl = sum(
                1 for d in detections
                if any(c != ctrl for c in d.detected_by)
            )
            detection_drop = baseline_detected - detected_without_ctrl
            drop_pct = (detection_drop / total_mutations) if total_mutations > 0 else 0.0

            marginal_results.append({
                "control_id": ctrl,
                "marginal_drop_count": detection_drop,
                "marginal_value_pct": round(drop_pct * 100, 2),
                "unique_catches": detection_drop,
                "is_critical": detection_drop > 0,
            })

        # Sort descending by marginal value
        marginal_results.sort(key=lambda x: x["marginal_value_pct"], reverse=True)
        return marginal_results

    @classmethod
    def compute_blindspot_map(cls, db: Session, run_id: str) -> List[Dict[str, Any]]:
        """Generates mutation class x stealth x magnitude detection heatmap."""
        run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
        if not run:
            return []

        mutations = db.execute(
            select(MutationLedger).where(MutationLedger.dataset_id == run.dataset_id)
        ).scalars().all()

        detections = db.execute(
            select(Detection).where(Detection.run_id == run_id)
        ).scalars().all()

        det_map = {d.mutation_id: d.detected for d in detections}

        matrix: Dict[tuple, Dict[str, int]] = defaultdict(lambda: {"tested": 0, "detected": 0})

        for m in mutations:
            c_name = m.class_name
            stealth = m.params.get("stealth", "subtle")
            mag = m.params.get("magnitude", "medium")
            key = (c_name, stealth, mag)

            matrix[key]["tested"] += 1
            if det_map.get(m.mutation_id, False):
                matrix[key]["detected"] += 1

        cells: List[Dict[str, Any]] = []
        for (c_name, stealth, mag), stats in matrix.items():
            tested = stats["tested"]
            detected = stats["detected"]
            rate = round((detected / tested) * 100, 1) if tested > 0 else 0.0
            cells.append({
                "class_name": c_name,
                "stealth": stealth,
                "magnitude": mag,
                "tested": tested,
                "detected": detected,
                "detection_rate_pct": rate,
                "status": "caught" if rate >= 90 else ("partial" if rate >= 50 else "blind_spot"),
            })

        cells.sort(key=lambda x: (x["class_name"], x["stealth"], x["magnitude"]))
        return cells
