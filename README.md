# Option Pricing and Volatility Analysis

SPX 옵션 데이터를 이용해 CRR, Black–Scholes–Merton, GBM Monte Carlo와
implied volatility를 구현하고 비교하는 교육·포트폴리오 프로젝트입니다.
Notebook은 실험과 해석에 사용하고, 재사용 계산은 Python package와 pytest로
검증합니다.

## 연구 질문

1. CRR 가격은 시간 스텝이 증가할 때 BSM 가격에 수렴하는가?
2. Monte Carlo 가격은 경로 수가 증가할 때 BSM 가격에 수렴하며,
   표준오차는 대략 `M^(-1/2)`로 감소하는가?
3. 고정된 SPX 옵션체인에서 implied-volatility skew는 어떤 형태인가?
4. 시장 midpoint와 ATM implied volatility를 고정한 BSM 가격은 어떻게
   다른가?

## 현재 상태

| 영역 | 상태 |
| --- | --- |
| SPX MarketData 수집과 전처리 | 완료 |
| CRR binomial pricing | 완료 |
| Risk-neutral GBM과 Monte Carlo pricing | 완료 |
| BSM closed-form pricing | 완료 |
| Bisection implied-volatility solver | 다음 작업 |
| 네 개의 최종 그림과 보고서 | 예정 |

## 범위

포함 범위는 European-style SPX call/put, 단일 snapshot·단일 만기,
midpoint 기반 IV, CRR/MC 수렴과 constant-volatility BSM 비교입니다.

KOSPI 200, American/exotic option, delta hedging, stochastic volatility,
다중 만기 surface, 거래전략과 production pipeline은 현재 범위 밖입니다.

## 구조

```text
.
├── data/                             # Git에서 제외되는 로컬 데이터
│   ├── raw/
│   ├── interim/
│   └── processed/
├── docs/                             # 계약, 결정, 구현 설명
├── notebooks/
│   ├── 00_sandbox/
│   ├── 01_option_chain/
│   ├── 02_binomial/
│   ├── 03_gbm_mc/
│   ├── 04_bsm/
│   └── 05_implied_volatility/
├── src/option_pricing_volatility/
│   ├── market_data/
│   ├── models/
│   ├── processes/
│   ├── simulation/
│   └── volatility/
└── tests/
```

## 작업 원칙

1. Notebook에서 식과 실험 구조를 확인합니다.
2. 재사용하거나 테스트해야 하는 계산은 `src`에 구현합니다.
3. Notebook은 package 함수를 import하고 그래프와 해석에 집중합니다.
4. 구현 변경에는 관련 pytest를 추가하거나 수정합니다.

세부 금융 계약은 `docs/model_contracts.md`, SPX 데이터 계약은
`docs/data_contracts.md`, 주요 설계 결정은 `docs/decisions.md`를 따릅니다.

## 개발 환경

```bash
conda activate finance
python -m pip install -e ".[dev,notebook]"
python -m pytest
python -m jupyter lab
```

## 데이터와 비밀정보

- MarketData token은 환경변수 `MARKETDATA_TOKEN`으로만 관리합니다.
- raw snapshot은 한 번 저장한 뒤 덮어쓰지 않습니다.
- raw, interim, processed CSV는 Git에 커밋하지 않습니다.
- 최종 결과에는 사용한 snapshot, `r`, `q`, `sigma_ATM` 정의와 Git commit을
  기록합니다.

## 최종 산출물

- `binomial_convergence`
- `mc_convergence`
- `iv_skew`
- `market_vs_constant_vol_bsm`
- 검증된 package와 tests
- 짧은 결과 보고서
