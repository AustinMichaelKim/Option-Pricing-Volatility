"""Monte Carlo pricing for European options under risk-neutral GBM."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real
from statistics import NormalDist

import numpy as np

from option_pricing_volatility.processes.gbm import sample_gbm_terminal


"""
몬테카를로 샘플링 결과를 저장하는 객체를 정의한다. 
sample_gbm_terminal 함수에서 받아온 주가 샘플링 결과를 받아오고,
이후 이 값을 이용, 옵션가격 통계데이터를 추출한다.
옵션가격은 샘플링 결과이므로, 여러 통계적 지표를 함께 제공한다.
따라서, class로 정의하는것이 적합.
"""
@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    """A Monte Carlo price estimate and its sampling uncertainty."""

    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    n_paths: int
    seed: int


"""
몬테카를로를 이용하여 옵션가격에 대한 객체를 생성하는 메인 함수이다.
"""
def mc_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    n_paths: int,
    option_type: str,
    dividend_yield: float = 0.0,
    *,
    seed: int,
    confidence_level: float = 0.95,
) -> MonteCarloResult:
    """Price a European call or put by exact-terminal GBM Monte Carlo.

    Time is measured in years; rates, dividend yield, and volatility are
    decimals. The standard error uses the discounted payoff sample standard
    deviation with ``ddof=1``. The two-sided confidence interval is an
    unclipped normal approximation at ``confidence_level``.
    """

    numeric_inputs = {
        "spot": spot,
        "strike": strike,
        "maturity": maturity,
        "rate": rate,
        "volatility": volatility,
        "dividend_yield": dividend_yield,
        "confidence_level": confidence_level,
    }

    """
    이 부분은 Binomial Tree와 동일하게, 입력값에 대한 validation을 수행한다.
    값들이 유한한 실수 + 유효한 부호범위등을 확인한다.
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
    if strike <= 0:
        raise ValueError("strike must be greater than 0")
    if maturity < 0:
        raise ValueError("maturity must be greater than or equal to 0")
    if volatility < 0:
        raise ValueError("volatility must be greater than or equal to 0")
    if not isinstance(option_type, str) or option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if isinstance(n_paths, bool) or not isinstance(n_paths, Integral) or n_paths < 2:
        raise ValueError("n_paths must be an integer greater than or equal to 2")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1")

    # 데이터 형변환.
    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)
    confidence_level = float(confidence_level)
    n_paths = int(n_paths)
    seed = int(seed)

    # 경계조건 계산한다. 만기0 이랑 변동성0인 경우는 하나로 정해진다.
    # 불필요한 샘플링을 제한한다.
    if maturity == 0:
        payoff = spot - strike if option_type == "call" else strike - spot
        return _deterministic_result(max(payoff, 0.0), n_paths, seed)

    if volatility == 0:
        discounted_spot = spot * math.exp(-dividend_yield * maturity)
        discounted_strike = strike * math.exp(-rate * maturity)
        payoff = (
            discounted_spot - discounted_strike
            if option_type == "call"
            else discounted_strike - discounted_spot
        )
        return _deterministic_result(max(payoff, 0.0), n_paths, seed)

    """
    랜덤샘플링, 몬테카를로 설정단계.
    난수시드 설정이후,  src/processes/gbm.py에서 주가 샘플링 함수를 호출.
    
    리턴값은 n_paths개의 샘플링된 만기 주가 NDArray이다.
    이후, 옵션타입에 따라 payoffs를 계산한다.
    """
    rng = np.random.default_rng(seed)
    terminal_spots = sample_gbm_terminal(
        spot=spot,
        maturity=maturity,
        rate=rate,
        volatility=volatility,
        n_paths=n_paths,
        dividend_yield=dividend_yield,
        rng=rng,
    )
    if option_type == "call":
        payoffs = np.maximum(terminal_spots - strike, 0.0)
    else:
        payoffs = np.maximum(strike - terminal_spots, 0.0)

    discounted_payoffs = math.exp(-rate * maturity) * payoffs

    """
    통계값들을 계산한다. 옵션가격, 표준오차, 신뢰구간을 계산한다.
    통계값 설명에 대한 추가 내용은 notion 문서 참고.
    """
    price = float(np.mean(discounted_payoffs))
    standard_error = float(
        np.std(discounted_payoffs, ddof=1) / math.sqrt(n_paths)
    )
    tail_probability = (1.0 - confidence_level) / 2.0
    critical_value = -NormalDist().inv_cdf(tail_probability)
    margin = critical_value * standard_error

    return MonteCarloResult(
        price=price,
        standard_error=standard_error,
        ci_low=price - margin,
        ci_high=price + margin,
        n_paths=n_paths,
        seed=seed,
    )


"""
변동성이 0일때 사용할, 결정론적인 옵션가격이다. 즉, 정규분포 Z_i 값이 필요없음.
이때는 따로 샘플링 수행하지 않고 바로 결과를 제공한다.
"""
def _deterministic_result(price: float, n_paths: int, seed: int) -> MonteCarloResult:
    return MonteCarloResult(
        price=price,
        standard_error=0.0,
        ci_low=price,
        ci_high=price,
        n_paths=n_paths,
        seed=seed,
    )
