"""Variance Threshold Control (Actual vs Budget and Prior Period)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class VarianceThresholdParams(BaseModel):
    enabled: bool = True
    abs_threshold: float = Field(25000.0, description="Absolute variance threshold in baseline currency")
    pct_threshold: float = Field(0.25, description="Percentage variance threshold (e.g. 0.25 = 25%)")
    check_ytd: bool = Field(True, description="Evaluate cumulative Year-To-Date drift")


class VarianceThresholdControl(BaseControl[VarianceThresholdParams]):
    key = "variance_threshold"
    name = "Budget & Prior Period Variance Threshold"
    category = "variance"
    description = (
        "Compares actual general ledger revenues and expenses against approved budgets and prior periods, "
        "flagging breaches exceeding absolute currency and percentage materiality thresholds, including subtle YTD drift."
    )
    intended_error_classes = ["budget_drift"]
    params_model = VarianceThresholdParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries
        budget_entries = context.budget_entries

        # Aggregate Actuals by (period, entity_id, account_code)
        # Revenue (4xxx): net credit (credit - debit)
        # Expense (5xxx): net debit (debit - credit)
        actuals: Dict[tuple, float] = defaultdict(float)
        gl_refs_by_bucket: Dict[tuple, List[str]] = defaultdict(list)

        for gl in gl_entries:
            acc = getattr(gl, "account_code", "")
            if not acc.startswith(("4", "5")):
                continue
            period = getattr(gl, "period", "")
            ent = getattr(gl, "entity_id", "")
            dr = float(getattr(gl, "debit", 0.0) or 0.0)
            cr = float(getattr(gl, "credit", 0.0) or 0.0)
            net = (cr - dr) if acc.startswith("4") else (dr - cr)

            key = (period, ent, acc)
            actuals[key] += net
            eid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            gl_refs_by_bucket[key].append(f"gl:{eid}")

        # Index budget by (period, entity_id, account_code)
        budget_map: Dict[tuple, float] = {}
        for b in budget_entries:
            key = (getattr(b, "period", ""), getattr(b, "entity_id", ""), getattr(b, "account_code", ""))
            budget_map[key] = float(getattr(b, "amount", 0.0))

        # Check monthly variances
        for key, act in actuals.items():
            period, ent, acc = key
            bud = budget_map.get(key, 0.0)
            diff = act - bud
            abs_diff = abs(diff)

            if bud > 0:
                pct_diff = abs_diff / bud
            else:
                pct_diff = 1.0 if abs_diff > 0 else 0.0

            if abs_diff >= p.abs_threshold and pct_diff >= p.pct_threshold:
                direction = "Overspend" if acc.startswith("5") and diff > 0 else ("Under-revenue" if acc.startswith("4") and diff < 0 else "Variance")
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-VAR-{period}-{ent}-{acc}",
                        control_id=self.key,
                        severity="medium" if abs_diff < 100000 else "high",
                        description=(
                            f"{direction} in {period} on account {acc} (entity {ent}): "
                            f"Actual {act:,.2f} vs Budget {bud:,.2f} (Variance: {diff:+,.2f} / {pct_diff:.1%})."
                        ),
                        affected_row_refs=gl_refs_by_bucket[key][:10],
                        amount=abs_diff,
                        account_code=acc,
                        period=period,
                        metadata={
                            "actual": act,
                            "budget": bud,
                            "variance": diff,
                            "variance_pct": pct_diff,
                            "type": "monthly_variance",
                        },
                    )
                )

        # Check YTD Drift if enabled
        if p.check_ytd:
            # Group by (entity_id, account_code) across periods in sorted order
            buckets_by_entity_acc: Dict[tuple, List[str]] = defaultdict(list)
            for (per, ent, acc) in set(list(actuals.keys()) + list(budget_map.keys())):
                buckets_by_entity_acc[(ent, acc)].append(per)

            for (ent, acc), periods in buckets_by_entity_acc.items():
                sorted_periods = sorted(set(periods))
                cum_act = 0.0
                cum_bud = 0.0
                all_refs: List[str] = []

                for per in sorted_periods:
                    k = (per, ent, acc)
                    cum_act += actuals.get(k, 0.0)
                    cum_bud += budget_map.get(k, 0.0)
                    all_refs.extend(gl_refs_by_bucket.get(k, []))

                    cum_diff = cum_act - cum_bud
                    cum_abs_diff = abs(cum_diff)
                    cum_pct = cum_abs_diff / cum_bud if cum_bud > 0 else (1.0 if cum_abs_diff > 0 else 0.0)

                    if cum_abs_diff >= (p.abs_threshold * 1.5) and cum_pct >= p.pct_threshold:
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-YTD-DRIFT-{per}-{ent}-{acc}",
                                control_id=self.key,
                                severity="high",
                                description=(
                                    f"Cumulative YTD budget drift on account {acc} (entity {ent}) through {per}: "
                                    f"YTD Actual {cum_act:,.2f} vs YTD Budget {cum_bud:,.2f} (Variance: {cum_diff:+,.2f} / {cum_pct:.1%})."
                                ),
                                affected_row_refs=all_refs[:10],
                                amount=cum_abs_diff,
                                account_code=acc,
                                period=per,
                                metadata={
                                    "ytd_actual": cum_act,
                                    "ytd_budget": cum_bud,
                                    "ytd_diff": cum_diff,
                                    "type": "ytd_drift",
                                },
                            )
                        )
                        break  # flag earliest YTD breach

        return findings
