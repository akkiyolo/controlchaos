"""Core double-entry synthetic general ledger generator."""

import uuid
from datetime import date
from typing import Any, Dict, List

import numpy as np

from app.services.generator.benford import sample_lognormal_amount
from app.services.generator.budget_gen import generate_budget_records
from app.services.generator.calendar_utils import (
    get_month_business_days,
    get_month_dates,
    get_month_end_business_day,
    get_period_strings,
)
from app.services.generator.fx_gen import generate_fx_rates
from app.services.generator.models import DecoyAnomaly, GeneratorParams, TransactionVolume
from app.services.generator.subledgers import create_subledger_entry
from app.services.generator.treasury_gen import generate_treasury_positions

COUNTERPARTIES = {
    "AR": ["Apex Asset Management", "Vanguard Global", "BlackRock Prime", "Citadel Securities", "Two Sigma Partners"],
    "AP": ["Bloomberg Finance LP", "Refinitiv Market Data", "Amazon Web Services", "Microsoft Enterprise", "Deloitte Advisory"],
    "FA": ["Dell Technologies", "Cisco Systems", "Equinix Data Centers", "Herman Miller"],
    "payroll": ["ADP Global Payroll", "Direct Deposit Clearing", "Mercer Benefits"],
    "cash": ["JPMorgan Chase Bank NA", "BNP Paribas SA", "Deutsche Bank AG", "State Street Clearing"],
}

STAFF_USERS = [
    ("alex.mercer@controlchaos.local", "david.ross@controlchaos.local"),
    ("elena.rostova@controlchaos.local", "marcus.vance@controlchaos.local"),
    ("sarah.chen@controlchaos.local", "david.ross@controlchaos.local"),
]


class SyntheticLedgerGenerator:
    """Generates complete, balanced, and realistic financial ledgers with sub-ledgers and treasury data."""

    def __init__(self, params: GeneratorParams, entities: List[dict]):
        self.params = params
        self.entities = entities
        self.rng = np.random.default_rng(params.seed)
        self.dataset_id = str(uuid.uuid4())
        self.periods = get_period_strings(params.start_date, params.months)

    def generate_all(self) -> Dict[str, Any]:
        """Runs the entire deterministic generator pipeline."""
        # 1. Collect all dates across the generated periods
        all_dates: List[date] = []
        for period in self.periods:
            y, m = map(int, period.split("-"))
            all_dates.extend(get_month_dates(y, m))

        # 2. FX Rates
        fx_rows, fx_lookup = generate_fx_rates(
            all_dates=all_dates,
            currencies=self.params.currencies,
            rng=self.rng,
            dataset_id=self.dataset_id,
        )

        # 3. Budget Targets
        budget_rows, budget_lookup = generate_budget_records(
            periods=self.periods,
            entities=self.entities,
            rng=self.rng,
            dataset_id=self.dataset_id,
        )

        # 4. Treasury Positions
        treasury_rows = generate_treasury_positions(
            all_dates=all_dates,
            entities=self.entities,
            rng=self.rng,
            dataset_id=self.dataset_id,
        )

        # 5. Double-Entry GL Batches and Sub-Ledger Entries
        gl_rows: List[dict] = []
        subledger_rows: List[dict] = []
        decoys: List[DecoyAnomaly] = []

        # Determine batch count per period based on volume parameter
        volume_counts = {
            TransactionVolume.LOW: (30, 60),      # ~30-60 batches/month
            TransactionVolume.MEDIUM: (150, 250), # ~150-250 batches/month
            TransactionVolume.HIGH: (400, 600),   # ~400-600 batches/month
        }
        min_b, max_b = volume_counts.get(self.params.volume, (30, 60))

        for period in self.periods:
            y, m = map(int, period.split("-"))
            b_days = get_month_business_days(y, m)
            month_end_date = get_month_end_business_day(y, m)
            month_end_str = month_end_date.isoformat()

            num_batches = int(self.rng.integers(min_b, max_b))

            for batch_idx in range(num_batches):
                batch_id = f"BATCH-{period}-{batch_idx+1:05d}"
                posting_date = b_days[int(self.rng.integers(0, len(b_days)))].isoformat()
                ent = self.entities[int(self.rng.integers(0, len(self.entities)))]
                ent_id = ent["id"]
                ccy = ent["currency"]
                fx_rate = fx_lookup.get((posting_date, ccy, "USD"), 1.0)
                creator, approver = STAFF_USERS[int(self.rng.integers(0, len(STAFF_USERS)))]

                # Transaction archetypes:
                # 0: Invoicing (Dr 1100 AR, Cr 4000/4100 Revenue)
                # 1: Vendor invoice (Dr 5100/5200/5300 Expense, Cr 2000 AP)
                # 2: AR Collection (Dr 1000 Cash, Cr 1100 AR)
                # 3: AP Payment (Dr 2000 AP, Cr 1000 Cash)
                # 4: Payroll run (Dr 5000 Payroll, Cr 1000 Cash)
                tx_type = int(self.rng.choice([0, 1, 2, 3, 4], p=[0.30, 0.35, 0.15, 0.15, 0.05]))

                amt = sample_lognormal_amount(self.rng)
                entry_uuid_1 = str(uuid.uuid4())
                entry_uuid_2 = str(uuid.uuid4())

                if tx_type == 0:
                    # Invoicing: Dr 1100 AR, Cr 4100 Fee Income
                    counterparty = str(self.rng.choice(COUNTERPARTIES["AR"]))
                    desc = f"Institutional advisory invoice to {counterparty}"
                    # Leg 1: Dr AR
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_1, batch_id, posting_date, period, ent_id,
                        "1100", debit=amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="AR_SUBLEDGER", creator=creator, approver=approver
                    ))
                    # Leg 2: Cr Revenue
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_2, batch_id, posting_date, period, ent_id,
                        "4100", debit=0.0, credit=amt, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="BILLING_SYS", creator=creator, approver=approver
                    ))
                    # Subledger AR
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_1, "AR", counterparty, amt, ccy, posting_date
                    ))

                elif tx_type == 1:
                    # Vendor expense: Dr 5100/5200/5300, Cr 2000 AP
                    exp_acc = str(self.rng.choice(["5100", "5200", "5300"]))
                    counterparty = str(self.rng.choice(COUNTERPARTIES["AP"]))
                    desc = f"Vendor operational billing - {counterparty}"
                    # Leg 1: Dr Expense
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_1, batch_id, posting_date, period, ent_id,
                        exp_acc, debit=amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="AP_SUBLEDGER", creator=creator, approver=approver
                    ))
                    # Leg 2: Cr AP
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_2, batch_id, posting_date, period, ent_id,
                        "2000", debit=0.0, credit=amt, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="AP_SUBLEDGER", creator=creator, approver=approver
                    ))
                    # Subledger AP
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_2, "AP", counterparty, amt, ccy, posting_date
                    ))

                elif tx_type == 2:
                    # AR Cash Collection: Dr 1000 Cash, Cr 1100 AR
                    counterparty = str(self.rng.choice(COUNTERPARTIES["AR"]))
                    desc = f"Wire settlement received from {counterparty}"
                    # Leg 1: Dr Cash
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_1, batch_id, posting_date, period, ent_id,
                        "1000", debit=amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="CASH_MANAGEMENT", creator=creator, approver=approver
                    ))
                    # Leg 2: Cr AR
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_2, batch_id, posting_date, period, ent_id,
                        "1100", debit=0.0, credit=amt, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="AR_SUBLEDGER", creator=creator, approver=approver
                    ))
                    # Subledger Cash
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_1, "cash", counterparty, amt, ccy, posting_date
                    ))

                elif tx_type == 3:
                    # AP Cash Payment: Dr 2000 AP, Cr 1000 Cash
                    counterparty = str(self.rng.choice(COUNTERPARTIES["AP"]))
                    desc = f"Authorized vendor disbursement to {counterparty}"
                    # Leg 1: Dr AP
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_1, batch_id, posting_date, period, ent_id,
                        "2000", debit=amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="AP_SUBLEDGER", creator=creator, approver=approver
                    ))
                    # Leg 2: Cr Cash
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_2, batch_id, posting_date, period, ent_id,
                        "1000", debit=0.0, credit=amt, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="CASH_MANAGEMENT", creator=creator, approver=approver
                    ))
                    # Subledger Cash
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_2, "cash", counterparty, amt, ccy, posting_date
                    ))

                elif tx_type == 4:
                    # Payroll: Dr 5000 Payroll, Cr 1000 Cash
                    payroll_amt = sample_lognormal_amount(self.rng, mean_log=10.5, sigma=0.5)
                    counterparty = str(self.rng.choice(COUNTERPARTIES["payroll"]))
                    desc = f"Staff compensation cycle - {counterparty}"
                    # Leg 1: Dr Payroll
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_1, batch_id, posting_date, period, ent_id,
                        "5000", debit=payroll_amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="PAYROLL_SYS", creator=creator, approver=approver
                    ))
                    # Leg 2: Cr Cash
                    gl_rows.append(self._create_gl_entry(
                        entry_uuid_2, batch_id, posting_date, period, ent_id,
                        "1000", debit=0.0, credit=payroll_amt, ccy=ccy, fx_rate=fx_rate,
                        desc=desc, source="CASH_MANAGEMENT", creator=creator, approver=approver
                    ))
                    # Subledger Payroll & Cash
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_1, "payroll", counterparty, payroll_amt, ccy, posting_date
                    ))
                    subledger_rows.append(create_subledger_entry(
                        self.dataset_id, entry_uuid_2, "cash", counterparty, payroll_amt, ccy, posting_date
                    ))

            # Month-End Accrual Spikes (booked exactly on month_end_str)
            for accrual_idx in range(5):
                accrual_batch = f"BATCH-ACCRUAL-{period}-{accrual_idx+1:02d}"
                accrual_amt = sample_lognormal_amount(self.rng, mean_log=9.0, sigma=0.8)
                ent = self.entities[int(self.rng.integers(0, len(self.entities)))]
                ent_id = ent["id"]
                ccy = ent["currency"]
                fx_rate = fx_lookup.get((month_end_str, ccy, "USD"), 1.0)
                creator, approver = STAFF_USERS[0]

                entry_id_dr = str(uuid.uuid4())
                entry_id_cr = str(uuid.uuid4())

                # Dr 5200 Professional Fees, Cr 2100 Accrued Expenses
                gl_rows.append(self._create_gl_entry(
                    entry_id_dr, accrual_batch, month_end_str, period, ent_id,
                    "5200", debit=accrual_amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                    desc=f"Month-end accrual for unbilled professional services ({period})",
                    source="GL_MANUAL_ACCRUAL", creator=creator, approver=approver
                ))
                gl_rows.append(self._create_gl_entry(
                    entry_id_cr, accrual_batch, month_end_str, period, ent_id,
                    "2100", debit=0.0, credit=accrual_amt, ccy=ccy, fx_rate=fx_rate,
                    desc=f"Month-end accrual provision ({period})",
                    source="GL_MANUAL_ACCRUAL", creator=creator, approver=approver
                ))

            # Legitimate Decoy Anomalies (one documented large valid anomaly every 3 months)
            if self.params.include_decoys and (m % 3 == 0):
                decoy_batch = f"BATCH-DECOY-{period}-01"
                decoy_amt = round(float(self.rng.uniform(450000.0, 850000.0)), 2)
                ent = self.entities[0]
                ent_id = ent["id"]
                ccy = ent["currency"]
                fx_rate = fx_lookup.get((month_end_str, ccy, "USD"), 1.0)
                creator, approver = STAFF_USERS[1]

                decoy_id = f"DECOY-{period}"
                decoy_desc = f"Board-approved annual core enterprise software infrastructure license ({period})"
                reason = "Valid one-off annual enterprise IT license renewal approved in Q1 Board minutes"

                entry_id_dr = str(uuid.uuid4())
                entry_id_cr = str(uuid.uuid4())

                gl_rows.append(self._create_gl_entry(
                    entry_id_dr, decoy_batch, month_end_str, period, ent_id,
                    "5100", debit=decoy_amt, credit=0.0, ccy=ccy, fx_rate=fx_rate,
                    desc=decoy_desc, source="AP_SUBLEDGER", creator=creator, approver=approver
                ))
                gl_rows.append(self._create_gl_entry(
                    entry_id_cr, decoy_batch, month_end_str, period, ent_id,
                    "2000", debit=0.0, credit=decoy_amt, ccy=ccy, fx_rate=fx_rate,
                    desc=decoy_desc, source="AP_SUBLEDGER", creator=creator, approver=approver
                ))
                subledger_rows.append(create_subledger_entry(
                    self.dataset_id, entry_id_cr, "AP", "Microsoft Enterprise Global", decoy_amt, ccy, month_end_str
                ))

                decoys.append(DecoyAnomaly(
                    decoy_id=decoy_id,
                    period=period,
                    entity_code=ent.get("code", "LE-100"),
                    account_code="5100",
                    amount=decoy_amt,
                    description=decoy_desc,
                    reason_valid=reason,
                ))

        # 6. Verify Double-Entry Balance Invariant in memory
        total_debits = sum(r["debit"] for r in gl_rows)
        total_credits = sum(r["credit"] for r in gl_rows)
        diff = abs(total_debits - total_credits)
        if diff > 0.001:
            raise RuntimeError(f"Double-entry balancing failure! Debits={total_debits}, Credits={total_credits}, Diff={diff}")

        return {
            "dataset_id": self.dataset_id,
            "gl_rows": gl_rows,
            "subledger_rows": subledger_rows,
            "budget_rows": budget_rows,
            "treasury_rows": treasury_rows,
            "fx_rows": fx_rows,
            "decoys": [d.model_dump() for d in decoys],
            "total_gl_entries": len(gl_rows),
            "total_subledger_entries": len(subledger_rows),
            "total_debits": round(total_debits, 4),
            "total_credits": round(total_credits, 4),
            "period_start": self.periods[0],
            "period_end": self.periods[-1],
        }

    def _create_gl_entry(
        self,
        entry_id: str,
        batch_id: str,
        posting_date: str,
        period: str,
        entity_id: str,
        account_code: str,
        debit: float,
        credit: float,
        ccy: str,
        fx_rate: float,
        desc: str,
        source: str,
        creator: str,
        approver: str,
    ) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "entry_id": entry_id,
            "posting_date": posting_date,
            "period": period,
            "entity_id": entity_id,
            "account_code": account_code,
            "debit": round(debit, 4),
            "credit": round(credit, 4),
            "currency": ccy,
            "fx_rate": round(fx_rate, 6),
            "description": desc,
            "source_system": source,
            "batch_id": batch_id,
            "created_by": creator,
            "approved_by": approver,
        }
