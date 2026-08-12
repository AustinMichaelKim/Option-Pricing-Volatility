# SPX Option Data Contract

이 문서는 고정된 MarketData SPX option-chain snapshot을 BSM과 implied
volatility 계산에 사용할 수 있는 데이터로 만드는 최소 계약을 정의한다.

```text
raw snapshot → normalized rows → accepted / rejected → IV-ready rows
```

## 1. 고정 분석 대상

- Underlying: `SPX`
- Provider: MarketData historical option chain
- Quote date: `2026-07-15`
- Requested DTE: `30`
- Requested settlement filter: `am=false`, `pm=true`
- Actual expiry in the snapshot: `2026-08-14T20:00:00Z`
- Day count: ACT/365F
- Default observed price: valid bid/ask midpoint

요청 DTE는 검색 조건일 뿐이다. 실제 `T`는 provider의 quote와 expiry
timestamp 차이로 다시 계산한다.

## 2. 저장 규칙

### `data/raw/marketdata_spx/`

- API 응답을 처음 받은 형태로 저장한다.
- 기존 nonempty raw 파일을 덮어쓰지 않는다.
- 동일한 요청은 raw cache를 읽고 API를 다시 호출하지 않는다.

### `data/interim/marketdata_spx/`

- rejected rows와 `rejection_reason`을 저장한다.

### `data/processed/marketdata_spx/`

- accepted rows를 저장한다.
- processed와 rejected 파일은 같은 raw snapshot에서 재생성할 수 있어야 한다.

시장 CSV와 API token은 Git에 커밋하지 않는다.

## 3. 최소 정규화 schema

| Field | 의미 |
| --- | --- |
| `option_symbol` | provider contract identifier |
| `underlying` | `SPX` |
| `quote_timestamp` | UTC-aware quote time |
| `expiry_timestamp` | UTC-aware expiry time |
| `option_type` | `call` 또는 `put` |
| `strike` | 양의 index-point strike |
| `bid`, `ask` | two-sided quote |
| `last` | 참고값; midpoint 대체 금지 |
| `volume`, `open_interest` | 유동성 참고값 |
| `spot` | provider underlying reference |
| `vendor_iv` | provider 참고값; 자체 IV와 분리 |

파생 필드는 다음과 같다.

```text
mid = (bid + ask) / 2
spread = ask - bid
relative_spread = spread / mid
T = (expiry_timestamp - quote_timestamp) / 365 days
spot_moneyness = strike / spot
log_spot_moneyness = log(strike / spot)
```

## 4. Accepted와 rejected

Accepted row는 최소한 다음을 만족해야 한다.

- 필수 identifier, price와 timestamp가 존재하고 finite다.
- `option_type`이 `call` 또는 `put`이다.
- `strike > 0`, `spot > 0`, `T > 0`이다.
- `bid > 0`, `ask >= bid`, `mid > 0`이다.
- `option_symbol`이 snapshot 안에서 중복되지 않는다.

Rejected row는 삭제하지 않고 하나 이상의 안정적인 reason code를 가진다.

```text
MISSING_REQUIRED_FIELD:<column>
NON_NUMERIC_REQUIRED_FIELD:<column>
NONFINITE_REQUIRED_FIELD:<column>
INVALID_TIMESTAMP:<column>
INVALID_OPTION_TYPE
NONPOSITIVE_STRIKE
NONPOSITIVE_SPOT
NONPOSITIVE_BID
CROSSED_QUOTE
NONPOSITIVE_MID
NONPOSITIVE_TTM
DUPLICATE_OPTION_SYMBOL
```

`volume == 0`, `open_interest == 0`, wide spread와 moneyness 범위는 row-level
오류가 아니라 분석용 quality filter다.

## 5. IV-ready fields

IV 계산 전에 다음 값을 명시적으로 추가한다.

| Field | 규칙 |
| --- | --- |
| `risk_free_rate` | 연속복리 연율 소수; 출처 기록 |
| `dividend_yield` | 연속복리 연율 소수; 출처 기록 |
| `target_price` | `mid` |
| `forward` | `spot * exp((r - q) * T)` |
| `log_forward_moneyness` | `log(strike / forward)` |

IV 결과는 최소한 다음 열을 가진다.

```text
implied_volatility
iv_status
iv_failure_reason
repricing_error
```

`0.85 <= strike / forward <= 1.15`와 liquidity threshold는 연구 표본 선택
조건이며 raw/accepted 여부를 바꾸지 않는다.

## 6. 무차익 검증

IV inversion 전에 `docs/model_contracts.md`의 European call/put bounds를
확인한다. 범위 밖 가격을 clipping하지 않고 실패로 기록한다.

## 7. 재현성

최종 결과는 다음 정보와 연결한다.

- raw filename과 request parameters
- quote와 expiry timestamp
- `r`, `q`의 값과 출처
- filter와 `sigma_ATM` 선택 규칙
- code commit

Unit tests는 live API를 호출하지 않고 synthetic response와 임시 경로를
사용한다.
