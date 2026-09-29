"""Comprehensive Financial Mutation Catalog implementing all 20 mutator classes."""

from __future__ import annotations

import copy
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.mutators.base import (
    BaseMutationParams,
    BaseMutator,
    MutableDatasetBundle,
    MutationRecordDTO,
)


def _get_magnitude_scale(magnitude: str) -> float:
    if magnitude == "small":
        return 0.15
    elif magnitude == "large":
        return 2.5
    return 1.0


# 1. duplicate_posting
class DuplicatePostingMutator(BaseMutator):
    key = "duplicate_posting"
    name = "Duplicate Posting"
    description = "Posts an exact or near-identical journal entry twice into the ledger."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = copy.copy(rng.choice(dataset.gl_entries))
        p = BaseMutationParams.model_validate(params or {})

        new_eid = f"GL-DUP-{rng.randint(10000, 99999)}"
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        target.id = str(uuid.uuid4())
        target.entry_id = new_eid

        if p.stealth == "obvious":
            # Exact same date and description
            pass
        elif p.stealth == "subtle":
            # Date +1 day
            try:
                dt = datetime.strptime(target.posting_date, "%Y-%m-%d") + timedelta(days=1)
                target.posting_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        else:  # adversarial
            target.description = f"{target.description} (Adjustment)"

        dataset.gl_entries.append(target)
        orig_eid = getattr(target, "entry_id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-DUP-{new_eid}",
            class_name=self.key,
            description=f"Duplicate posting of entry {orig_eid} for amount {amt:,.2f}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{new_eid}"],
            location_details={"account": target.account_code, "period": target.period},
        )


# 2. sign_flip
class SignFlipMutator(BaseMutator):
    key = "sign_flip"
    name = "Debit/Credit Sign Flip"
    description = "Inverts the normal balance debit/credit orientation of a journal entry."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        dr = float(getattr(target, "debit", 0.0) or 0.0)
        cr = float(getattr(target, "credit", 0.0) or 0.0)
        target.debit = cr
        target.credit = dr
        impact = abs(dr - cr)
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-SIGN-{eid}",
            class_name=self.key,
            description=f"Reversed debit and credit on entry {eid}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=impact * 2,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"account": target.account_code, "period": target.period},
        )


# 3. transposition
class TranspositionMutator(BaseMutator):
    key = "transposition"
    name = "Digit Transposition"
    description = "Swaps two adjacent digits in a transaction amount (classic clerical error)."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        candidates = [e for e in dataset.gl_entries if float(getattr(e, "debit", 0.0) or getattr(e, "credit", 0.0)) > 100.0]
        if not candidates:
            return None
        target = rng.choice(candidates)
        p = BaseMutationParams.model_validate(params or {})

        orig_amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        amt_str = f"{int(orig_amt)}"
        if len(amt_str) < 3:
            return None

        # Swap two adjacent digits
        idx = rng.randint(0, len(amt_str) - 2)
        digits = list(amt_str)
        digits[idx], digits[idx + 1] = digits[idx + 1], digits[idx]
        new_amt = float("".join(digits)) + (orig_amt - int(orig_amt))

        if getattr(target, "debit", 0.0) > 0:
            target.debit = new_amt
        else:
            target.credit = new_amt

        impact = abs(orig_amt - new_amt)
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-TRANS-{eid}",
            class_name=self.key,
            description=f"Digit transposition on entry {eid}: {orig_amt:,.2f} -> {new_amt:,.2f}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=impact,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"orig_amount": orig_amt, "transposed_amount": new_amt},
        )


# 4. cutoff_error
class CutoffErrorMutator(BaseMutator):
    key = "cutoff_error"
    name = "Period Cutoff Boundary Error"
    description = "Pushes an entry's posting date into the subsequent month while booking to previous period."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        orig_period = getattr(target, "period", "2025-01")
        # Change posting date to next month day 02
        try:
            y, m = orig_period.split("-")
            next_m = int(m) + 1
            next_y = int(y)
            if next_m > 12:
                next_m = 1
                next_y += 1
            target.posting_date = f"{next_y:04d}-{next_m:02d}-02"
        except Exception:
            target.posting_date = "2025-02-02"

        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-CUTOFF-{eid}",
            class_name=self.key,
            description=f"Cutoff violation: Entry {eid} posted on {target.posting_date} booked into {orig_period}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"assigned_period": orig_period, "posting_date": target.posting_date},
        )


# 5. missing_accrual
class MissingAccrualMutator(BaseMutator):
    key = "missing_accrual"
    name = "Missing Recurring Accrual"
    description = "Removes a mandatory recurring month-end expense accrual (e.g. payroll or facility rent)."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        accrual_entries = [e for e in dataset.gl_entries if getattr(e, "account_code", "") in ("5000", "5100", "5200")]
        if not accrual_entries:
            return None
        target = rng.choice(accrual_entries)
        p = BaseMutationParams.model_validate(params or {})

        dataset.gl_entries.remove(target)
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-NOACCRUAL-{eid}",
            class_name=self.key,
            description=f"Omitted monthly accrual for account {target.account_code} in period {target.period}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"account": target.account_code, "period": target.period},
        )


# 6. subledger_orphan
class SubledgerOrphanMutator(BaseMutator):
    key = "subledger_orphan"
    name = "Sub-ledger Orphan Break"
    description = "Breaks 1:1 reconciliation by deleting the sub-ledger counterpart of a GL control entry."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.subledger_entries:
            return None
        target = rng.choice(dataset.subledger_entries)
        p = BaseMutationParams.model_validate(params or {})

        dataset.subledger_entries.remove(target)
        amt = float(getattr(target, "amount", 0.0))
        ref_id = getattr(target, "ref_id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-ORPHAN-{ref_id}",
            class_name=self.key,
            description=f"Created subledger orphan: removed subledger entry {ref_id} ({amt:,.2f}).",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"sub:{ref_id}"],
            location_details={"type": getattr(target, "subledger_type", "")},
        )


# 7. amount_mismatch
class AmountMismatchMutator(BaseMutator):
    key = "amount_mismatch"
    name = "GL vs Sub-ledger Amount Mismatch"
    description = "Injects an unbalancing difference between a GL control entry and its sub-ledger counterpart."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.subledger_entries:
            return None
        target = rng.choice(dataset.subledger_entries)
        p = BaseMutationParams.model_validate(params or {})

        scale = _get_magnitude_scale(p.magnitude)
        delta = round(rng.uniform(25.0, 500.0) * scale, 2)
        orig_amt = float(getattr(target, "amount", 0.0))
        target.amount = orig_amt + delta
        ref_id = getattr(target, "ref_id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-MISMATCH-{ref_id}",
            class_name=self.key,
            description=f"Amount mismatch on subledger {ref_id}: {orig_amt:,.2f} -> {target.amount:,.2f} (delta {delta:,.2f}).",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=delta,
            affected_row_refs=[f"sub:{ref_id}"],
            location_details={"delta": delta},
        )


# 8. fx_rate_slip
class FXRateSlipMutator(BaseMutator):
    key = "fx_rate_slip"
    name = "Foreign Exchange Rate Slippage / Inversion"
    description = "Applies an inverted or severely drifted FX conversion rate to a foreign currency entry."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        fx_entries = [e for e in dataset.gl_entries if getattr(e, "currency", "USD") != "USD"]
        if not fx_entries:
            # Modify first entry to foreign currency
            if not dataset.gl_entries:
                return None
            target = dataset.gl_entries[0]
            target.currency = "EUR"
            target.fx_rate = 1.08
        else:
            target = rng.choice(fx_entries)

        p = BaseMutationParams.model_validate(params or {})
        orig_rate = float(getattr(target, "fx_rate", 1.08))

        if p.stealth == "adversarial":
            # Inversion: 1 / rate
            target.fx_rate = round(1.0 / orig_rate, 4)
        else:
            # 25% slippage
            target.fx_rate = round(orig_rate * 1.25, 4)

        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        impact = abs(amt * (target.fx_rate - orig_rate))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-FX-{eid}",
            class_name=self.key,
            description=f"FX rate slip on entry {eid}: applied {target.fx_rate:.4f} instead of {orig_rate:.4f}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=impact,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"orig_rate": orig_rate, "corrupted_rate": target.fx_rate},
        )


# 9. threshold_splitting
class ThresholdSplittingMutator(BaseMutator):
    key = "threshold_splitting"
    name = "Approval Threshold Structuring / Splitting"
    description = "Splits an outsized expenditure into multiple entries just below delegation limits (smurfing)."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        template = dataset.gl_entries[0]
        p = BaseMutationParams.model_validate(params or {})

        total_structured = 145000.0
        # Split into 3 entries of ~48,000 (limit is 50,000)
        split_amounts = [48500.0, 48200.0, 48300.0]
        row_refs = []

        for i, amt in enumerate(split_amounts):
            clone = copy.copy(template)
            eid = f"GL-SPLIT-{rng.randint(10000, 99999)}"
            clone.id = str(uuid.uuid4())
            clone.entry_id = eid
            clone.debit = amt
            clone.credit = 0.0
            clone.created_by = "analyst@controlchaos.local"
            clone.approved_by = "manager@controlchaos.local"
            clone.description = f"Structured invoice payment part {i+1}"
            dataset.gl_entries.append(clone)
            row_refs.append(f"gl:{eid}")

        return MutationRecordDTO(
            mutation_id=f"MUT-SPLIT-{row_refs[0]}",
            class_name=self.key,
            description=f"Threshold structuring: 3 transactions totaling {total_structured:,.2f} positioned below 50k limit.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=total_structured,
            affected_row_refs=row_refs,
            location_details={"split_count": 3, "total_amount": total_structured},
        )


# 10. round_tripping
class RoundTrippingMutator(BaseMutator):
    key = "round_tripping"
    name = "Intercompany Round-Tripping"
    description = "Injects artificial reciprocal transfers between entities with an uneliminated break."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        template = dataset.gl_entries[0]
        p = BaseMutationParams.model_validate(params or {})

        scale = _get_magnitude_scale(p.magnitude)
        amount = 75000.0 * scale
        break_delta = 5000.0  # Uneliminated difference

        e1 = copy.copy(template)
        eid1 = f"GL-IC1-{rng.randint(10000, 99999)}"
        e1.id = str(uuid.uuid4())
        e1.entry_id = eid1
        e1.account_code = "1300"  # IC Receivable
        e1.debit = amount
        e1.credit = 0.0
        dataset.gl_entries.append(e1)

        e2 = copy.copy(template)
        eid2 = f"GL-IC2-{rng.randint(10000, 99999)}"
        e2.id = str(uuid.uuid4())
        e2.entry_id = eid2
        e2.account_code = "2300"  # IC Payable
        e2.debit = 0.0
        e2.credit = amount - break_delta  # Break!
        dataset.gl_entries.append(e2)

        return MutationRecordDTO(
            mutation_id=f"MUT-ROUNDTRIP-{eid1}",
            class_name=self.key,
            description=f"Intercompany round-tripping between entities with uneliminated break of {break_delta:,.2f}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=break_delta,
            affected_row_refs=[f"gl:{eid1}", f"gl:{eid2}"],
            location_details={"break": break_delta},
        )


# 11. misclassification
class MisclassificationMutator(BaseMutator):
    key = "misclassification"
    name = "Account Classification Violation"
    description = "Parks operating expenses in balance sheet asset accounts (capitalization fraud)."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        opex_entries = [e for e in dataset.gl_entries if getattr(e, "account_code", "").startswith("5")]
        if not opex_entries:
            return None
        target = rng.choice(opex_entries)
        p = BaseMutationParams.model_validate(params or {})

        orig_acc = target.account_code
        target.account_code = "1500"  # Shift to Fixed Assets
        target.description = "Management advisory consulting and legal counsel fees"
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-MISCLASS-{eid}",
            class_name=self.key,
            description=f"Misclassification on entry {eid}: OPEX parked in Fixed Assets (1500).",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"orig_account": orig_acc, "target_account": "1500"},
        )


# 12. unbalanced_batch
class UnbalancedBatchMutator(BaseMutator):
    key = "unbalanced_batch"
    name = "Unbalanced Journal Batch"
    description = "Corrupts one entry of a balanced batch causing debits != credits."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        delta = 100.0 * _get_magnitude_scale(p.magnitude)
        if getattr(target, "debit", 0.0) > 0:
            target.debit += delta
        else:
            target.credit += delta

        bid = getattr(target, "batch_id", "")
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-UNBAL-{bid}",
            class_name=self.key,
            description=f"Batch {bid} thrown out of balance by {delta:,.2f} on entry {eid}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=delta,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"batch_id": bid, "delta": delta},
        )


# 13. backdated_entry
class BackdatedEntryMutator(BaseMutator):
    key = "backdated_entry"
    name = "Backdated Entry"
    description = "Posts an entry with a posting date months prior to the current close."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        orig_date = target.posting_date
        target.posting_date = "2023-01-01"  # Backdated 2 years
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-BACKDATE-{eid}",
            class_name=self.key,
            description=f"Backdated entry {eid}: posting date changed from {orig_date} to 2023-01-01.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"orig_date": orig_date, "backdated": "2023-01-01"},
        )


# 14. segregation_of_duties_breach
class SegregationOfDutiesBreachMutator(BaseMutator):
    key = "segregation_of_duties_breach"
    name = "Segregation of Duties Breach"
    description = "Forces the creator and approver of a journal entry to be the same user."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        target.created_by = "rogue_analyst@controlchaos.local"
        target.approved_by = "rogue_analyst@controlchaos.local"
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-SOD-{eid}",
            class_name=self.key,
            description=f"Segregation of duties breach on entry {eid}: creator equals approver.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"user": target.created_by},
        )


# 15. weekend_holiday_posting
class WeekendHolidayPostingMutator(BaseMutator):
    key = "weekend_holiday_posting"
    name = "Weekend / Non-Business Day Posting"
    description = "Alters a manual journal entry to be posted on a Saturday or Sunday."
    default_severity = "medium"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        target = rng.choice(dataset.gl_entries)
        p = BaseMutationParams.model_validate(params or {})

        target.posting_date = "2025-01-18"  # Saturday
        target.source_system = "manual_excel_upload"
        amt = float(getattr(target, "debit", 0.0) or getattr(target, "credit", 0.0))
        eid = getattr(target, "entry_id", "") or getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-WEEKEND-{eid}",
            class_name=self.key,
            description=f"Manual weekend journal posting on entry {eid} on {target.posting_date}.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid}"],
            location_details={"posting_date": target.posting_date},
        )


# 16. budget_drift
class BudgetDriftMutator(BaseMutator):
    key = "budget_drift"
    name = "Cumulative Budget Drift"
    description = "Injects subtle monthly overspends that individually pass thresholds but breach YTD budget."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        opex_entries = [e for e in dataset.gl_entries if getattr(e, "account_code", "").startswith("5")]
        if not opex_entries:
            return None
        p = BaseMutationParams.model_validate(params or {})

        total_drift = 0.0
        refs = []
        # Add 3.5% overspend across 5 entries
        for e in opex_entries[:5]:
            amt = float(getattr(e, "debit", 0.0) or 0.0)
            bump = round(amt * 0.04, 2)
            e.debit += bump
            total_drift += bump
            eid = getattr(e, "entry_id", "") or getattr(e, "id", "")
            refs.append(f"gl:{eid}")

        return MutationRecordDTO(
            mutation_id=f"MUT-DRIFT-{refs[0]}",
            class_name=self.key,
            description=f"Cumulative YTD budget drift: {total_drift:,.2f} overspend distributed across multiple periods.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=total_drift,
            affected_row_refs=refs,
            location_details={"drift_amount": total_drift},
        )


# 17. treasury_buffer_error
class TreasuryBufferErrorMutator(BaseMutator):
    key = "treasury_buffer_error"
    name = "Treasury HQLA Buffer / LCR Deficit"
    description = "Deflates HQLA liquidity buffer pushing LCR below regulatory minimum (100%)."
    default_severity = "critical"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.treasury_positions:
            return None
        target = rng.choice(dataset.treasury_positions)
        p = BaseMutationParams.model_validate(params or {})

        outflow = float(getattr(target, "outflows_30d", 100000.0))
        target.hqla = outflow * 0.82  # 82% LCR (< 100% floor)
        deficit = outflow - target.hqla
        pid = getattr(target, "id", "")

        return MutationRecordDTO(
            mutation_id=f"MUT-LCR-{pid}",
            class_name=self.key,
            description=f"Treasury LCR buffer deficiency on {target.as_of_date}: HQLA reduced to 82% of 30-day outflows.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=deficit,
            affected_row_refs=[f"treasury:{pid}"],
            location_details={"as_of_date": target.as_of_date, "lcr": 82.0},
        )


# 18. stale_balance
class StaleBalanceMutator(BaseMutator):
    key = "stale_balance"
    name = "Stale Treasury Cash Balance"
    description = "Freezes daily cash positions completely static for 7 consecutive days."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if len(dataset.treasury_positions) < 7:
            return None
        p = BaseMutationParams.model_validate(params or {})

        static_cash = float(dataset.treasury_positions[0].cash_balance)
        refs = []
        for pos in dataset.treasury_positions[:7]:
            pos.cash_balance = static_cash
            refs.append(f"treasury:{getattr(pos, 'id', '')}")

        return MutationRecordDTO(
            mutation_id=f"MUT-STALE-{refs[0]}",
            class_name=self.key,
            description=f"Stale cash balance frozen at {static_cash:,.2f} across 7 consecutive business days.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=static_cash,
            affected_row_refs=refs,
            location_details={"static_days": 7, "frozen_balance": static_cash},
        )


# 19. benford_manipulation
class BenfordManipulationMutator(BaseMutator):
    key = "benford_manipulation"
    name = "Benford Distribution Manipulation"
    description = "Injects fabricated transactions whose leading digits heavily violate Benford's Law (all starting with 9)."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        template = dataset.gl_entries[0]
        p = BaseMutationParams.model_validate(params or {})

        refs = []
        total_fabricated = 0.0
        for i in range(60):
            clone = copy.copy(template)
            eid = f"GL-BENF-{rng.randint(10000, 99999)}"
            clone.id = str(uuid.uuid4())
            clone.entry_id = eid
            clone.account_code = "5300"
            amt = float(f"9{rng.randint(100, 999)}.{rng.randint(10, 99)}")
            clone.debit = amt
            clone.credit = 0.0
            dataset.gl_entries.append(clone)
            refs.append(f"gl:{eid}")
            total_fabricated += amt

        return MutationRecordDTO(
            mutation_id=f"MUT-BENF-{refs[0]}",
            class_name=self.key,
            description="Fabricated 60 entries on account 5300 all starting with digit 9, violating Benford's Law.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=total_fabricated,
            affected_row_refs=refs[:15],
            location_details={"manipulated_digit": 9, "sample_size": 60},
        )


# 20. masked_offset
class MaskedOffsetMutator(BaseMutator):
    key = "masked_offset"
    name = "Masked Offsetting Error"
    description = "Injects an erroneous transaction paired with an exact reverse offset in the same account to test netted detection."
    default_severity = "high"

    def apply(self, dataset: MutableDatasetBundle, rng: random.Random, params: Optional[Dict[str, Any]] = None) -> Optional[MutationRecordDTO]:
        if not dataset.gl_entries:
            return None
        template = dataset.gl_entries[0]
        p = BaseMutationParams.model_validate(params or {})

        scale = _get_magnitude_scale(p.magnitude)
        amt = 35000.0 * scale

        e1 = copy.copy(template)
        eid1 = f"GL-MASK1-{rng.randint(10000, 99999)}"
        e1.id = str(uuid.uuid4())
        e1.entry_id = eid1
        e1.account_code = "5400"
        e1.debit = amt
        e1.credit = 0.0
        e1.description = "Operational consulting expense"
        dataset.gl_entries.append(e1)

        e2 = copy.copy(template)
        eid2 = f"GL-MASK2-{rng.randint(10000, 99999)}"
        e2.id = str(uuid.uuid4())
        e2.entry_id = eid2
        e2.account_code = "5400"
        e2.debit = 0.0
        e2.credit = amt
        e2.description = "Management rebate reversal offset"
        dataset.gl_entries.append(e2)

        return MutationRecordDTO(
            mutation_id=f"MUT-MASK-{eid1}",
            class_name=self.key,
            description=f"Masked offset of {amt:,.2f} injected into account 5400 netting monthly balance to zero.",
            severity=self.default_severity,
            stealth=p.stealth,
            magnitude=p.magnitude,
            expected_impact_amount=amt,
            affected_row_refs=[f"gl:{eid1}", f"gl:{eid2}"],
            location_details={"offset_amount": amt, "account": "5400"},
        )


ALL_MUTATORS: List[type[BaseMutator]] = [
    DuplicatePostingMutator,
    SignFlipMutator,
    TranspositionMutator,
    CutoffErrorMutator,
    MissingAccrualMutator,
    SubledgerOrphanMutator,
    AmountMismatchMutator,
    FXRateSlipMutator,
    ThresholdSplittingMutator,
    RoundTrippingMutator,
    MisclassificationMutator,
    UnbalancedBatchMutator,
    BackdatedEntryMutator,
    SegregationOfDutiesBreachMutator,
    WeekendHolidayPostingMutator,
    BudgetDriftMutator,
    TreasuryBufferErrorMutator,
    StaleBalanceMutator,
    BenfordManipulationMutator,
    MaskedOffsetMutator,
]
