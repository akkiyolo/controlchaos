"""Approval Threshold and Transaction Splitting Control."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class ThresholdSplittingParams(BaseModel):
    enabled: bool = True
    approval_limit: float = Field(50000.0, description="Mandatory single-transaction approval threshold limit")
    split_lower_pct: float = Field(0.70, description="Fraction of limit that starts the suspicious splitting band (e.g. 70%)")
    window_days: int = Field(3, description="Rolling time window to aggregate split attempts")
    min_cluster_count: int = Field(2, description="Minimum number of split items to trigger alert")


class ThresholdSplittingControl(BaseControl[ThresholdSplittingParams]):
    key = "threshold_splitting"
    name = "Approval Threshold & Transaction Splitting"
    category = "policy"
    description = (
        "Detects suspicious clusters of journal entries or disbursements positioned just below mandatory "
        "delegation-of-authority approval limits (smurfing/structuring) executed within a tight date window."
    )
    intended_error_classes = ["threshold_splitting"]
    params_model = ThresholdSplittingParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # We look for entries whose amount is in the splitting danger zone:
        # split_lower_pct * approval_limit <= amount < approval_limit
        lower_bound = p.split_lower_pct * p.approval_limit
        upper_bound = p.approval_limit

        # Group suspicious entries by (entity_id, account_code, created_by)
        grouped: Dict[tuple, List[Any]] = defaultdict(list)
        for gl in gl_entries:
            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
            if lower_bound <= amt < upper_bound:
                key = (
                    getattr(gl, "entity_id", ""),
                    getattr(gl, "account_code", ""),
                    getattr(gl, "created_by", ""),
                )
                grouped[key].append(gl)

        for (ent, acc, creator), entries in grouped.items():
            if len(entries) < p.min_cluster_count:
                continue

            # Sort by posting date
            entries.sort(key=lambda x: getattr(x, "posting_date", ""))

            # Sliding window over entries
            n = len(entries)
            i = 0
            while i < n:
                window_entries = [entries[i]]
                try:
                    d0 = datetime.strptime(getattr(entries[i], "posting_date", ""), "%Y-%m-%d")
                except ValueError:
                    i += 1
                    continue

                for j in range(i + 1, n):
                    try:
                        dj = datetime.strptime(getattr(entries[j], "posting_date", ""), "%Y-%m-%d")
                    except ValueError:
                        continue

                    if (dj - d0).days <= p.window_days:
                        window_entries.append(entries[j])
                    else:
                        break

                if len(window_entries) >= p.min_cluster_count:
                    cluster_total = sum(
                        float(getattr(e, "debit", 0.0) or getattr(e, "credit", 0.0)) for e in window_entries
                    )
                    if cluster_total > p.approval_limit:
                        row_refs = [f"gl:{getattr(e, 'entry_id', '') or getattr(e, 'id', '')}" for e in window_entries]
                        dates = [getattr(e, "posting_date", "") for e in window_entries]
                        amounts = [
                            float(getattr(e, "debit", 0.0) or getattr(e, "credit", 0.0)) for e in window_entries
                        ]

                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-SPLIT-{ent}-{acc}-{dates[0]}",
                                control_id=self.key,
                                severity="critical",
                                description=(
                                    f"Threshold structuring detected: User '{creator}' posted {len(window_entries)} items "
                                    f"just below the {p.approval_limit:,.0f} limit on account {acc} (entity {ent}) "
                                    f"within {p.window_days} days. Individual amounts: {amounts}. "
                                    f"Total structured amount: {cluster_total:,.2f}."
                                ),
                                affected_row_refs=row_refs,
                                amount=cluster_total,
                                account_code=acc,
                                period=getattr(window_entries[0], "period", None),
                                metadata={
                                    "creator": creator,
                                    "item_count": len(window_entries),
                                    "cluster_total": cluster_total,
                                    "limit": p.approval_limit,
                                    "dates": dates,
                                },
                            )
                        )
                        # Jump past the window to avoid duplicate reporting
                        i += len(window_entries)
                        continue

                i += 1

        return findings
