# AI Log 09 - Station 4 Phase 4C Signal And Evidence

## Objective

Implement only Station 4 Phase 4C for SignalScope:

- Signal: standalone sector sentiment context.
- Evidence: flagship Evidence Lens showing direction, breadth, agreement,
  evidence confidence, and allocation effect.

No Decision allocation builder, Challenge matched-shrinkage UI, new analytics,
new models, parameter tuning, raw data loading, runtime VADER/NLTK, runtime
sentiment scoring, optimisation, or backtest rebuilding was implemented.

## Files Changed

- `app/data.py`
- `app/charts.py`
- `app/design.py`
- `app/components.py`
- `app/signal.py`
- `app/evidence.py`
- `tests/test_app_interactions.py`
- `tests/test_app_signal_evidence.py`
- `ai/09_station4_phase4c_signal_evidence.md`

No frozen analytical source files under `src/` and no existing saved result
artifacts under `results/` were modified.

## Runtime Artifacts

Startup remains unchanged from Phase 4B:

- `results/tables/performance_metrics.csv`
- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/tables/asset_class_exposure.csv`
- `results/tables/first_live_dates.csv`
- `results/tables/confidence_lens_summary.csv`
- `results/tables/sentiment_disagreement_examples.csv`
- `results/tables/sentiment_candidate_cases.csv`

Startup size remains `3,429,747` bytes.

Lazy Phase 4C artifacts:

- `results/data/sector_sentiment_index.csv`: `1,456,429` bytes.
- `results/data/sector_sentiment_confidence.csv`: `101,853` bytes.
- `results/tables/sentiment_weighting_disagreements.csv`: `12,323` bytes.
- `results/tables/sentiment_weighting_comparison.csv`: `1,089,112` bytes.
- `results/tables/confidence_lens_attenuation_cases.csv`: `1,528` bytes.
- `results/data/ticker_day_sentiment.csv`: `3,017,800` bytes.

`results/data/headline_sentiment_scores.csv` remains forbidden and is not in the
startup or lazy registry.

## Signal Interaction

The Signal page answers: "What does the news say?"

It includes:

- sector selector for the 10 saved sectors;
- period selector;
- signal date selector;
- primary sector sentiment timeline;
- gold evidence availability ticks under the blue signal trace;
- selected sector/date context;
- `Inspect this evidence` CTA that navigates to Evidence and preserves sector
  and date context.

The page keeps Confidence Lens detail out of the main Signal view. It uses only a
small progressive disclosure for equal-ticker aggregation and technical notes.

## Evidence Lens

The Evidence page answers: "How well supported is this reading?"

The flagship Lens presents one continuous product flow:

1. WHAT THE NEWS SAYS -> Sentiment direction.
2. HOW MUCH OF THE SECTOR WAS OBSERVED -> Ticker coverage.
3. DID THE TICKERS AGREE? -> Agreement.
4. EVIDENCE CONFIDENCE -> Evidence support for using the signal.
5. ALLOCATION EFFECT -> Raw sentiment tilt versus evidence-adjusted tilt.

Primary labels avoid z-scores, B63, A21, C, dispersion, and formulas. Those
details appear only under `How this works`.

Evidence confidence is described as how broad and internally consistent the
observed news evidence is. It is not described as probability, truth, accuracy,
forecast confidence, or predictive certainty.

## Breadth Representation

The Lens uses discrete evidence cells in the gold evidence language. Because the
frozen artifact uses trailing 63-trading-day breadth, the UI labels the measure
as trailing ticker-day coverage rather than falsely describing it as same-day
company count.

Example label:

`119 of 315 trailing ticker-days represented`

## Agreement Representation

Agreement is shown as an evidence rail and plain-language state:

- `Signals were aligned`
- `Signals were mixed`
- `Signals strongly disagreed`

These are deterministic presentation labels derived from the saved `a21`
agreement value. Technical dispersion language stays in the disclosure.

Curated neutrality/cancellation cases use lazy `ticker_day_sentiment.csv` to show
actual ticker-level marks on a negative-to-positive axis.

## Allocation Effect

The Evidence page shows raw versus evidence-adjusted allocation effect using
saved artifact fields. For a general Evidence Lens row, the bars use
`raw_tilt` and `confidence_adjusted_tilt` from
`sector_sentiment_confidence.csv`.

When the selected row matches a saved attenuation case, the bars use
`standard_change` and `confidence_change` from
`confidence_lens_attenuation_cases.csv`.

The UI states that this is a portfolio-disturbance view, not a return forecast.

## Neutrality / Cancellation

The Evidence page includes the shortcut:

`Neutrality is not always consensus.`

Both sides use real saved empirical cases:

Consensus-neutral case:

- date: `2021-02-25`
- sector: `Materials`
- sector sentiment: `0.0`
- cross-ticker dispersion: `0.0`
- active ticker count: `3`
- headline count: `4`
- DOW: `0.0`
- SHW: `0.0`

Cancellation case:

- date: `2020-07-09`
- sector: `Industrials`
- sector sentiment: `0.0188888888888889`
- cross-ticker dispersion: `0.7277056687771303`
- active ticker count: `3`
- headline count: `5`
- lowest ticker: `MMM`, `-0.6808`
- highest ticker: `CAT`, `0.7717`

Primary copy: "The average is flat, but the companies disagree."

The UI says these are selected diagnostic cases and does not claim that this is
typical or pervasive.

## Volume / Breadth

The Evidence page includes the shortcut:

`More headlines do not necessarily mean broader evidence.`

Saved case:

- date: `2020-07-24`
- sector: `Tech`
- headline count: `44`
- active ticker share: `0.6`
- dominant ticker: `INTC`
- dominant ticker headline share: `0.636364`
- ticker headline-share HHI: `0.521694`
- sector sentiment: `0.195417`

Lazy ticker-day rows show:

- ADBE: `1` headline
- AMD: `15` headlines
- INTC: `28` headlines

The visual uses a headline pile and five ticker slots, with two slots explicitly
shown as no-news slots. HHI appears only under technical detail.

## Attenuation Case

Saved Confidence Lens attenuation shortcut:

- base method: `Minimum Variance`
- date: `2021-11-01`
- sector: `RealEstate`
- signal cutoff date: `2021-10-29`
- `z_star`: `1.669803459455642`
- `b63`: `0.3777777777777777`
- `a21`: `0.901107710891938`
- confidence: `0.3404184685591766`
- raw tilt: `0.1669803459455642`
- confidence-adjusted tilt: `0.0568431936462704`
- raw sector change: `0.0225259863957884`
- evidence-adjusted sector change: `0.0081958889867612`

Primary copy: "Same news direction. Less portfolio movement."

No return-improvement claim is made.

## Equal-Ticker Finding

The saved `sentiment_weighting_comparison.csv` table contains:

- saved sector-day rows: `10,070`
- paired finite sector-days: `9,832`
- sign reversals: `561`
- sign reversal share on paired finite sector-days: `0.057058584214808784`

The UI therefore states:

`Headline weighting changed the direction of the apparent sector signal on
5.71% of paired finite sector-days (561 of 9,832).`

This uses the paired finite denominator; rows with a missing equal-ticker or
headline-weighted reading are excluded from the denominator rather than counted
as comparable sector-days.

## Navigation / Session State

Phase 4C uses:

- `selected_sector`
- `selected_signal_date`
- `evidence_case`

Signal -> Evidence preserves sector/date context. Evidence -> Signal preserves
sector/date context. Curated cases update Signal/Evidence context without
touching selected fund state.

## Visual Semantics

The new views inherit the Phase 4B dark-first design:

- blue signal trace for sentiment direction;
- gold evidence ticks, cells, and support markers;
- salmon action/selection markers;
- amber for headline concentration/disagreement emphasis;
- muted red for negative ticker sentiment;
- deep green-charcoal surfaces and restrained borders.

The SignalScope motif is functional: a continuous blue signal line sits above
discrete gold evidence availability marks on Signal, and the Evidence Lens uses
signal rails plus evidence cells as the core product structure.

## Tests Added

Added `tests/test_app_signal_evidence.py` for:

- lazy registry and forbidden headline artifact checks;
- sector universe extraction;
- selected-sector validation;
- sentiment time-series filtering;
- selected date validation;
- no-news missing treatment;
- weighting sign-reversal summary from saved artifact;
- evidence sector/date selection;
- breadth, agreement, and confidence formatting;
- allocation-effect frame selection;
- exact real neutrality/cancellation case values;
- exact real volume/breadth case values;
- exact real attenuation case values;
- JSON serialisation and Altair validation for new Vega-Lite specs.

Extended `tests/test_app_interactions.py` for:

- Signal render and sector switching;
- Signal -> Evidence context preservation;
- Evidence -> Signal context preservation;
- curated Neutrality, Volume/Breadth, and Attenuation shortcuts.

## Verification

Focused Phase 4C tests:

```text
18 passed in 2.85s
```

Full test suite:

```text
70 passed in 9.76s
```

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Streamlit smoke:

```text
HTTP_STATUS=200
```

The first two smoke wrappers timed out while the server itself was already
serving HTTP 200. The direct HTTP check returned `200`, and leftover
`streamlit_app.py --server.port 8765` processes were stopped.

Render-state pass:

```text
Signal_Tech_OK
Signal_Industrials_OK
Signal_RealEstate_OK
Evidence_RealEstate_OK
```

Playwright was not installed locally, so pixel-level browser screenshots were
not produced without adding a dependency. AppTest render checks, chart-schema
validation, and HTTP smoke were used for local verification; a final manual
browser visual pass remains useful before public deployment.

Frozen analytics verification:

```text
git status --short -- src results
```

returned no output.

Runtime dependency scan:

- no `src.data_access` import;
- no hosted raw-data loader calls;
- no `nltk` import;
- no `SentimentIntensityAnalyzer`;
- no `scipy.optimize`;
- no `run_backtest`.

`VADER` appears only in investor-facing technical disclosure text explaining the
precomputed build-time baseline. `headline_sentiment_scores.csv` appears only in
the explicit app-layer denylist and tests.

## Deferred

Still deferred:

- Phase 4D Decision allocation builder;
- Phase 4E Challenge matched-shrinkage falsification UI;
- final responsive/pixel browser pass beyond AppTest and HTTP smoke.

Decision and Challenge remain unimplemented journey states.

## Phase 4C.2 Final State and UX Consistency

### Objective

Perform a final surgical consistency pass on the approved Signal and Evidence
experience. This pass fixed visible browser-QA state leakage and first-read UX
issues only.

No Phase 4D allocation builder, Challenge UI, frozen analytical source change,
saved result artifact change, raw data loading, runtime VADER/NLTK computation,
optimisation, or backtest recomputation was introduced.

### Root Cause

The Materials/RealEstate mismatch came from split Signal/Evidence state:

- durable context lived in `selected_sector` and `selected_signal_date`;
- Signal widgets also retained independent values in `signal_sector_select` and
  `signal_date_select`;
- Evidence widgets retained independent values in `evidence_sector_select` and
  `evidence_date_select`;
- curated Evidence buttons updated durable sector/date context and
  `evidence_case`, but did not synchronise the Signal/Evidence widget keys on
  the next render.

That allowed stale curated-case context, especially RealEstate attenuation
context, to survive after later manual Signal interaction. The visible selector
and the rendered context could therefore be sourced from different pieces of
Streamlit session state across reruns.

### Final Session-State Rule

Signal now resolves one authoritative sector/date context before rendering any
sector-specific UI.

- Manual Signal sector, period, or date changes are marked by widget callbacks.
- Manual Signal interaction clears the active curated-case override.
- Sector or period changes reset the selected Signal date to the latest observed
  sector sentiment available in the active period.
- Manual date selection is preserved, including deliberate no-news dates.
- Pending curated or navigation context is applied before widgets render, then
  the widget keys are synchronised to that resolved context.

The same resolved Signal context now drives the sector selector, timeline,
date options, selected-date marker, status banner, and `Inspect this evidence`
CTA.

### Default Signal-Date Behaviour

The Signal date default now chooses the latest date with an observed sector
sentiment value for the selected sector and active period. No-news dates remain
available in the date selector and still render an explicit no-news status when
the user selects one deliberately.

The Signal period selector now defaults to `Recent 2Y` to reduce first-read
timeline density while retaining `All` and individual year options.

### Curated-Case State Rule

Curated Evidence shortcuts remain explicit actions:

- Neutrality vs cancellation sets the saved Industrials diagnostic context.
- Volume vs breadth sets the saved Tech diagnostic context.
- Confidence attenuation sets the saved RealEstate attenuation context.

Each shortcut stores a pending Signal/Evidence context to be applied before the
next page render. Once the user manually changes Signal sector, period, or date,
the curated-case override is cleared and cannot continue to control Signal-page
banners or observations.

### Signal/Evidence Navigation

Signal -> Evidence now stores an explicit pending Evidence context containing
the currently selected Signal sector/date. Evidence applies that context before
rendering its own selector widgets.

If the selected Signal date is a saved rebalance date, Evidence opens that exact
rebalance context. If it is not a rebalance date, Evidence opens the prior,
first, or final saved rebalance as appropriate and shows the existing explicit
date-transition disclosure.

Evidence -> Signal preserves the selected Evidence sector/date through a pending
Signal context, so the Signal widget keys and banner are coherent on return.

### Availability Strip Refinement

The Signal timeline still uses the saved `active_ticker_share` same-day
availability values. The gold availability display was simplified from a dense
secondary band into a low-profile row of small gold square marks underneath the
blue sentiment line. Opacity encodes same-day evidence availability, and tooltips
retain active ticker share, observed ticker count, and possible ticker count.

The caption now states that blue shows sentiment direction and gold dots show
how much same-day evidence existed for each sector-date.

### Status Banner Refinement

Observed Signal dates now render concise same-day status:

`Sector · date`

`Sector sentiment +x.xx`

`n of m companies represented today`

No-news dates render:

`Sector · date`

`No observed sector news.`

This keeps same-day active breadth separate from Evidence Lens trailing B63
breadth.

### Evidence Lens Wording

The first-read Signal-direction row now uses plain-language trading-signal
labels such as `Near-neutral trading signal`. The secondary copy says it is
built from the saved 21-day sector signal used by the trading overlay and is
different from the daily Signal-page reading. Cross-sectional standardisation
language is no longer in the first-read row.

### Navigation Contrast

Inactive journey labels received a modest contrast increase while remaining
secondary to the active stage. The navigation design and journey order were not
changed.

### Forensic Corrections Preserved

The pass preserved the Phase 4C.1 forensic corrections:

- equal-ticker wording uses `561 of 9,832` paired finite sector-days, `5.71%`;
- Equal Weight says it has no optimisation estimation window;
- daily Signal readings remain distinguished from monthly Evidence rebalance
  context;
- date-transition disclosures remain explicit;
- 2020 diagnostic examples remain labelled pre-OOS diagnostics;
- primary attenuation bars use saved realised sector allocation changes when a
  curated attenuation case is selected;
- B63 is labelled as trailing breadth, not same-day breadth;
- confidence is not described as probability, truth, or return-prediction
  confidence;
- existing dark SignalScope colour semantics and Fund/Risk map functionality
  remain intact.

### Tests

Added or updated deterministic coverage for:

- Signal selector sector matching the status-banner sector for Materials, Tech,
  Industrials, and RealEstate;
- sector change resetting/revalidating the selected date;
- default Signal date using an observed sector sentiment where possible;
- deliberate no-news dates remaining selectable and correctly labelled;
- manual Signal interaction clearing stale curated-case override state;
- Signal -> Evidence context preservation for Materials, Tech, Industrials, and
  RealEstate;
- Evidence -> Signal preservation;
- curated case -> manual Signal transition for neutrality and attenuation cases;
- Signal availability strip input/spec values;
- the existing `561 / 9,832 = 5.71%` forensic denominator check.

Focused Signal/Evidence tests:

```text
25 passed in 6.02s
```

Full test suite:

```text
80 passed in 14.77s
```

### Final Verification

Hand-in checker:

```text
21 checks passed.
2 reminder(s):
  [WARN] delete __pycache__/ and *.pyc before you zip - they are auto-generated and not needed
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

Streamlit smoke-start:

```text
HTTP_STATUS=200
```

Frozen analytics verification:

```text
git status --short -- fins2026/z5367955_projectB/src fins2026/z5367955_projectB/results
```

returned no output.

Runtime dependency scan returned no app-layer use of raw data loaders,
`data_access`, NLTK/VADER computation, optimisation, or backtest
recomputation. `VADER` remains visible only as build-time explanatory copy.

`git diff --check -- fins2026/z5367955_projectB` returned no whitespace errors.

Phase 4D was not started.
