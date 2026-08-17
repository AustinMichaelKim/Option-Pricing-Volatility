# Option Pricing and Volatility Analysis

Notion page : https://slime-colony-47f.notion.site/Option-Pricing-and-Volatility-Analysis-38b2123be49080ca91afe7939b42df81?source=copy_link

Hull 교재에서 이론적 기반을 마련합니다.  CRR, Black–Scholes–Merton, GBM Monte Carlo와 implied volatility를 코드로 구현합니다. 실제 SPX option 시장 데이터를 API로 받아와서 핵심 질문들에 대답하고, 결과 데이터를 시각화 합니다.

Hull 교재 독해 및 필기노트 정리사항은 Notion: Introduction to Financial Engineering  에 저장해 놓았습니다.

이해한 이론적 지식을 바탕으로 VS code 및 codex 를 활용하여 프로젝트의 핵심 질문을 위한 코드를 구현하였고, Notion: Code Implementation and Review 에 구현 및 리뷰 기록을 저장했습니다.

마지막으로, 핵심 질문에 대한 답을 그래프로 시각화 하여 Notion: Result and Discussion  페이지에 보기 쉽게 정리해 놓았습니다.


## 프로젝트 핵심 질문

1. CRR 가격은 시간 스텝이 증가할 때 BSM 가격에 수렴하는가?
2. Monte Carlo 가격은 경로 수가 증가할 때 BSM 가격에 수렴하며,
   표준오차는 대략 `M^(-1/2)`로 감소하는가?
3. SPX 옵션체인에서 implied volatility skew는 어떤 형태인가?
4. 옵션의 시장가격과 ATM implied volatility를 고정한 BSM 가격은 어떻게
   다른가?

## 현재 상태

| 영역 | 상태 |
| --- | --- |
| SPX MarketData 수집과 전처리 | 완료 |
| CRR binomial pricing | 완료 |
| Risk-neutral GBM과 Monte Carlo pricing | 완료 |
| BSM closed-form pricing | 완료 |
| Bisection implied-volatility solver | 완료 |
| 네 개의 최종 그림과 보고서 | 완료 |

## 범위

포함 범위는 유럽형 SPX call/put 옵션 데이터, 단일 snapshot·단일 만기,
midpoint 기반 IV, CRR/MC 수렴과 constant-volatility BSM 비교입니다.

American/exotic option, delta hedging, stochastic volatility,
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
│   ├── 05_implied_volatility/
│   ├── main1_convergence_to_bsm/
│   └── main2_iv_skew_and_constant_volattiltiy/
├── src/option_pricing_volatility/
│   ├── market_data/
│   ├── models/
│   ├── processes/
│   ├── simulation/
│   └── volatility/
└── tests/
```

## 작업 프로세스

1. Notebook에는 실험 및 데이터 처리 및 계산 로직을 구현합니다.
2. 재사용하는 함수 및 로직은 `src`에 구현합니다.
3. 구현한 코드 및 모듈 상세는 `docs`에 ipynb파일로 저장합니다.
3. 세부 금융 계약은 `docs/model_contracts.md`, SPX 데이터 계약은
`docs/data_contracts.md`, 주요 설계 결정은 `docs/decisions.md`를 따릅니다.


## 개발 환경

```bash
conda activate finance
python -m pip install -e ".[dev,notebook]"
python -m pytest
python -m jupyter lab
```

## 데이터와 비밀정보

- 데이터는 [MARKET{DATA}](https://www.marketdata.app/) API를 통해서 내려받습니다.
- MarketData token은 환경변수 `MARKETDATA_TOKEN`으로만 관리합니다.
- raw snapshot은 한 번 저장한 뒤 덮어쓰지 않습니다.
- raw, interim, processed CSV는 Git에 커밋하지 않습니다.


## 최종 산출물

1. main1_convergence_to_bsm
  - `binomial_convergence`
  - `mc_convergence`

2. main2_iv_skew_and_constant_volattiltiy
  - `iv_skew`
  - `market_vs_constant_vol_bsm`
