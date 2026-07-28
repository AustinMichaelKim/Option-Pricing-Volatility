# Repository Instructions

## Project purpose

This repository is an educational implementation of option pricing and
volatility analysis. The intended progression is:

1. inspect and normalize real option-chain data;
2. implement binomial and Black–Scholes–Merton pricing;
3. implement GBM and Monte Carlo simulation;
4. recover implied volatility;
5. analyze delta hedging and hedging P&L.

Do not pre-implement later milestones merely because their directories exist.
Keep each change within the scope of the current task and its prerequisite
theory.

## Working approach

* Inspect the relevant files, tests, and Git status before editing.
* For a multi-file or mathematically nontrivial change, propose a short plan
  before implementation.
* Preserve unrelated user changes and avoid broad refactors unless requested.
* Prefer the smallest change that satisfies the task.
* Do not commit, push, or modify external services unless explicitly requested.
* If a financial convention or intended behavior is ambiguous and materially
  affects the result, ask instead of guessing.

## Repository architecture

* `notebooks/`: reading notes, exploration, experiments, plots, and result
  interpretation.
* `src/option_pricing_volatility/market_data/`: option-chain ingestion,
  schemas, and normalization.
* `src/option_pricing_volatility/models/`: deterministic pricing models,
  including binomial and BSM.
* `src/option_pricing_volatility/processes/`: stochastic-process definitions,
  including GBM.
* `src/option_pricing_volatility/simulation/`: Monte Carlo estimators and
  simulation engines.
* `src/option_pricing_volatility/volatility/`: implied-volatility solvers and
  volatility analysis.
* `src/option_pricing_volatility/hedging/`: hedge rules, self-financing
  bookkeeping, and hedge simulations.
* `tests/`: deterministic unit tests and small synthetic fixtures.
* `data/raw/`: immutable local downloads.
* `data/interim/`: intermediate local transformations.
* `data/processed/`: analysis-ready local data.
* `outputs/`: reproducible tables and figures.
* `docs/`: detailed model contracts, assumptions, and design decisions.

Do not introduce another top-level package or move responsibilities between
these areas without a concrete architectural reason.

## Notebook-to-package workflow

* Use notebooks to understand a formula, inspect data, and design an
  experiment.
* Promote code to `src/option_pricing_volatility/` when it becomes reusable or
  is needed by more than one notebook.
* After promotion, import the package implementation; do not retain a second
  implementation in the notebook.
* Reusable calculations must not depend on notebook globals, hidden state, or
  cell execution order.
* Keep notebooks focused on orchestration, visualization, and interpretation.
* When notebook behavior changes, restart the kernel and run the affected
  notebook top to bottom when practical. If it was not executed, report that.

## Financial and numerical conventions

* Express prices and strikes in the same currency units.
* Express maturity and time steps in years.
* Express rates and volatilities as decimals, not percentages.
* Use continuously compounded rates unless the task or model contract states
  otherwise.
* Make dividend treatment explicit: use dividend yield `q` or a documented
  discrete-dividend assumption.
* Make option style, call/put type, valuation time, and settlement assumptions
  explicit.
* Initial pricing implementations should cover European calls and puts unless
  the task explicitly expands the scope.
* Separate model assumptions from numerical-method choices.
* Randomized functions must accept an explicit `numpy.random.Generator` or
  seed. Do not rely on mutable global random state.
* Validate domains such as `S > 0`, `K > 0`, `T >= 0`, and `sigma >= 0`, and
  raise informative errors for invalid inputs.
* Document any numerical tolerance, convergence rule, clipping, or fallback
  that can change a financial result.

Put detailed formulas and model-specific contracts in
`docs/model_contracts.md`; keep this file focused on durable repository rules.

## Testing and validation

* Use `pytest`.
* Add or update tests whenever reusable logic in `src` changes.
* Keep tests independent of live APIs, current market conditions, network
  access, and local downloaded data.
* Use hand-calculated or independently derived cases for core formulas.
* Use fixed RNG inputs and statistically justified tolerances for simulations;
  avoid flaky tests based on a single random outcome.
* Where applicable, test financial invariants:

  * no-arbitrage bounds;
  * put–call parity;
  * call-price monotonicity in spot;
  * nonnegative European option vega;
  * binomial convergence toward BSM under matching assumptions;
  * Monte Carlo confidence intervals against an analytical benchmark;
  * `price -> implied volatility -> repriced value` round trips.
* Test boundary cases deliberately, including `T = 0`, `sigma = 0`, deep
  ITM/OTM inputs, and invalid solver brackets where relevant.

Run the narrowest relevant tests while iterating. Before declaring a reusable
code change complete, run:

```bash
python -m pytest
```

Also run configured formatting, lint, type, or notebook checks when the
repository defines them. Do not claim a check passed unless it was executed.

## Data, outputs, and security

* Never commit credentials, tokens, `.env` files, or environment-specific
  paths.
* Do not commit raw or processed market downloads unless the task explicitly
  establishes a small, redistributable fixture.
* Test fixtures must be small, synthetic or legally redistributable, and free
  of secrets or personal data.
* Treat `data/raw/` as immutable: transformations must write to `data/interim/`
  or `data/processed/`.
* Keep generated plots and tables reproducible from code.
* Avoid committing large notebook outputs, raw records, or volatile
  environment metadata.

## Dependencies and code quality

* Prefer the standard library and existing project dependencies.
* Do not add or replace a dependency merely for convenience. Explain the need
  and tradeoff before changing project dependencies.
* Add type hints to public functions and concise docstrings that state inputs,
  outputs, units, assumptions, and important failure modes.
* Keep data acquisition separate from normalization and financial
  calculations.
* Favor clear formulas and auditable intermediate values over premature
  abstraction or optimization.

## Completion report

When finishing a task, report:

* files changed and the behavioral effect;
* financial assumptions or conventions introduced;
* validation commands run and their results;
* checks not run and why;
* remaining limitations or follow-up work.
