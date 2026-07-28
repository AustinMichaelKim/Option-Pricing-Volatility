# Data Contracts

This document defines how option-chain data is acquired, stored, normalized,
and filtered. Provider-specific adapters may differ, but normalized outputs
must follow this contract.

## 1. Storage layers

### `data/raw/`

- Immutable snapshots exactly as downloaded or exported.
- Never overwrite a raw file in place.
- Preserve provider field names and metadata where practical.
- File names should include underlying, quote date/time, and source identifier.

### `data/interim/`

- Parsed or partially normalized data.
- May contain provider-specific fields needed for debugging.

### `data/processed/`

- Analysis-ready tables using the normalized schema below.
- Must be reproducible from raw data and code.

Large or non-redistributable downloads should remain uncommitted. Tests use
small synthetic or legally redistributable fixtures.

## 2. Required normalized fields

| Field | Type | Meaning |
|---|---|---|
| `underlying` | string | Underlying ticker or identifier |
| `quote_timestamp` | timezone-aware datetime | Time the quote snapshot represents |
| `expiration` | timezone-aware datetime or documented market date | Contract expiration |
| `option_type` | categorical/string | `call` or `put` |
| `strike` | float | Positive strike price |
| `bid` | float/nullable | Best bid |
| `ask` | float/nullable | Best ask |
| `last` | float/nullable | Last traded price |
| `volume` | integer/nullable | Session volume when supplied |
| `open_interest` | integer/nullable | Open interest when supplied |
| `underlying_spot` | float | Spot or documented reference underlying price |
| `source` | string | Data provider or origin |
| `contract_id` | string/nullable | Provider contract symbol or stable identifier |

Optional provider fields may be retained if clearly named and documented.
Provider-supplied implied volatility must not overwrite project-computed implied
volatility.

## 3. Time conventions

- Store timestamps as timezone-aware values.
- Normalize stored instants to UTC when feasible; convert to exchange or local
  time only for presentation.
- Preserve the original provider timestamp and timezone metadata when
  available.
- Initial time to maturity uses ACT/365F:

```text
T = max(expiration_timestamp - quote_timestamp, 0) / 365 calendar days
```

- If the provider supplies only an expiration date, the assumed expiration
  time and exchange timezone must be documented.
- Do not mix calendar-day and trading-day year fractions within one analysis.

## 4. Price normalization

For valid two-sided quotes:

```text
mid = (bid + ask) / 2
spread = ask - bid
relative_spread = spread / mid, when mid > 0
```

A quote is not a valid two-sided quote when:

- bid or ask is missing;
- bid or ask is negative;
- ask is below bid;
- both bid and ask are zero;
- the resulting midpoint is nonpositive.

Do not replace missing or invalid midpoints with `last` silently. A notebook may
compare midpoint and last-trade prices, but the selected pricing input must be
explicit.

## 5. Derived fields

Processed data should derive fields as needed, including:

- `mid`;
- `spread` and `relative_spread`;
- `T` in years;
- `moneyness = strike / underlying_spot`;
- optional `log_moneyness = log(strike / forward_reference)` when the forward
  convention is defined;
- intrinsic value;
- relevant European no-arbitrage lower and upper price bounds;
- `is_valid_quote`;
- one or more `filter_reason` values;
- project-computed `implied_volatility` and solver status.

Derived columns must identify the rate, dividend, spot/forward reference, and
valuation timestamp used when those choices affect the value.

## 6. Filtering principles

- Preserve observations before filtering whenever storage size permits.
- Add flags and reason codes before dropping rows.
- Keep data-quality filters separate from research filters.

### Data-quality examples

- invalid bid/ask pair;
- nonpositive strike or spot;
- nonpositive time to maturity for a live-contract analysis;
- target price outside European no-arbitrage bounds;
- duplicated contract snapshot.

### Research-filter examples

- maximum relative spread;
- minimum open interest or volume;
- moneyness range;
- selected expirations;
- exclusion of extremely short maturities.

Research thresholds must be defined in the notebook or configuration that uses
them; they are not universal financial truths.

## 7. Provenance and reproducibility

Each raw snapshot or processed dataset should make it possible to recover:

- source/provider;
- acquisition or export time;
- quote timestamp represented by the data;
- underlying spot reference;
- transformation code version when practical;
- filters and parameter values used;
- rate and dividend inputs used for derived financial fields.

Avoid depending on a provider's current live response to reproduce a historical
figure. Save the permitted source snapshot or a redistributable fixture.

## 8. Testing rules

- Unit tests must not call live APIs.
- Use small synthetic tables covering valid, missing, crossed, zero, and
  duplicated quotes.
- Test timezone handling and year-fraction calculation explicitly.
- Test that raw inputs are not mutated by normalization functions unless the
  function contract clearly says otherwise.
