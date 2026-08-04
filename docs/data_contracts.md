# KOSPI 200 Option Data Contract

This document defines the minimum contract for turning one fixed KOSPI 200
option-chain snapshot into model-ready inputs. It covers the Stage 1 path:

```text
raw -> normalized -> validated -> model-ready
```

Provider-specific column names remain provisional until the first real snapshot
is audited. Unknown values must be recorded as `TBD` or rejected; they must not
be guessed.

## 1. Storage and immutability

### `data/raw/`

- Store the source snapshot exactly as downloaded or exported.
- Never overwrite or edit a raw file in place.
- Keep market downloads uncommitted unless redistribution is permitted.
- Record the source filename, file checksum, acquisition time, and provider.

### `data/interim/`

- Store normalized rows and rejected rows separately.
- Preserve the original provider columns needed for audit and debugging.

### `data/processed/`

- Store only reproducible, model-ready tables.
- Every processed file must be reproducible from a raw snapshot, configuration,
  and code version.

## 2. Required snapshot metadata

Each snapshot must record:

- `snapshot_id`;
- provider and acquisition/export method;
- acquisition time and the quote time represented by the data;
- original timezone and normalized timezone;
- market session;
- underlying reference value and its observation time;
- contract expiry convention, exercise style, settlement type, multiplier, and
  currency;
- source filename and checksum;
- redistribution or storage restrictions;
- configuration and Git commit used for transformation.

A missing value may be marked `TBD` during raw inspection. A row cannot become
model-ready when the missing value materially changes `S`, `K`, `T`, option
identity, or the pricing convention.

## 3. Normalized schema

The raw provider field corresponding to each normalized field must be added
after snapshot inspection.

| Field | Type | Nullable | Source or rule |
|---|---|---:|---|
| `underlying` | string | no | Canonical identifier, initially `KOSPI200` |
| `contract_id` | string | yes | Provider symbol or stable contract identifier |
| `quote_timestamp` | timezone-aware datetime | no | Provider quote time; normalize to UTC |
| `expiry_timestamp` | timezone-aware datetime | no* | Provider expiry, or a documented date-only assumption |
| `option_type` | string | no | Normalize to `call` or `put` |
| `strike` | float64 | no | Positive index-point strike |
| `bid` | float64 | yes | Best bid |
| `ask` | float64 | yes | Best ask |
| `last` | float64 | yes | Last traded price; never a silent midpoint fallback |
| `volume` | nullable integer | yes | Session volume when supplied |
| `open_interest` | nullable integer | yes | Open interest when supplied |
| `vendor_implied_volatility` | float64 | yes | Provider value, preserved separately |
| `spot` | float64 | no* | Positive underlying reference for pricing |
| `spot_timestamp` | timezone-aware datetime | no* | Observation time of `spot` |
| `futures_price` | float64 | yes | Same-expiry reference when used to infer forward or `q` |
| `futures_timestamp` | timezone-aware datetime | yes | Observation time of `futures_price` |
| `risk_free_rate` | float64 | no* | Annual continuously compounded decimal |
| `source` | string | no | Provider or origin |

`no*` means required for model-ready output, although the normalized audit table
may retain the row with a rejection reason when the value is unavailable.

Provider-specific columns may be retained if their names and units are clear.
They must not overwrite normalized or project-derived fields.

## 4. Time and price conventions

- Preserve original timestamp text and timezone metadata when available.
- Store normalized instants as timezone-aware UTC values.
- If expiry is supplied as a date only, record the assumed expiry time and
  timezone. Without that assumption, `T` is not model-ready.
- Use ACT/365F consistently:

```text
T = max(expiry_timestamp - quote_timestamp, 0) / 365 calendar days
```

A structurally valid two-sided quote requires finite values satisfying:

```text
0 <= bid <= ask
not (bid == 0 and ask == 0)
```

For such quotes:

```text
mid = (bid + ask) / 2
spread = ask - bid
relative_spread = spread / mid, when mid > 0
```

The initial model-ready policy uses `mid` as `target_price` and requires
`bid > 0`. Zero-bid rows are preserved but rejected or flagged explicitly.
`last` may be analyzed separately but must never be substituted silently.

## 5. Derived and model-ready fields

Normalization or validation may derive:

- `mid`, `spread`, and `relative_spread`;
- `T` in years;
- `forward` and `implied_q` when the spot, same-expiry futures, rate, and timing
  convention are documented;
- `log_forward_moneyness = log(strike / forward)`;
- European no-arbitrage lower and upper bounds;
- `target_price`;
- `quality_flags`;
- `rejection_reasons`;
- project-computed `model_implied_volatility`, solver status, and repricing
  error.

The minimum fields passed to a spot-form European pricing model are:

```text
spot, strike, T, risk_free_rate, dividend_yield,
option_type, target_price
```

A documented forward-form convention may replace `spot` and `dividend_yield`.
The convention must be consistent across pricing, implied-volatility inversion,
and reporting.

## 6. Validation and failure policy

Validation is separated into three levels.

### Dataset-level errors

Fail the pipeline when the file cannot be parsed, required columns cannot be
mapped, snapshot metadata is absent, or units cannot be determined.

### Row-level rejection

Retain rejected rows and attach one or more stable reason codes, including:

- `MISSING_REQUIRED_FIELD`;
- `INVALID_TIMESTAMP` or `UNKNOWN_EXPIRY_TIME`;
- `INVALID_OPTION_TYPE`;
- `NONPOSITIVE_STRIKE` or `NONPOSITIVE_SPOT`;
- `MISSING_BID_ASK`, `NEGATIVE_QUOTE`, `CROSSED_QUOTE`, or `ZERO_QUOTE`;
- `NONPOSITIVE_BID` under the initial model-ready policy;
- `NONPOSITIVE_TTM`;
- `DUPLICATE_CONTRACT_QUOTE`;
- `PRICE_OUTSIDE_ARBITRAGE_BOUNDS`.

No rejected row may disappear without a reason code. A row may have multiple
reasons.

### Quality and research flags

Wide spread, low volume or open interest, observation-time mismatch, selected
expiry, and moneyness range are quality or research filters. Their thresholds
belong in configuration or the analysis notebook, not in this universal
contract.

Normalization functions must not mutate the raw input DataFrame unless the
function signature explicitly documents mutation.

## 7. Provenance and reproducibility

Accepted and rejected outputs must remain traceable to:

- `snapshot_id`, source file, and checksum;
- provider and acquisition/export time;
- quote, spot, and futures observation times;
- field mapping and transformation configuration;
- rate, dividend, forward, expiry-time, and day-count assumptions;
- code commit and dependency version when practical.

Historical results must not depend only on a provider's current live response.
Use a permitted immutable snapshot or a small redistributable fixture.

## 8. Required tests

Unit tests must not call live APIs. Small synthetic fixtures must cover:

- valid, missing, negative, crossed, zero-bid, and all-zero quotes;
- duplicate contract quotes;
- valid and invalid option-type mappings;
- timezone conversion, date-only expiry, and ACT/365F;
- nonpositive `spot`, `strike`, and `T`;
- raw-input immutability;
- accepted/rejected separation and 100% reason-code accounting.

Provider field names, exact expiry-time handling, contract multiplier,
settlement details, and redistribution constraints remain provisional until the
first real KOSPI 200 snapshot audit. Record the accepted provider decision in
`docs/decisions.md` when those items are fixed.
