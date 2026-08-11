"""Exact terminal sampling for risk-neutral geometric Brownian motion."""

from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np
from numpy.typing import NDArray


def sample_gbm_terminal(
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    n_paths: int,
    dividend_yield: float = 0.0,
    *,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Sample terminal prices from the exact risk-neutral GBM distribution.

    Time is measured in years; rates, dividend yield, and volatility are
    decimals. The returned array has shape ``(n_paths,)`` and ``float64``
    dtype. ``rng`` must be an explicit ``numpy.random.Generator``; global
    random state is never used.
    """

    numeric_inputs = {
        "spot": spot,
        "maturity": maturity,
        "rate": rate,
        "volatility": volatility,
        "dividend_yield": dividend_yield,
    }
    for name, value in numeric_inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be a finite real number")

    if spot <= 0:
        raise ValueError("spot must be greater than 0")
    if maturity < 0:
        raise ValueError("maturity must be greater than or equal to 0")
    if volatility < 0:
        raise ValueError("volatility must be greater than or equal to 0")
    if isinstance(n_paths, bool) or not isinstance(n_paths, Integral) or n_paths < 2:
        raise ValueError("n_paths must be an integer greater than or equal to 2")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")

    spot = float(spot)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)
    n_paths = int(n_paths)

    if maturity == 0:
        return np.full(n_paths, spot, dtype=np.float64)

    drift = (rate - dividend_yield - 0.5 * volatility**2) * maturity
    if volatility == 0:
        terminal_spot = spot * math.exp(drift)
        return np.full(n_paths, terminal_spot, dtype=np.float64)

    normal_samples = rng.standard_normal(n_paths)
    diffusion = volatility * math.sqrt(maturity) * normal_samples
    terminal_spots = spot * np.exp(drift + diffusion)
    return np.asarray(terminal_spots, dtype=np.float64)
