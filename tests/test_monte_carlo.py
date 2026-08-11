from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pytest

from option_pricing_volatility.processes.gbm import sample_gbm_terminal
from option_pricing_volatility.simulation import monte_carlo
from option_pricing_volatility.simulation.monte_carlo import mc_price


BASE_INPUTS = {
    "spot": 100.0,
    "strike": 100.0,
    "maturity": 1.0,
    "rate": 0.05,
    "volatility": 0.2,
    "n_paths": 10_000,
    "option_type": "call",
    "dividend_yield": 0.0,
    "seed": 42,
}


def test_terminal_gbm_sampling_is_reproducible_for_same_seed() -> None:
    first = sample_gbm_terminal(
        spot=100.0,
        maturity=1.0,
        rate=0.05,
        volatility=0.2,
        n_paths=8,
        rng=np.random.default_rng(1234),
    )
    second = sample_gbm_terminal(
        spot=100.0,
        maturity=1.0,
        rate=0.05,
        volatility=0.2,
        n_paths=8,
        rng=np.random.default_rng(1234),
    )

    np.testing.assert_array_equal(first, second)
    assert first.shape == (8,)
    assert first.dtype == np.float64


def test_terminal_gbm_deterministic_boundaries() -> None:
    zero_maturity = sample_gbm_terminal(
        spot=100.0,
        maturity=0.0,
        rate=0.05,
        volatility=0.2,
        n_paths=3,
        rng=np.random.default_rng(1),
    )
    zero_volatility = sample_gbm_terminal(
        spot=100.0,
        maturity=2.0,
        rate=0.05,
        volatility=0.0,
        n_paths=3,
        dividend_yield=0.01,
        rng=np.random.default_rng(1),
    )

    np.testing.assert_array_equal(zero_maturity, np.full(3, 100.0))
    np.testing.assert_allclose(zero_volatility, 100.0 * math.exp(0.04 * 2.0))


def test_mc_price_is_reproducible_for_same_seed() -> None:
    assert mc_price(**BASE_INPUTS) == mc_price(**BASE_INPUTS)


@pytest.mark.parametrize(
    ("option_type", "expected"),
    [("call", 5.0), ("put", 0.0)],
)
def test_zero_maturity_returns_intrinsic_value_with_no_sampling_error(
    option_type: str, expected: float
) -> None:
    result = mc_price(
        105.0,
        100.0,
        0.0,
        0.05,
        0.2,
        2,
        option_type,
        seed=7,
    )

    assert result.price == expected
    assert result.standard_error == 0.0
    assert result.ci_low == result.price == result.ci_high


@pytest.mark.parametrize("option_type", ["call", "put"])
def test_zero_volatility_returns_discounted_deterministic_payoff(
    option_type: str,
) -> None:
    spot = 100.0
    strike = 95.0
    maturity = 2.0
    rate = 0.03
    dividend_yield = 0.01
    result = mc_price(
        spot,
        strike,
        maturity,
        rate,
        0.0,
        2,
        option_type,
        dividend_yield,
        seed=7,
    )
    forward_value = spot * math.exp(-dividend_yield * maturity) - strike * math.exp(
        -rate * maturity
    )
    expected = max(forward_value if option_type == "call" else -forward_value, 0.0)

    assert result.price == pytest.approx(expected)
    assert result.standard_error == 0.0
    assert result.ci_low == result.price == result.ci_high


@pytest.mark.parametrize("n_paths", [1, 1.5, True])
def test_invalid_n_paths_raise_value_error(n_paths: object) -> None:
    inputs = dict(BASE_INPUTS)
    inputs["n_paths"] = n_paths

    with pytest.raises(ValueError, match="n_paths"):
        mc_price(**inputs)  # type: ignore[arg-type]


def test_invalid_option_type_raises_value_error() -> None:
    inputs = dict(BASE_INPUTS)
    inputs["option_type"] = "digital"

    with pytest.raises(ValueError, match="option_type"):
        mc_price(**inputs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spot", math.nan),
        ("strike", math.inf),
        ("maturity", -0.1),
        ("volatility", -0.1),
        ("rate", math.inf),
        ("dividend_yield", math.nan),
        ("confidence_level", 1.0),
        ("seed", -1),
    ],
)
def test_invalid_numeric_inputs_raise_value_error(field: str, value: object) -> None:
    inputs = dict(BASE_INPUTS)
    inputs[field] = value

    with pytest.raises(ValueError):
        mc_price(**inputs)  # type: ignore[arg-type]


def test_default_confidence_interval_uses_normal_approximation() -> None:
    result = mc_price(**BASE_INPUTS)
    critical_value = NormalDist().inv_cdf(0.975)
    margin = critical_value * result.standard_error

    assert result.ci_low == pytest.approx(result.price - margin)
    assert result.ci_high == pytest.approx(result.price + margin)


def test_standard_error_uses_discounted_payoff_sample_std(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        monte_carlo,
        "sample_gbm_terminal",
        lambda **_: np.array([80.0, 120.0]),
    )

    result = mc_price(100.0, 100.0, 1.0, 0.0, 0.2, 2, "call", seed=1)

    assert result.price == 10.0
    assert result.standard_error == 10.0


@pytest.mark.parametrize(
    ("option_type", "bsm_benchmark"),
    [
        ("call", 10.450583572185565),
        ("put", 5.573526022256971),
    ],
)
def test_mc_price_is_statistically_consistent_with_bsm_benchmark(
    option_type: str, bsm_benchmark: float
) -> None:
    result = mc_price(
        spot=100.0,
        strike=100.0,
        maturity=1.0,
        rate=0.05,
        volatility=0.2,
        n_paths=50_000,
        option_type=option_type,
        seed=42,
    )

    # A four-standard-error band has about 99.994% normal-approximation coverage.
    assert abs(result.price - bsm_benchmark) <= 4.0 * result.standard_error
