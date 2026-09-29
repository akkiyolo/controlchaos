"""Accrual Completeness Control."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class AccrualCompletenessParams(BaseModel):
    enabled: bool = True
    required_accounts: List[str] = Field(
        default_factory=lambda: ["5000", "5100", "5200"],
        description="List of recurring expense accounts that must have postings every period (e.g. Rent, Payroll, Tech)",
    )


class AccrualCompletenessControl(BaseControl[AccrualCompletenessParams]):
    key = "accrual_completeness"
    name = "Accrual Completeness"
    category = "completeness"
    description = (
        "Validates that required recurring operational accruals (payroll, facilities/rent, software/tech) "
        "are systematically recognized in every accounting period for each active reporting entity."
    )
    intended_error_classes = ["missing_accrual"]
    params_model = AccrualCompletenessParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # Extract all distinct entities and active periods present in GL
        entities = set()
        periods = set()
        postings: Dict[tuple, List[str]] = defaultdict(list)

        for gl in gl_entries:
            ent = getattr(gl, "entity_id", "")
            per = getattr(gl, "period", "")
            acc = getattr(gl, "account_code", "")
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")

            if ent:
                entities.add(ent)
            if per:
                periods.add(per)
            if acc in p.required_accounts:
                postings[(ent, per, acc)].append(f"gl:{gid}")

        # Check for missing accruals
        for ent in sorted(entities):
            for per in sorted(periods):
                for req_acc in p.required_accounts:
                    key = (ent, per, req_acc)
                    if not postings.get(key):
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-MISSING-ACCRUAL-{ent}-{per}-{req_acc}",
                                control_id=self.key,
                                severity="high",
                                description=(
                                    f"Missing recurring accrual: No journal entries posted to mandatory account {req_acc} "
                                    f"for entity {ent} in period {per}."
                                ),
                                affected_row_refs=[f"entity:{ent}", f"period:{per}"],
                                amount=None,
                                account_code=req_acc,
                                period=per,
                                metadata={"entity_id": ent, "period": per, "account_code": req_acc},
                            )
                        )

        return findings
