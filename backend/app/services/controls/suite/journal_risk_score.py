"""Journal Entry Multi-Factor Risk Scoring Control."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class JournalRiskScoreParams(BaseModel):
    enabled: bool = True
    risk_threshold: float = Field(0.65, description="Composite risk score threshold (0.0 to 1.0) to flag entry")
    round_number_step: int = Field(10000, description="Step for round number anomaly detection (e.g. 10,000, 50,000)")
    weekend_weight: float = Field(0.35, description="Risk weight for entries posted on weekends")
    round_amount_weight: float = Field(0.25, description="Risk weight for perfectly round transaction amounts")
    manual_source_weight: float = Field(0.20, description="Risk weight for non-automated/manual source systems")
    large_amount_threshold: float = Field(100000.0, description="Threshold above which large amount risk is added")
    large_amount_weight: float = Field(0.20, description="Risk weight for large amounts")


class JournalRiskScoreControl(BaseControl[JournalRiskScoreParams]):
    key = "journal_risk_score"
    name = "Journal Entry Risk Scoring"
    category = "risk_scoring"
    description = (
        "Computes a multi-factor risk composite score for every journal entry factoring in non-business day postings, "
        "manual source systems, round thousand amount patterns, and outsized transactions."
    )
    intended_error_classes = ["backdated_entry", "weekend_holiday_posting"]
    params_model = JournalRiskScoreParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        for gl in gl_entries:
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            date_str = getattr(gl, "posting_date", "")
            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
            source = (getattr(gl, "source_system", "") or "").lower()

            risk_score = 0.0
            reasons: List[str] = []

            # 1. Weekend factor
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
                        risk_score += p.weekend_weight
                        reasons.append(f"Weekend posting ({dt.strftime('%A')})")
                except ValueError:
                    pass

            # 2. Round amount factor
            if amt >= p.round_number_step and (amt % p.round_number_step == 0):
                risk_score += p.round_amount_weight
                reasons.append(f"Round amount ({amt:,.0f})")

            # 3. Manual source factor
            if "manual" in source or "excel" in source or "adhoc" in source:
                risk_score += p.manual_source_weight
                reasons.append(f"Manual source ({source})")

            # 4. Large amount factor
            if amt >= p.large_amount_threshold:
                risk_score += p.large_amount_weight
                reasons.append(f"Large amount ({amt:,.2f})")

            if risk_score >= p.risk_threshold:
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-RISK-JRNL-{gid}",
                        control_id=self.key,
                        severity="high" if risk_score >= 0.80 else "medium",
                        description=(
                            f"High journal entry risk score ({risk_score:.2f} >= {p.risk_threshold:.2f}) on entry {gid}. "
                            f"Risk indicators: {', '.join(reasons)}."
                        ),
                        affected_row_refs=[f"gl:{gid}"],
                        amount=amt,
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                        metadata={"risk_score": risk_score, "reasons": reasons, "posting_date": date_str},
                    )
                )

        return findings
