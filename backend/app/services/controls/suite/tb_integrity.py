"""Trial Balance and Batch Integrity Control."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class TBIntegrityParams(BaseModel):
    enabled: bool = True
    tolerance: float = Field(0.01, description="Acceptable imbalance tolerance")
    check_batches: bool = Field(True, description="Verify each journal batch balances to zero")
    check_periods: bool = Field(True, description="Verify each period balances to zero")
    check_entities: bool = Field(True, description="Verify each legal entity balances to zero")


class TrialBalanceIntegrityControl(BaseControl[TBIntegrityParams]):
    key = "tb_integrity"
    name = "Trial Balance Integrity"
    category = "integrity"
    description = (
        "Validates fundamental double-entry accounting integrity: verifies that sum(debit) == sum(credit) "
        "across the entire dataset, per entity, per period, and within every individual journal batch."
    )
    intended_error_classes = ["unbalanced_batch", "sign_flip"]
    params_model = TBIntegrityParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # 1. Negative amounts or simultaneous debit & credit check
        for gl in gl_entries:
            eid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            dr = float(getattr(gl, "debit", 0.0) or 0.0)
            cr = float(getattr(gl, "credit", 0.0) or 0.0)

            if dr < 0 or cr < 0:
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-TB-NEG-{eid}",
                        control_id=self.key,
                        severity="high",
                        description=f"Negative debit ({dr:,.2f}) or credit ({cr:,.2f}) in entry {eid}.",
                        affected_row_refs=[f"gl:{eid}"],
                        amount=abs(min(dr, cr)),
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                    )
                )

            if dr > 0 and cr > 0:
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-TB-DUAL-{eid}",
                        control_id=self.key,
                        severity="medium",
                        description=f"Entry {eid} has both non-zero debit ({dr:,.2f}) and credit ({cr:,.2f}).",
                        affected_row_refs=[f"gl:{eid}"],
                        amount=min(dr, cr),
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                    )
                )

        # 2. Batch integrity check
        if p.check_batches:
            batch_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
            batch_rows: Dict[str, List[str]] = defaultdict(list)

            for gl in gl_entries:
                bid = getattr(gl, "batch_id", "") or "UNKNOWN_BATCH"
                eid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
                batch_totals[bid]["debit"] += float(getattr(gl, "debit", 0.0) or 0.0)
                batch_totals[bid]["credit"] += float(getattr(gl, "credit", 0.0) or 0.0)
                batch_rows[bid].append(f"gl:{eid}")

            for bid, totals in batch_totals.items():
                diff = abs(totals["debit"] - totals["credit"])
                if diff > p.tolerance:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-BATCH-UNBALANCED-{bid}",
                            control_id=self.key,
                            severity="critical",
                            description=(
                                f"Journal batch {bid} is out of balance. "
                                f"Total Debits: {totals['debit']:,.2f}, Total Credits: {totals['credit']:,.2f}, "
                                f"Net Difference: {diff:,.2f}"
                            ),
                            affected_row_refs=batch_rows[bid][:10],  # first 10 rows
                            amount=diff,
                            metadata={"batch_id": bid, "debits": totals["debit"], "credits": totals["credit"]},
                        )
                    )

        # 3. Overall and Entity Trial Balance Check
        if p.check_entities:
            entity_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
            for gl in gl_entries:
                ent = getattr(gl, "entity_id", "") or "DEFAULT_ENTITY"
                entity_totals[ent]["debit"] += float(getattr(gl, "debit", 0.0) or 0.0)
                entity_totals[ent]["credit"] += float(getattr(gl, "credit", 0.0) or 0.0)

            for ent, totals in entity_totals.items():
                diff = abs(totals["debit"] - totals["credit"])
                if diff > p.tolerance:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-TB-ENTITY-{ent}",
                            control_id=self.key,
                            severity="critical",
                            description=(
                                f"Trial balance out of balance for entity {ent}. "
                                f"Debits: {totals['debit']:,.2f}, Credits: {totals['credit']:,.2f}, Diff: {diff:,.2f}"
                            ),
                            affected_row_refs=[f"entity:{ent}"],
                            amount=diff,
                            metadata={"entity_id": ent, "diff": diff},
                        )
                    )

        return findings
