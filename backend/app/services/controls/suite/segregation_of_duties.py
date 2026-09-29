"""Segregation of Duties (Maker-Checker Violation) Control."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class SegregationOfDutiesParams(BaseModel):
    enabled: bool = True
    exempt_system_users: bool = Field(True, description="Exempt automated background bot accounts (e.g. system)")
    system_user_identifiers: List[str] = Field(
        default_factory=lambda: ["system", "auto", "batch_job", "cron"],
        description="Usernames considered automated system accounts",
    )


class SegregationOfDutiesControl(BaseControl[SegregationOfDutiesParams]):
    key = "segregation_of_duties"
    name = "Segregation of Duties (Maker-Checker)"
    category = "compliance"
    description = (
        "Enforces internal control governance by flagging manual journal entries where the creator (maker) "
        "and approver (checker) are the same individual, breaching segregation of duties policy."
    )
    intended_error_classes = ["segregation_of_duties_breach"]
    params_model = SegregationOfDutiesParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        for gl in gl_entries:
            creator = (getattr(gl, "created_by", "") or "").strip().lower()
            approver = (getattr(gl, "approved_by", "") or "").strip().lower()
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")

            if not creator or not approver:
                continue

            if creator == approver:
                if p.exempt_system_users and any(s in creator for s in p.system_user_identifiers):
                    continue

                amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-SOD-{gid}",
                        control_id=self.key,
                        severity="high" if amt < 100000 else "critical",
                        description=(
                            f"Segregation of duties breach on entry {gid}: User '{creator}' "
                            f"both created and approved this journal entry for amount {amt:,.2f}."
                        ),
                        affected_row_refs=[f"gl:{gid}"],
                        amount=amt,
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                        metadata={"creator": creator, "approver": approver, "amount": amt},
                    )
                )

        return findings
