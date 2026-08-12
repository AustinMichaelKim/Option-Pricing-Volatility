from __future__ import annotations

import math

import pytest

from option_pricing_volatility.models.bsm import bsm_price
from option_pricing_volatility.volatility.implied_volatility import (
    implied_volatility,
)


PARAMETERS = {
    "spot": 100.0,
    "strike": 105.0,
    "maturity": 0.75,
    "rate": 0.03,
    "dividend_yield": 0.01,
}


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_known_volatility_is_recovered(option_type: str) -> None:
    original_volatility = 0.24
    market_price = bsm_price(
        **PARAMETERS,
        volatility=original_volatility,
        option_type=option_type,
    )

    result = implied_volatility(
        **PARAMETERS,
        market_price=market_price,
        option_type=option_type,
    )

    assert result.converged is True
    assert result.volatility == pytest.approx(original_volatility, abs=1e-9)


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_recovered_volatility_reprices_within_price_tolerance(
    option_type: str,
) -> None:
    price_tolerance = 1e-9
    market_price = bsm_price(
        **PARAMETERS,
        volatility=0.31,
        option_type=option_type,
    )

    result = implied_volatility(
        **PARAMETERS,
        market_price=market_price,
        option_type=option_type,
        price_tolerance=price_tolerance,
        volatility_tolerance=1e-14,
    )
    repriced = bsm_price(
        **PARAMETERS,
        volatility=result.volatility,
        option_type=option_type,
    )

    assert abs(repriced - market_price) <= price_tolerance
    assert result.repricing_error == pytest.approx(repriced - market_price)


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_zero_volatility_price_returns_zero_implied_volatility(
    option_type: str,
) -> None:
    market_price = bsm_price(
        **PARAMETERS,
        volatility=0.0,
        option_type=option_type,
    )

    result = implied_volatility(
        **PARAMETERS,
        market_price=market_price,
        option_type=option_type,
    )

    assert result.volatility == 0.0
    assert result.repricing_error == 0.0
    assert result.iterations == 0


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_market_price_outside_no_arbitrage_bounds_is_rejected(
    option_type: str,
) -> None:
    if option_type == "call":
        upper_bound = PARAMETERS["spot"] * math.exp(
            -PARAMETERS["dividend_yield"] * PARAMETERS["maturity"]
        )
    else:
        upper_bound = PARAMETERS["strike"] * math.exp(
            -PARAMETERS["rate"] * PARAMETERS["maturity"]
        )

    with pytest.raises(ValueError, match="no-arbitrage bounds"):
        implied_volatility(
            **PARAMETERS,
            market_price=upper_bound + 1.0,
            option_type=option_type,
        )


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_root_outside_volatility_bracket_is_rejected(option_type: str) -> None:
    market_price = bsm_price(
        **PARAMETERS,
        volatility=0.8,
        option_type=option_type,
    )

    with pytest.raises(ValueError, match="not attainable within volatility bracket"):
        implied_volatility(
            **PARAMETERS,
            market_price=market_price,
            option_type=option_type,
            volatility_upper=0.5,
        )


def test_no_arbitrage_bounds_are_not_extended_by_price_tolerance() -> None:
    lower_bound = max(
        0.0,
        PARAMETERS["strike"]
        * math.exp(-PARAMETERS["rate"] * PARAMETERS["maturity"])
        - PARAMETERS["spot"]
        * math.exp(-PARAMETERS["dividend_yield"] * PARAMETERS["maturity"]),
    )

    with pytest.raises(ValueError, match="no-arbitrage bounds"):
        implied_volatility(
            **PARAMETERS,
            market_price=lower_bound - 5e-9,
            option_type="put",
            price_tolerance=1e-8,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spot", 0.0),
        ("strike", -1.0),
        ("maturity", 0.0),
        ("market_price", math.nan),
        ("rate", math.inf),
        ("dividend_yield", "0.01"),
        ("option_type", "digital"),
        ("volatility_lower", -0.1),
        ("volatility_upper", 0.0),
        ("price_tolerance", 0.0),
        ("volatility_tolerance", 0.0),
        ("max_iterations", 0),
    ],
)
def test_invalid_inputs_raise_value_error(field: str, value: object) -> None:
    inputs: dict[str, object] = {
        **PARAMETERS,
        "market_price": 8.0,
        "option_type": "call",
        "volatility_lower": 1e-8,
        "volatility_upper": 5.0,
        "price_tolerance": 1e-8,
        "volatility_tolerance": 1e-12,
        "max_iterations": 200,
    }
    inputs[field] = value

    with pytest.raises(ValueError):
        implied_volatility(**inputs)  # type: ignore[arg-type]


def test_nonconvergence_raises_runtime_error() -> None:
    market_price = bsm_price(
        **PARAMETERS,
        volatility=0.37,
        option_type="call",
    )

    with pytest.raises(RuntimeError, match="did not converge"):
        implied_volatility(
            **PARAMETERS,
            market_price=market_price,
            option_type="call",
            price_tolerance=1e-15,
            volatility_tolerance=1e-15,
            max_iterations=1,
        )


def test_volatility_bracket_width_can_trigger_convergence() -> None:
    original_volatility = 0.23456789
    volatility_tolerance = 1e-4
    market_price = bsm_price(
        **PARAMETERS,
        volatility=original_volatility,
        option_type="call",
    )

    result = implied_volatility(
        **PARAMETERS,
        market_price=market_price,
        option_type="call",
        price_tolerance=1e-16,
        volatility_tolerance=volatility_tolerance,
    )
    repriced = bsm_price(
        **PARAMETERS,
        volatility=result.volatility,
        option_type="call",
    )

    assert result.converged is True
    assert abs(result.volatility - original_volatility) <= volatility_tolerance
    assert abs(result.repricing_error) > 1e-16
    assert result.repricing_error == pytest.approx(repriced - market_price)


def test_unusable_finite_volatility_bracket_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite BSM endpoint prices"):
        implied_volatility(
            **PARAMETERS,
            market_price=8.0,
            option_type="call",
            volatility_upper=1e308,
        )
