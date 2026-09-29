"""Benford-compliant and log-normal amount sampling utilities."""

import math
from typing import List

import numpy as np

# Theoretical Benford leading digit probabilities P(d) = log10(1 + 1/d)
BENFORD_PROBABILITIES = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}


def sample_lognormal_amount(
    rng: np.random.Generator,
    mean_log: float = 8.5,    # exp(8.5) ~= $4,900
    sigma: float = 1.6,       # wide dispersion
    min_amount: float = 50.0,
    max_amount: float = 2500000.0,
) -> float:
    """
    Samples an amount from a log-normal distribution.
    Naturally produces leading digits that conform closely to Benford's Law.
    """
    val = float(rng.lognormal(mean=mean_log, sigma=sigma))
    val = max(min_amount, min(val, max_amount))
    return round(val, 2)


def get_leading_digit(amount: float) -> int:
    """Extracts the first non-zero digit of an amount."""
    amt_str = f"{abs(amount):.6f}".lstrip("0").replace(".", "")
    return int(amt_str[0]) if amt_str else 1


def calculate_benford_distribution(amounts: List[float]) -> dict:
    """Calculates observed leading digit frequencies and MAD from theoretical Benford."""
    counts = {d: 0 for d in range(1, 10)}
    total = 0
    for a in amounts:
        if abs(a) > 0.001:
            d = get_leading_digit(a)
            if 1 <= d <= 9:
                counts[d] += 1
                total += 1

    if total == 0:
        return {"observed": {d: 0.0 for d in range(1, 10)}, "mad": 0.0}

    observed = {d: counts[d] / total for d in range(1, 10)}
    # Mean Absolute Deviation (MAD)
    mad = float(np.mean([abs(observed[d] - BENFORD_PROBABILITIES[d]) for d in range(1, 10)]))

    return {
        "observed": observed,
        "theoretical": BENFORD_PROBABILITIES,
        "mad": round(mad, 5),
        "total_samples": total,
    }
