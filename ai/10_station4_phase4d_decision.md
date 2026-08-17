# AI Log 10 - Station 4 Phase 4D Decision

## Objective

Implement only Station 4 Phase 4D:

`Decision - Look-through Capital Allocation`

The rubric requirement is allocation across funds. The product target is stronger
than a generic slider allocator: SignalScope asks what selected fund wrappers
actually become underneath.

Investor question:

`What does this allocation actually become?`

Supporting copy:

`Combine fund sleeves, then look through the labels to the underlying exposure.`

Challenge was not started.

## Design Thesis

The Decision page extends the SignalScope logic:

- Signal: do not trust a headline average without inspecting evidence.
- Evidence: do not trust direction without inspecting breadth and agreement.
- Decision: do not trust fund labels without inspecting underlying holdings.

The central Phase 4D insight is:

`More fund sleeves do not automatically mean more independent exposures.`

The page therefore uses a current structural look-through, not a custom
historical performance calculator.

## Verified Artifact Contract

The implementation uses only startup-loaded compact artifacts:

- `results/tables/performance_metrics.csv`
- `results/data/fund_weights.csv`
- `results/tables/asset_class_exposure.csv`
- `results/tables/first_live_dates.csv`

`fund_weights.csv` contains:

- `date`
- `fund_family`
- `method`
- `method_type`
- `asset`
- `asset_class`
- `weight`
- `live_rebalance_date`
- `decision_date`
- `estimation_start`
- `estimation_end`
- `estimation_window`

`asset_class_exposure.csv` contains:

- `date`
- `fund_family`
- `method`
- `method_type`
- `asset_class`
- `exposure`

All nine latest saved fund-weight snapshots are aligned at `2023-12-01`.
The app detects snapshot alignment from the artifacts instead of hardcoding it.

## Allocation Data Model

The Decision page uses dedicated state only:

- `decision_funds`
- `decision_allocations`

It does not overwrite:

- `selected_fund_family`
- `selected_fund_method`
- `selected_sector`
- `selected_signal_date`
- `evidence_case`

If a Fund/Risk selected fund exists, Decision starts from `100%` of that fund.
If no context exists, it starts from the deterministic benchmark sleeve
`Combined / Equal Weight`. This is labelled as a starting view, not a
recommendation.

The interface allows up to four selected fund sleeves. All nine sleeves are
available:

- Equity / Equal Weight
- Equity / Minimum Variance
- Equity / Maximum Sharpe
- Crypto / Equal Weight
- Crypto / Minimum Variance
- Crypto / Maximum Sharpe
- Combined / Equal Weight
- Combined / Minimum Variance
- Combined / Maximum Sharpe

## Validation

The page validates:

- fund exists;
- no duplicate sleeve;
- finite allocation;
- allocation is at least 0%;
- allocation is at most 100%;
- total allocation equals 100% within tight tolerance;
- selected latest weights exist;
- selected latest weights sum approximately to 1.

Invalid totals are not silently normalised. The UI shows states such as:

- `Allocated: 90.0% | Remaining: 10.0%`
- `Allocated: 110.0% | Overallocated: 10.0%`

An explicit `Normalise to 100%` action exists.

## Look-through Formula

For each underlying asset:

```text
lookthrough_weight(asset)
= sum over selected funds [
    capital_weight(fund) * latest_saved_fund_weight(asset)
  ]
```

Duplicate assets across fund sleeves are aggregated by stable `asset`
identifier. Saved fund weights are not mutated.

## Asset-class Aggregation

Asset class comes directly from saved `fund_weights.csv`. The app aggregates
the resulting look-through holdings by saved `asset_class`, then displays one
horizontal asset-class bar for Equity versus Crypto.

No raw data, `src.data_access`, or source-price reconstruction is used.

## Effective Holdings

Effective underlying holdings is calculated as:

```text
N_eff = 1 / sum(w_i^2)
```

where `w_i` are aggregate look-through underlying weights. The UI explains this
as an approximation of how many equally weighted positions would produce similar
concentration, not a literal security count or recommendation.

The page also reports top-5 share:

```text
sum of the five largest aggregate look-through weights
```

## Pairwise Overlap

Pairwise latest-holdings overlap is calculated as:

```text
overlap(A, B) = sum_i min(w_Ai, w_Bi)
```

Missing assets are aligned to zero. The UI labels this exactly as the share of
two latest saved fund-weight profiles held in common.

It is not described as:

- return correlation;
- risk correlation;
- diversification probability;
- a forecast;
- independence.

For two selected sleeves the page shows one overlap measure. For three or four
sleeves it shows the most-overlapping and least-overlapping selected pair, with
a progressive-disclosure pairwise bar view.

## Real Artifact Examples

All examples use latest saved snapshot `2023-12-01`.

### 100% Equity / Equal Weight

- underlying securities: `50`
- largest position: `ABBV`, `2.000%`
- effective holdings: `50.000`
- top-5 share: `10.000%`
- asset class: `100.000%` equity, `0.000%` crypto

### 100% Crypto / Equal Weight

- underlying securities: `10`
- largest position: `ADA-USD`, `10.000%`
- effective holdings: `10.000`
- top-5 share: `50.000%`
- asset class: `0.000%` equity, `100.000%` crypto

### 100% Combined / Equal Weight

- underlying securities: `60`
- largest position: `ABBV`, `1.6667%`
- effective holdings: `60.000`
- top-5 share: `8.333%`
- asset class: `83.333%` equity, `16.667%` crypto

### 50% Equity EW + 50% Crypto EW

- underlying securities: `60`
- largest position: `ADA-USD`, `5.000%`
- effective holdings: `33.333`
- top-5 share: `25.000%`
- asset class: `50.000%` equity, `50.000%` crypto

### 50% Equity EW + 50% Combined EW

- underlying securities: `60`
- largest position: `ABBV`, `1.8333%`
- effective holdings: `57.143`
- top-5 share: `9.167%`
- asset class: `91.667%` equity, `8.333%` crypto
- overlapping equities aggregate correctly. For example `ABBV` receives
  `0.5 * 2.000% + 0.5 * 1.6667% = 1.8333%`.

### Optimised Three-fund Mix

For `40% Combined / Maximum Sharpe`, `35% Equity / Minimum Variance`, and
`25% Crypto / Minimum Variance`:

- underlying securities: `26`
- largest position: `GE`, `18.524%`
- effective holdings: `10.210`
- top-5 share: `61.599%`
- asset class: `69.076%` equity, `30.924%` crypto

### Overlap Examples

- Equity / Equal Weight versus Combined / Equal Weight:
  `83.333%` holdings overlap.
- Equity / Equal Weight versus Crypto / Equal Weight:
  `0.000%` holdings overlap.

## No Custom Historical Backtest

Decision deliberately does not calculate historical return, volatility, Sharpe,
drawdown, or growth of one dollar for the user-created multi-fund allocation.

Reason:

- crypto-only funds use a native seven-day calendar;
- equity-only and combined funds use equity trading calendars;
- a custom historical mix would require a new calendar convention;
- it would also require new assumptions about fund-of-fund rebalancing, sleeve
  drift, transaction costs, and weekend crypto treatment.

Those assumptions are not part of the frozen analytical specification.

The visible disclosure says:

`Custom mixes are structural look-throughs of saved fund weights, not new
historical backtests.`

## Evidence-policy Connection

Decision keeps base construction primary. It states that SignalScope does not
rebuild a custom fund mix from headline sentiment, and that the frozen
Confidence Lens was tested only as a control on the equity sentiment overlay.

If the Evidence attenuation case is active, Decision may show its saved
RealEstate / 1 Nov 2021 raw and evidence-adjusted sector changes. It does not
apply those changes to the user's custom allocation.

## Design Decisions

The page preserves the locked dark-first SignalScope system:

- deep green-charcoal surfaces;
- salmon for action and selection;
- fund-family colours kept separate from signal/evidence/action semantics;
- gold only for evidence and overlap interpretation;
- restrained proportional strips instead of donut charts;
- no generic metric-card wall.

The flagship component is `Allocation anatomy`:

```text
FUND SLEEVES -> ASSET CLASSES -> UNDERLYING HOLDINGS
```

This mirrors the earlier Evidence Lens structure without making Decision feel
like a separate calculator.

## Files Changed

- `app/decision.py`
- `app/charts.py`
- `app/components.py`
- `app/design.py`
- `tests/test_app_decision.py`
- `ai/10_station4_phase4d_decision.md`

No frozen analytical source files and no existing saved result artifacts were
modified.

## Tests

Added deterministic tests for:

- fund-label validation;
- underallocation;
- overallocation;
- exact 100%;
- duplicate fund rejection;
- negative allocation rejection;
- one-fund look-through;
- two-fund look-through;
- duplicate asset aggregation;
- look-through weights summing to one;
- asset-class aggregation;
- effective holdings;
- largest holding;
- top-5 share;
- overlap formula;
- missing assets as zero in overlap;
- snapshot date consistency;
- invalid latest saved weights;
- missing fund weights;
- Decision static guardrail against custom performance construction.

Added real artifact tests for:

- `100% Equity / Equal Weight`;
- `100% Crypto / Equal Weight`;
- `100% Combined / Equal Weight`;
- `50% Equity EW + 50% Crypto EW`;
- `50% Equity EW + 50% Combined EW`;
- an optimised three-fund mix;
- Equity EW versus Combined EW overlap;
- Equity EW versus Crypto EW overlap.

Added AppTest coverage for:

- Decision loads;
- initial state inherits selected Fund/Risk fund;
- invalid 90% total;
- invalid 110% total;
- valid 50/50 mix;
- three-fund mix;
- remove sleeve;
- Decision -> Evidence;
- Decision -> Fund;
- Decision -> Risk;
- Decision -> Challenge placeholder;
- Fund, Risk, Signal, Evidence, Decision, and Challenge render without
  exceptions after the change.

## Verification

Focused Decision tests:

```text
15 passed in 4.80s
```

Full test suite:

```text
95 passed in 16.05s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Bounded Streamlit smoke-start:

```text
HTTP_STATUS=200
```

Frozen analytics verification:

```text
git status --short -- fins2026/z5367955_projectB/src fins2026/z5367955_projectB/results
```

returned no output.

Decision runtime guardrail:

```text
rg -n "fund_returns|net_return|gross_return|growth_net|drawdown|net_sharpe|run_backtest|scipy\\.optimize|transaction_cost|load_equity_prices|load_crypto_prices|load_news_headlines|SentimentIntensityAnalyzer|nltk|src\\.data_access" app/decision.py
```

returned no matches.

The first smoke wrapper timed out while checking port `8765`; matching
Streamlit Python processes were stopped. Subsequent bounded smoke-starts
returned `HTTP_STATUS=200`; the final verification used port `8768` and was
stopped after verification.

## Limitations

- No custom historical performance is shown for user-created mixes by design.
- Mobile pixel-level browser screenshots were not produced.
- Pairwise overlap is a descriptive latest-holdings measure only.
- Effective holdings is descriptive concentration context, not a target or
  suitability rule.

## Challenge Deferral

Phase 4E Challenge remains unimplemented. The Decision CTA can navigate to the
existing Challenge placeholder only. No matched-shrinkage Challenge UI, Challenge
charts, or Challenge artifact loading was added in Phase 4D.

## Phase 4D.1 Visual Authorship and Decision UX

Human browser QA found that the Phase 4D Decision implementation was
analytically correct but still read too much like unlabeled chart output in a
few places. A prior Codex pass was interrupted during this visual polish work by
a `404 Not Found /backend-api/codex/responses/compact` failure, so this pass
first reconstructed the partial on-disk state rather than restarting Phase 4D.

Surviving changes from the interrupted pass were preserved:

- singular/plural narrative grammar:
  - `Your 1 fund sleeve resolves to ...`
  - `Your N fund sleeves resolve to ...`
- direct-label fund-wrapper strips;
- direct-label asset-class strips;
- concise `Allocation %` input label;
- Normalise action hidden when the allocation already totals exactly `100.0%`;
- broad holdings remainder separated from the visible security bars;
- no custom historical mix backtest and no new analytics.

This pass completed the remaining visual authorship work:

- removed stale, inactive Decision-only Vega helpers for fund-wrapper and
  asset-class strip charts from `app/charts.py`;
- removed the unused `top_holdings_display()` helper that still contained the
  old `Other holdings` pseudo-security row;
- kept active Decision holdings, overlap, and method-exposure charts only;
- changed active Decision holdings and overlap chart colours to restrained
  neutral structural tones instead of Signal blue or Evidence gold;
- changed Decision narrative, anatomy connector, and overlap insight styling to
  neutral control tones where the element is structural rather than signal,
  evidence, or action;
- retained salmon only for actual action/selection controls;
- retained the thesis bridge:
  `FUND COUNT != UNDERLYING DIVERSIFICATION`;
- tightened the Evidence Policy first-read copy:
  `Base construction remains primary. SignalScope does not rebuild this custom
  mix from headline sentiment; news evidence acts only as a tested control
  layer.`

Allocation Anatomy now reads as a direct look-through flow:

```text
FUND WRAPPERS -> ASSET CLASSES -> UNDERLYING HOLDINGS
```

For `100% Combined / Equal Weight`, the live app shows:

- wrapper: `Combined / Equal Weight` and `100.0%`;
- asset classes: `Equity 83.3%` and `Crypto 16.7%`;
- underlying holdings: representative securities plus a separate remainder
  statement, `52 additional holdings` and `86.7% combined`, rather than a large
  `Other holdings` bar.

Overlap remains the signature Decision insight and the formula is unchanged:

```text
overlap(A, B) = sum_i min(w_Ai, w_Bi)
```

The two-sleeve overlap copy now leads with the structural interpretation:

`2 fund sleeves, but 83.3% of their latest weight profiles overlap.`

This is explicitly not described as correlation, risk overlap, a forecast,
redundancy, or an allocation recommendation. The `Equity / Equal Weight` plus
`Crypto / Equal Weight` contrast remains `0.0%` ticker overlap.

Tests were updated to match the live UI:

- AppTest now targets repeated `Allocation %` controls by occurrence rather
  than stale `Allocation % for Sleeve N` labels;
- stale tests for removed Decision-only strip Vega specs were removed;
- active Decision chart specs are still validated;
- deterministic coverage now checks singular and plural grammar, direct wrapper
  labels, direct asset-class labels, broad remainder count and percentage,
  absence of `Other holdings` from the visible holding rows, exact Combined EW
  structure, 50/50 Equity+Crypto structure and overlap, 50/50 Equity+Combined
  structure and overlap, unchanged overlap formula, and invalid 90%/110%
  allocations;
- AppTest covers 100% Combined EW, 50/50 Equity+Crypto, 50/50 Equity+Combined,
  a three-fund mix including Maximum Sharpe, invalid underallocation,
  invalid overallocation, Normalise visibility, direct labels, remainder
  treatment, overlap insight, navigation, and all existing journey stages.

Verification after Phase 4D.1:

```text
Focused Decision tests:
17 passed in 6.46s

Full test suite:
97 passed in 19.65s

Hand-in checker:
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.

Bounded Streamlit smoke:
HTTP_STATUS=200

git diff --check -- .
returned no output.

git status --short -- src results
returned no output.
```

Decision runtime guardrail was rechecked. `app/decision.py` contains no custom
return simulation, Sharpe calculation, drawdown calculation, optimiser,
backtest construction, raw data loading, `src.data_access`, VADER, or NLTK
runtime computation.

Phase 4D and Phase 4D.1 are now safe to freeze. Phase 4E Challenge has not been
started.
