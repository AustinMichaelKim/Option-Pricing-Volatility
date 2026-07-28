# Project Decisions

Record decisions that materially affect architecture, financial meaning,
numerical behavior, data interpretation, or reproducibility.

## Decision template

```text
## D-XXX: Short title

- Date: YYYY-MM-DD
- Status: proposed | accepted | superseded
- Context:
- Decision:
- Rationale:
- Consequences:
- Related files:
```

## D-001: Use a package-first architecture

- Date: 2026-07-28
- Status: accepted
- Context: Exploratory notebooks are useful for learning, but duplicated model
  code makes results difficult to test and audit.
- Decision: Reusable calculations live under
  `src/option_pricing_volatility/`; notebooks orchestrate, visualize, and
  interpret package code.
- Rationale: This preserves an educational notebook workflow while producing a
  testable portfolio project.
- Consequences: Once notebook code becomes reusable, it must be promoted and
  the duplicate implementation removed.
- Related files: `AGENTS.md`, `docs/project_brief.md`.

## D-002: Use continuously compounded rates and dividend yields

- Date: 2026-07-28
- Status: accepted
- Context: BSM, CRR, GBM, and put-call parity require a consistent rate
  convention.
- Decision: Default to continuously compounded annual `r` and `q`, expressed as
  decimals.
- Rationale: This matches the initial analytical formulas and risk-neutral
  simulation contract.
- Consequences: Any data source supplying another convention must be converted
  explicitly.
- Related files: `docs/model_contracts.md`.

## D-003: Use ACT/365F for the initial year fraction

- Date: 2026-07-28
- Status: accepted
- Context: Option data requires a reproducible conversion from timestamps to
  years.
- Decision: Use actual elapsed calendar time divided by 365 days for the first
  project version.
- Rationale: It is simple, explicit, and adequate for the educational analysis.
- Consequences: Results may differ slightly from vendor or exchange conventions;
  comparisons must document this.
- Related files: `docs/data_contracts.md`, `docs/model_contracts.md`.

## D-004: Use midpoint as the default observed option price

- Date: 2026-07-28
- Status: accepted
- Context: Last trade can be stale, while bid or ask alone reflects one side of
  the market.
- Decision: For a valid two-sided quote, use `(bid + ask) / 2` as the default
  implied-volatility target.
- Rationale: It is a transparent baseline for educational cross-sectional
  analysis.
- Consequences: Invalid or one-sided quotes are flagged rather than silently
  replaced with last trade.
- Related files: `docs/data_contracts.md`.

## D-005: Limit the first pricing scope to European calls and puts

- Date: 2026-07-28
- Status: accepted
- Context: The core project focuses on BSM, Monte Carlo, implied volatility, and
  delta hedging.
- Decision: The first complete implementation supports European calls and puts.
- Rationale: This keeps analytical benchmarks available and controls project
  scope.
- Consequences: American contracts from real option chains must be interpreted
  cautiously; American pricing is a later extension rather than silently
  treated as identical.
- Related files: `docs/project_brief.md`, `docs/model_contracts.md`.

## D-006: Require explicit random-number control

- Date: 2026-07-28
- Status: accepted
- Context: Monte Carlo and hedging experiments must be reproducible and tests
  must not rely on global mutable state.
- Decision: Randomized public functions accept a NumPy `Generator` or explicit
  seed.
- Rationale: This enables deterministic debugging and controlled experiments.
- Consequences: Convenience functions must not hide uncontrolled global RNG use.
- Related files: `AGENTS.md`, `docs/model_contracts.md`.

## D-007: Do not silently repair financially invalid inputs

- Date: 2026-07-28
- Status: accepted
- Context: Clipping prices, probabilities, solver brackets, or volatility can
  make code appear successful while changing the financial problem.
- Decision: Invalid domains and nonconvergent numerical cases produce
  informative errors or explicit failure results.
- Rationale: Auditability and learning value are more important than producing a
  number for every input.
- Consequences: Notebooks must display and interpret exclusions and failures.
- Related files: `docs/model_contracts.md`, `docs/data_contracts.md`.

## D-008: Leave the market-data provider provisional

- Date: 2026-07-28
- Status: proposed
- Context: The repository structure is ready, but the first real option-chain
  source has not yet been fixed in this document set.
- Decision: Select the provider during M1 and record access method, licensing,
  timestamps, field mapping, and reproducibility constraints here.
- Rationale: Provider choice affects schema mapping and what data may be stored
  or shared.
- Consequences: Do not build provider-specific assumptions into core financial
  modules.
- Related files: `docs/roadmap.md`, `docs/data_contracts.md`.
