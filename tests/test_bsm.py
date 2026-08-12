from __future__ import annotations

import math

import pytest

from option_pricing_volatility.models.bsm import bsm_price


@pytest.mark.parametrize(
    ("option_type", "expected"),
    [
        ("call", 10.450583572185565),
        ("put", 5.573526022256971),
    ],
)
def test_standard_bsm_benchmark(option_type: str, expected: float) -> None:
    price = bsm_price(100.0, 100.0, 1.0, 0.05, 0.2, option_type)

    assert price == pytest.approx(expected)


def test_put_call_parity_with_dividend_yield() -> None:
    spot = 100.0
    strike = 105.0
    maturity = 1.25
    rate = 0.04
    volatility = 0.25
    dividend_yield = 0.015

    call = bsm_price(
        spot, strike, maturity, rate, volatility, "call", dividend_yield
    )
    put = bsm_price(
        spot, strike, maturity, rate, volatility, "put", dividend_yield
    )
    parity_value = spot * math.exp(-dividend_yield * maturity) - strike * math.exp(
        -rate * maturity
    )

    assert call - put == pytest.approx(parity_value)


@pytest.mark.parametrize(
    ("option_type", "expected"),
    [("call", 5.0), ("put", 0.0)],
)
def test_zero_maturity_returns_intrinsic_value(
    option_type: str, expected: float
) -> None:
    assert bsm_price(105.0, 100.0, 0.0, 0.05, 0.2, option_type) == expected


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_zero_volatility_returns_discounted_deterministic_payoff(
    option_type: str,
) -> None:
    spot = 100.0
    strike = 95.0
    maturity = 2.0
    rate = 0.03
    dividend_yield = 0.01
    forward_value = spot * math.exp(-dividend_yield * maturity) - strike * math.exp(
        -rate * maturity
    )
    expected = max(forward_value if option_type == "call" else -forward_value, 0.0)

    price = bsm_price(
        spot, strike, maturity, rate, 0.0, option_type, dividend_yield
    )

    assert price == pytest.approx(expected)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spot", 0.0),
        ("strike", -1.0),
        ("maturity", -0.1),
        ("volatility", -0.1),
        ("rate", math.inf),
        ("dividend_yield", math.nan),
        ("option_type", "digital"),
    ],
)
def test_invalid_inputs_raise_value_error(field: str, value: object) -> None:
    inputs: dict[str, object] = {
        "spot": 100.0,
        "strike": 100.0,
        "maturity": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
        "dividend_yield": 0.0,
    }
    inputs[field] = value

    with pytest.raises(ValueError):
        bsm_price(**inputs)  # type: ignore[arg-type]
