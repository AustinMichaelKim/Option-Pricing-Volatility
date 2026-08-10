from __future__ import annotations

import math

import pytest

from option_pricing_volatility.models.binomial import crr_price


@pytest.mark.parametrize(
    ("option_type", "expected"),
    [("call", 40.0), ("put", 20.0)],
)
def test_one_step_prices_are_hand_checkable(option_type: str, expected: float) -> None:
    price = crr_price(
        spot=100.0,
        strike=100.0,
        maturity=1.0,
        rate=math.log(1.25),
        volatility=math.log(2.0),
        steps=1,
        option_type=option_type,
    )

    assert price == pytest.approx(expected)


@pytest.mark.parametrize(
    ("option_type", "expected"),
    [("call", 5.0), ("put", 0.0)],
)
def test_zero_maturity_returns_intrinsic_value(
    option_type: str, expected: float
) -> None:
    price = crr_price(105.0, 100.0, 0.0, 0.05, 0.2, 0, option_type)

    assert price == expected


def test_zero_volatility_returns_discounted_deterministic_payoff() -> None:
    spot = 100.0
    strike = 95.0
    maturity = 2.0
    rate = 0.03
    dividend_yield = 0.01

    call = crr_price(
        spot,
        strike,
        maturity,
        rate,
        0.0,
        8,
        "call",
        dividend_yield,
    )
    put = crr_price(
        spot,
        strike,
        maturity,
        rate,
        0.0,
        8,
        "put",
        dividend_yield,
    )
    forward_value = spot * math.exp(-dividend_yield * maturity) - strike * math.exp(
        -rate * maturity
    )

    assert call == pytest.approx(max(forward_value, 0.0))
    assert put == pytest.approx(max(-forward_value, 0.0))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spot", 0.0),
        ("strike", -1.0),
        ("maturity", -0.1),
        ("volatility", -0.1),
        ("rate", math.inf),
        ("dividend_yield", math.nan),
        ("steps", 0),
        ("steps", 1.5),
        ("option_type", "digital"),
    ],
)
def test_invalid_basic_inputs_raise_value_error(field: str, value: object) -> None:
    inputs: dict[str, object] = {
        "spot": 100.0,
        "strike": 100.0,
        "maturity": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "steps": 2,
        "option_type": "call",
        "dividend_yield": 0.0,
    }
    inputs[field] = value

    with pytest.raises(ValueError):
        crr_price(**inputs)  # type: ignore[arg-type]


def test_probability_outside_unit_interval_raises_value_error() -> None:
    with pytest.raises(ValueError, match="risk-neutral probability"):
        crr_price(100.0, 100.0, 1.0, 1.0, 0.1, 1, "call")


def test_put_call_parity() -> None:
    spot = 100.0
    strike = 105.0
    maturity = 1.25
    rate = 0.04
    dividend_yield = 0.015
    volatility = 0.25
    steps = 64

    call = crr_price(
        spot,
        strike,
        maturity,
        rate,
        volatility,
        steps,
        "call",
        dividend_yield,
    )
    put = crr_price(
        spot,
        strike,
        maturity,
        rate,
        volatility,
        steps,
        "put",
        dividend_yield,
    )
    parity_value = spot * math.exp(-dividend_yield * maturity) - strike * math.exp(
        -rate * maturity
    )

    assert call - put == pytest.approx(parity_value, abs=1e-10)


def test_crr_call_converges_to_standard_bsm_benchmark() -> None:
    spot = 100.0
    bsm_call_benchmark = 10.450583572185565

    crr_call = crr_price(spot, 100.0, 1.0, 0.05, 0.2, 4096, "call")

    assert abs(crr_call - bsm_call_benchmark) / spot < 1e-4
