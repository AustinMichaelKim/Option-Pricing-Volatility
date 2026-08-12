# Model Contracts

This document defines the financial and numerical behavior expected from model
code. A change that alters these contracts must update the relevant tests and
be recorded in `docs/decisions.md`.

## 1. Common notation and units

- `S`: underlying spot price, strictly positive.
- `K`: strike price, strictly positive.
- `T`: time to maturity in years, nonnegative.
- `r`: continuously compounded annual risk-free rate as a decimal.
- `q`: continuously compounded annual dividend yield as a decimal.
- `sigma`: annualized volatility as a decimal, nonnegative.
- `option_type`: explicit call or put indicator.
- Prices and strikes use the same currency unit.

Unless a task states otherwise, options are European and cash-settled at
maturity for pricing purposes. The initial year-fraction convention is ACT/365F,
as defined in `docs/data_contracts.md`.

## 2. Black-Scholes-Merton contract

For `T > 0` and `sigma > 0`:

```text
d1 = [ln(S / K) + (r - q + 0.5 sigma^2) T] / (sigma sqrt(T))
d2 = d1 - sigma sqrt(T)

call = S exp(-qT) N(d1) - K exp(-rT) N(d2)
put  = K exp(-rT) N(-d2) - S exp(-qT) N(-d1)
```

### Boundary behavior

At `T = 0`, return intrinsic value:

```text
call = max(S - K, 0)
put  = max(K - S, 0)
```

At `sigma = 0` and `T > 0`, use the discounted deterministic payoff under the
risk-neutral drift:

```text
call = max(S exp(-qT) - K exp(-rT), 0)
put  = max(K exp(-rT) - S exp(-qT), 0)
```

Do not force a small positive volatility merely to avoid the special case.

### Put-call parity

```text
call - put = S exp(-qT) - K exp(-rT)
```

### European no-arbitrage bounds

```text
max(0, S exp(-qT) - K exp(-rT)) <= call <= S exp(-qT)
max(0, K exp(-rT) - S exp(-qT)) <= put  <= K exp(-rT)
```

### Greeks

Analytical Greeks must state whether they are per one-unit change or per
percentage-point change. The default is mathematical units:

- delta: price change per one currency-unit change in `S`;
- vega: price change per `1.00` change in volatility, not per one volatility
  percentage point;
- theta: price change per year unless a presentation layer explicitly converts
  it to per-day units.

Initial deltas for `T > 0` and `sigma > 0` are:

```text
call_delta = exp(-qT) N(d1)
put_delta  = exp(-qT) [N(d1) - 1]
```

## 3. Cox-Ross-Rubinstein binomial contract

For `n` time steps:

```text
dt = T / n
u = exp(sigma sqrt(dt))
d = 1 / u
p = [exp((r - q) dt) - d] / (u - d)
```

- Require integer `n >= 1` when `T > 0`.
- Validate that `p` lies in `[0, 1]`; do not silently clip it.
- Discount one step by `exp(-r dt)`.
- The first implementation prices European calls and puts only.
- For `T = 0` or `sigma = 0`, follow the same economic boundary behavior as
  the BSM contract rather than constructing a degenerate tree.

## 4. Risk-neutral GBM contract

Under the pricing measure:

```text
dS_t = (r - q) S_t dt + sigma S_t dW_t
```

For exact terminal simulation:

```text
S_T = S_0 exp[(r - q - 0.5 sigma^2) T + sigma sqrt(T) Z]
Z ~ Normal(0, 1)
```

Simulation functions must accept an explicit `numpy.random.Generator` or seed.
Returned arrays must have documented shape and dtype behavior.

## 5. Monte Carlo pricing contract

For payoff `H(S_T)`:

```text
price_estimate = exp(-rT) * sample_mean(H(S_T))
standard_error = exp(-rT) * sample_std(H(S_T), ddof=1) / sqrt(n_paths)
```

The default two-sided confidence interval uses a normal approximation and a
configurable confidence level. The result object should expose at least:

- estimate;
- standard error;
- confidence-interval lower and upper bounds;
- path count;
- seed or RNG provenance when available.

Do not present a Monte Carlo estimate without its uncertainty in analysis
outputs.

## 6. Implied-volatility contract

Implied volatility is the nonnegative `sigma` that reprices a European option
to a target price under the BSM assumptions and supplied `S`, `K`, `T`, `r`,
and `q`.

Before root finding:

1. validate ordinary input domains;
2. require `T > 0` because implied volatility is not uniquely identified at
   expiry;
3. check the target against the relevant no-arbitrage bounds;
4. define and document solver bracket, price tolerance, volatility tolerance,
   and maximum iterations.

The initial scalar implementation uses bisection with these defaults:

```text
volatility bracket = [1e-8, 5.0]
price tolerance = 1e-8
volatility tolerance = 1e-12
maximum iterations = 200
```

The no-arbitrage and bracket price ranges are strict validity checks and are
not enlarged by a numerical tolerance. Before checking the positive-volatility
bracket, a target within the price tolerance of the `sigma = 0` BSM price
returns an implied volatility of exactly `0.0`. Bisection converges when either
the absolute repricing error is within the price tolerance or the volatility
bracket width is within the volatility tolerance.

An invalid target or a target outside the configured bracket raises
`ValueError`. Exhausting the maximum iterations raises `RuntimeError` rather
than returning an endpoint or unconverged estimate.

Do not silently:

- clip an invalid target price into the arbitrage bounds;
- return a bracket endpoint as though it were a converged root;
- replace a failed result with `NaN` without a reason code or exception.

A successful result exposes the volatility, signed repricing error
`BSM_price - target_price`, iteration count, and convergence status.

## 7. Delta-hedging contract

The initial hedging experiment uses one short European option unless a task
states another position convention.

A self-financing ledger must explicitly track:

- option position and sign;
- stock units held as the hedge;
- cash account after establishing or rebalancing the hedge;
- cash accrual at the continuously compounded risk-free rate;
- dividends or dividend yield treatment;
- transaction timing;
- terminal option settlement and stock liquidation.

Initial experiments assume zero transaction costs. This is a model assumption,
not a statement about real markets.

Rebalancing occurs on a documented time grid. Hedging P&L must state whether it
is measured from the option writer's or buyer's perspective and whether the
initial option premium is included.

## 8. Numerical behavior

- Invalid financial domains raise informative exceptions.
- Vectorization behavior must be documented rather than accidental.
- Tolerances belong near the algorithm or in a named configuration, not as
  unexplained magic numbers.
- Avoid silent clipping except where the contract explicitly calls for a
  presentation-only display limit.
- Prefer stable alternative formulas or explicit boundary branches when direct
  evaluation becomes numerically unreliable.
