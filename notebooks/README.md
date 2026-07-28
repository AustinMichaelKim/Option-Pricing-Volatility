# Notebooks

이 디렉터리가 프로젝트의 주 작업 공간입니다. 각 주제 디렉터리에서 독해
내용을 수치로 확인하고, 데이터를 탐색하며, 표와 그래프를 만듭니다.

## 주제 디렉터리

- `00_sandbox/`: 짧은 환경 확인과 일회성 실험
- `01_option_chain/`: 실제 옵션체인 수집, 점검, 정리
- `02_binomial/`: binomial model 실험
- `03_gbm/`: GBM 경로와 분포 실험
- `04_bsm/`: BSM 가격과 민감도 실험
- `05_monte_carlo/`: Monte Carlo 가격결정 실험
- `06_implied_volatility/`: 내재변동성과 volatility surface 실험
- `07_delta_hedging/`: delta hedging과 hedge P&L 실험

## Notebook에서 Python 패키지로 옮기는 기준

다음 조건을 만족하는 코드는 대응하는 `src/option_pricing_volatility/` 하위
패키지로 옮깁니다.

1. 두 개 이상의 노트북에서 재사용할 수 있다.
2. 입력과 출력이 명확하고 notebook 전역 상태에 의존하지 않는다.
3. 금융 관례와 가정을 함수 인자 또는 문서로 표현할 수 있다.
4. pytest로 검증할 수 있다.

옮긴 뒤에는 노트북의 원본 구현을 제거하고 패키지 함수를 import합니다.
