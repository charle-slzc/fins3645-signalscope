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

## Phase 4B.3 Visual Authorship and Brand System

### Design Problem

The Fund and Risk pages were technically correct and visually competent, but
still carried common AI-dashboard patterns: repeated rounded cards, symmetric
metric grids, generic dark panels, table-like comparisons, and explanatory
prose that sometimes described implementation rather than investor meaning.

This pass made the Fund/Risk experience feel more authored around the
SignalScope premise: a signal is only useful when the evidence under it is
inspectable.

No Phase 4C analytics or functionality was implemented.

### Motif And Logo Decision

Decision: use a minimal SignalScope logo mark plus the Signal/Evidence Trace
motif.

The mark combines:

- one continuous signal stroke;
- discrete evidence points;
- two horizontal scope rails.

It appears beside the `SignalScope` wordmark in the hero. The same trace motif
is implemented as a reusable CSS/inline-SVG primitive for later Signal/Evidence
views.

### Colour System

The design layer now documents semantic colour roles:

- signal positive and signal negative for later directional signal semantics;
- evidence and uncertainty for support, breadth, and disagreement;
- control for subdued benchmark/placebo language;
- fund-family colours kept separate from signal semantics;
- one SignalScope accent for active journey and CTA states.

Colours were not added merely for decoration.

### Typography

The visual hierarchy now separates:

- product wordmark;
- page question;
- section label;
- primary metric value;
- secondary metric value;
- interpretive copy;
- technical disclosure.

All caps are restricted to tiny labels and compact categorical metadata.
Financial values use strong numeric typography and tabular-friendly sizing.

### Card Reductions

The pass reduced generic card language by:

- replacing the three truth pills with a thin inline truth strip;
- replacing the peer metric boxes with relative-position strips;
- removing the investor-facing startup artifact status line;
- removing the boxed control-panel wrapper in favour of a restrained control
  frame;
- turning holdings notes into editorial dividers rather than more cards.

Cards remain only where they support comprehension, such as the dark fact-sheet
performance strip.

### Navigation Treatment

The journey remains exactly:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

A thin visual journey rail now sits above the keyboard-usable Streamlit
selector. The active stage is marked with the SignalScope accent, giving the
navigation a purposeful analytical workflow feel without replacing the working
control.

### Hero Treatment

The hero now has:

- wordmark plus Signal/Evidence mark;
- preserved line: `See the signal. Inspect the evidence.`;
- dark authored surface;
- Signal/Evidence trace motif;
- inline truth strip preserving OOS, negative sentiment result, and no-advice
  disclosure.

### Peer Comparison Redesign

The selected-vs-family panel now uses relative-position strips:

- selected value marker;
- family median marker;
- selected value and median text;
- metric-specific context.

Volatility explicitly preserves the tradeoff interpretation and does not imply
that higher or lower is automatically "best."

### Risk Hierarchy

Risk now reads more like a fund fact sheet:

- fund identity and small methodological context;
- key performance;
- risk context;
- growth of $1;
- drawdown;
- portfolio structure;
- holdings and concentration;
- exposure;
- historical OOS methodology disclosure.

Annualised return is visually primary, while volatility, Sharpe, and max
drawdown remain visible but secondary.

### Holdings Hierarchy

Broad near-equal funds tell a structure story first:

- number of holdings;
- effective holdings;
- largest position;
- latest holdings date.

Representative bars then support the structure without implying the omitted
positions are one economic bucket.

Concentrated funds invert the emphasis:

- largest holding;
- effective holdings;
- latest holdings date;
- product-level concentration flags;
- dominant holdings visually displayed.

Thresholds and calculations were not changed.

### Exposure Simplification

Combined funds use one custom 100% stacked horizontal sleeve bar with embedded
Crypto and Equity percentages.

Single-family funds use compact inline exposure pills. Redundant Combined
exposure pills and repeated percentage prose were removed.

### Chart System

The risk-return chart now has:

- stronger axis and legend contrast;
- restrained grid;
- selected-fund annotation;
- selected point outline/size emphasis;
- sober fund-family colours distinct from signal semantics.

Growth, drawdown, and holdings continue to use the same restrained chart
language, with Growth remaining the primary performance visual.

### Prose Reduction

Implementation-provenance captions were reduced. Technical details are
centralised in `Historical OOS Methodology`, while chart captions now focus more
on investor meaning.

### Accessibility And Responsive Behaviour

The pass preserved:

- readable contrast;
- colour plus text labels rather than colour-only semantics;
- keyboard-usable Streamlit controls;
- meaningful button labels;
- stacked mobile layouts for metrics, relative-position strips, and truth
  labels;
- exposure labels that remain visible without hover.

Playwright was not installed locally, so browser viewport screenshots were not
available without adding a dependency. Streamlit AppTest render checks covered
the requested Fund and Risk states.

### Visual Self-Audit

Scores after the pass:

- visual polish: 9/10;
- professionalism: 9/10;
- distinctive brand identity: 9/10;
- investor usability: 9/10;
- consistency: 9/10;
- accessibility: 9/10;
- perceived human authorship: 9/10;
- resistance to AI-generated dashboard appearance: 8.5/10.

Remaining weakness: without a real browser screenshot tool, final pixel-level
mobile spacing cannot be visually audited here. The responsive CSS and AppTest
state checks reduce the risk, but a manual browser pass is still useful before
public deployment.

### Phase 4B.3 Verification

Focused app tests:

```text
15 passed in 0.78s
```

Full test suite:

```text
47 passed in 10.06s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Render checks:

```text
FUND_ALL_OK
FUND_COMBINED_OK
RISK_Combined_Equal_Weight_OK
RISK_Combined_Maximum_Sharpe_OK
RISK_Crypto_only_Maximum_Sharpe_OK
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

## Phase 4B.2 Final Micro-Polish

### Objective

Perform the final scoped visual refinement of the Fund and Risk pages before
freezing Phase 4B. This pass was app-layer visual/usability polish only. No
Signal, Evidence, Decision, or Challenge functionality was implemented.

No frozen analytical source, methodology, numerical output, portfolio logic,
return series, weights, cost assumption, or result artifact was changed.

### Brand Contrast Improvements

The Fund-page SignalScope hero was restyled as a dark elevated product surface:

- `SignalScope` now renders in high-contrast light text;
- the eyebrow `EVIDENCE-FIRST DECISION COCKPIT` is more readable but secondary;
- the product line and supporting copy remain restrained, not neon or glossy.

### Chart-Label Improvements

The risk-return map keeps the same values, scales, family focus behaviour, and
selected-fund highlight. The Vega-Lite axis and legend settings were adjusted
for better contrast:

- darker x/y axis titles;
- darker tick labels;
- stronger family and method legend labels;
- selected fund remains larger with a stronger outline.

### Peer Wording Fix

The peer panel no longer says a selected fund is compared with "its 3 family
peers." The helper now reports the family size and the count of other peers, for
example:

`Position within the 3-fund Combined family (2 other peers)`

A deterministic test now covers this wording logic.

### Peer-Panel Restyling

The selected-vs-family context panel was restyled from a light slab to a compact
dark elevated panel with restrained borders, stronger numeric typography,
secondary explanatory text, and a smaller vertical footprint.

It still shows selected annualised return, volatility, and Sharpe versus family
medians.

### Context-Strip Restyling

The Risk context values:

- first live date;
- total turnover;
- trailing estimation observations;

now render as smaller dark context chips consistent with the main performance
strip. They remain secondary to return, volatility, Sharpe, and max drawdown.

### Combined Caveat Restyling

The calendar caveat was changed from a bright light alert into a restrained dark
disclosure with an amber accent. The substance remains:

- Combined funds use the equity trading calendar;
- weekend-only crypto moves are not represented as continuous seven-day crypto
  P&L in the combined fund series.

### Asset-Class Exposure Improvements

Combined fund exposure now uses a custom 100% horizontal stacked sleeve bar with
immediate percentage labels:

- Crypto sleeve;
- Equity sleeve.

The redundant exposure pills were removed for Combined funds. Equity-only and
Crypto-only funds keep compact exposure pills instead of a large 100% chart.

### Startup-Status Removal

The investor-facing Fund page no longer shows:

`Startup evidence pack loaded: ...`

Artifact validation remains in `app/data.py`; only the engineering provenance
line was removed from the primary investor experience.

### Concentrated-Fund QA

Render checks covered:

- Fund / All;
- Fund / Combined focus;
- Risk / Combined Equal Weight as a broad near-equal case;
- Risk / Combined Maximum Sharpe as a concentrated case;
- Risk / Crypto Maximum Sharpe as an additional concentrated case.

The broad case does not imply that remaining holdings are one giant economic
bucket. Concentrated cases show dominant holdings and product-level
concentration flags. Largest holding, effective holdings, and latest holdings
date remain visible.

### Phase 4B.2 Verification

Focused app tests:

```text
15 passed in 1.27s
```

Full test suite:

```text
47 passed in 11.79s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Render checks:

```text
FUND_ALL_OK
FUND_COMBINED_FOCUS_OK
RISK_Combined_Equal_Weight_OK
RISK_Combined_Maximum_Sharpe_OK
RISK_Crypto_only_Maximum_Sharpe_OK
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

## Phase 4B.4 Interaction and Dark-System Hardening

### Objective

Complete the final Phase 4B hardening pass for the Fund and Risk experience
only. This pass locked SignalScope as a dark-first product foundation, improved
chart and text contrast, consolidated navigation, added native risk-return chart
selection, tightened state synchronisation, and reduced remaining generic
dashboard patterns.

Phase 4C did not begin. Signal, Evidence, Decision, and Challenge remain future
journey stages/placeholders.

### Dark-Mode Lock

`.streamlit/config.toml` now sets Streamlit's deployed theme to dark mode with a
SignalScope primary colour. The app no longer relies on the user's operating
system or browser preference for critical readability.

The design system now defines explicit dark-first semantic tokens:

- deep charcoal background;
- elevated dark charcoal surface;
- subtle green-charcoal alternate surface;
- high-contrast off-white primary text;
- readable muted secondary and tertiary text;
- visible dark borders;
- salmon action/active state;
- blue signal family;
- gold evidence family;
- amber warning/disagreement family;
- restrained red negative/risk family;
- neutral grey control/placebo family;
- distinct fund-family colours separate from signal semantics.

### Navigation Consolidation

The duplicate custom journey rail was removed. The app keeps one primary
functional journey control:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

Navigation remains stateful through `st.session_state["view"]`, with
`st.segmented_control` as the primary implementation and `st.radio` as the
fallback for older Streamlit versions.

### Motif And Hero Reduction

The existing SignalScope mark was preserved but reduced in scale. The
Signal/Evidence motif remains the same concept: a continuous signal trace above
discrete evidence points. Its footprint is now smaller and integrated into the
compressed hero instead of spanning a large decorative area.

The hero keeps:

- `SignalScope`;
- `See the signal. Inspect the evidence.`;
- the nine-fund value proposition;
- truth labels for OOS backtest, negative sentiment result, and no-advice;
- the primary `Inspect evidence` action.

Controls now sit closer to the first viewport.

### Spacing And Layout

The CSS now uses a deliberate spacing rhythm around 8px, 16px, 24px, and 40px
steps. Page width is constrained, copy line lengths are capped, and primary
charts retain wide canvases. Redundant page wrappers, light slabs, and unused
engineering status UI were removed.

### Chart Contrast And Dark-Native Vega-Lite

All Fund/Risk Vega-Lite specs now define explicit dark-theme chart settings:

- transparent authored chart background;
- readable axis label and title colours;
- readable legend label and title colours;
- readable annotation text;
- subtle gridlines;
- visible axis domains and ticks;
- dark-compatible tooltip field names with investor-facing language.

The risk-return map, growth chart, drawdown chart, holdings chart, and exposure
chart specs share the same chart-system config instead of relying on Streamlit
theme inheritance.

### Native Chart Click Selection

The risk-return map now uses Streamlit's native Vega-Lite selection API:

```python
st.vega_lite_chart(
    chart_frame,
    charts.risk_return_spec(),
    width="stretch",
    key="risk_return_map",
    on_select="rerun",
    selection_mode=charts.FUND_SELECTION_NAME,
)
```

The layered chart defines a named point selection using stable fields:

- `fund_family`;
- `method`.

A pure helper parses Streamlit selection events and validates the selected
fund against `performance_metrics.csv`. Clicking a fund point updates the
selected fund state, reruns the app, updates the dropdown, updates the chart
highlight and direct label, updates the relative-position panel, and makes
`Open fact sheet` point to the clicked fund.

No JavaScript hack was used.

### Filter Behaviour

Family filtering remains view-only and does not alter analytical data:

- `All` shows all nine funds;
- `Equity` shows the three equity-only funds;
- `Crypto` shows the three crypto-only funds;
- `Combined` shows the three combined funds.

Method filtering visibly changes the risk-return map:

- `All` shows all methods;
- `Equal Weight` shows three Equal Weight funds;
- `Minimum Variance` shows three Minimum Variance funds;
- `Maximum Sharpe` shows three Maximum Sharpe funds.

Family and Method filters compose correctly. For example,
`Combined + Maximum Sharpe` yields the single Combined Maximum Sharpe fund.
If the previous selected fund is outside the visible filtered universe, the app
selects a valid visible fund deterministically.

### Selected-Fund Synchronisation

The selected-fund state model remains:

- `st.session_state["selected_fund_family"]`;
- `st.session_state["selected_fund_method"]`.

The manual dropdown, chart click selection, selected chart marker, direct chart
annotation, peer comparison, `Open fact sheet`, and Risk page all read from the
same state. Stale selections are rejected or replaced with a valid visible fund.

### Relative Position

The relative-position component was preserved. It now sits on the dark system
without an extra card wrapper and distinguishes:

- family median: quiet gold vertical tick;
- selected fund: stronger salmon circular marker.

The dynamic peer wording is preserved, for example:

`Position within the 3-fund Combined family (2 other peers)`

Volatility wording continues to avoid implying that higher volatility is better.

### Holdings Layout

The Risk holdings section now uses the available width more intentionally:

- broad portfolios place the representative holdings visual beside context
  values for holding count, effective holdings, largest position, and latest
  saved date;
- broad-holdings copy is shorter and editorial;
- concentrated funds put concentration flags first, then largest holding and
  effective-holdings context, beside the top-position chart.

No saved weight, concentration, or effective-holdings calculation changed.

### Exposure Simplification

Combined funds show one 100% stacked exposure bar with embedded Crypto and
Equity percentages.

Single-family funds show one compact statement such as `100% Equity` or
`100% Crypto`.

Duplicated pills and repeated exposure prose were removed.

### Button And Navigation QA

AppTest exercised:

- all journey stages;
- `Fund -> Risk`;
- `Risk -> Fund`;
- `Fund -> Evidence`;
- `Risk -> Signal`;
- Family filter sequence;
- Method filter sequence;
- `Combined + Maximum Sharpe`;
- manual selected-fund change into Risk.

Native chart event simulation was not practical through AppTest, so the
selection-event parser is covered by deterministic unit tests.

### Phase 4B.4 Verification

Focused app tests:

```text
24 passed in 3.50s
```

Full test suite:

```text
56 passed in 11.80s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
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

App-layer runtime dependency scan confirmed no `data_access`, raw hosted-data
loader calls, NLTK/VADER, optimiser, or backtest recomputation tokens in
`streamlit_app.py` or `app/`. The only app-layer reference to
`headline_sentiment_scores.csv` remains the explicit never-load guardrail in
`app/data.py`.

Playwright was not installed locally, so pixel-level browser screenshots were
not available without adding a dependency. Streamlit AppTest render/state checks
and bounded HTTP smoke-start were used for local verification.

## Phase 4B.4 Risk-Return Map Regression Repair

### Objective

Perform a surgical repair of the Fund-page risk-return map after the Phase 4B.4
interaction hardening caused the chart area to render blank while the rest of
the Fund and Risk pages continued to work.

No redesign was performed. The approved dark SignalScope visual system,
single journey navigation, controls, Relative Position component, and Risk page
were preserved. Phase 4C did not begin.

### Diagnosis

The data path was not the cause. The dataframe passed to the risk-return chart
was non-empty for all required filter states:

- `All / All`: 9 funds;
- `Equity / All`: 3 funds;
- `Crypto / All`: 3 funds;
- `Combined / All`: 3 funds;
- `All / Equal Weight`: 3 funds;
- `All / Minimum Variance`: 3 funds;
- `All / Maximum Sharpe`: 3 funds;
- `Combined / Maximum Sharpe`: 1 fund.

The root cause was an invalid Vega-Lite encoding introduced during selected
point hardening. The risk-return map used a conditional `size` encoding while
also setting `legend: None` on that same value channel. Vega-Lite schema
validation rejected the spec with:

```text
Additional properties are not allowed ('value' was unexpected)
```

That invalid client-side spec explains why Streamlit could render the rest of
the page while the chart marks disappeared.

### Repair

Files changed for this repair:

- `app/charts.py`;
- `app/funds.py`;
- `tests/test_app_funds.py`;
- this AI log.

The invalid `legend: None` property was removed from the conditional `size`
encoding.

The layered selection design was also simplified for reliability:

- the selectable point layer is now the primary chart layer;
- the native selection parameter is defined directly on that point layer;
- the selection field is a stable deterministic `fund_key`;
- the selected-state data flag was renamed from `selected` to `is_selected` to
  avoid possible ambiguity with Vega selection internals;
- the selected fund remains visually clear through larger point size, stronger
  salmon stroke, and a direct label.

Native click selection was retained. The Streamlit call still uses:

```python
st.vega_lite_chart(..., key="risk_return_map", on_select="rerun",
                   selection_mode=charts.FUND_SELECTION_NAME)
```

The event parser now handles both the earlier `fund_family` + `method` event
shape and the repaired `fund_key` event shape.

### Verification

Focused tests:

```text
19 passed in 1.84s
```

The focused tests now include:

- chart input row counts for every required Family/Method filter state;
- selected fund visibility in the chart input;
- Vega-Lite JSON serialisation;
- Altair/Vega-Lite schema validation of the risk-return spec;
- valid x/y encodings;
- named native selection on `fund_key`;
- selection-event parsing for native event shapes.

Full test suite:

```text
57 passed in 10.82s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

HTTP smoke:

```text
HTTP_STATUS=200
```

Rendered chart verification:

- Streamlit AppTest renders the Fund page with one Vega-Lite chart element and
  no exceptions;
- the chart proto contains the repaired valid spec, the `fund_pick` selection
  mode, `x = volatility_pct`, `y = return_pct`, and the Fund chart data;
- Altair validates the exact risk-return spec against the Vega-Lite schema;
- All/All chart input contains nine plotted fund rows and one selected row.

Headless Chrome/Edge screenshots were attempted, but this host produced browser
connection-refused screenshots despite PowerShell confirming the Streamlit
server returned HTTP 200. Temporary screenshots, logs, and browser profiles were
removed. The reliable automated render evidence is therefore AppTest chart
presence plus Vega-Lite schema validation and non-empty plotted data.

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

## Phase 4B.1 Visual Product Polish

### Objective

Perform a scoped visual product polish pass based on direct review of the
rendered Fund and Risk pages. The task was investor usability and hierarchy
only. No methodology, analytical numbers, frozen source files, or frozen result
artifacts were changed.

### Fund Page Changes

The Fund page was tightened so the eye moves:

`hero -> controls -> risk-return map -> interpretation -> selected peer context`

Changes made:

- grouped Family, Method, selected fund, and `Open fact sheet` in a centred
  control area;
- kept wide enough chart space while avoiding controls that feel disconnected on
  large monitors;
- retained all nine funds when Family is `All`;
- used the Family filter as the focus mechanism for the risk-return map, so
  Equity, Crypto, and Combined views each receive a readable scale without
  changing data;
- replaced six definition cards with a compact `How to read this comparison`
  disclosure;
- replaced the ranking-table snapshot with selected-fund context versus the
  selected fund's family medians.

The visual focus copy explicitly states that the Family focus changes only the
displayed comparison scale and not the backtest.

### Risk Page Changes

The Risk fact sheet was restyled to reduce high-contrast white card clutter:

- performance strip now uses dark elevated fact-sheet surfaces;
- first-live date, turnover, and estimation window moved into a compact context
  strip;
- Combined calendar caveat remains clearly visible;
- growth remains the primary performance visual;
- drawdown remains secondary;
- holdings now adapt to portfolio structure;
- Combined exposure uses a clean 100% stacked horizontal bar with percentage
  labels, while single-family funds use compact exposure pills.

### Adaptive Holdings Treatment

The previous display-only `Other holdings` bar could look like a large economic
bucket for broad near-equal funds. Phase 4B.1 adds adaptive presentation:

- broad near-equal funds show representative positions plus a statement that the
  remaining positions are similar or smaller weights, not one bucket;
- concentrated funds show top-position bars and explicit product-level
  concentration flags;
- the saved `fund_weights.csv` artifact remains unchanged.

The concentration flags remain display heuristics:

- top position above 25%;
- effective holdings below 5.

They are labelled as product-level concentration flags rather than academically
validated danger thresholds.

### Files Changed In 4B.1

- `app/funds.py`
- `app/charts.py`
- `app/components.py`
- `app/design.py`
- `tests/test_app_funds.py`
- `ai/08_station4_phase4b_funds_risk.md`

No Signal, Evidence, Decision, or Challenge functionality was implemented.

### Additional Tests

Added or extended helper tests for:

- broad near-equal fund detection;
- representative-holdings display;
- selected-fund family-peer median comparison.

### Phase 4B.1 Verification

Focused app tests:

```text
15 passed in 1.30s
```

Full test suite:

```text
47 passed in 11.37s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Render checks:

```text
FUND_OK
DIVERSIFIED_RISK_OK
CONCENTRATED_RISK_OK
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
