"""Foreign exchange rate matrix generator with daily stochastic drift."""

from datetime import date
from typing import Dict, List, Tuple

import numpy as np

BASE_RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.0850,
    "GBP": 1.2820,
    "CHF": 1.1350,  # 1 CHF = ~1.135 USD (or USD/CHF ~ 0.88)
    "INR": 0.0116,  # 1 INR = ~0.0116 USD (or USD/INR ~ 86.2)
}


def generate_fx_rates(
    all_dates: List[date],
    currencies: List[str],
    rng: np.random.Generator,
    dataset_id: str,
) -> Tuple[List[dict], Dict[Tuple[str, str, str], float]]:
    """
    Generates daily FX rates with stochastic geometric drift.
    Returns:
        (fx_rows: List[dict] for DB, lookup_cache: Dict[(date_str, from_ccy, to_ccy), rate])
    """
    # Initialize base rates
    current_rates = {ccy: BASE_RATES_TO_USD.get(ccy, 1.0) for ccy in currencies}
    daily_vol = 0.003  # ~0.3% daily volatility

    fx_rows = []
    lookup_cache = {}

    for d in all_dates:
        d_str = d.isoformat()

        # Update rates with daily drift (excluding USD which is base 1.0)
        for ccy in currencies:
            if ccy != "USD":
                drift = rng.normal(0, daily_vol)
                current_rates[ccy] = round(current_rates[ccy] * (1.0 + drift), 6)

        # Cross rates between all pairs
        for from_ccy in currencies:
            for to_ccy in currencies:
                if from_ccy == to_ccy:
                    rate = 1.0
                else:
                    # from_ccy to USD / to_ccy to USD
                    rate = round(current_rates[from_ccy] / current_rates[to_ccy], 6)

                lookup_cache[(d_str, from_ccy, to_ccy)] = rate
                fx_rows.append({
                    "dataset_id": dataset_id,
                    "date": d_str,
                    "from_ccy": from_ccy,
                    "to_ccy": to_ccy,
                    "rate": rate,
                })

    return fx_rows, lookup_cache
