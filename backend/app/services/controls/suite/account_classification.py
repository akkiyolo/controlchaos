"""Account Classification Rules Control."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class AccountClassificationParams(BaseModel):
    enabled: bool = True
    opex_keywords: List[str] = Field(
        default_factory=lambda: [
            "consulting",
            "software license",
            "travel expense",
            "hotel",
            "airfare",
            "meal",
            "office supplies",
            "advisory fee",
            "legal counsel",
        ],
        description="Keywords indicative of operating expenses (OPEX)",
    )
    capex_keywords: List[str] = Field(
        default_factory=lambda: ["server hardware", "property acquisition", "leasehold improvement", "vehicle purchase"],
        description="Keywords indicative of capital expenditure (CAPEX)",
    )


class AccountClassificationControl(BaseControl[AccountClassificationParams]):
    key = "account_classification"
    name = "Account Classification & Narrative Validation"
    category = "classification"
    description = (
        "Inspects journal entry narrative text and transaction characteristics against chart of accounts taxonomy, "
        "detecting misclassified items such as OPEX parked in balance sheet assets or improper direct revenue debits."
    )
    intended_error_classes = ["misclassification"]
    params_model = AccountClassificationParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        opex_patterns = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in p.opex_keywords]
        capex_patterns = [re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE) for k in p.capex_keywords]

        for gl in gl_entries:
            desc = (getattr(gl, "description", "") or "").strip()
            acc = getattr(gl, "account_code", "")
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))

            if not desc or not acc:
                continue

            # Check 1: OPEX keywords posted to Balance Sheet (1xxx Assets or 2xxx Liabilities)
            if acc.startswith(("1", "2")):
                for kw, pattern in zip(p.opex_keywords, opex_patterns):
                    if pattern.search(desc):
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-MISCLASS-OPEX-BS-{gid}",
                                control_id=self.key,
                                severity="high",
                                description=(
                                    f"Suspected misclassification on entry {gid}: Operating expense narrative ('{kw}') "
                                    f"posted to balance sheet account {acc}. Description: '{desc}'."
                                ),
                                affected_row_refs=[f"gl:{gid}"],
                                amount=amt,
                                account_code=acc,
                                period=getattr(gl, "period", None),
                                metadata={"matched_keyword": kw, "account_family": acc[0]},
                            )
                        )
                        break

            # Check 2: CAPEX keywords posted directly to OPEX (5xxx)
            elif acc.startswith("5"):
                for kw, pattern in zip(p.capex_keywords, capex_patterns):
                    if pattern.search(desc):
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-MISCLASS-CAPEX-OPEX-{gid}",
                                control_id=self.key,
                                severity="medium",
                                description=(
                                    f"Potential capital item expensed on entry {gid}: Narrative ('{kw}') "
                                    f"posted directly to operating expense account {acc}."
                                ),
                                affected_row_refs=[f"gl:{gid}"],
                                amount=amt,
                                account_code=acc,
                                period=getattr(gl, "period", None),
                                metadata={"matched_keyword": kw},
                            )
                        )
                        break

        return findings
