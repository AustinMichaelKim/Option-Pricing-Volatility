"""Black-Scholes-Merton pricing for European options."""

from __future__ import annotations

import math
from numbers import Real
from statistics import NormalDist


def bsm_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    option_type: str,
    dividend_yield: float = 0.0,
) -> float:
    """Price a scalar European call or put with the BSM closed-form solution.

    Prices share one currency unit, maturity is in years, and the continuously
    compounded rate and dividend yield and annualized volatility are decimals.
    Invalid financial domains raise ``ValueError``; the returned option price
    is a ``float``.
    """

    numeric_inputs = {
        "spot": spot,
        "strike": strike,
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
    if strike <= 0:
        raise ValueError("strike must be greater than 0")
    if maturity < 0:
        raise ValueError("maturity must be greater than or equal to 0")
    if volatility < 0:
        raise ValueError("volatility must be greater than or equal to 0")
    if not isinstance(option_type, str) or option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)

    if maturity == 0:
        payoff = spot - strike if option_type == "call" else strike - spot
        return float(max(payoff, 0.0))

    discounted_spot = spot * math.exp(-dividend_yield * maturity)
    discounted_strike = strike * math.exp(-rate * maturity)
    if volatility == 0:
        payoff = (
            discounted_spot - discounted_strike
            if option_type == "call"
            else discounted_strike - discounted_spot
        )
        return float(max(payoff, 0.0))

    volatility_time = volatility * math.sqrt(maturity)
    d1 = (
        math.log(spot / strike)
        + (rate - dividend_yield + 0.5 * volatility**2) * maturity
    ) / volatility_time
    d2 = d1 - volatility_time
    normal = NormalDist()

    if option_type == "call":
        price = discounted_spot * normal.cdf(d1) - discounted_strike * normal.cdf(d2)
    else:
        price = discounted_strike * normal.cdf(-d2) - discounted_spot * normal.cdf(-d1)

    return float(price)
