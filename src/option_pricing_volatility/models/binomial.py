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

    # 입력한 값이 유한한 실수인지 확인한다. (bool은 제외)
    for name, value in numeric_inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be a finite real number")

    # 유한한 실수값 중에서, 유효한 값 범위인지 확인한다.
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

    # 입력값을 모두 float으로 형변환하여, 일관성유지.
    spot = float(spot)
    strike = float(strike)
    maturity = float(maturity)
    rate = float(rate)
    volatility = float(volatility)
    dividend_yield = float(dividend_yield)

    # 첫번째 조건분기:  만기가 0 이면, 현재 내재가치를 바로 리턴한다.
    if maturity == 0:
        payoff = spot - strike if option_type == "call" else strike - spot
        return max(payoff, 0.0)
    # 스텝 값이 유효한지 확인한다. (bool은 제외)
    if isinstance(steps, bool) or not isinstance(steps, Integral) or steps < 1:
        raise ValueError(
            "steps must be an integer greater than or equal to 1 when maturity > 0"
        )
    steps = int(steps)

    # 두번째 조건분기 : 변동성이 0이면, 결정론적 기대 payoff를 계산해서 바로 리턴.
    # 불필요한 트리 형성을 막는다.
    if volatility == 0:
        discounted_spot = spot * math.exp(-dividend_yield * maturity)
        discounted_strike = strike * math.exp(-rate * maturity)
        payoff = (
            discounted_spot - discounted_strike
            if option_type == "call"
            else discounted_strike - discounted_spot
        )
        return max(payoff, 0.0)

    # CRR 트리계산 준비; up, down을 계산하고, risk-neutral probability를 계산한다.
    dt = maturity / steps
    up = math.exp(volatility * math.sqrt(dt))
    down = 1.0 / up
    probability = (math.exp((rate - dividend_yield) * dt) - down) / (up - down)
    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            f"risk-neutral probability must be in [0, 1]; got {probability}"
        )

    discount = math.exp(-rate * dt)  # 한 스텝 할인계수
    terminal_spot = spot * down**steps # N번째 스텝 모두 down으로 이동한 주가.

    # N번 모두 down 한 노드부터, u/d 를 곱해가면서 총 N개 사이즈의 노드를 만든다.
    node_ratio = up / down
    values: list[float] = []

    # Sd^N 에서 시작해서, payoff 를 계산한다. call/put 에 따라 삼항연산자 이용.
    # 이후, 이 스텝을 u/d를 곱하면서 반복.
    for _ in range(steps + 1):
        payoff = (
            terminal_spot - strike
            if option_type == "call"
            else strike - terminal_spot
        )
        values.append(max(payoff, 0.0))
        terminal_spot *= node_ratio

    # 마지막으로, backward induciton을 통해서 N-1번째, N-2번째 스텝을 계산.
    # N-1번째의 0번 노드는 N번째의 0,1노드를 쓰는데, 이후 N번째의 0번 노드 값은 안쓰이므로,
    # 하나의 배열에서 제자리 계산을 수행. 메모리를 아낀다.
    down_probability = 1.0 - probability
    for nodes in range(steps, 0, -1):
        for node in range(nodes):
            values[node] = discount * (
                down_probability * values[node] + probability * values[node + 1]
            )

    return float(values[0])
