"""Cox-Ross-Rubinstein pricing for European options."""

from __future__ import annotations

import math
from numbers import Integral, Real


def crr_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
    option_type: str,
    dividend_yield: float = 0.0,
) -> float:
    """Price a European call or put with a scalar CRR binomial tree.

    Time is measured in years; rates, dividend yield, and volatility are
    decimals. Invalid domains or a risk-neutral probability outside ``[0, 1]``
    raise ``ValueError``.
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
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)

    if maturity == 0:
        payoff = spot - strike if option_type == "call" else strike - spot
        return max(payoff, 0.0)

    if isinstance(steps, bool) or not isinstance(steps, Integral) or steps < 1:
        raise ValueError(
            "steps must be an integer greater than or equal to 1 when maturity > 0"
        )
    steps = int(steps)

    if volatility == 0:
        discounted_spot = spot * math.exp(-dividend_yield * maturity)
        discounted_strike = strike * math.exp(-rate * maturity)
        payoff = (
            discounted_spot - discounted_strike
            if option_type == "call"
            else discounted_strike - discounted_spot
        )
        return max(payoff, 0.0)

    dt = maturity / steps
    up = math.exp(volatility * math.sqrt(dt))
    down = 1.0 / up
    probability = (math.exp((rate - dividend_yield) * dt) - down) / (up - down)
    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            f"risk-neutral probability must be in [0, 1]; got {probability}"
        )

    discount = math.exp(-rate * dt)
    terminal_spot = spot * down**steps
    node_ratio = up / down
    values: list[float] = []
    for _ in range(steps + 1):
        payoff = (
            terminal_spot - strike
            if option_type == "call"
            else strike - terminal_spot
        )
        values.append(max(payoff, 0.0))
        terminal_spot *= node_ratio

    down_probability = 1.0 - probability
    for nodes in range(steps, 0, -1):
        for node in range(nodes):
            values[node] = discount * (
                down_probability * values[node] + probability * values[node + 1]
            )

    return float(values[0])
