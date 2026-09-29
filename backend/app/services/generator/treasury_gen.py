"""Treasury positions and Liquidity Coverage Ratio (LCR) generator."""

from datetime import date
from typing import List

import numpy as np

FUNDING_SOURCES = ["retail_deposits", "repo_secured", "corporate_operational", "unsecured_wholesale"]
MATURITY_BUCKETS = ["overnight", "7d", "30d", "90d", "1y+"]


def generate_treasury_positions(
    all_dates: List[date],
    entities: List[dict],
    rng: np.random.Generator,
    dataset_id: str,
) -> List[dict]:
    """
    Generates daily treasury positions ensuring baseline LCR ratio stays strictly above 100%.
    LCR = HQLA / Net 30-Day Outflows.
    """
    treasury_rows = []

    for ent in entities:
        ent_id = ent["id"]
        ccy = ent["currency"]

        # Base balances
        cash_base = 45000000.0 if ccy in ("USD", "EUR", "GBP") else 2500000000.0  # scaled for INR
        hqla_base = cash_base * 1.5

        for d in all_dates:
            d_str = d.isoformat()

            # Random daily liquidity movements (+/- 1.5%)
            daily_factor = 1.0 + float(rng.normal(0, 0.015))
            cash_bal = round(cash_base * daily_factor, 2)
            hqla_bal = round(hqla_base * (1.0 + float(rng.normal(0, 0.01))), 2)

            # Inflows and Outflows for 30d horizon
            outflows_30d = round(hqla_bal * float(rng.uniform(0.65, 0.80)), 2)
            # Net outflows capped so that HQLA / net_outflows >= 115% in baseline
            inflows_30d = round(outflows_30d * float(rng.uniform(0.20, 0.40)), 2)

            funding_source = str(rng.choice(FUNDING_SOURCES))
            funding_amt = round(cash_bal * float(rng.uniform(0.3, 0.6)), 2)
            maturity = str(rng.choice(MATURITY_BUCKETS))

            treasury_rows.append({
                "dataset_id": dataset_id,
                "as_of_date": d_str,
                "entity_id": ent_id,
                "currency": ccy,
                "cash_balance": cash_bal,
                "hqla": hqla_bal,
                "outflows_30d": outflows_30d,
                "inflows_30d": inflows_30d,
                "funding_source": funding_source,
                "funding_amount": funding_amt,
                "maturity_bucket": maturity,
            })

    return treasury_rows
