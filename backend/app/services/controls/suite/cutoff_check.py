"""Period Cutoff Verification Control."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class CutoffCheckParams(BaseModel):
    enabled: bool = True
    cutoff_window_days: int = Field(5, description="Days near month-end to inspect for cutoff boundary crossings")


class CutoffCheckControl(BaseControl[CutoffCheckParams]):
    key = "cutoff_check"
    name = "Period Cutoff Verification"
    category = "cutoff"
    description = (
        "Inspects transactions posted near accounting period close (month-end / quarter-end) "
        "to ensure revenue and expenses are recognized in the correct accounting period matching the transaction value date."
    )
    intended_error_classes = ["cutoff_error"]
    params_model = CutoffCheckParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries
        sub_entries = context.subledger_entries

        # Map subledgers by gl_entry_id and ref_id
        sub_map: Dict[str, Any] = {}
        for s in sub_entries:
            gid = getattr(s, "gl_entry_id", None)
            if gid:
                sub_map[gid] = s
            rid = getattr(s, "ref_id", "")
            if rid:
                sub_map[rid] = s

        for gl in gl_entries:
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            posting_date_str = getattr(gl, "posting_date", "")
            period = getattr(gl, "period", "")  # YYYY-MM

            if not posting_date_str:
                continue

            try:
                p_date = datetime.strptime(posting_date_str, "%Y-%m-%d")
            except ValueError:
                continue

            posting_period = p_date.strftime("%Y-%m")

            # Check 1: Does posting_date period match the entry's declared accounting period?
            if period and posting_period != period:
                amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-CUTOFF-PERIOD-{gid}",
                        control_id=self.key,
                        severity="high",
                        description=(
                            f"Cutoff violation on entry {gid}: Posting date {posting_date_str} (period {posting_period}) "
                            f"was booked into accounting period {period}."
                        ),
                        affected_row_refs=[f"gl:{gid}"],
                        amount=amt,
                        account_code=getattr(gl, "account_code", None),
                        period=period,
                        metadata={"posting_date": posting_date_str, "assigned_period": period},
                    )
                )

            # Check 2: Value date in subledger vs posting date in GL crossing period boundary
            sub = sub_map.get(str(gid))
            if sub:
                val_date_str = getattr(sub, "value_date", "")
                if val_date_str:
                    try:
                        v_date = datetime.strptime(val_date_str, "%Y-%m-%d")
                        val_period = v_date.strftime("%Y-%m")
                        if val_period != posting_period:
                            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
                            findings.append(
                                FindingDTO(
                                    finding_id=f"FIND-CUTOFF-SUB-{gid}",
                                    control_id=self.key,
                                    severity="high",
                                    description=(
                                        f"Cutoff mismatch between GL {gid} (posted {posting_date_str}) "
                                        f"and subledger value date {val_date_str} crossing period boundary ({posting_period} vs {val_period})."
                                    ),
                                    affected_row_refs=[f"gl:{gid}", f"sub:{getattr(sub, 'ref_id', '')}"],
                                    amount=amt,
                                    account_code=getattr(gl, "account_code", None),
                                    period=period,
                                    metadata={"posting_date": posting_date_str, "value_date": val_date_str},
                                )
                            )
                    except ValueError:
                        pass

        return findings
