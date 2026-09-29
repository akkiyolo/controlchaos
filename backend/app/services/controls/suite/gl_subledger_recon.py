"""GL to Subledger Reconciliation Control."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class GLSubledgerReconParams(BaseModel):
    enabled: bool = True
    tolerance: float = Field(0.01, description="Absolute difference tolerance")
    break_aging_days_threshold: int = Field(30, description="Flag breaks older than N days")
    control_account_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "1100": "cash",
            "1200": "AR",
            "1500": "FA",
            "2000": "AP",
            "5100": "payroll",
        },
        description="GL account code to subledger type mapping",
    )


class GLSubledgerReconControl(BaseControl[GLSubledgerReconParams]):
    key = "gl_subledger_recon"
    name = "GL-to-Subledger Reconciliation"
    category = "reconciliation"
    description = (
        "Reconciles General Ledger control accounts against supporting sub-ledgers "
        "(AR, AP, Fixed Assets, Payroll, Cash), detecting orphans, amount mismatches, "
        "and aged unmatched breaks."
    )
    intended_error_classes = ["subledger_orphan", "amount_mismatch"]
    params_model = GLSubledgerReconParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries
        sub_entries = context.subledger_entries

        # Map GL entries by entry_id and by (subledger_type, ref_id)
        # GL accounts mapped to subledgers
        control_accs = set(p.control_account_map.keys())
        relevant_gl = [e for e in gl_entries if getattr(e, "account_code", "") in control_accs]

        # Index subledger entries by gl_entry_id and ref_id
        sub_by_gl_id: Dict[str, List[Any]] = defaultdict(list)
        sub_by_ref: Dict[str, Any] = {}
        for s in sub_entries:
            s_gl_id = getattr(s, "gl_entry_id", None)
            if s_gl_id:
                sub_by_gl_id[str(s_gl_id)].append(s)
            s_ref_id = getattr(s, "ref_id", "")
            if s_ref_id:
                sub_by_ref[str(s_ref_id)] = s

        matched_sub_ids = set()

        # 1. Check each relevant GL entry
        for gl in relevant_gl:
            gl_id = str(getattr(gl, "entry_id", "") or getattr(gl, "id", "") or "")
            gl_amount = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
            expected_subtype = p.control_account_map.get(str(getattr(gl, "account_code", "") or ""))

            matching_subs = sub_by_gl_id.get(gl_id, [])
            if not matching_subs and gl_id in sub_by_ref:
                matching_subs = [sub_by_ref[gl_id]]

            if not matching_subs:
                # Subledger Orphan: GL entry has no subledger counterpart
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-ORPH-GL-{gl_id}",
                        control_id=self.key,
                        severity="high",
                        description=(
                            f"GL control account {getattr(gl, 'account_code', '')} entry {gl_id} "
                            f"for {gl_amount:,.2f} has no corresponding {expected_subtype} subledger record."
                        ),
                        affected_row_refs=[f"gl:{gl_id}"],
                        amount=gl_amount,
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                        metadata={"type": "gl_orphan", "expected_subledger": expected_subtype},
                    )
                )
            else:
                for sub in matching_subs:
                    sub_id = getattr(sub, "ref_id", "") or getattr(sub, "id", "")
                    matched_sub_ids.add(sub_id)
                    sub_amount = float(getattr(sub, "amount", 0.0))
                    diff = abs(gl_amount - sub_amount)

                    if diff > p.tolerance:
                        findings.append(
                            FindingDTO(
                                finding_id=f"FIND-MISMATCH-{gl_id}-{sub_id}",
                                control_id=self.key,
                                severity="medium" if diff < 1000 else "high",
                                description=(
                                    f"Amount mismatch on GL {gl_id} ({gl_amount:,.2f}) vs "
                                    f"subledger {sub_id} ({sub_amount:,.2f}). Difference: {diff:,.2f}"
                                ),
                                affected_row_refs=[f"gl:{gl_id}", f"sub:{sub_id}"],
                                amount=diff,
                                account_code=getattr(gl, "account_code", None),
                                period=getattr(gl, "period", None),
                                metadata={"gl_amount": gl_amount, "sub_amount": sub_amount, "diff": diff},
                            )
                        )

        # 2. Check for Subledger entries with no matching GL entry
        for sub in sub_entries:
            sub_id = getattr(sub, "ref_id", "") or getattr(sub, "id", "")
            target_gl_id = getattr(sub, "gl_entry_id", None)
            if sub_id not in matched_sub_ids:
                if not target_gl_id or not any(getattr(g, "entry_id", "") == target_gl_id for g in relevant_gl):
                    sub_amount = float(getattr(sub, "amount", 0.0))
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-ORPH-SUB-{sub_id}",
                            control_id=self.key,
                            severity="medium",
                            description=(
                                f"Subledger {getattr(sub, 'subledger_type', '')} record {sub_id} "
                                f"for {sub_amount:,.2f} has no matching GL control entry."
                            ),
                            affected_row_refs=[f"sub:{sub_id}"],
                            amount=sub_amount,
                            period=None,
                            metadata={"type": "subledger_orphan", "subledger_type": getattr(sub, "subledger_type", "")},
                        )
                    )

        return findings
