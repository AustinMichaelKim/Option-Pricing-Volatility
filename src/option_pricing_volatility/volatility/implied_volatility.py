"""Scalar implied volatility for European options under BSM."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

from option_pricing_volatility.models.bsm import bsm_price


"""
변동성 계산 이분법 알고리즘의 결과 객체.
1. tolerance 1e-12 보다 작아 수렴할때의 변동성
2. repricing_error: 시장 가격과 BSM 가격의 차이
3. iterations: 수렴할때까지 반복한 횟수
4. converged: 수렴 여부
"""
@dataclass(frozen=True, slots=True)
class ImpliedVolatilityResult:
    """A converged BSM implied-volatility estimate and its diagnostics."""

    volatility: float
    repricing_error: float
    iterations: int
    converged: bool


"""
변동성 계산 핵심 함수.
[volatilit_lower, volatility_upper] 구간에서 이분법으로 implied volatility를 계산한다.  [1e-8, 5.0] 구간이 기본값이다.
"""
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
    price_tolerance: float = 1e-8,  # 시장가격과 BSM가격이 이값보다 작으면 변동성 =0 으로 간주.
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

    """
    함수 입력값 유효성 검사. 기존의 모듈 함수들과 동일함.
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

    """
    입력값 데이터 형변환. 추후 계산 과정에서 float형으로 계산하기 위해서.
    """
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


    """
    먼저 시장 가격이 무차익 범위 내에 존재하는지 확인한다. ( lower and upper bound of Call and Put options).
    즉, 시장가격이 이론에서 제시하는 상한 하한을 넘어가면 에러를 발생시킨다.
    => 에러가 뜬 경우에는 함수의 입력값 세팅이 잘못되었을 수 있음. 
    """
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


    """
    이분법 알고리즘을 통한 volatility의 계산.
    1. 먼저 volatility = 0 인 경우의 BSM 가격을 계산한다. ( bsm_price에 volatility = 0.0 으로 입력 )  만약  시장가 - BSM(iv=0) < 10^-8이면  iv=0 리턴.
    """
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

    """
    2. 함수에 입력한 bracket [volatility_lower, volatility_upper] 에서 BSM 가격을 계산한다. 
        - 만약, braket 양끝에서의 bsm 가격이 OverflowError가 발생한다는 것은, float형으로 계산할 수 없는 값이 나왔다는 것이므로, bracket을 조정해야 한다.
    """
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

    """
    3. 시장가격과, bracket 양 끝 bsm 가격을 비교한다.  
        - lower_price < market_price < upper_price  인 경우만 해당 알고리즘이 유효하다.  ( bracket iv 는 lower은 1e-8, upper는 5.0으로 설정되어 있음 )
        - 시장가가 이 범위를 벗어나면, 이분법 알고리즘이 유효하지 않으므로, ValueError를 발생시킨다.
    """
    lower_error = lower_price - market_price
    upper_error = upper_price - market_price

    if market_price < lower_price or market_price > upper_price:
        raise ValueError(
            "market_price is not attainable within volatility bracket "
            f"[{volatility_lower}, {volatility_upper}]; BSM price range is "
            f"[{lower_price}, {upper_price}], got {market_price}"
        )

    """
    4. bracket 양 끝 bsm 가격과,  그 사이에 있는 market price를 비교한다.
        - 만약, lower_error or upper_error 가 10^-8 보다 작다 ==  market price가 양 끝 bsm 가격과 거의 같다는 말.
        - 따라서, volatility를 리턴하고 종료한다.
    """
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

    """
    5. 4번을 통과한 것은,  market price가 bracket 양 끝 bsm 가격과 충분히 떨어져 있다는 의미.
        - 따라서, bracket 양 끝을 기준으로 이분법 알고리즘을 수행한다
    """
    lower = volatility_lower
    upper = volatility_upper
    latest_error = lower_error

    """
    이분법 알고리즘 수행
        1. bracket의 중간값 volatility에 대해서 bsm 가격을 계산한다.
        2. market price와 비교한다.
            - | midpoint_bsm_price  -  market_price | < 1e-8 => 수렴. midpoint_volatility 리턴
            
            - lower_price < market_price < midpoint_price  =>  new braket [lower_volatility, midpoint_volatility]

            - midpoint_price <  market_price < upper_price =>  new braket [midpoint_volatility, upper_volatility]
    """
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

        # 중간 변동성에서 구한 bsm가격이 시장가와 거의 유사한경우
        if abs(latest_error) <= price_tolerance:
            return ImpliedVolatilityResult(
                volatility=midpoint,
                repricing_error=latest_error,
                iterations=iteration,
                converged=True,
            )

        # 중간 변동성 bsm 가격이 시장가보다 더 크다 => 상한을 mid로 재설정
        # 중간 변동성 bsm 가격이 시장가보다 더 작다 => 하한을 mid로 재설정
        if latest_error > 0.0:
            upper = midpoint
        else:
            lower = midpoint

        """
        6. 새로운 volatility 구간을 잡았는데,  그 구간의 차이가 1e-12라면, 그냥 그 값을 변동성으로 계산한다. 
            - [1.000000000.. , 1.000000000..] =>  그냥 변동성을 1.0000000.. 으로 간주.
        """
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

    """
    최대 반복동안 수렴하지 않으면 반복문을 빠져나오고, 해당 런타임 에러가 실행된다.
    이 경우, 반복수를 늘리거나, 아니면 brakcet 구간을 재설정한다.
    """
    raise RuntimeError(
        "implied volatility did not converge within "
        f"{max_iterations} iterations; last absolute pricing error was "
        f"{abs(latest_error)} and bracket width was {upper - lower}"
    )
