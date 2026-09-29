"""Intercompany Elimination and Round-Tripping Control."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class IntercompanyEliminationParams(BaseModel):
    enabled: bool = True
    tolerance: float = Field(1.0, description="Maximum allowable elimination difference across group entities")
    ic_receivable_account: str = Field("1300", description="Intercompany receivable account code")
    ic_payable_account: str = Field("2300", description="Intercompany payable account code")


class IntercompanyEliminationControl(BaseControl[IntercompanyEliminationParams]):
    key = "intercompany_elimination"
    name = "Intercompany Elimination & Round-Tripping"
    category = "reconciliation"
    description = (
        "Reconciles intercompany accounts across the corporate group (IC Receivables vs IC Payables), "
        "ensuring group-level consolidation elimination nets to zero and detecting unreciprocated transfers or round-tripping."
    )
    intended_error_classes = ["round_tripping"]
    params_model = IntercompanyEliminationParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # Group intercompany entries by period
        period_data: Dict[str, Dict[str, float]] = defaultdict(lambda: {"rec": 0.0, "pay": 0.0})
        period_rows: Dict[str, List[str]] = defaultdict(list)

        for gl in gl_entries:
            acc = getattr(gl, "account_code", "")
            if acc not in (p.ic_receivable_account, p.ic_payable_account):
                continue

            per = getattr(gl, "period", "")
            dr = float(getattr(gl, "debit", 0.0) or 0.0)
            cr = float(getattr(gl, "credit", 0.0) or 0.0)
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")

            period_rows[per].append(f"gl:{gid}")

            if acc == p.ic_receivable_account:
                # Receivable normal balance is debit
                period_data[per]["rec"] += (dr - cr)
            elif acc == p.ic_payable_account:
                # Payable normal balance is credit
                period_data[per]["pay"] += (cr - dr)

        for per, totals in period_data.items():
            rec_total = totals["rec"]
            pay_total = totals["pay"]
            diff = abs(rec_total - pay_total)

            if diff > p.tolerance:
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-IC-ELIM-{per}",
                        control_id=self.key,
                        severity="critical",
                        description=(
                            f"Intercompany elimination failure in period {per}: "
                            f"IC Receivables ({rec_total:,.2f}) does not match IC Payables ({pay_total:,.2f}). "
                            f"Uneliminated break: {diff:,.2f}."
                        ),
                        affected_row_refs=period_rows[per][:15],
                        amount=diff,
                        account_code=f"{p.ic_receivable_account}/{p.ic_payable_account}",
                        period=per,
                        metadata={
                            "period": per,
                            "receivables_total": rec_total,
                            "payables_total": pay_total,
                            "diff": diff,
                        },
                    )
                )

        return findings
