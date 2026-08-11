"""Monte Carlo pricing for European options under risk-neutral GBM."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real
from statistics import NormalDist

import numpy as np

from option_pricing_volatility.processes.gbm import sample_gbm_terminal


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    """A Monte Carlo price estimate and its sampling uncertainty."""

    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    n_paths: int
    seed: int


def mc_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    n_paths: int,
    option_type: str,
    dividend_yield: float = 0.0,
    *,
    seed: int,
    confidence_level: float = 0.95,
) -> MonteCarloResult:
    """Price a European call or put by exact-terminal GBM Monte Carlo.

    Time is measured in years; rates, dividend yield, and volatility are
    decimals. The standard error uses the discounted payoff sample standard
    deviation with ``ddof=1``. The two-sided confidence interval is an
    unclipped normal approximation at ``confidence_level``.
    """

    numeric_inputs = {
        "spot": spot,
        "strike": strike,
        "maturity": maturity,
        "rate": rate,
        "volatility": volatility,
        "dividend_yield": dividend_yield,
        "confidence_level": confidence_level,
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
    if strike <= 0:
        raise ValueError("strike must be greater than 0")
    if maturity < 0:
        raise ValueError("maturity must be greater than or equal to 0")
    if volatility < 0:
        raise ValueError("volatility must be greater than or equal to 0")
    if not isinstance(option_type, str) or option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if isinstance(n_paths, bool) or not isinstance(n_paths, Integral) or n_paths < 2:
        raise ValueError("n_paths must be an integer greater than or equal to 2")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1")

    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)
    confidence_level = float(confidence_level)
    n_paths = int(n_paths)
    seed = int(seed)

    if maturity == 0:
        payoff = spot - strike if option_type == "call" else strike - spot
        return _deterministic_result(max(payoff, 0.0), n_paths, seed)

    if volatility == 0:
        discounted_spot = spot * math.exp(-dividend_yield * maturity)
        discounted_strike = strike * math.exp(-rate * maturity)
        payoff = (
            discounted_spot - discounted_strike
            if option_type == "call"
            else discounted_strike - discounted_spot
        )
        return _deterministic_result(max(payoff, 0.0), n_paths, seed)

    rng = np.random.default_rng(seed)
    terminal_spots = sample_gbm_terminal(
        spot=spot,
        maturity=maturity,
        rate=rate,
        volatility=volatility,
        n_paths=n_paths,
        dividend_yield=dividend_yield,
        rng=rng,
    )
    if option_type == "call":
        payoffs = np.maximum(terminal_spots - strike, 0.0)
    else:
        payoffs = np.maximum(strike - terminal_spots, 0.0)

    discounted_payoffs = math.exp(-rate * maturity) * payoffs
    price = float(np.mean(discounted_payoffs))
    standard_error = float(
        np.std(discounted_payoffs, ddof=1) / math.sqrt(n_paths)
    )
    tail_probability = (1.0 - confidence_level) / 2.0
    critical_value = -NormalDist().inv_cdf(tail_probability)
    margin = critical_value * standard_error

    return MonteCarloResult(
        price=price,
        standard_error=standard_error,
        ci_low=price - margin,
        ci_high=price + margin,
        n_paths=n_paths,
        seed=seed,
    )


def _deterministic_result(price: float, n_paths: int, seed: int) -> MonteCarloResult:
    return MonteCarloResult(
        price=price,
        standard_error=0.0,
        ci_low=price,
        ci_high=price,
        n_paths=n_paths,
        seed=seed,
    )
