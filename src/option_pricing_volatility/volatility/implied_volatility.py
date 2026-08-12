"""Scalar implied volatility for European options under BSM."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

from option_pricing_volatility.models.bsm import bsm_price


@dataclass(frozen=True, slots=True)
class ImpliedVolatilityResult:
    """A converged BSM implied-volatility estimate and its diagnostics."""

    volatility: float
    repricing_error: float
    iterations: int
    converged: bool


def implied_volatility(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    market_price: float,
    option_type: str,
    dividend_yield: float = 0.0,
    *,
    volatility_lower: float = 1e-8,
    volatility_upper: float = 5.0,
    price_tolerance: float = 1e-8,
    volatility_tolerance: float = 1e-12,
    max_iterations: int = 200,
) -> ImpliedVolatilityResult:
    """Recover scalar BSM implied volatility with bisection.

    Prices and strikes share one unit. Maturity is in ACT/365F years; the
    continuously compounded rate and dividend yield and annualized volatility
    are decimals. The default volatility bracket is ``[1e-8, 5.0]``.

    ``ValueError`` is raised for invalid inputs, a target outside discounted
    European no-arbitrage bounds, or a target not attainable inside the
    volatility bracket. ``RuntimeError`` is raised if bisection exhausts
    ``max_iterations``. A target matching the zero-volatility BSM price within
    ``price_tolerance`` returns volatility ``0.0`` without iteration.
    Otherwise, convergence means either the absolute repricing error is within
    ``price_tolerance`` or the final bracket width is within
    ``volatility_tolerance``. ``repricing_error`` is signed as BSM price minus
    market price.
    """

    numeric_inputs = {
        "spot": spot,
        "strike": strike,
        "maturity": maturity,
        "rate": rate,
        "market_price": market_price,
        "dividend_yield": dividend_yield,
        "volatility_lower": volatility_lower,
        "volatility_upper": volatility_upper,
        "price_tolerance": price_tolerance,
        "volatility_tolerance": volatility_tolerance,
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
    if maturity <= 0:
        raise ValueError("maturity must be greater than 0")
    if not isinstance(option_type, str) or option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if volatility_lower < 0:
        raise ValueError("volatility_lower must be greater than or equal to 0")
    if volatility_upper <= volatility_lower:
        raise ValueError("volatility_upper must be greater than volatility_lower")
    if price_tolerance <= 0:
        raise ValueError("price_tolerance must be greater than 0")
    if volatility_tolerance <= 0:
        raise ValueError("volatility_tolerance must be greater than 0")
    if (
        isinstance(max_iterations, bool)
        or not isinstance(max_iterations, Integral)
        or max_iterations < 1
    ):
        raise ValueError("max_iterations must be an integer greater than or equal to 1")

    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    market_price = float(market_price)
    dividend_yield = float(dividend_yield)
    volatility_lower = float(volatility_lower)
    volatility_upper = float(volatility_upper)
    price_tolerance = float(price_tolerance)
    volatility_tolerance = float(volatility_tolerance)
    max_iterations = int(max_iterations)

    try:
        discounted_spot = spot * math.exp(-dividend_yield * maturity)
        discounted_strike = strike * math.exp(-rate * maturity)
    except OverflowError as exc:
        raise ValueError("discounted spot and strike must be finite") from exc
    if not math.isfinite(discounted_spot) or not math.isfinite(discounted_strike):
        raise ValueError("discounted spot and strike must be finite")

    if option_type == "call":
        arbitrage_lower = max(0.0, discounted_spot - discounted_strike)
        arbitrage_upper = discounted_spot
    else:
        arbitrage_lower = max(0.0, discounted_strike - discounted_spot)
        arbitrage_upper = discounted_strike

    if market_price < arbitrage_lower or market_price > arbitrage_upper:
        raise ValueError(
            "market_price must lie within the discounted no-arbitrage bounds "
            f"[{arbitrage_lower}, {arbitrage_upper}] for a {option_type}; "
            f"got {market_price}"
        )

    zero_price = bsm_price(
        spot,
        strike,
        maturity,
        rate,
        0.0,
        option_type,
        dividend_yield,
    )
    zero_error = zero_price - market_price
    if abs(zero_error) <= price_tolerance:
        return ImpliedVolatilityResult(
            volatility=0.0,
            repricing_error=zero_error,
            iterations=0,
            converged=True,
        )

    try:
        lower_price = bsm_price(
            spot,
            strike,
            maturity,
            rate,
            volatility_lower,
            option_type,
            dividend_yield,
        )
        upper_price = bsm_price(
            spot,
            strike,
            maturity,
            rate,
            volatility_upper,
            option_type,
            dividend_yield,
        )
    except OverflowError as exc:
        raise ValueError(
            "volatility bracket must produce finite BSM endpoint prices"
        ) from exc
    lower_error = lower_price - market_price
    upper_error = upper_price - market_price

    if market_price < lower_price or market_price > upper_price:
        raise ValueError(
            "market_price is not attainable within volatility bracket "
            f"[{volatility_lower}, {volatility_upper}]; BSM price range is "
            f"[{lower_price}, {upper_price}], got {market_price}"
        )

    if abs(lower_error) <= price_tolerance:
        return ImpliedVolatilityResult(
            volatility=volatility_lower,
            repricing_error=lower_error,
            iterations=0,
            converged=True,
        )
    if abs(upper_error) <= price_tolerance:
        return ImpliedVolatilityResult(
            volatility=volatility_upper,
            repricing_error=upper_error,
            iterations=0,
            converged=True,
        )

    lower = volatility_lower
    upper = volatility_upper
    latest_error = lower_error

    for iteration in range(1, max_iterations + 1):
        midpoint = 0.5 * (lower + upper)
        midpoint_price = bsm_price(
            spot,
            strike,
            maturity,
            rate,
            midpoint,
            option_type,
            dividend_yield,
        )
        latest_error = midpoint_price - market_price

        if abs(latest_error) <= price_tolerance:
            return ImpliedVolatilityResult(
                volatility=midpoint,
                repricing_error=latest_error,
                iterations=iteration,
                converged=True,
            )

        if latest_error > 0.0:
            upper = midpoint
        else:
            lower = midpoint

        if upper - lower <= volatility_tolerance:
            estimate = 0.5 * (lower + upper)
            estimate_price = bsm_price(
                spot,
                strike,
                maturity,
                rate,
                estimate,
                option_type,
                dividend_yield,
            )
            return ImpliedVolatilityResult(
                volatility=estimate,
                repricing_error=estimate_price - market_price,
                iterations=iteration,
                converged=True,
            )

    raise RuntimeError(
        "implied volatility did not converge within "
        f"{max_iterations} iterations; last absolute pricing error was "
        f"{abs(latest_error)} and bracket width was {upper - lower}"
    )
