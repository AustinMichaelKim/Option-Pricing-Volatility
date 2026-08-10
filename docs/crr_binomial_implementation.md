# CRR binomial tree 구현 설명

이 문서는 유럽형 옵션을 가격화하는 CRR(Cox–Ross–Rubinstein) binomial tree
구현과 수렴 실험 코드를 설명한다.

관련 파일은 다음과 같다.

- 가격 계산:
  [binomial.py](../src/option_pricing_volatility/models/binomial.py)
- 단위 테스트:
  [test_binomial.py](../tests/test_binomial.py)
- 수렴 실험:
  [02_01_binomial_tree_model.ipynb](../notebooks/02_binomial/02_01_binomial_tree_model.ipynb)
- 금융·수치 계약:
  [model_contracts.md](model_contracts.md)

## 1. 구현 목적

연구 질문은 고정된 만기 \(T\)에서 시간 스텝 수 \(N\)을 늘릴 때 CRR
가격이 향후 구현할 BSM 가격에 수렴하는지 확인하는 것이다.

\[
\Delta t = \frac{T}{N}
\]

따라서 극한은 다음과 같이 표현한다.

\[
N \rightarrow \infty,
\qquad
\Delta t \rightarrow 0
\]

줄어드는 값은 시간 스텝의 개수 \(N\)이 아니라 각 스텝의 길이
\(\Delta t\)이다.

## 2. 공개 API

가격 함수의 인터페이스는 다음과 같다.

    crr_price(
        spot,
        strike,
        maturity,
        rate,
        volatility,
        steps,
        option_type,
        dividend_yield=0.0,
    ) -> float

각 인수의 의미와 단위는 다음과 같다.

| 인수 | 의미 | 규칙 |
|---|---|---|
| spot | 현재 기초자산 가격 \(S\) | 0보다 커야 한다 |
| strike | 행사가격 \(K\) | 0보다 커야 한다 |
| maturity | 잔존만기 \(T\) | 연 단위이며 0 이상이다 |
| rate | 무위험이자율 \(r\) | 연속복리 소수 단위다 |
| volatility | 변동성 \(\sigma\) | 연율 소수 단위이며 0 이상이다 |
| steps | 시간 스텝 수 \(N\) | \(T>0\)이면 1 이상의 정수다 |
| option_type | 옵션 종류 | call 또는 put만 허용한다 |
| dividend_yield | 배당수익률 \(q\) | 연속복리 소수 단위다 |

함수는 하나의 옵션 가격을 부동소수점 값으로 반환한다. 배열 입력,
batch pricing, American 옵션은 지원하지 않는다.

## 3. CRR 모형 설정

한 스텝의 길이와 상승·하락 배수는 다음과 같다.

\[
\Delta t = \frac{T}{N}
\]

\[
u = e^{\sigma\sqrt{\Delta t}},
\qquad
d = \frac{1}{u}
\]

위험중립측도에서 기초자산의 한 스텝 기대 성장률이
\(e^{(r-q)\Delta t}\)가 되도록 위험중립 상승확률을 정한다.

\[
p =
\frac{e^{(r-q)\Delta t}-d}{u-d}
\]

한 스텝의 할인계수는 다음과 같다.

\[
\text{discount} = e^{-r\Delta t}
\]

계산된 \(p\)가 \([0,1]\) 밖에 있으면 해당 시간 격자와 입력값으로는
유효한 위험중립확률을 만들 수 없다. 구현은 값을 0이나 1로 보정하지 않고
ValueError를 발생시킨다. 이는 잘못된 모형 설정을 정상 가격처럼 반환하지
않기 위한 선택이다.

## 4. 가격 계산 흐름

### 4.1 입력 검증

함수는 먼저 spot, strike, maturity, rate, volatility,
dividend_yield가 유한한 실수인지 확인한다. 이후 가격과 만기, 변동성의
도메인 및 option_type을 검증한다.

\(T>0\)이면 steps는 bool이 아닌 1 이상의 정수여야 한다. \(T=0\)에서는
트리를 만들지 않으므로 steps를 사용하지 않는다.

### 4.2 만기와 무변동성 경계

\(T=0\)이면 즉시 intrinsic value를 반환한다.

\[
C = \max(S-K,0)
\]

\[
P = \max(K-S,0)
\]

\(T>0\)이고 \(\sigma=0\)이면 퇴화한 트리를 만들지 않고 위험중립
결정론적 payoff의 현재가치를 반환한다.

\[
C =
\max\left(
S e^{-qT} - K e^{-rT},
0
\right)
\]

\[
P =
\max\left(
K e^{-rT} - S e^{-qT},
0
\right)
\]

### 4.3 만기 payoff 생성

만기에서 상승 횟수가 \(j\)인 노드의 기초자산 가격은 다음과 같다.

\[
S_{N,j} = S u^j d^{N-j},
\qquad
j=0,\ldots,N
\]

코드는 가장 낮은 만기 노드 \(Sd^N\)에서 시작한 뒤 인접 노드 비율
\(u/d\)를 곱하면서 만기 payoff 배열을 만든다.

\[
C_{N,j} = \max(S_{N,j}-K,0)
\]

\[
P_{N,j} = \max(K-S_{N,j},0)
\]

### 4.4 backward induction

만기 payoff에서 현재 시점으로 한 레벨씩 돌아오며 다음 값을 계산한다.

\[
V_{i,j}
=
e^{-r\Delta t}
\left[
(1-p)V_{i+1,j}
+pV_{i+1,j+1}
\right]
\]

배열의 앞부분을 제자리에서 갱신하므로 전체 트리를 저장하지 않는다.
최대 \(N+1\)개의 노드 값만 유지하여 메모리 복잡도는 \(O(N)\)이다.
각 레벨의 모든 노드를 평가하므로 실행시간 복잡도는 \(O(N^2)\)이다.

## 5. 1-step 손계산 예제

테스트의 1-step 사례는 다음 입력을 사용한다.

\[
S=K=100,\quad
T=1,\quad
r=\log(1.25),\quad
q=0,\quad
\sigma=\log(2),\quad
N=1
\]

이때

\[
u=2,\qquad d=0.5,\qquad p=0.5,\qquad e^{-r}=0.8
\]

이다. 상승 노드의 주가는 200, 하락 노드의 주가는 50이다.

- call payoff는 상승 시 100, 하락 시 0이므로 가격은
  \(0.8 \times (0.5 \times 100)=40\)이다.
- put payoff는 상승 시 0, 하락 시 50이므로 가격은
  \(0.8 \times (0.5 \times 50)=20\)이다.

이 값은 구현의 상승·하락 노드 방향, 위험중립확률, 할인 적용을 독립적으로
검산하는 기준이다.

## 6. 테스트가 확인하는 내용

test_binomial.py는 연구 질문과 함수 계약에 필요한 다음 항목만 확인한다.

| 테스트 | 확인 내용 |
|---|---|
| 1-step call/put | 손으로 계산한 40과 20을 재현한다 |
| \(T=0\) | intrinsic value를 반환한다 |
| \(\sigma=0\) | 할인된 결정론적 payoff를 반환한다 |
| 잘못된 입력 | 도메인, finite 값, steps, option_type을 거부한다 |
| 잘못된 \(p\) | 확률을 clipping하지 않고 예외를 발생시킨다 |
| put–call parity | \(C-P=Se^{-qT}-Ke^{-rT}\)를 만족한다 |
| BSM benchmark | \(N=4096\) CRR call 가격의 상대오차가 기준보다 작다 |

수렴 테스트의 표준 입력은 다음과 같다.

\[
S=K=100,\quad T=1,\quad r=0.05,\quad q=0,\quad \sigma=0.2
\]

BSM call 기준값은 10.450583572185565이며 테스트 조건은 다음과 같다.

\[
\frac{|V_{4096}-V_{\mathrm{BSM}}|}{S}<10^{-4}
\]

이 기준값은 테스트용 상수일 뿐이며 현재 패키지에는 BSM 가격 함수를
구현하지 않았다.

## 7. 노트북의 수렴 결과 테이블

노트북은 동일한 synthetic 입력에 대해 다음 스텝 격자를 사용한다.

    [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]

call과 put 각각에 대해 tidy-form DataFrame을 만들며 열은 다음 네 개다.

| 열 | 의미 |
|---|---|
| option_type | call 또는 put |
| steps | 시간 스텝 수 \(N\) |
| dt | \(T/N\) |
| crr_price | 해당 \(N\)에서 계산한 CRR 가격 |

이 구조에는 향후 BSM 구현 후 bsm_price, absolute_error,
relative_error 열을 직접 추가할 수 있다. CRR 가격은 odd/even 스텝에
따라 진동할 수 있으므로 각 행에서 오차가 단조롭게 감소한다고 가정해서는
안 된다.

## 8. 현재 범위와 한계

현재 구현은 다음 범위로 제한된다.

- European call과 put만 지원한다.
- 하나의 scalar 옵션만 계산한다.
- 메모리는 \(O(N)\)이지만 실행시간은 \(O(N^2)\)이다.
- BSM, Greeks, American 옵션, Monte Carlo, implied volatility는 구현하지
  않았다.
- plotting 함수는 없으며 노트북은 향후 그래프 입력으로 사용할 테이블만
  만든다.
- 극단적으로 큰 입력이나 스텝 수를 위한 별도 overflow·underflow 안정화는
  포함하지 않는다.
