# AI Log 06 - Station 4 Product Design

## Prompt Recorded

The student approved the Station 4 product direction after a read-only product
audit:

- Product concept: SignalScope is an evidence-first decision cockpit with guided
  storytelling.
- Core product line: "See the signal. Inspect the evidence."
- Investor journey: Fund -> Risk -> Signal -> Evidence -> Decision -> Challenge.

The first task created the Station 4 product implementation specification
without writing Streamlit code and without modifying analytical methodology,
analytical source files, or existing analytical results. A subsequent final
red-team pass returned REVISE, then implement. This log now records the approved
red-team revisions that produced the final implementation specification.

## Files Read

- `AGENTS.md`
- `PROJECT_BRIEF.md`
- `README.md`
- `SUBMISSION_CHECKLIST.md`
- `planning/part_b_methodology_spec.md`
- `ai/01_project_b_architecture.md`
- `ai/02_station3a_portfolios.md`
- `ai/03_phase2a_sentiment_diagnostics.md`
- `ai/04_phase2b_confidence_lens.md`
- `ai/05_phase2c_matched_shrinkage_falsification.md`
- `streamlit_app.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `docs/STUDENT_DEPLOY.md`
- compact current result artifacts under `results/data/` and `results/tables/`

Shared Streamlit planning guidance was also checked through the local
`build-app` and Streamlit app workflow documentation.

## Current Product State

`streamlit_app.py` is still the starter application. It currently loads hosted
equity data through `src.data_access` and uses generic `Funds`, `Sentiment`, and
`Data` tabs with TODO copy. That is acceptable before implementation but is not
the final Station 4 product. The Station 4 implementation must replace this with
precomputed artifact loading and journey navigation.

No Streamlit code was written in this step.

## Product Principles Locked

The Station 4 product spec locks these principles:

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

## Key Empirical Values Verified

Runtime data budget:

- final startup CSV set: 3,429,747 bytes, 3.43 MB decimal, about 3.27 MiB;
- `results/data/headline_sentiment_scores.csv`: 45,327,317 bytes, about
  43.23 MiB, therefore excluded from deployed runtime loading.

Neutrality versus cancellation example from
`results/tables/sentiment_disagreement_examples.csv`:

- 2020-07-09 Industrials;
- sector sentiment `0.018889`;
- cross-ticker sentiment standard deviation `0.727706`;
- active ticker count `3`;
- headline count `5`;
- MMM `-0.6808`;
- CAT `0.7717`.

Consensus-neutral comparison example:

- 2021-02-25 Materials;
- sector sentiment `0.0`;
- cross-ticker sentiment standard deviation `0.0`;
- active ticker count `3`;
- headline count `4`;
- DOW `0.0`;
- SHW `0.0`.

Volume versus breadth example from
`results/tables/sentiment_candidate_cases.csv`:

- 2020-07-24 Tech;
- headline count `44`;
- active ticker share `0.6`;
- dominant ticker `INTC`;
- dominant ticker headline share `0.636364`;
- ticker headline share HHI `0.521694`;
- sector sentiment `0.195417`.

Phase 2C falsification values:

- `C_mean = 0.6591585049725245`;
- `C_match = 0.6322361773345248`;
- Confidence absolute tilt sum `17.491438564163516`;
- Placebo absolute tilt sum `17.491438564163516`;
- aggregate absolute tilt difference `0.0`;
- H1 performance improvement rejected;
- H2 reduced sentiment disturbance supported;
- H3 dynamic evidence-state distinction supported;
- H4 economic necessity rejected.

## Product Architecture Decision

The approved architecture is not generic tabs. It is journey navigation:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

Reason:

- it maps directly to the investor journey;
- it keeps investable funds first;
- it lets research depth unfold progressively;
- it avoids large eager hidden views that Streamlit tabs can render;
- it gives each screen one investor question.

## Final Red-Team Decisions Locked

First screen:

- title: `SignalScope`;
- line: `See the signal. Inspect the evidence.`;
- value proposition: `Compare nine systematic funds, inspect risk and holdings,
  then test whether news sentiment deserves trust.`;
- left visual: compact nine-fund risk/return comparison;
- right visual: News direction -> ticker coverage -> agreement ->
  confidence-adjusted allocation effect;
- truth labels: Historical OOS backtest, Sentiment did not beat Base, No
  forecast or investment advice;
- primary CTA: Compare funds;
- secondary CTA: Inspect evidence.

Above the fold must not show formulas, research diagnostics, H1-H4 labels,
methodology tables, placebo terminology, or constant-control details.

Signal and Evidence are deliberately separate:

- Signal answers: What does the news say over time?
- Evidence answers: How well supported is this particular reading?
- Evidence is the flagship interaction and must not reproduce another sentiment
  line chart.

Primary Confidence Lens language:

- WHAT THE NEWS SAYS: sentiment direction;
- HOW MUCH OF THE SECTOR WAS OBSERVED: ticker coverage / breadth;
- DID THE TICKERS AGREE?: agreement / disagreement;
- EVIDENCE CONFIDENCE: breadth x agreement, formula only in `How this works`;
- ALLOCATION EFFECT: raw sentiment tilt versus confidence-adjusted tilt.

The primary investor UI must not lead with `z_star`, `B63`, `A21`, `C`,
`C_match`, shrinkage, population standard deviation, or mathematical formulas.

Model Challenge is three investor questions:

1. Did sentiment beat the Base portfolio? No.
2. Did Confidence reduce sentiment disturbance? Yes.
3. Was dynamic Confidence economically necessary? Not clearly.

Then the app shows the surviving insight: after total signal strength was
matched, Confidence Lens still changed WHERE signals were muted or preserved.
H1-H4 labels, exact `C_match`, exact aggregate tilt matching, full metric
tables, and detailed methodology appear only after expansion.

Final component removals and downranking:

- `ArtifactHealth` is removed from the primary investor component inventory;
- full artifact manifests and full diagnostic tables stay out of primary views;
- asset-level control weight detail is deeply optional only;
- decorative evidence-gate graphics are rejected if they obscure before/after
  allocation effects.

Report traceability was added to the product spec so the final report can map:
Fund to comparison, Risk to fact sheet, Signal/Evidence to sentiment analytics,
Decision to allocation, Challenge to innovation and critical interpretation, and
deployment architecture to precomputed-output reliability.

## Runtime Data Contract

Startup artifacts:

- `results/tables/performance_metrics.csv`
- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/tables/asset_class_exposure.csv`
- `results/tables/first_live_dates.csv`
- `results/tables/confidence_lens_summary.csv`
- `results/tables/sentiment_candidate_cases.csv`
- `results/tables/sentiment_disagreement_examples.csv`

`first_live_dates.csv` belongs in startup because it is tiny and supports the
Fund/Risk first-read methodology disclosure: each fund can state when it became
live and which estimation-window convention applies without loading analytical
diagnostics.

Lazy artifacts:

- `results/data/sector_sentiment_index.csv`
- `results/data/sector_sentiment_confidence.csv`
- `results/tables/confidence_placebo_comparison.csv`
- `results/tables/confidence_placebo_quadrants.csv`
- `results/tables/confidence_placebo_cases.csv`
- `results/tables/confidence_placebo_turnover_decomposition.csv`
- `results/tables/confidence_placebo_selectivity.csv`
- `results/tables/sentiment_weighting_disagreements.csv`
- `results/data/fusion_placebo_returns.csv`
- `results/data/fusion_returns.csv` only if reconstructing fusion charts
  interactively
- selected PNG figures only when useful in optional research detail

`fusion_placebo_weights.csv` is not part of the normal lazy contract. It may be
used only as deeply optional technical detail if asset-level control weights are
explicitly needed.

Never load:

- `results/data/headline_sentiment_scores.csv`;
- raw data through `src/data_access.py`;
- runtime VADER/NLTK;
- runtime optimisers or backtests.

## Major Product Components Specified

The spec defines these reusable Streamlit component concepts:

- FundSelector
- MetricStrip
- RiskReturnMap
- GrowthChart
- DrawdownChart
- HoldingsPanel
- ExposureBar
- ConcentrationWarning
- SignalIndexChart
- SignalEvidenceLadder
- EvidenceConfidencePanel
- CancellationExplorer
- VolumeBreadthPanel
- ModelChallengePanel
- AllocationBuilder
- MethodologyDisclosure

`ArtifactHealth` was removed from the primary investor component inventory. It
may exist only as developer/debug functionality, footer-level technical status,
or not at all.

No code was created for these components in this step. They are design contracts
for the next implementation phase.

## Competition Design Logic

The app should not compete by showing more tables. It should compete by making a
hard analytical result understandable:

1. Signal versus evidence is the core product metaphor.
2. Neutrality/cancellation and volume/breadth are made intuitive visually.
3. Matched-shrinkage falsification is investor-facing rather than hidden.

This makes negative results and falsification part of the product's trust model.
The app should not manufacture seven equally important competition moments.

## Implementation Plan Locked

The spec breaks Station 4 into safe phases:

1. 4A Artifact loader and design system.
2. 4B Fund experience.
3. 4C Evidence experience.
4. 4D Allocation builder.
5. 4E Model challenge.
6. 4F Responsive/deployment polish.
7. 4G Tests and fresh-deploy verification.

Each phase lists files to change, tests to add, artifact dependencies, and
completion criteria. Implementation has not started.

## Do-Not-Build Decisions

The spec explicitly rejects:

- live trading prices;
- runtime headline search;
- LLM chatbot;
- Monte Carlo forecasts;
- sentiment-based price targets;
- excessive tabs;
- decorative 3D charts;
- unexplained scores;
- extra analytical models after freeze;
- runtime VADER scoring;
- loading `headline_sentiment_scores.csv`;
- raw data load through `data_access.py`.

These features either weaken investor usefulness, add deployment risk, violate
the analytical freeze, or imply predictive certainty not supported by the
evidence.

## Files Created

- `planning/station4_product_spec.md`
- `ai/06_station4_product_design.md`

## Verification

This was a documentation-only step. No analytical code, app code, source data,
or existing analytical result artifact was modified.

Next implementation should start with Phase 4A from
`planning/station4_product_spec.md`, then verify with targeted app/static tests
before building deeper product views.
