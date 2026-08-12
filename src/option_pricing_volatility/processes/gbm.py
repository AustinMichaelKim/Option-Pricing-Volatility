"""Exact terminal sampling for risk-neutral geometric Brownian motion."""

from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np
from numpy.typing import NDArray


"""
src/simulation/monte_carlo.py에서 호출되는 함수이다.
몬테카를로 샘플링을 위해서, GBM 확률과정에 기반한 주가 샘플링을 수행한다.
노트북에 설명된, 로그정규분포에서 샘플링을 수행한다.
"""
def sample_gbm_terminal(
        
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    n_paths: int, # 샘플링할 경로의 수이다. 즉, n_paths개의 주가 샘플링을 수행한다.
    dividend_yield: float = 0.0,
    *,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    """Sample terminal prices from the exact risk-neutral GBM distribution.

    Time is measured in years; rates, dividend yield, and volatility are
    decimals. The returned array has shape ``(n_paths,)`` and ``float64``
    dtype. ``rng`` must be an explicit ``numpy.random.Generator``; global
    random state is never used.
    """

    numeric_inputs = {
        "spot": spot,
        "maturity": maturity,
        "rate": rate,
        "volatility": volatility,
        "dividend_yield": dividend_yield,
    }

    """
    입력값 유효검사 단계
    """
    for name, value in numeric_inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be a finite real number")

    if spot <= 0:
        raise ValueError("spot must be greater than 0")
    if maturity < 0:
        raise ValueError("maturity must be greater than or equal to 0")
    if volatility < 0:
        raise ValueError("volatility must be greater than or equal to 0")
    if isinstance(n_paths, bool) or not isinstance(n_paths, Integral) or n_paths < 2:
        raise ValueError("n_paths must be an integer greater than or equal to 2")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")

    # 형변환
    spot = float(spot)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)
    n_paths = int(n_paths)

    # 경계조건
    if maturity == 0:
        return np.full(n_paths, spot, dtype=np.float64)

    drift = (rate - dividend_yield - 0.5 * volatility**2) * maturity
    if volatility == 0:
        terminal_spot = spot * math.exp(drift)
        return np.full(n_paths, terminal_spot, dtype=np.float64)

    """
    난수 샘플링 단계. 입력으로 받은 난수생성기 rng를 이용해서 샘플링한다.
    terminal_spots는 샘플링할 만기 주가이다.
    노트북에 설명된 공식 참조.
    """
    normal_samples = rng.standard_normal(n_paths)
    diffusion = volatility * math.sqrt(maturity) * normal_samples
    terminal_spots = spot * np.exp(drift + diffusion)
    return np.asarray(terminal_spots, dtype=np.float64)
