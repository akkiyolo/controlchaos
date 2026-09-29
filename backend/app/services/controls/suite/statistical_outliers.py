"""Statistical Outlier Detection Control."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class StatisticalOutliersParams(BaseModel):
    enabled: bool = True
    multiplier: float = Field(3.0, description="IQR multiplier (e.g. 3.0 for extreme outliers)")
    min_sample_size: int = Field(15, description="Minimum number of transactions in account to run IQR test")


class StatisticalOutliersControl(BaseControl[StatisticalOutliersParams]):
    key = "statistical_outliers"
    name = "Statistical Outlier Detection (IQR / Robust Z-Score)"
    category = "forensic"
    description = (
        "Applies robust non-parametric statistical outlier analysis (Interquartile Range IQR) per GL account "
        "to pinpoint anomalous transactions, transpositions, or masked outsized postings deviating sharply from typical distributions."
    )
    intended_error_classes = ["transposition", "masked_offset"]
    params_model = StatisticalOutliersParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # Group amounts and entries by account_code
        by_account: Dict[str, List[Any]] = defaultdict(list)
        for gl in gl_entries:
            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
            if amt > 0.0:
                acc = getattr(gl, "account_code", "")
                by_account[acc].append(gl)

        for acc, entries in by_account.items():
            if len(entries) < p.min_sample_size:
                continue

            amounts = [float(getattr(e, "debit", 0.0) or getattr(e, "credit", 0.0)) for e in entries]
            q25, q75 = np.percentile(amounts, [25, 75])
            iqr = q75 - q25

            if iqr <= 0:
                continue

            upper_bound = q75 + (p.multiplier * iqr)

            for e in entries:
                amt = float(getattr(e, "debit", 0.0) or getattr(e, "credit", 0.0))
                if amt > upper_bound:
                    gid = getattr(e, "entry_id", "") or getattr(e, "id", "")
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-OUTLIER-{acc}-{gid}",
                            control_id=self.key,
                            severity="high" if amt > (q75 + 5.0 * iqr) else "medium",
                            description=(
                                f"Statistical outlier in account {acc}: Entry {gid} amount {amt:,.2f} "
                                f"exceeds upper IQR threshold of {upper_bound:,.2f} (Q75: {q75:,.2f}, IQR: {iqr:,.2f})."
                            ),
                            affected_row_refs=[f"gl:{gid}"],
                            amount=amt,
                            account_code=acc,
                            period=getattr(e, "period", None),
                            metadata={"amount": amt, "upper_bound": upper_bound, "q75": q75, "iqr": iqr},
                        )
                    )

        return findings
