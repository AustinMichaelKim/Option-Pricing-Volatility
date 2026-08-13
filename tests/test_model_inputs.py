from __future__ import annotations

import math

import pandas as pd
import pytest

from option_pricing_volatility.volatility import (
    estimate_forward_and_dividend_yield,
)


def test_forward_is_pair_median_and_dividend_yield_matches_parity() -> None:
    spot = 100.0
    maturity = 0.25
    rate = 0.04
    expected_forward = 102.0
    growth_factor = math.exp(rate * maturity)

    rows = []
    for strike, forward_candidate, put_mid in (
        (90.0, 101.0, 2.0),
        (100.0, 102.0, 5.0),
        (110.0, 120.0, 12.0),
    ):
        call_mid = put_mid + (forward_candidate - strike) / growth_factor
        rows.extend(
            [
                {
                    "strike": strike,
                    "option_type": "call",
                    "mid": call_mid,
                    "spot": spot,
                    "T": maturity,
                },
                {
                    "strike": strike,
                    "option_type": "put",
                    "mid": put_mid,
                    "spot": spot,
                    "T": maturity,
                },
            ]
        )
    rows.extend(
        [
            {
                "strike": 95.0,
                "option_type": "call",
                "mid": 8.0,
                "spot": spot,
                "T": maturity,
            },
            {
                "strike": 105.0,
                "option_type": "call",
                "mid": math.nan,
                "spot": spot,
                "T": maturity,
            },
            {
                "strike": 105.0,
                "option_type": "put",
                "mid": 8.0,
                "spot": spot,
                "T": maturity,
            },
        ]
    )

    result = estimate_forward_and_dividend_yield(pd.DataFrame(rows), rate)

    expected_dividend_yield = rate - math.log(expected_forward / spot) / maturity
    assert result.forward == pytest.approx(expected_forward)
    assert result.dividend_yield == pytest.approx(expected_dividend_yield)


def test_no_finite_same_strike_pair_is_rejected() -> None:
    options = pd.DataFrame(
        [
            {
                "strike": 100.0,
                "option_type": "call",
                "mid": 5.0,
                "spot": 100.0,
                "T": 0.25,
            },
            {
                "strike": 100.0,
                "option_type": "put",
                "mid": math.nan,
                "spot": 100.0,
                "T": 0.25,
            },
        ]
    )

    with pytest.raises(ValueError, match="finite same-strike call/put pair"):
        estimate_forward_and_dividend_yield(options, 0.04)


@pytest.mark.parametrize(
    ("column", "different_value", "message"),
    [
        ("spot", 101.0, "one spot value"),
        ("T", 0.5, "one maturity"),
    ],
)
def test_options_must_share_snapshot_inputs(
    column: str,
    different_value: float,
    message: str,
) -> None:
    options = pd.DataFrame(
        [
            {
                "strike": 100.0,
                "option_type": "call",
                "mid": 6.0,
                "spot": 100.0,
                "T": 0.25,
            },
            {
                "strike": 100.0,
                "option_type": "put",
                "mid": 4.0,
                "spot": 100.0,
                "T": 0.25,
            },
            {
                "strike": 110.0,
                "option_type": "call",
                "mid": 2.0,
                "spot": 100.0,
                "T": 0.25,
            },
        ]
    )
    options.loc[2, column] = different_value

    with pytest.raises(ValueError, match=message):
        estimate_forward_and_dividend_yield(options, 0.04)
