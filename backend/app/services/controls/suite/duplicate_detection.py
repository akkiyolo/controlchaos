"""Duplicate Posting Detection Control."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class DuplicateDetectionParams(BaseModel):
    enabled: bool = True
    window_days: int = Field(3, description="Date window to look for duplicates")
    amount_tolerance: float = Field(0.0, description="Amount tolerance for fuzzy match")
    exact_match_only: bool = Field(False, description="If true, only check identical dates and amounts")


class DuplicateDetectionControl(BaseControl[DuplicateDetectionParams]):
    key = "duplicate_detection"
    name = "Duplicate Transaction Detection"
    category = "integrity"
    description = (
        "Identifies exact and fuzzy duplicate journal entries and subledger transactions "
        "sharing identical or near-identical amounts, accounts, counterparties, or posting dates."
    )
    intended_error_classes = ["duplicate_posting"]
    params_model = DuplicateDetectionParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # Group GL entries by (entity_id, account_code)
        grouped: Dict[tuple, List[Any]] = defaultdict(list)
        for gl in gl_entries:
            key = (getattr(gl, "entity_id", ""), getattr(gl, "account_code", ""))
            grouped[key].append(gl)

        flagged_pairs = set()

        for (ent, acc), entries in grouped.items():
            n = len(entries)
            for i in range(n):
                e1 = entries[i]
                id1 = getattr(e1, "entry_id", "") or getattr(e1, "id", "")
                d1_str = getattr(e1, "posting_date", "")
                amt1 = float(getattr(e1, "debit", 0.0) or getattr(e1, "credit", 0.0))
                desc1 = getattr(e1, "description", "").strip().lower()

                if amt1 <= 0.001:
                    continue

                try:
                    d1 = datetime.strptime(d1_str, "%Y-%m-%d")
                except ValueError:
                    continue

                for j in range(i + 1, n):
                    e2 = entries[j]
                    id2 = getattr(e2, "entry_id", "") or getattr(e2, "id", "")

                    if (id1, id2) in flagged_pairs or (id2, id1) in flagged_pairs:
                        continue

                    d2_str = getattr(e2, "posting_date", "")
                    amt2 = float(getattr(e2, "debit", 0.0) or getattr(e2, "credit", 0.0))
                    desc2 = getattr(e2, "description", "").strip().lower()

                    if abs(amt1 - amt2) > p.amount_tolerance:
                        continue

                    try:
                        d2 = datetime.strptime(d2_str, "%Y-%m-%d")
                    except ValueError:
                        continue

                    days_diff = abs((d1 - d2).days)
                    if days_diff > p.window_days:
                        continue

                    # Check debit/credit direction matches (not an offset/reversal)
                    dr1 = float(getattr(e1, "debit", 0.0) or 0.0)
                    dr2 = float(getattr(e2, "debit", 0.0) or 0.0)
                    cr1 = float(getattr(e1, "credit", 0.0) or 0.0)
                    cr2 = float(getattr(e2, "credit", 0.0) or 0.0)

                    if (dr1 > 0 and dr2 > 0) or (cr1 > 0 and cr2 > 0):
                        # Both are debit or both are credit
                        flagged_pairs.add((id1, id2))
                        severity = "critical" if (days_diff == 0 and desc1 == desc2) else "high"
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-DUP-{id1}-{id2}",
                                control_id=self.key,
                                severity=severity,
                                description=(
                                    f"Potential duplicate posting detected: Entry {id1} ({d1_str}) and {id2} ({d2_str}) "
                                    f"both post {amt1:,.2f} to account {acc} (entity {ent}). Window: {days_diff} days."
                                ),
                                affected_row_refs=[f"gl:{id1}", f"gl:{id2}"],
                                amount=amt1,
                                account_code=acc,
                                period=getattr(e1, "period", None),
                                metadata={
                                    "first_entry": id1,
                                    "second_entry": id2,
                                    "days_apart": days_diff,
                                    "amount": amt1,
                                },
                            )
                        )

        return findings
