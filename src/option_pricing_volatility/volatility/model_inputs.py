"""Forward and dividend-yield inputs inferred from option midpoints."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real

import numpy as np
import pandas as pd


"""
본 모듈에서는 주어진 옵션데이터와 무위험금리등의 정보를 통해서, 배당수익률과 forward 가격을 산출하는 함수를 구현한다.
"""


@dataclass(frozen=True, slots=True)
class ForwardDividendEstimate:
    """One representative forward and implied continuous dividend yield."""

    forward: float
    dividend_yield: float


def estimate_forward_and_dividend_yield(
    options: pd.DataFrame,
    risk_free_rate: float,
) -> ForwardDividendEstimate:
    """Estimate one forward and dividend yield for a single option expiry.

    Same-strike call and put midpoints produce forward candidates via put-call
    parity, ``K + exp(rT) * (C - P)``. The representative forward is their
    median, and the continuously compounded annual dividend yield is
    ``r - log(F / S) / T``.
    """

    required_columns = {"mid", "spot", "T", "strike", "option_type"}
    missing_columns = sorted(required_columns.difference(options.columns))
    if missing_columns:
        raise ValueError(f"options is missing required columns: {missing_columns}")
    if (
        isinstance(risk_free_rate, bool)
        or not isinstance(risk_free_rate, Real)
        or not math.isfinite(risk_free_rate)
    ):
        raise ValueError("risk_free_rate must be a finite real number")

    numeric_columns = ["strike", "mid", "spot", "T"]
    eligible = options.loc[:, [*numeric_columns, "option_type"]].copy()
    eligible[numeric_columns] = eligible[numeric_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )
    snapshot_rows = eligible.loc[
        eligible["option_type"].isin({"call", "put"})
        & np.isfinite(eligible[["spot", "T"]]).all(axis=1)
        & (eligible["spot"] > 0.0)
        & (eligible["T"] > 0.0)
    ]
    if snapshot_rows["spot"].nunique() != 1:
        raise ValueError("options must share one spot value")
    if snapshot_rows["T"].nunique() != 1:
        raise ValueError("options must share one maturity")

    spot = float(snapshot_rows["spot"].iloc[0])
    maturity = float(snapshot_rows["T"].iloc[0])
    finite_rows = np.isfinite(eligible[numeric_columns]).all(axis=1)
    eligible = eligible.loc[
        finite_rows
        & eligible["option_type"].isin({"call", "put"})
        & (eligible["strike"] > 0.0)
        & (eligible["spot"] > 0.0)
        & (eligible["T"] > 0.0)
    ]

    if eligible.duplicated(["strike", "option_type"]).any():
        raise ValueError("options must contain at most one call and put per strike")

    calls = eligible.loc[
        eligible["option_type"].eq("call"),
        ["strike", "mid"],
    ].rename(columns={"mid": "call_mid"})
    puts = eligible.loc[
        eligible["option_type"].eq("put"),
        ["strike", "mid"],
    ].rename(columns={"mid": "put_mid"})
    pairs = calls.merge(puts, on="strike", how="inner", validate="one_to_one")
    if pairs.empty:
        raise ValueError(
            "options must contain at least one finite same-strike call/put pair"
        )

    risk_free_rate = float(risk_free_rate)
    try:
        growth_factor = math.exp(risk_free_rate * maturity)
    except OverflowError as exc:
        raise ValueError(
            "risk_free_rate and T must produce a finite growth factor"
        ) from exc
    if not math.isfinite(growth_factor):
        raise ValueError("risk_free_rate and T must produce a finite growth factor")

    forward_candidates = (
        pairs["strike"].to_numpy()
        + growth_factor
        * (pairs["call_mid"].to_numpy() - pairs["put_mid"].to_numpy())
    )
    forward_candidates = forward_candidates[np.isfinite(forward_candidates)]
    if forward_candidates.size == 0:
        raise ValueError("put-call parity produced no finite forward candidates")

    forward = float(np.median(forward_candidates))
    if forward <= 0.0:
        raise ValueError("median put-call parity forward must be greater than 0")

    dividend_yield = risk_free_rate - math.log(forward / spot) / maturity
    if not math.isfinite(dividend_yield):
        raise ValueError("implied dividend_yield must be finite")

    return ForwardDividendEstimate(
        forward=forward,
        dividend_yield=dividend_yield,
    )
