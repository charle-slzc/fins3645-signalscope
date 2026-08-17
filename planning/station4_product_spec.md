# Station 4 Product Implementation Specification

Product: SignalScope  
Core product line: "See the signal. Inspect the evidence."  
Approved concept: evidence-first decision cockpit with guided storytelling.  
Approved journey: Fund -> Risk -> Signal -> Evidence -> Decision -> Challenge.

This specification is the implementation contract for Station 4. The analytical
research pipeline is frozen. Station 4 must translate existing results into a
deployed investor product without changing analytical methodology, analytical
source files, or existing analytical result artifacts.

Final red-team status: REVISE, then implement. This version incorporates the
approved red-team revisions and is the final product implementation
specification for Station 4.

## 1. Product Principles

1. Investable product first, research depth second.
2. Every sentiment signal should have an evidence trace.
3. The app must distinguish sentiment direction from evidence confidence.
4. Negative results and falsification are product trust features.
5. Do not imply alpha, forecasting certainty, truth confidence, predictive
   accuracy, or investment advice.
6. Complexity must be progressive, not dumped on the landing screen.
7. Every chart must answer one investor question.
8. The user should never need to understand the code or research pipeline to
   understand the product.
9. The product should feel distinctive without imitating Bloomberg, Robinhood,
   Apple, or another identifiable interface.
10. The product wins if the first read is simple and the rigor is progressively
    revealed. It loses if it opens like a research notebook with nicer charts.

## 2. Locked Product Decisions

- Concept: evidence-first decision cockpit with guided storytelling.
- Core line: "See the signal. Inspect the evidence."
- Journey: Fund -> Risk -> Signal -> Evidence -> Decision -> Challenge.
- Core interactive charts should be rebuilt from compact CSVs where feasible.
- Research-level PNGs may be reused only where rebuilding them adds no investor
  value.
- Initial runtime data budget: target about 3.43 MB before deeper or lazy views
  are opened.
- Never load `results/data/headline_sentiment_scores.csv` in Streamlit.
- Do not load raw data through `src/data_access.py` at runtime.
- No runtime VADER/NLTK, optimisation, backtesting, sentiment scoring, or full
  research recomputation.
- Do not show formulas, H1-H4 labels, methodology tables, or placebo language
  above the fold.

## 3. Information Architecture

Use journey navigation rather than generic tabs. The top-level state should be a
segmented journey selector:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

Implementation later may use `st.radio(horizontal=True)`, `st.segmented_control`
when available, or a small custom button row. Do not use generic tabs named
Home, Funds, Sentiment, Data, or About. Use stateful conditional rendering
rather than eagerly rendered tabs.

### Screen: Fund

- Investor question: Which systematic funds can I invest in?
- Purpose: establish the investable product set before exposing research depth.
- Components: landing summary, FundSelector, RiskReturnMap, compact fund ranking,
  method caveat strip.
- Data artifacts: `performance_metrics.csv`, `fund_returns.csv`,
  `fund_weights.csv`, `asset_class_exposure.csv`.
- Interaction: choose family filters, choose method focus, click a fund to open
  its fact sheet.
- Takeaway: SignalScope offers Equity, Crypto, and Combined fund families across
  Equal Weight, Minimum Variance, and Maximum Sharpe, all evaluated out of
  sample.
- Next action: open the selected fund's Risk view.

### Screen: Risk

- Investor question: What am I buying, and what risks come with it?
- Purpose: present the selected fund as a fact sheet, not as a row in a table.
- Components: MetricStrip, GrowthChart, DrawdownChart, HoldingsPanel,
  ExposureBar, ConcentrationWarning, MethodologyDisclosure.
- Data artifacts: `fund_returns.csv`, `fund_weights.csv`,
  `performance_metrics.csv`, `asset_class_exposure.csv`, `first_live_dates.csv`.
- Interaction: selected fund persists from Fund view; user can switch method or
  family; hover charts; expand method assumptions.
- Takeaway: return, volatility, drawdown, turnover, exposure, and concentration
  are visible together.
- Next action: inspect the news signal affecting the equity sleeve.

### Screen: Signal

- Investor question: What does the news say across equity sectors?
- Purpose: show the standalone equal-ticker sector sentiment index and the
  reason equal-ticker aggregation was used. Signal answers "What does the news
  say over time?" and should provide context only.
- Components: sector sentiment time-series, sector selector, compact evidence
  context, weighting disagreement callout.
- Data artifacts: `sector_sentiment_index.csv`,
  `sentiment_weighting_disagreements.csv`.
- Interaction: choose sector and period; compare sector sentiment with compact
  evidence context such as active ticker count and headline count.
- Takeaway: the news signal is a headline-based sentiment reading, not ground
  truth or a forecast.
- Next action: open the Evidence view to inspect support for a chosen signal.

### Screen: Evidence

- Investor question: How well does the available evidence support the sentiment
  reading?
- Purpose: make the flagship distinction between sentiment direction and
  evidence confidence. Evidence answers "How well supported is this particular
  reading?" and should not reproduce another sentiment line chart.
- Components: SignalEvidenceLadder, CancellationExplorer,
  VolumeBreadthPanel, optional sector/date selector.
- Data artifacts: `sector_sentiment_confidence.csv`,
  `sentiment_disagreement_examples.csv`, `sentiment_candidate_cases.csv`.
- Interaction: choose sector and rebalance date for the ladder; choose example
  mode for neutrality/cancellation and volume/breadth.
- Takeaway: the same sentiment direction can imply different allocation changes
  depending on breadth and agreement.
- Next action: move to Decision to compare allocation effects.

### Screen: Decision

- Investor question: What allocation would I choose, and how would it have
  behaved historically?
- Purpose: satisfy the allocation requirement without implying forecasting.
- Components: AllocationBuilder, blended growth and drawdown, contribution by
  fund, blended equity/crypto exposure, disclosure strip.
- Data artifacts: `fund_returns.csv`, `fund_weights.csv`,
  `asset_class_exposure.csv`, `performance_metrics.csv`.
- Interaction: select 2-5 precomputed funds, enter capital, adjust weights to
  sum to 100 percent, view blended historical OOS behavior.
- Takeaway: allocation changes risk composition; historical OOS performance is
  descriptive, not predictive.
- Next action: open Challenge to test whether the sentiment innovation survived
  falsification.

### Screen: Challenge

- Investor question: Did the sentiment innovation really add investment value?
- Purpose: convert negative results into trust.
- Components: ModelChallengePanel, three investor challenge cards, compact
  surviving-insight panel, expandable technical details.
- Data artifacts: `confidence_placebo_comparison.csv`,
  `confidence_placebo_turnover_decomposition.csv`,
  `confidence_placebo_cases.csv`, `confidence_placebo_quadrants.csv`.
- Interaction: switch between Minimum Variance and Maximum Sharpe; reveal the
  matched constant-shrinkage control only after the primary investor story;
  inspect where dynamic confidence differs from the constant control.
- Takeaway: SignalScope is not an alpha-marketing dashboard. The Confidence Lens
  did not beat the Base portfolio, but it does change which evidence states are
  attenuated after aggregate signal strength is matched.
- Next action: return to Fund or Decision with a more skeptical view of the
  signal.

## 4. Landing Experience

The first screen must establish the product in about 10 seconds.

### Hero Copy

Title:

`SignalScope`

Line:

`See the signal. Inspect the evidence.`

Supporting copy:

`Compare nine systematic funds, inspect risk and holdings, then test whether
news sentiment deserves trust.`

Truth labels:

- `Historical OOS backtest`
- `Sentiment did not beat Base`
- `No forecast or investment advice`

### Primary Visual

Use a split "signal versus evidence" hero:

- left side: compact risk-return scatter for the nine investable funds;
- right side: mini evidence trace showing News direction -> ticker coverage ->
  agreement -> confidence-adjusted allocation effect.

This must be interactive or data-derived, not a decorative hero image.

### First User Action

Primary action: `Compare funds`.  
Secondary action: `Inspect evidence`.

### Do Not Put Above The Fold

- raw tables;
- VADER methodology;
- model formulas;
- H1-H4 labels;
- placebo terminology;
- methodology tables;
- full artifact manifests;
- research diagnostics;
- headline-level data;
- generic "this app" implementation copy;
- any alpha, forecast, or "best investment" claim.

## 5. Fund Comparison

### Coverage

Families:

- Equity-only
- Crypto-only
- Combined

Methods:

- Equal Weight
- Minimum Variance
- Maximum Sharpe

### Primary Comparison Chart

Use a risk-return map:

- x-axis: net annualised volatility;
- y-axis: net annualised return;
- marker color: family;
- marker shape or border: method type, benchmark versus optimisation;
- marker size or halo: absolute max drawdown or total turnover;
- tooltip: Sharpe, max drawdown, total turnover, first live date, OOS sample.

This makes the comparison visual before showing detailed metrics.

### Selection Controls

- family filter: All, Equity-only, Crypto-only, Combined;
- method filter: All, Equal Weight, Minimum Variance, Maximum Sharpe;
- rank by: Sharpe, annualised return, max drawdown, volatility, turnover,
  concentration;
- selected fund persists across screens.

### Ranking Behaviour

Show a compact ranked list below the chart, but not as the primary interface.
Each row should read like a fund tile:

`Combined / Maximum Sharpe | Sharpe 0.980 | Return 24.1% | Vol 24.6% | Max DD -26.6% | Turnover 24.6x`

### Caveats

Visible caveat strip:

`Out-of-sample backtest, 2021-2023. Monthly rebalance. Long-only and fully
invested. 10 bps cost per dollar of turnover. Historical performance is not a
forecast.`

### Investor-Friendly Metric Labels

Use these labels consistently in fund comparison, fact sheets, allocation, and
Challenge summaries:

| Metric | Investor-facing interpretation |
|---|---|
| Annualised return | historical OOS return, not expected return |
| Sharpe | return per unit of volatility |
| Max drawdown | worst peak-to-trough fall |
| Turnover | trading intensity and potential cost drag |
| Effective holdings | how concentrated the fund behaves |

### Optimisation Concentration

Surface concentration as a warning, not a hidden diagnostic. Latest examples
from existing artifacts:

- Combined / Maximum Sharpe: top asset GE at 45.3%, effective holdings 3.75.
- Equity-only / Maximum Sharpe: top asset GE at 50.4%, effective holdings 3.13.
- Crypto-only / Maximum Sharpe: BTC-USD at 66.7%, effective holdings 1.83.
- Crypto-only / Minimum Variance: TRX-USD at 50.1%, effective holdings 2.08.

Use a warning state when top asset weight exceeds 25% or effective holdings is
below 5.

## 6. Fund Fact Sheet

The fact sheet is the core investor product page.

### Visual Hierarchy

1. Fund name and method badge.
2. One-line interpretation: "higher return with higher turnover", "lower risk
   but concentrated", etc.
3. MetricStrip: annualised return, volatility, Sharpe, max drawdown, total
   turnover.
4. GrowthChart and DrawdownChart.
5. HoldingsPanel and ExposureBar.
6. MethodologyDisclosure.

### Required Content

- growth of $1 from net returns;
- drawdown from net returns;
- latest holdings;
- top-asset concentration;
- effective number of holdings;
- equity/crypto exposure where relevant;
- total turnover;
- first live date;
- transaction cost assumption;
- annualisation convention;
- estimation window and monthly rebalance disclosure.

### Chart Interactions

- Growth and drawdown share the same date range.
- Hover shows date, net growth, daily net return, and drawdown.
- A "show costs" toggle may compare gross and net growth only if it uses
  existing `fund_returns.csv`; it must not recompute the backtest.
- HoldingsPanel supports top 10 and "all holdings" expansion.

### First Notice

The first thing a user should notice is not the highest return. It should be
the tradeoff between return, drawdown, turnover, and concentration.

### Concentration Warnings

If top asset weight exceeds 25%:

`Concentration warning: this optimisation produced a large single-asset
position. Review holdings before allocating.`

If effective holdings is below 5:

`Diversification warning: the portfolio behaves like fewer than five equally
weighted holdings.`

## 7. Signal + Evidence Lens

This is the flagship experience. It must show logic, not just metrics.
The investor should understand the product without opening equations.

### User Inputs

- sector;
- live rebalance date or nearest available date;
- optional base method: Minimum Variance or Maximum Sharpe for allocation
  context.

### Visual Logic Sequence

Use a vertical ladder or horizontal stepper:

1. WHAT THE NEWS SAYS -> SENTIMENT DIRECTION  
   Component: diverging sentiment bar labelled negative to positive. The
   primary label is "sentiment direction." Technical values such as `z_star`,
   `s21`, `z_score`, and clipping rules belong only in "How this works."

2. HOW MUCH OF THE SECTOR WAS OBSERVED -> TICKER COVERAGE / BREADTH  
   Component: ticker coverage rail. Filled cells or a segmented bar show how
   much sector evidence exists. The label is "ticker coverage" or "breadth";
   `breadth_observed_ticker_days`, `breadth_possible_ticker_days`, and `b63`
   belong only in technical detail.

3. DID THE TICKERS AGREE? -> AGREEMENT / DISAGREEMENT  
   Component: compact dot spread or agreement strip. The first-read copy should
   say whether observed ticker signals are clustered or split. Avoid population
   standard deviation terminology on first read.

4. EVIDENCE CONFIDENCE  
   Component: confidence rail or compact panel. Explain as "breadth x
   agreement" in plain language, but show the formula only in "How this works."
   Label it "evidence confidence", never probability, accuracy, truth
   confidence, or certainty.

5. ALLOCATION EFFECT  
   Component: paired pre-normalisation tilt bars:
   - Raw sentiment tilt;
   - Confidence-adjusted tilt.

   The optional placebo/control belongs in Challenge only.

### Intuitive Explanation

The user should see one signal pass through evidence checks before it affects
allocation. This makes it obvious why the same sentiment direction can produce
different portfolio effects.

### Copy

`Direction says which way the news leans. Evidence confidence says how much the
available ticker-level evidence supports using that direction.`

### Progressive Disclosure

Do not lead the primary investor UI with `z_star`, `B63`, `A21`, `C`, `C_match`,
shrinkage, population standard deviation, or mathematical formulas. Keep those
inside an expander labelled `How this works`.

## 8. Neutrality vs Cancellation

Hero line:

`Neutrality is not always consensus.`

### Verified High-Dispersion Example

Existing artifact: `sentiment_disagreement_examples.csv`

- date: 2020-07-09;
- sector: Industrials;
- sector sentiment: 0.018889;
- cross-ticker sentiment standard deviation: 0.727706;
- active ticker count: 3;
- headline count: 5;
- lowest ticker: MMM at -0.6808;
- highest ticker: CAT at +0.7717.

### Verified Consensus-Neutral Example

Existing artifact: `sentiment_disagreement_examples.csv`

- date: 2021-02-25;
- sector: Materials;
- sector sentiment: 0.0;
- cross-ticker sentiment standard deviation: 0.0;
- active ticker count: 3;
- headline count: 4;
- lowest ticker: DOW at 0.0;
- highest ticker: SHW at 0.0.

### Visual

Use the simplest possible side-by-side visual:

- A horizontal negative-to-positive sentiment axis.
- Consensus neutrality: ticker dots clustered close to zero; average near zero.
- Cancellation: ticker dots separated across positive and negative territory;
  average still near zero.

Use a small constituent sentiment strip per case. Draw the sector average as a
vertical marker. Do not require the user to read statistical terminology before
the visual makes sense.

### Interaction

- toggle between "consensus neutral" and "cancellation";
- choose from available examples;
- hover each ticker dot for ticker, sentiment, active ticker count, and headline
  count.

### Explanatory Copy

Primary copy:

`The average is flat, but the tickers disagree.`

Detail copy:

`A near-zero sector reading can mean all observed tickers were neutral. It can
also mean positive and negative ticker signals cancelled out. SignalScope treats
those as different evidence states.`

### Investor Takeaway

Do not treat a flat sector sentiment line as automatically calm. Inspect
dispersion before interpreting neutrality.

Do not overstate frequency. Say "selected diagnostic cases show" rather than
"neutrality usually means cancellation."

Keep the verified Industrials and Materials cases available as evidence/detail,
but avoid standard deviation terminology on the first read.

## 9. Volume vs Breadth

Hero line:

`More headlines do not necessarily mean broader evidence.`

### Verified Example

Existing artifact: `sentiment_candidate_cases.csv`

- date: 2020-07-24;
- sector: Tech;
- headline count: 44;
- active ticker share: 0.6;
- dominant ticker: INTC;
- dominant ticker headline share: 0.636364;
- ticker headline share HHI: 0.521694;
- sector sentiment: 0.195417.

### Visual Metaphor

Use a "headline pile versus sector map" visual:

- left: 44 small headline marks;
- right: five ticker slots, with only three represented;
- visually show that most headlines belong to INTC in the selected diagnostic
  example.

This shows that high volume can still be concentrated.

### Chart Form

Alternative if easier in Streamlit:

- top row: headline volume bar;
- middle row: active ticker breadth strip;
- bottom row: dominant ticker share bar.

### Investor Takeaway

Headline count measures volume. Breadth measures whether the sector signal is
supported across constituents. SignalScope uses breadth because a pile of
headlines on one firm is not the same as broad sector evidence.

Primary copy:

`Lots of headlines, but most came from one ticker.`

Do not require HHI interpretation. HHI may appear only under technical detail.

## 10. Model Challenge

This is a trust feature, not an academic appendix.

### Primary Investor Structure

Use three cards or reveal steps.

Card / Step 1:

`Did sentiment beat the Base portfolio?`

Answer: `No.`

Explain that Base Minimum Variance had the highest Sharpe among the primary
comparison.

Card / Step 2:

`Did Confidence reduce sentiment disturbance?`

Answer: `Yes.`

Explain that turnover fell relative to Standard Sentiment.

Card / Step 3:

`Was dynamic Confidence economically necessary?`

Answer: `Not clearly.`

Explain that matched constant shrinkage explained much of the turnover
reduction.

Then show one compact surviving insight:

`After total signal strength was matched, Confidence Lens still changed WHERE
signals were muted or preserved.`

### Models To Explain In Detail

- Base portfolio: the equity optimiser without sentiment overlay.
- Standard Sentiment: applies raw sentiment direction at the fixed tilt
  strength.
- Matched constant-shrinkage control: applies the same signal direction with one
  constant coefficient matched to total signal strength.
- Confidence Lens: applies signal direction scaled by evidence confidence.

The words "placebo", "shrinkage", `C_match`, and H1-H4 labels should appear
only after expansion.

### Expanded Metrics To Show

These exact tables belong after the three investor cards or inside an expanded
technical detail. They must not be the first read.

Primary Minimum Variance comparison:

| Overlay | Sharpe | Total turnover |
|---|---:|---:|
| Base | 0.403991 | 11.519144 |
| Standard Sentiment | 0.389406 | 12.046790 |
| Matched-Shrinkage Placebo | 0.395251 | 11.802350 |
| Confidence Lens | 0.391828 | 11.807426 |

Maximum Sharpe robustness:

| Overlay | Sharpe | Total turnover |
|---|---:|---:|
| Base | 0.469005 | 24.908840 |
| Standard Sentiment | 0.462941 | 25.058270 |
| Matched-Shrinkage Placebo | 0.465544 | 24.968792 |
| Confidence Lens | 0.461784 | 25.006839 |

Aggregate signal-strength match:

- Confidence absolute tilt sum: 17.491438564163516.
- Placebo absolute tilt sum: 17.491438564163516.
- Difference: 0.0.

Turnover falsification:

- Minimum Variance Standard-to-Confidence turnover reduction: 0.239363.
- Minimum Variance placebo reduction share: 102.1%.
- Maximum Sharpe Standard-to-Confidence turnover reduction: 0.051431.
- Maximum Sharpe placebo reduction share: 174.0%.

Dynamic distinction:

- C_mean: 0.6591585.
- C_match: 0.6322362.
- Confidence below C_match: 41.1% of observations.
- Confidence above C_match: 58.9% of observations.

### Expandable Technical Detail

Only after expansion should the user see:

- H1-H4 labels;
- exact `C_match`;
- exact aggregate tilt matching;
- full metric tables;
- detailed methodology.

Technical H-test mapping:

- H1 performance improvement: REJECT.
- H2 reduced sentiment disturbance: SUPPORT.
- H3 dynamic evidence-state distinction: SUPPORT.
- H4 economic necessity: REJECT.

`The matched placebo asks whether a smaller constant sentiment coefficient could
explain the result. It matches total pre-normalisation signal strength exactly.
Anything left must come from where the Confidence Lens attenuates or preserves
signals.`

Primary UI must not show H1-H4 labels, `C_match`, exact aggregate tilt matching,
or full methodology tables.

## 11. Allocation Builder

The allocation builder satisfies the brief requirement to allocate across funds.
It is descriptive, not advisory.

### Inputs

- select 2-5 existing precomputed funds;
- capital amount;
- allocation percentages summing to 100%;
- optional date range within common available OOS period.

On mobile, prefer compact numeric inputs or sliders inside a form with one
`Update allocation` action rather than continuously recalculating on every
input change.

### Permitted Runtime Calculations

- join selected precomputed fund net returns by date;
- compute weighted blended daily returns;
- compute blended growth of $1;
- compute drawdown from blended growth;
- compute annualised volatility and Sharpe using existing period convention;
- compute fund contribution to weighted return;
- combine latest selected fund exposures using user weights;
- combine latest selected fund holdings approximately by weighted fund weights
  only when this can be explained as an approximation.

No new optimisation, forecasting, Monte Carlo, expected returns, recommended
allocations, pseudo-robo-advice, or backtest recomputation.

### Data Requirements

- `fund_returns.csv`;
- `fund_weights.csv`;
- `asset_class_exposure.csv`;
- `performance_metrics.csv`.

### Safeguards

- hard validation that weights sum to 100%;
- warning or block if selected funds do not share a valid OOS date
  intersection;
- display common sample start and end;
- warn when allocation includes crypto-only funds because calendar frequency and
  volatility differ;
- warn when selected funds are highly concentrated.

### Disclosures

Primary disclosure:

`No new optimisation. No forecast. Historical OOS blend only.`

Secondary disclosure:

`This allocation combines precomputed historical out-of-sample fund returns. It
is not a forecast, recommendation, or personalised investment advice.`

## 12. Visual Design System

Concept: SIGNAL versus EVIDENCE.

### Layout Philosophy

- wide but bounded content width, about 1180-1280 px for dense analytical
  sections;
- first viewport split into product decision and evidence trace;
- progressive detail, with compact "why this matters" notes beside charts;
- no cards inside cards;
- one main chart per journey view, with supporting compact panels only;
- no primary wide raw tables;
- formulas in expanders;
- no excessive Plotly objects at startup;
- generous whitespace and progressive disclosure;
- avoid generic Streamlit metric-card walls.

### Header Hierarchy

- product title: restrained, not oversized after landing;
- section labels map to journey states;
- chart titles must be investor questions;
- captions carry sample period, unit, and caveat.

### Card Treatment

- use flat panels for repeated fund tiles and warnings only;
- radius 6-8 px;
- subtle borders, no heavy drop shadows;
- avoid decorative card grids when a chart or table answers the question better.

### Spacing Scale

- 4 px micro alignment;
- 8 px component padding;
- 16 px component gaps;
- 24 px section gaps;
- 40 px major view separation.

### Typography

- deploy-safe fonts only: Streamlit default sans, Inter-like system stack, or
  Source Sans style where available;
- tabular numerals for metrics and tables;
- avoid negative letter spacing;
- keep compact panel headings modest, not hero-sized.

### Color Semantics

- positive sentiment: restrained green;
- negative sentiment: muted red;
- neutral or base state: graphite/grey;
- evidence confidence: teal to blue scale;
- disagreement/uncertainty: amber;
- placebo/control: orange or cool grey;
- warnings: amber, not red unless blocking.

Do not use decorative gradients unless the gradient encodes confidence or
evidence level.

Signal colour and evidence colour must be visually distinct. Placebo/control
must use a separate neutral semantic treatment so users do not confuse it with
sentiment or evidence confidence.

### Chart Conventions

- every chart has an explicit investor question as title;
- use unified hover for time series;
- use consistent date range controls;
- sort all time series before plotting;
- show units: percent, growth of $1, turnover, weight, Sharpe;
- annotate caveats directly on charts when needed.

Do not use decorative "evidence gate" graphics that obscure the actual
before/after allocation effect.

### Empty/Missing States

- no sentiment: "No observed headlines for this sector-date";
- no allocation overlap: "Selected funds do not share enough overlapping OOS
  dates";
- no evidence case: "No diagnostic case selected";
- never silently fill missing sentiment as neutral.

### Responsive/Mobile Behaviour

- stack hero split into decision first, evidence second;
- collapse risk-return map below fund tiles on narrow screens;
- use horizontal scrolling only for dense data expansions, not primary views;
- metric strips wrap after two metrics on mobile;
- ladder becomes vertical on mobile.

## 13. Component Inventory

| Component | Inputs | Output | Artifact dependency | Investor purpose |
|---|---|---|---|---|
| FundSelector | family, method, selected fund | selected `(family, method)` | `performance_metrics.csv` | choose an investable fund |
| MetricStrip | selected fund metrics | compact KPI row | `performance_metrics.csv` | read return/risk quickly |
| RiskReturnMap | performance table, filters | interactive scatter | `performance_metrics.csv` | compare funds visually |
| GrowthChart | selected fund returns | growth of $1 | `fund_returns.csv` | inspect path of returns |
| DrawdownChart | selected fund returns | drawdown chart | `fund_returns.csv` | inspect downside path |
| HoldingsPanel | selected latest weights | top holdings and concentration | `fund_weights.csv` | understand what the fund owns |
| ExposureBar | selected fund/fund mix | equity/crypto exposure | `asset_class_exposure.csv`, `fund_weights.csv` | understand asset-class mix |
| ConcentrationWarning | top weight, effective holdings | warning state | `fund_weights.csv` | prevent hidden concentration |
| SignalIndexChart | sector, date range | sector sentiment line | `sector_sentiment_index.csv` | inspect what news says |
| SignalEvidenceLadder | sector, rebalance date | news direction -> ticker coverage -> agreement -> evidence confidence -> allocation effect | `sector_sentiment_confidence.csv` | understand confidence logic without formulas first |
| EvidenceConfidencePanel | breadth, agreement, confidence | plain-language confidence rail and before/after tilt | `sector_sentiment_confidence.csv` | show evidence confidence without decorative confusion |
| CancellationExplorer | selected diagnostic example | consensus vs cancellation comparison | `sentiment_disagreement_examples.csv` | show neutrality ambiguity |
| VolumeBreadthPanel | selected diagnostic example | headline pile vs breadth map | `sentiment_candidate_cases.csv` | show volume vs evidence breadth |
| ModelChallengePanel | base method | four-way falsification view | `confidence_placebo_comparison.csv`, `confidence_placebo_turnover_decomposition.csv` | build trust through negative results |
| AllocationBuilder | selected funds, capital, weights | blended OOS history and exposure | `fund_returns.csv`, `fund_weights.csv`, `asset_class_exposure.csv` | allocate across funds |
| MethodologyDisclosure | selected fund/view | concise assumptions | `first_live_dates.csv`, `performance_metrics.csv`, static copy | explain method without code |

`ArtifactHealth` is removed from the primary investor component inventory. If
implemented at all, it may exist only as developer/debug functionality or a
footer-level technical status note. Do not show full artifact manifests in the
app body.

## 14. Runtime Data Contract

Use `st.cache_data` in implementation for deterministic CSV loads. Do not use
`src/data_access.py` at runtime.

### Load At Startup

Startup budget target: about 3.43 MB. The first load should support the landing
screen, Fund, Risk, Decision, and small evidence teasers without loading full
Signal or Challenge data.

| Artifact | Size bytes | Purpose |
|---|---:|---|
| `results/tables/performance_metrics.csv` | 3,238 | fund comparison and metrics |
| `results/data/fund_returns.csv` | 1,779,532 | fund growth/drawdown and allocation builder |
| `results/data/fund_weights.csv` | 1,596,050 | holdings, concentration, blended holdings |
| `results/tables/asset_class_exposure.csv` | 30,245 | exposure bars |
| `results/tables/first_live_dates.csv` | 605 | first-live dates and estimation-window disclosures for Fund/Risk methodology |
| `results/tables/confidence_lens_summary.csv` | 1,588 | headline Confidence Lens summary |
| `results/tables/sentiment_disagreement_examples.csv` | 3,357 | neutrality/cancellation cases |
| `results/tables/sentiment_candidate_cases.csv` | 15,132 | volume/breadth cases |

Total initial CSV load: 3,429,747 bytes, 3.43 MB decimal, about 3.27 MiB.

`first_live_dates.csv` belongs in startup because it is small and supports the
methodology disclosure that appears in the first two journey steps. It lets the
Fund and Risk views state when each fund became live and which estimation-window
convention applies without loading analytical diagnostics.

### Load Conditionally/Lazily

| Artifact | Size bytes | Trigger |
|---|---:|---|
| `results/data/sector_sentiment_index.csv` | 1,456,429 | Signal view time-series context |
| `results/data/sector_sentiment_confidence.csv` | 101,853 | Evidence Lens view |
| `results/tables/confidence_placebo_comparison.csv` | 5,056 | Challenge view primary cards |
| `results/tables/confidence_placebo_quadrants.csv` | 953 | Evidence-state summary in Challenge detail |
| `results/tables/confidence_placebo_cases.csv` | 3,677 | Challenge examples |
| `results/tables/confidence_placebo_turnover_decomposition.csv` | 828 | Challenge turnover readout |
| `results/tables/confidence_placebo_selectivity.csv` | 107,455 | advanced Challenge detail |
| `results/tables/sentiment_weighting_disagreements.csv` | 12,323 | Signal weighting detail |
| `results/data/fusion_placebo_returns.csv` | 847,232 | Challenge return-path detail |
| `results/data/fusion_returns.csv` | 1,942,338 | only if reconstructing fusion charts interactively |
| selected PNG figures | 41-157 KB each | only if reused in research detail |
| `results/tables/sentiment_weighting_comparison.csv` | 1,089,112 | only if full diagnostic comparison is needed |
| `results/data/ticker_day_sentiment.csv` | 3,017,800 | avoid unless future app view genuinely requires ticker-day drilldown |

`fusion_placebo_weights.csv` is not part of the normal lazy contract. It may be
used only as deeply optional technical detail if asset-level control weights are
explicitly needed; do not load it for the primary Challenge view.

### Never Load

| Artifact | Size bytes | Reason |
|---|---:|---|
| `results/data/headline_sentiment_scores.csv` | 45,327,317 | 43.23 MiB headline-level audit artifact; not needed for investor runtime |
| raw hosted data through `src/data_access.py` | n/a | analytical core is frozen; runtime should use precomputed artifacts |
| anything loaded through `src/data_access.py` | n/a | no raw hosted datasets in app runtime |
| optimiser diagnostics by default | 82,527 | research/audit only; optional downloadable appendix if needed |

## 15. Navigation / Rendering Strategy

Streamlit tabs can execute hidden content eagerly. The app should therefore use
stateful conditional rendering rather than large eager tabs.

Recommended approach:

1. Maintain `st.session_state["view"]` for journey view.
2. Render one major view at a time from the journey selector.
3. Load startup artifacts once with `st.cache_data`.
4. Load heavier view-specific artifacts inside the selected view only.
5. Use stable widget keys for fund, family, method, sector, date, and
   allocation controls.
6. Avoid a changing query parameter as the only source of truth for active view.
7. Optional later: initialize from query params once for shareable views, then
   let session state own navigation.

This protects Community Cloud performance and avoids hidden chart errors.

## 16. Copy And Disclosure System

Use consistent investor-facing definitions.

| Concept | Preferred wording | Avoid |
|---|---|---|
| OOS backtest | "historical out-of-sample backtest" | "forecast", "expected future return" |
| Transaction costs | "10 bps per dollar of turnover deducted on rebalance dates" | "frictionless" |
| Evidence confidence | "how much breadth and agreement support using the sentiment direction" | "probability", "accuracy", "truth confidence" |
| Sentiment direction | "which way the recent sector news leans" | "truth", "prediction" |
| Breadth | "how much of the sector had observed ticker-level evidence" | "headline count" |
| Agreement | "how consistent observed ticker signals were" | "certainty" |
| Matched-shrinkage placebo | "a constant-shrinkage control matched to the same total signal strength" | "dummy model" |
| Concentration | "how much of the fund sits in a few positions" | "optimiser problem" without context |
| Historical performance | "past OOS performance in this sample" | "will perform" |
| No advice | "educational prototype, not personalised investment advice" | legalistic wall of text |

## 17. Competition Differentiators

Prioritise only three flagship differentiators. Do not try to manufacture seven
equally important competition moments.

1. Signal versus evidence as the core product metaphor.  
   Visual: first-screen risk-return map beside the plain-language evidence
   trace.  
   Interaction: the user can move from fund comparison to evidence inspection
   without reading formulas.  
   Evidence: Station 3 funds plus `sector_sentiment_confidence.csv`.  
   Why hard to copy superficially: it turns the whole product into a trust
   framework rather than a fund table plus sentiment chart.

2. Neutrality/cancellation and volume/breadth made intuitive visually.  
   Visual: a flat average with disagreeing ticker dots; 44 headlines but only
   three of five ticker slots represented, mostly INTC.  
   Evidence: `sentiment_disagreement_examples.csv` and
   `sentiment_candidate_cases.csv`.  
   Why hard to copy superficially: it converts real diagnostic cases into
   investor interpretation traps that are visible in seconds.

3. Matched-shrinkage falsification made investor-facing rather than hidden.  
   Visual: three challenge cards and one surviving-insight panel.  
   Interaction: reveal exact H-tests, aggregate tilt matching, and full tables
   only after the investor answer is clear.  
   Evidence: Phase 2C comparison, turnover decomposition, cases, and
   selectivity artifacts.  
   Why hard to copy superficially: it makes a negative result part of the
   product's credibility instead of burying it in an appendix.

## 18. Rubric Traceability

This table is intentionally simple so it can be reused in the final report.

| Journey / architecture | Mandatory or rubric requirement | Exact product component | Artifact evidence |
|---|---|---|---|
| Fund | compare funds | FundSelector, RiskReturnMap, compact ranked fund tiles | `performance_metrics.csv` |
| Risk | open a fund fact sheet | MetricStrip, GrowthChart, DrawdownChart, HoldingsPanel, ExposureBar, ConcentrationWarning, MethodologyDisclosure | `fund_returns.csv`, `fund_weights.csv`, `asset_class_exposure.csv`, `first_live_dates.csv` |
| Signal | surface standalone sentiment analytics | SignalIndexChart and equal-ticker evidence context | `sector_sentiment_index.csv`, `sentiment_weighting_disagreements.csv` |
| Evidence | explain whether a sentiment reading is supported | SignalEvidenceLadder, CancellationExplorer, VolumeBreadthPanel | `sector_sentiment_confidence.csv`, `sentiment_disagreement_examples.csv`, `sentiment_candidate_cases.csv` |
| Decision | set an allocation across funds | AllocationBuilder with historical OOS blend and exposure | `fund_returns.csv`, `fund_weights.csv`, `asset_class_exposure.csv` |
| Challenge | innovation, critical interpretation, falsification evidence | three-card ModelChallengePanel plus expandable technical details | `confidence_placebo_comparison.csv`, `confidence_placebo_turnover_decomposition.csv`, `confidence_placebo_quadrants.csv`, `confidence_placebo_cases.csv`, `confidence_placebo_selectivity.csv` |
| Deployment architecture | precomputed-output and reliability requirement | cached startup loader, lazy view-specific loaders, runtime bans | compact CSV contract; no `headline_sentiment_scores.csv`, no raw hosted data, no `data_access.py` runtime load |

## 19. Performance / Deployment Plan

- Startup artifact size: 3,429,747 bytes, 3.43 MB decimal, about 3.27 MiB.
- Use `st.cache_data` for deterministic CSV loads.
- Lazy-load view-specific research detail.
- No analytical imports except lightweight constants if absolutely necessary.
- No runtime NLTK.
- No hosted raw data.
- No solver.
- No backtest recomputation.
- No sentiment scoring.
- No secret dependency.
- Streamlit Community Cloud compatible with `requirements.txt`
  (`streamlit>=1.50,<2`, pandas, numpy, scipy, pyarrow, requests,
  matplotlib).
- Keep `.streamlit/config.toml` at repo root.
- Final checks later: `streamlit run streamlit_app.py`,
  `python scripts/check_handin.py`, full pytest, and fresh browser test.

## 20. Do-Not-Build Register

| Rejected feature | Why rejected |
|---|---|
| Live trading prices | changes the data product and adds unstable external dependency |
| Runtime headline search | requires 43 MB headline audit artifact and invites raw-text browsing instead of investor decision flow |
| LLM chatbot | high complexity, hallucination risk, no rubric need |
| Monte Carlo forecasts | implies future return distribution not supported by frozen analysis |
| Sentiment-based price targets | violates no-alpha/no-forecast product principle |
| Excessive tabs | fragments the journey and can trigger eager hidden rendering |
| Decorative 3D charts | weak investor value and likely performance cost |
| Unexplained composite scores | conflicts with evidence-first transparency |
| Extra analytical models after freeze | violates analytical freeze and creates verification risk |
| Runtime VADER scoring | forbidden by deployment and methodology rules |
| Loading `headline_sentiment_scores.csv` | too large and research-side only |
| Raw data load through `data_access.py` | unnecessary after freeze and slows cloud startup |

## 21. Implementation Plan

### Phase 4A - Artifact Loader And Design System

- Files to change: `streamlit_app.py`; optional future helper modules if the app
  becomes too large.
- Tests to add: smoke import test; artifact existence/schema test; no
  `data_access`, `nltk`, `SentimentIntensityAnalyzer`, optimiser, or backtest
  calls in `streamlit_app.py`.
- Artifact dependencies: startup set only.
- Completion criteria: app loads compact artifacts under 5 MB startup target,
  renders landing screen, no raw-data load.

### Phase 4B - Fund Experience

- Files to change: `streamlit_app.py`.
- Tests to add: fund list contains all nine `(family, method)` combinations;
  selected fund fact sheet renders; concentration warnings trigger for known
  concentrated funds.
- Artifact dependencies: `performance_metrics.csv`, `fund_returns.csv`,
  `fund_weights.csv`, `asset_class_exposure.csv`, `first_live_dates.csv`.
- Completion criteria: Fund and Risk journey states are usable and investor
  facing.

### Phase 4C - Evidence Experience

- Files to change: `streamlit_app.py`.
- Tests to add: Signal and Evidence views render without headline-level data;
  verified examples appear with exact values; missing sentiment is not displayed
  as neutral.
- Artifact dependencies: `sector_sentiment_index.csv`,
  `sector_sentiment_confidence.csv` lazily,
  `sentiment_disagreement_examples.csv`, `sentiment_candidate_cases.csv`.
- Completion criteria: SignalEvidenceLadder, Neutrality vs Cancellation, and
  Volume vs Breadth experiences are implemented.

### Phase 4D - Allocation Builder

- Files to change: `streamlit_app.py`.
- Tests to add: allocation weights must sum to 100%; selected funds share date
  intersection; blended returns are weighted from precomputed returns.
- Artifact dependencies: `fund_returns.csv`, `fund_weights.csv`,
  `asset_class_exposure.csv`.
- Completion criteria: investor can allocate capital across 2-5 precomputed
  funds with historical OOS outputs and caveats.

### Phase 4E - Model Challenge

- Files to change: `streamlit_app.py`.
- Tests to add: three investor cards render exactly; expanded technical detail
  renders H1-H4 verdicts and aggregate tilt matching only after disclosure; Base
  beats sentiment variants in primary Sharpe comparison.
- Artifact dependencies: `confidence_placebo_comparison.csv`,
  `confidence_placebo_turnover_decomposition.csv`,
  `confidence_placebo_quadrants.csv`, `confidence_placebo_cases.csv`,
  optional lazy `confidence_placebo_selectivity.csv`.
- Completion criteria: falsification is understandable in under 30 seconds.

### Phase 4F - Responsive And Deployment Polish

- Files to change: `streamlit_app.py`, optionally `.streamlit/config.toml` only
  if theme settings are needed.
- Tests to add: app text scan for forbidden phrases, local absolute paths, raw
  data calls, and generic TODO copy.
- Artifact dependencies: none new.
- Completion criteria: mobile layout stacks cleanly, metric strips wrap, no
  overlapping labels, no starter copy remains.

### Phase 4G - Tests And Fresh-Deploy Verification

- Files to change: tests only, if needed.
- Tests to add: Streamlit AppTest smoke tests for journey states where reliable;
  static checks for runtime bans; artifact schema checks.
- Artifact dependencies: all runtime artifacts.
- Completion criteria:
  - repo interpreter `-m pytest -q` passes;
  - `python scripts/check_handin.py` passes except expected PDF/pycache
    reminders if still present;
  - `streamlit run streamlit_app.py` works locally;
  - fresh browser test confirms initial load speed and navigation.

## 22. Final Architecture Summary

Recommended final architecture:

- one thin `streamlit_app.py` entrypoint for Station 4;
- cached compact artifact loader;
- stateful journey navigation;
- one selected fund state shared across Fund, Risk, and Decision;
- one selected sector/date state shared across Signal and Evidence;
- lazy research detail loading for Evidence and Challenge;
- no analytical recomputation.

First-screen design:

- SignalScope title;
- "See the signal. Inspect the evidence.";
- split risk-return and evidence-trace visual;
- primary action `Compare funds`;
- honest note that sentiment did not automatically improve returns.

Exact navigation:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

Hero interactions:

1. Fund comparison risk-return map.
2. Fund fact sheet with concentration warnings.
3. Signal + Evidence Lens ladder.
4. Neutrality vs Cancellation explorer.
5. Model Challenge with matched constant-control falsification.

Biggest remaining product risk:

Overbuilding a research cockpit that overwhelms the investor journey. The remedy
is progressive disclosure: product first, evidence second, research audit last.

Strongest competition advantage:

Most correct submissions will show funds, metrics, and sentiment charts.
SignalScope will show why the sentiment signal should or should not be trusted,
and it will make negative results part of the trust architecture rather than a
buried caveat.

Final implementation choices:

- keep the locked journey as `Fund | Risk | Signal | Evidence | Decision |
  Challenge`;
- use one `streamlit_app.py` entrypoint initially, splitting helpers only if the
  implementation becomes hard to maintain without changing behaviour;
- rebuild primary charts interactively from compact CSVs; reuse PNGs only for
  optional deep research detail;
- trigger concentration warnings when top asset weight exceeds 25% or effective
  holdings is below 5;
- keep Challenge as the final journey state, with only the landing truth label
  `Sentiment did not beat Base` on the first screen;
- use distinct signal, evidence, and neutral-control colour semantics as defined
  above.
