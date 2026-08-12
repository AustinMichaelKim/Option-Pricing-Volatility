# Repository Instructions

## Project purpose and scope

This repository is an educational option-pricing and volatility-analysis
project. The active market dataset is one fixed SPX option-chain snapshot.

The project answers four questions:

1. Does CRR converge to the BSM price as the number of steps increases?
2. Does GBM Monte Carlo converge to BSM, with standard error decreasing at the
   expected rate?
3. What implied-volatility skew appears in the SPX snapshot?
4. How do market midpoints differ from BSM prices using one ATM volatility?

KOSPI 200 processing, delta hedging, American options, volatility-surface
calibration, trading strategies, and production systems are outside the active
scope. Do not implement them unless the user explicitly changes the scope.

## Working approach

- Inspect the relevant files, tests, and Git status before editing.
- For a multi-file or mathematically nontrivial change, give a short plan.
- Preserve unrelated user changes and avoid broad refactors.
- Prefer the smallest change that satisfies the current task.
- Do not commit, push, change branches, or modify external services unless the
  user explicitly requests it.
- Ask when a financial convention is ambiguous and materially changes a result.
- Do not create another top-level Python package.

## Repository authority

- `docs/model_contracts.md` owns financial and numerical behavior.
- `docs/data_contracts.md` owns the SPX schema, price, time, and validation
  conventions.
- `docs/decisions.md` records accepted and superseded project decisions.
- Source code and tests show the currently implemented behavior.
- README and implementation notes are explanatory, not separate contracts.

If code/tests and a contract disagree, do not silently choose one. Identify the
mismatch and update the contract, implementation, and tests together as
required by the task.

## Repository architecture

- `notebooks/`: experiments, plots, and result interpretation.
- `src/option_pricing_volatility/market_data/`: SPX acquisition helpers.
- `src/option_pricing_volatility/models/`: CRR and BSM pricing.
- `src/option_pricing_volatility/processes/`: risk-neutral GBM sampling.
- `src/option_pricing_volatility/simulation/`: Monte Carlo estimators.
- `src/option_pricing_volatility/volatility/`: implied-volatility logic.
- `tests/`: deterministic tests and small synthetic fixtures.
- `data/raw/`: immutable local downloads.
- `data/interim/`: rejected or intermediate local outputs.
- `data/processed/`: reproducible analysis-ready local outputs.
- `docs/`: contracts, decisions, and concise implementation explanations.

## Notebook-to-package workflow

- Use notebooks to explore formulas, inspect data, design experiments, and
  interpret results.
- Put reusable or testable calculations under `src/option_pricing_volatility/`.
- After promotion, import the package function; do not keep a second notebook
  implementation.
- Reusable functions must not depend on notebook globals or cell order.
- When practical, restart and run an affected notebook top to bottom. If it was
  not executed, report that fact.

## Financial and numerical conventions

- Prices and strikes use the same units.
- Maturity is in ACT/365F years.
- Rates, dividend yield, and volatility are annual decimals.
- Rates and dividend yields are continuously compounded.
- The pricing scope is European call/put.
- Make `T = 0`, `sigma = 0`, no-arbitrage bounds, solver brackets, tolerances,
  and failure behavior explicit.
- Randomized functions use an explicit NumPy `Generator` or seed.
- Do not clip invalid prices, probabilities, volatility, or solver output to
  manufacture a successful result.

Detailed formulas belong in `docs/model_contracts.md`, not in this file.

## Testing and validation

- Use `pytest` and add tests whenever reusable logic changes.
- Tests must not call live APIs or depend on current market conditions.
- Use independent benchmarks or financial invariants where applicable:
  no-arbitrage bounds, put-call parity, CRR-to-BSM convergence,
  Monte Carlo confidence intervals, and IV round trips.
- Test invalid domains and the `T = 0` and `sigma = 0` boundaries deliberately.
- Run the narrowest relevant tests while iterating and, before completion, run:

```bash
python -m pytest
```

Do not claim a check passed unless it was executed.

## Data and security

- Never commit credentials, tokens, `.env` files, or environment-specific paths.
- Treat `data/raw/` as immutable and keep market downloads out of Git.
- Keep tests synthetic, small, and legally redistributable.
- Preserve accepted and rejected rows with traceable reason codes.
- Record the source snapshot and financial assumptions used for final figures.

## Completion report

When finishing a task, report:

- files changed and behavioral effect;
- financial assumptions or conventions introduced;
- tests or notebook runs completed;
- checks not run and why;
- remaining limitations or follow-up work.
