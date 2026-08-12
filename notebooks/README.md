# Notebooks

Notebook은 package 코드를 실행해 데이터를 확인하고, 실험 결과를 표와
그래프로 만들며, 그 결과를 해석하는 공간입니다. 재사용 계산을 notebook에
중복 구현하지 않습니다.

## 디렉터리

- `00_sandbox/`: 짧은 환경 확인과 일회성 실험
- `01_option_chain/`: SPX 수집과 전처리
- `02_binomial/`: CRR 가격과 BSM 수렴 실험
- `03_gbm_mc/`: GBM terminal sampling과 MC 수렴 실험
- `04_bsm/`: BSM closed-form 확인과 benchmark
- `05_implied_volatility/`: 이분탐색 IV, SPX skew와 constant-volatility 비교

IV 작업의 기본 notebook은 다음 파일입니다.

```text
05_implied_volatility/05_01_implied_volatility_calculation.ipynb
```

## Package로 옮기는 기준

다음 중 하나에 해당하면 `src/option_pricing_volatility/`로 옮깁니다.

1. 두 개 이상의 실험에서 재사용한다.
2. 입력·출력과 실패 정책이 명확하다.
3. pytest로 독립 검증해야 한다.

옮긴 뒤에는 notebook의 복사 구현을 제거하고 package 함수를 import합니다.
