"""Budget figures generator with plausible baseline variance."""

from typing import Dict, List, Tuple

import numpy as np

# Standard monthly baseline budget targets per account (base amounts in USD)
ACCOUNT_BASE_BUDGET = {
    # Revenues (credits)
    "4000": 3500000.0,  # Trading and Interest Revenue
    "4100": 1200000.0,  # Fee and Advisory Income
    # Expenses (debits)
    "5000": 1800000.0,  # Compensation and Payroll Expense
    "5100": 450000.0,   # Technology & Market Data Licensing
    "5200": 250000.0,   # Professional Fees & Legal Services
    "5300": 300000.0,   # Occupancy & Facilities Expense
}


def generate_budget_records(
    periods: List[str],
    entities: List[dict],
    rng: np.random.Generator,
    dataset_id: str,
) -> Tuple[List[dict], Dict[Tuple[str, str, str], float]]:
    """
    Generates monthly budget targets per entity and account.
    Returns:
        (budget_rows: List[dict] for DB, budget_lookup: Dict[(period, entity_id, account_code), amount])
    """
    budget_rows = []
    budget_lookup = {}

    for period in periods:
        month_idx = int(period.split("-")[1])
        # Slight seasonality factor (e.g. Q4 budget ramp)
        seasonal_mult = 1.0 + (0.05 if month_idx in (11, 12) else 0.0)

        for ent in entities:
            ent_id = ent["id"]
            # Currency conversion or entity sizing
            size_factor = 1.2 if ent["currency"] == "USD" else 0.85

            for acc_code, base_amt in ACCOUNT_BASE_BUDGET.items():
                # Minor stochastic variation (+/- 2%) across months
                drift = rng.normal(0, 0.02)
                budget_amt = round(base_amt * size_factor * seasonal_mult * (1.0 + drift), 2)

                budget_lookup[(period, ent_id, acc_code)] = budget_amt
                budget_rows.append({
                    "dataset_id": dataset_id,
                    "period": period,
                    "entity_id": ent_id,
                    "account_code": acc_code,
                    "amount": budget_amt,
                })

    return budget_rows, budget_lookup
