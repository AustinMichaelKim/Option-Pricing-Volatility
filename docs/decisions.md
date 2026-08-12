# Project Decisions

이 문서는 금융적 의미, numerical behavior, 데이터 해석 또는 저장소 구조를
바꾸는 결정만 기록한다.

## D-001: Package-first reusable code

- Date: 2026-07-28
- Status: accepted
- Decision: 재사용 계산은 `src/option_pricing_volatility/`, 실험과 해석은
  notebooks, 검증은 tests에 둔다.
- Consequence: package로 옮긴 구현을 notebook에 중복 유지하지 않는다.

## D-002: Common rate and time conventions

- Date: 2026-07-28
- Status: accepted
- Decision: `r`, `q`는 연속복리 연율 소수, `T`는 ACT/365F 연 단위를
  사용한다.
- Consequence: 다른 source convention은 명시적으로 변환한다.

## D-003: Midpoint as observed market price

- Date: 2026-07-28
- Status: accepted
- Decision: 유효한 two-sided quote의 `(bid + ask) / 2`를 IV target과 시장
  비교 가격으로 사용한다.
- Consequence: `last`나 vendor IV를 조용히 대체값으로 사용하지 않는다.

## D-004: European call/put scope

- Date: 2026-07-28
- Status: accepted
- Decision: 현재 pricing과 IV 범위는 European call/put으로 제한한다.
- Consequence: American/exotic pricing은 별도 범위 변경 없이는 구현하지 않는다.

## D-005: Explicit randomness and failure

- Date: 2026-07-28
- Status: accepted
- Decision: randomized functions는 명시적 Generator 또는 seed를 받고,
  invalid inputs와 nonconvergence는 예외나 reason code로 드러낸다.
- Consequence: clipping과 global mutable RNG를 사용하지 않는다.

## D-006: Provider initially provisional

- Date: 2026-07-28
- Status: superseded
- Decision: 초기에는 실제 option-chain provider를 고정하지 않았다.
- Superseded by: D-007.

## D-007: Use one fixed MarketData SPX snapshot

- Date: 2026-08-09
- Status: accepted
- Decision: MarketData의 `2026-07-15` SPX historical snapshot에서 PM-settled
  단일 만기를 사용한다. Raw cache를 불변 입력으로 보존한다.
- Consequence: provider mapping은 market-data 계층에만 두고 모델 코드는
  SPX API 응답 형식에 의존하지 않는다.
- Related: `docs/data_contracts.md`.

## D-008: Final MVP is four figures

- Date: 2026-08-12
- Status: accepted
- Decision: 최종 MVP는 binomial convergence, MC convergence, SPX IV skew,
  market midpoint vs constant-volatility BSM의 네 결과로 제한한다.
- Consequence: KOSPI 200, delta hedging, 전체 Greeks와 volatility surface는
  활성 범위에서 제외한다.

## D-009: Scalar implied volatility uses bracketed bisection

- Date: 2026-08-12
- Status: accepted
- Decision: European call/put implied volatility is inverted from the existing
  BSM price with scalar bisection on the default volatility bracket
  `[1e-8, 5.0]`. A target matching the zero-volatility price within the price
  tolerance maps to `0.0` before the positive-volatility bracket is checked.
- Consequence: invalid prices and missing roots raise `ValueError`, iteration
  exhaustion raises `RuntimeError`, and successful results retain signed
  repricing error and iteration diagnostics.
