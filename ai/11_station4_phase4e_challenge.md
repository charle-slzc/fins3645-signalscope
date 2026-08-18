# AI Log 11 - Station 4 Phase 4E Challenge

## Objective

Implement only Station 4 Phase 4E:

`Challenge - Model Falsification`

Investor question:

`Does the cleverer model actually earn its complexity?`

No analytical source files under `src/` and no saved analytical artifacts under
`results/` were modified. No new analytics, parameter tuning, report work,
deployment work, raw data loading, runtime VADER/NLTK scoring, optimisation, or
backtest rebuilding was introduced.

## Falsification Thesis

SignalScope challenges its own Confidence Lens. The page asks whether the
evidence-aware dynamic rule earns its complexity, or whether a simpler constant
shrinkage control can explain much of the economic effect.

The investor-facing conclusion is deliberately skeptical:

- sentiment did not beat Base in the primary comparison;
- Confidence reduced sentiment-induced portfolio movement relative to raw
  Standard Sentiment;
- dynamic Confidence was not clearly economically necessary because the matched
  constant control explained much of the shrinkage effect;
- the surviving value is selective signal governance, not alpha.

## Rubric Purpose

Innovation:

- self-falsification of the project's own innovation;
- matched-strength placebo rather than a weak unscaled comparison;
- surviving selective-governance insight.

Technical rigour:

- precomputed falsification artifacts only;
- no return-informed placebo fit;
- negative results preserved visibly.

Investor usability:

- three-question verdict;
- plain-language matched constant control;
- case-level examples instead of a research table wall.

Honesty:

- no alpha claim;
- economic necessity rejected;
- simpler control acknowledged.

## Artifacts Used

Challenge lazy-loads:

- `results/tables/confidence_placebo_comparison.csv` - 5,056 bytes;
- `results/tables/confidence_placebo_turnover_decomposition.csv` - 828 bytes;
- `results/tables/confidence_placebo_selectivity.csv` - 107,455 bytes;
- `results/tables/confidence_placebo_quadrants.csv` - 953 bytes;
- `results/tables/confidence_placebo_cases.csv` - 3,677 bytes.

Optional lazy registry support was also added for:

- `results/tables/confidence_placebo_sector_year.csv` - 1,002 bytes;
- `results/data/fusion_placebo_returns.csv` - 847,232 bytes.

The startup artifact set was not changed. `results/data/headline_sentiment_scores.csv`
remains explicitly forbidden in the runtime denylist.

## Exact Primary Performance Comparison

Primary base method: `Minimum Variance`.

| Overlay | Annualised return | Annualised volatility | Sharpe | Max drawdown | Total turnover |
|---|---:|---:|---:|---:|---:|
| Base | 0.0515178650673677 | 0.1275223135861384 | 0.4039909849390289 | -0.1556036980120373 | 11.5191438254282 |
| Standard Sentiment | 0.0497588116169598 | 0.1277812516462894 | 0.3894061998601869 | -0.1604337690402629 | 12.046789706438036 |
| Matched-Shrinkage Placebo | 0.0504566451973735 | 0.1276570637941086 | 0.3952514941026097 | -0.1586063242671266 | 11.802349627041298 |
| SignalScope Confidence Lens | 0.0500286381113825 | 0.127680186610631 | 0.3918277333346022 | -0.1591402037855162 | 11.807426243797446 |

Primary interpretation:

`Adding headline sentiment did not improve the primary fund's OOS Sharpe. Base
remained strongest on Sharpe.`

## Disturbance Result

Primary `Minimum Variance` turnover decomposition:

- Base total turnover: `11.5191438254282`;
- Standard total turnover: `12.046789706438036`;
- Matched constant total turnover: `11.802349627041298`;
- Confidence total turnover: `11.807426243797446`;
- Standard-to-Confidence turnover reduction: `0.2393634626405916`;
- constant shrinkage explained percent: `102.1208820678576`.

The page frames this as less sentiment-induced portfolio movement, not as an
automatic improvement.

## Matched-Strength Verification

From `confidence_placebo_selectivity.csv`:

- valid rebalance-sector observations: `360`;
- `C_match`: `0.6322361773345248`;
- mean confidence: `0.6591585049725245`;
- Standard absolute tilt sum: `27.66598810891609`;
- Confidence absolute tilt sum: `17.491438564163516`;
- Placebo absolute tilt sum: `17.491438564163516`;
- Placebo minus Confidence absolute tilt: `0.0`.

This supports the primary matched-strength visual:

`Confidence = Matched constant`

for total absolute pre-normalisation signal tilt in the saved artifact.

## No Return-Informed Matching

The UI explains that the matching constant is derived from saved signal
magnitude and evidence confidence fields, not OOS return performance.

The implementation also exposes a deterministic helper check:

- `confidence_placebo_selectivity.csv` contains no return, Sharpe, performance,
  or drawdown columns;
- every saved case row says:
  `deterministic from signal/evidence state only; no subsequent returns used`.

The code-level definition previously inspected in `src/placebo.py` is:

`C_match = sum(abs(Z_star) * C) / sum(abs(Z_star))`

No `src/` code was edited.

## Selectivity Result

From `confidence_placebo_selectivity.csv`:

- 148 of 360 observations are below `C_match`;
- below share: `0.4111111111111111`;
- 212 of 360 observations are above `C_match`;
- above share: `0.5888888888888889`;
- max selective deviation: `0.0583054117701456`.

Investor interpretation:

- below matched constant: more conservative than constant shrinkage;
- above matched constant: more permissive than constant shrinkage;
- neither side is labelled good or bad.

## Case Selection

The primary saved case pair uses `Minimum Variance`.

Extra attenuation:

- case type: `weak_evidence_more_attenuation_than_placebo`;
- sector/date: `Utilities / 2021-06-01`;
- `z_star`: `2.0`;
- confidence: `0.3407091184837965`;
- `C_match`: `0.6322361773345248`;
- matched constant multiplier: `1.1264472354669048`;
- Confidence multiplier: `1.0681418236967593`;
- selective deviation: `0.0583054117701456`.

Extra preservation:

- case type: `strong_evidence_less_attenuation_than_placebo`;
- sector/date: `Financials / 2023-09-01`;
- `z_star`: `-1.9552305657685027`;
- confidence: `0.8555335717253036`;
- `C_match`: `0.6322361773345248`;
- matched constant multiplier: `0.8763832501290901`;
- Confidence multiplier: `0.8327234610521587`;
- selective deviation: `0.0436597890769315`.

These two cases support the surviving insight:

`Same total signal strength. Different decisions about where to trust it.`

## H1-H4 Verdicts

Research verdicts shown only under progressive disclosure:

| Hypothesis | Claim | Verdict |
|---|---|---|
| H1 | performance improvement | REJECT |
| H2 | reduced sentiment-induced disturbance | SUPPORT |
| H3 | dynamic evidence-state distinction | SUPPORT |
| H4 | economic necessity | REJECT |

## Maximum Sharpe Robustness

Shown only under progressive disclosure:

| Overlay | Annualised return | Annualised volatility | Sharpe | Max drawdown | Total turnover |
|---|---:|---:|---:|---:|---:|
| Base | 0.085413015875011 | 0.1821152568786394 | 0.4690052735775443 | -0.2641262522687944 | 24.908840121459143 |
| Standard Sentiment | 0.0852233727112252 | 0.1840911588970649 | 0.4629411494925627 | -0.2621956908681887 | 25.058270328965065 |
| Matched-Shrinkage Placebo | 0.0853380303290158 | 0.1833083253125819 | 0.4655436690259177 | -0.2628679456929653 | 24.968792497912368 |
| SignalScope Confidence Lens | 0.0848249087194275 | 0.1836895070607652 | 0.4617841817789139 | -0.2633050552023057 | 25.006839029807654 |

The robustness result points in the same direction: Base Sharpe remains higher
than sentiment variants.

## Design Decisions

- Replaced the Challenge placeholder with a forensic, restrained final page.
- Used an editorial numbered verdict stack rather than giant traffic-light
  cards.
- Used neutral bars for performance comparison; Base is visible and not hidden.
- Introduced the matched constant control in plain language before showing
  formulas.
- Put H1-H4 and formulas under expanders.
- Added navigation actions: `Back to Decision`, `Inspect Evidence Lens`, and
  `Compare funds`.
- Avoided victory-lap language, green/red winner colouring, and alpha claims.

## Files Changed

- `app/challenge.py`
- `app/charts.py`
- `app/components.py`
- `app/data.py`
- `app/design.py`
- `tests/test_app_challenge.py`
- `tests/test_app_decision.py`
- `ai/11_station4_phase4e_challenge.md`

No files under `src/` or `results/` were modified.

## Tests Added

Added `tests/test_app_challenge.py` for:

- lazy Challenge artifact registration and forbidden headline artifact guard;
- exact Base/Standard/Placebo/Confidence primary metrics;
- exact Maximum Sharpe robustness metrics;
- exact `C_match`;
- matched total absolute tilt equality;
- no return-informed matching where inferable from saved metadata;
- H1-H4 mapping;
- below/above matched constant percentages;
- real extra-attenuation case;
- real extra-preservation case;
- Challenge language/runtime guardrails;
- Challenge chart spec validation;
- Challenge AppTest render and navigation.

Updated `tests/test_app_decision.py` so Decision -> Challenge now expects the
implemented Challenge page rather than the Phase 4E placeholder.

## Verification

Focused Challenge tests:

```text
12 passed in 5.01s
```

Full test suite:

```text
108 passed in 21.14s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Bounded Streamlit smoke:

```text
HTTP_STATUS=200
```

Frozen analytics verification:

```text
git status --short -- src results
```

returned no output.

Whitespace check:

```text
git diff --check -- .
```

returned no output.

Runtime dependency scan:

```text
rg -n "src\\.data_access|from src import data_access|load_equity_prices|load_crypto_prices|load_news_headlines|nltk|SentimentIntensityAnalyzer|scipy\\.optimize|run_backtest|optimise|optimize|backtest_overlay_returns|calculate_shrinkage_constants|build_placebo_suite|headline_sentiment_scores" streamlit_app.py app
```

returned only approved presentation/guardrail occurrences:

- `app/data.py` denylist entry for `headline_sentiment_scores.csv`;
- display-only wording for optimiser context in existing Fund/Risk copy;
- display-only wording in Challenge robustness disclosure.

No runtime raw-data loading, VADER/NLTK computation, optimiser, backtest, or
placebo fitting call was introduced.

## Limitations

- The Challenge page is still a product summary, not a full research appendix.
  It intentionally does not show all Phase 2C rows by default.
- The app does not display a full return-path detail chart for Challenge, though
  `fusion_placebo_returns.csv` is available in the lazy registry if later needed.
- Pixel-level browser screenshot checks were not performed in this phase.
- The known hand-in reminders remain: remove generated cache files before zip
  and add the final report PDF later.

## Freeze Readiness

Phase 4E is ready to freeze if the student accepts the product framing:

`REVISE, not accept or abandon.`

The final Challenge page makes the negative result prominent, explains the
matched constant control, preserves Base as the reference point, and ties the
surviving value back to selective signal governance.

## Phase 4E.1 Visual and Interpretation QA

### Objective

Perform only a final Challenge visual and interpretation fix pass after human
screenshot QA. The concept and three-question Challenge structure were already
approved, so this pass deliberately avoided a broader redesign and did not begin
Phase 4F.

No `src/` files, no `results/` files, no frozen Phase 2C methodology, no
analytics, and no parameters were changed.

### Human QA Findings

Three issues were reported:

1. The primary `102.1%` turnover wording was mathematically defensible but
   awkward for an investor page.
2. The case visual compared raw pre-normalisation multipliers around `1.0`,
   which could mislead users for negative-direction signals.
3. The `Where Confidence differed` Vega-Lite split could appear blank or
   under-rendered in screenshots, leaving a large empty region.

### 102.1% Wording Correction

The primary verdict no longer says that the matched constant control explains
`102.1%` of the primary turnover reduction.

Primary wording now says:

`The simpler constant control reproduced slightly more than the turnover
reduction achieved by Confidence. This weakens the case that dynamic Confidence
was economically necessary.`

Exact technical detail remains under disclosure:

- Standard turnover: `12.046789706438036`;
- Confidence turnover: `11.807426243797446`;
- Confidence reduction: `0.2393634626405916`;
- constant-shrinkage share of that reduction:
  `102.1208820678576%`.

The value is not described as accuracy, predictive power, model fit, or
probability.

### Matched-Strength Precision Treatment

The first-read matched-strength section now uses compact display precision:

`Confidence 17.49 = matched constant 17.49. Difference: 0.00.`

Exact saved values remain in technical disclosure:

- Confidence absolute tilt sum: `17.491438564163516`;
- matched constant absolute tilt sum: `17.491438564163516`;
- difference: `0.0`.

The intent is to make the key investor idea immediate:

`The two rules use the same total amount of sentiment.`

### Signal-Magnitude Presentation Rule

The primary case visual no longer uses raw multipliers.

Presentation transformation:

`signal_magnitude = abs(multiplier - 1.0)`

For chart direction:

- positive signal: magnitude extends right;
- negative signal: magnitude extends left.

This is a view-layer transformation of already-saved multiplier fields. It does
not create a new analytical result and does not alter Phase 2C.

Raw multipliers remain only in technical disclosure.

### Utilities Extra-Attenuation Treatment

Saved case:

- sector/date: `Utilities / 2021-06-01`;
- signal direction: positive;
- matched constant multiplier: `1.1264472354669048`;
- Confidence multiplier: `1.0681418236967593`;
- matched signal magnitude: `0.1264472354669048`, displayed as `+12.6%`;
- Confidence signal magnitude: `0.0681418236967593`, displayed as `+6.8%`.

Investor interpretation:

`Weak evidence caused Confidence to mute more of the positive signal than the
matched constant.`

### Financials Extra-Preservation Treatment

Saved case:

- sector/date: `Financials / 2023-09-01`;
- signal direction: negative;
- matched constant multiplier: `0.8763832501290901`;
- Confidence multiplier: `0.8327234610521587`;
- matched signal magnitude: `0.1236167498709099`, displayed as leftward
  `12.4%`;
- Confidence signal magnitude: `0.1672765389478413`, displayed as leftward
  `16.7%`.

The UI and tests now make explicit that negative-direction preservation is read
from distance from neutral, not raw multiplier ordering. Confidence has a lower
raw multiplier than the matched constant in this case, but it preserves more of
the negative directional signal because its magnitude from neutral is larger.

Investor interpretation:

`Stronger evidence caused Confidence to preserve more of the negative signal
than the matched constant.`

### Where Confidence Differed Chart Audit

The potentially blank Vega-Lite normalized bar was replaced in the primary UI
with a compact HTML split bar and direct labels:

- `41.1%` more conservative than the matched constant;
- `58.9%` more permissive than the matched constant.

Primary wording:

`41.1% of valid observations were more conservative than the matched constant;
58.9% were more permissive.`

Follow-up:

`These are evidence states, not good/bad labels.`

This avoids a large empty plot region while preserving the exact saved
selectivity counts:

- 148 of 360 below the matched constant;
- 212 of 360 above the matched constant.

### What Survived

The surviving-insight section remains restrained:

`Same total signal strength. Different decisions about where to trust it.`

It now adds that Confidence did not improve the primary fund's OOS Sharpe and a
simpler constant rule reproduced the economic shrinkage. The surviving role is
narrower selective governance: changing where the weak textual signal is muted
or preserved.

### Tests

Updated `tests/test_app_challenge.py` to cover:

- Base Sharpe remains highest among the four primary variants;
- primary `explains 102.1%` copy is absent;
- exact `102.1208820678576%` remains available under technical disclosure;
- `signal_magnitude(multiplier) = abs(multiplier - 1)`;
- Utilities matched magnitude `12.6%` and Confidence magnitude `6.8%`;
- Utilities renders as extra attenuation;
- Financials matched magnitude `12.4%` and Confidence magnitude `16.7%`;
- Financials renders as extra preservation;
- negative-direction preservation is based on signal magnitude, not raw
  multiplier ordering;
- primary case visual frame does not expose raw `multiplier`;
- `41.1%` / `58.9%` selectivity values render;
- `Where Confidence differed` contains a real compact split visual;
- `REVISE` remains the recommendation;
- Challenge static guardrails against alpha, probability, prediction, runtime
  analytics, and return-informed fitting remain intact.

Focused Challenge tests:

```text
11 passed in 4.14s
```

### Verification

Final verification after this QA pass:

```text
python.exe -m pytest -q
108 passed

python.exe scripts/check_handin.py
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

Runtime scan showed no Challenge runtime use of raw data, `data_access`,
VADER/NLTK, optimiser code, backtesting, parameter tuning, or return-informed
placebo fitting. The only app-layer occurrences of flagged terms remain
display-only wording or the existing forbidden-headline-artifact denylist.

### Freeze Assessment

Phase 4E is now safe to freeze:

1. Base remains visually strongest.
2. The `102.1%` result is interpreted safely.
3. Matched signal-strength equality is obvious at first read.
4. Case visuals use direction-aware signal magnitude.
5. The Financials negative preservation case cannot be misread from raw
   multiplier ordering.
6. Utilities attenuation is intuitive.
7. `Where Confidence differed` is no longer visually blank.
8. `WHAT SURVIVED` remains restrained.
9. `REVISE` remains the recommendation.
10. Phase 4F was not started.
