# AI Log 08 - Station 4 Phase 4B Fund And Risk Experience

## Objective

Implement only Station 4 Phase 4B: the SignalScope Fund comparison and Risk fact
sheet experience.

The scope was deliberately limited to:

- comparing all nine systematic funds;
- selecting a fund and preserving that selection across Fund and Risk;
- showing an investor-facing fact sheet with historical OOS performance, risk,
  holdings, concentration, turnover, and asset-class exposure.

Signal, Evidence, Decision, and Challenge functionality remains deferred.

## Fund View Design

The Fund stage now keeps the SignalScope first-screen hierarchy from Phase 4A,
then adds:

- family and method filters;
- a persistent selected-fund control;
- an `Open fact sheet` action that moves to Risk;
- a hoverable risk-return map for the filtered fund universe;
- compact metric-language explanations;
- a comparison snapshot that can rank by Sharpe, annualised return, max
  drawdown, volatility, or turnover.

The map uses annualised volatility on the x-axis and annualised historical OOS
return on the y-axis. Family is shown with categorical product colours, method is
shown with point shape, and the selected fund is highlighted. No efficient
frontier or "best fund" claim was added.

## Risk Fact-Sheet Design

The Risk stage now renders a complete selected-fund fact sheet:

- fund family, method, and method-type badge;
- concise method explanation;
- compact return, volatility, Sharpe, and max-drawdown strip;
- growth of $1 chart built from saved net OOS fund returns;
- drawdown chart built from the same saved path;
- turnover and first-live context;
- latest holdings chart with an optional display-only remainder bucket;
- top holding, largest weight, effective holdings, and warnings;
- latest equity/crypto exposure;
- method and cost disclosure.

This is intentionally not a wall of raw tables or default metric cards.

## Artifacts Used

Only existing Phase 4A startup artifacts were used:

- `results/tables/performance_metrics.csv`
- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/tables/asset_class_exposure.csv`
- `results/tables/first_live_dates.csv`

No raw data, headline-level sentiment, optimiser diagnostics, or analytical
source modules are loaded by the app.

## Runtime Calculations Allowed

Phase 4B adds view-layer calculations only:

- selected-fund validation from `performance_metrics.csv`;
- growth of $1 from saved `net_return`;
- drawdown from that displayed growth path;
- latest saved weights by date;
- top holding and largest single-asset weight;
- effective number of holdings as `1 / sum(weight_i^2)`;
- latest saved asset-class exposure;
- display-only top-holdings remainder bucket.

No backtest, optimisation, VADER scoring, raw price loading, or transaction-cost
recalculation was added.

## Concentration Treatment

Concentration is surfaced explicitly instead of hidden:

- largest holding and weight;
- effective holdings;
- warning if top asset weight is above 25%;
- warning if effective holdings is below 5.

The app does not call concentrated optimised funds diversified.

## Turnover Treatment

Turnover uses `total_turnover` already saved in `performance_metrics.csv`.

No additional lazy turnover artifact was needed for Phase 4B. The fact sheet
states that turnover is trading intensity and potential cost drag, and that net
returns already reflect the frozen 10 bps transaction-cost assumption.

## Combined Calendar Caveat

Combined fund fact sheets display the required caveat:

The combined fund uses the equity trading calendar. Weekend-only crypto moves
are not represented as continuous seven-day crypto P&L in the combined series.

Crypto-only and equity-only family caveats are also shown from saved calendar
conventions.

## Files Changed

- `app/funds.py`
- `app/charts.py`
- `app/components.py`
- `app/design.py`
- `app/navigation.py`
- `tests/test_app_funds.py`
- `ai/08_station4_phase4b_funds_risk.md`

No frozen analytical source files or existing analytical result artifacts were
modified.

## Tests

Added deterministic helper tests for:

- nine expected fund family/method combinations;
- selected-fund validation and missing-fund handling;
- growth of $1 from synthetic saved net returns;
- drawdown from the same path;
- latest-weight extraction;
- effective holdings;
- concentration flags;
- display-only holdings remainder;
- latest exposure lookup;
- missing exposure errors.

Existing app dependency-ban tests continue to scan all app modules for raw-data,
VADER/NLTK, optimiser, and backtest dependencies.

## Verification

Focused app tests:

```text
12 passed in 1.14s
```

Full test suite:

```text
44 passed in 8.93s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Streamlit render check:

```text
APPTEST_FUND_RISK_OK
```

Streamlit bounded smoke-start:

```text
HTTP_STATUS=200
```

Frozen analytical-file check:

```text
git status --short -- src results
```

returned no output.

## Deferred Work

Phase 4C remains responsible for:

- Signal sector sentiment time-series view;
- Evidence Lens;
- neutrality versus cancellation explorer;
- volume versus breadth panel.

Later phases remain responsible for:

- Decision allocation builder;
- Challenge matched-shrinkage falsification view;
- final responsive/deployment polish beyond the Fund/Risk scope.

