# AGENTS.md - Project B Agent Instructions

This folder is `z5367955_projectB`, the Part B submission for FINS3645. Work only
inside this folder unless the student explicitly authorises a wider change.
`../z5367955_projectA` is the student's own Part A submission and may be read for
reuse, but it must not be edited.

Read `PROJECT_BRIEF.md`, `context/project_context.md`, `context/DATA_GUIDE.md`,
`context/verify_ai_output.md`, and `planning/part_b_methodology_spec.md` before
implementing methodology-sensitive changes.

## Scope

Part B covers Data Factory Floor Stations 3 and 4:

- optimal funds and walk-forward out-of-sample backtests;
- headline sentiment scoring and standalone sector sentiment indices;
- a look-ahead-safe sentiment fusion attempt;
- a deployed Streamlit app that loads precomputed outputs.

Do not implement Part B analytical code until the unresolved methodology
parameters in `planning/part_b_methodology_spec.md` are approved.

## Non-Negotiable Methodology Rules

- Enforce strict no-look-ahead behaviour. Portfolio estimation, scaling,
  covariance estimation, expected-return estimation, sentiment signals, evidence
  coverage, hyperparameter choices, and any innovation used for trading must use
  information available strictly before the return being traded.
- Compute equity returns on the native equity trading calendar.
- Compute crypto returns on the native seven-day crypto calendar before any
  alignment.
- Build combined equity-plus-crypto funds on the common equity trading calendar
  only after native returns have been calculated.
- Annualise equity-only native funds with 252 periods per year.
- Annualise crypto-only native funds with 365 periods per year.
- Annualise combined funds evaluated on the common equity trading calendar with
  252 periods per year.
- Equal Weight is a benchmark only. It does not count as one of the two required
  optimisation methods.
- Minimum Variance and Maximum Sharpe are mandatory optimisation methods.
- Risk Parity is a possible later extension, but do not implement it until the
  student explicitly asks.

## Portfolio And Optimisation Rules

- Treat each `(asset family, method)` pair as a separate investable fund.
- Required method labels must distinguish benchmark and optimisation methods.
- State and enforce portfolio constraints explicitly before implementation.
- Optimisers must emit diagnostics: success flag, solver status/message,
  objective value, constraint residuals, final weight sum, min/max weights,
  asset count, covariance condition or regularisation note, and fallback status.
- Guard against silent solver failure, identical outputs across methods, NaNs,
  singular covariance matrices, tiny daily-return objective scaling, and
  accidental leverage or shorting.
- Fallback behaviour must be explicit and testable. Do not silently substitute
  Equal Weight when an optimiser fails.

## Sentiment Rules

- Do not forward-fill sentiment.
- Ticker-day sentiment is missing when no headline exists.
- Sector sentiment aggregates only tickers with observed news for that sector
  date and must preserve evidence counts, including active ticker count and
  headline count.
- Sentiment can affect weights only after at least one trading-day lag. A
  headline aligned to Monday is first usable for Tuesday's trade.
- Missing lagged sentiment for a trading overlay means no sentiment tilt for the
  affected ticker, not a filled or inferred signal.
- Never backfill sentiment or coverage from future observations.
- VADER or NLTK work is build-time only. `nltk` belongs in
  `requirements-dev.txt`; `streamlit_app.py` must not import `nltk` or score
  sentiment.

## Evidence-Aware Sentiment Extension

The planned innovation is an Evidence-Aware Sentiment overlay extending the Part A
News Evidence Coverage Layer. Full-sample 2020-2023 coverage rates/classes from
Part A must never be used in an out-of-sample backtest. Any coverage feature used
for trading must be reconstructed dynamically from information available only
through `t-1`, using an approved trailing or expanding window and an approved
scaling function.

Do not choose the final coverage formula, lookback window, or scaling function
without student approval.

## Streamlit And Artifact Rules

- `scripts/run_part_b.py` is the reproducible build path for analytical outputs.
- `streamlit_app.py` must load precomputed artifacts from `results/` and must not
  run portfolio backtests, optimisers, VADER, or long-running feature builds.
- Preserve exact required artifact filenames:
  - `results/data/fund_returns.csv`
  - `results/data/fund_weights.csv`
  - `results/data/sector_sentiment_index.csv`
  - `results/tables/performance_metrics.csv`
- Additional artifacts may be added with clear deterministic names under
  `results/data/`, `results/tables/`, or `results/figures/`.
- Generated artifacts must be deterministic: sorted rows/columns, stable method
  labels, ISO dates, no unnamed indexes, and reproducible CSV writes.
- Do not commit raw data, credentials, secrets, local `.env`, or
  `.streamlit/secrets.toml`.

## Testing And Verification

- Use test-first verification for material transformations.
- Port relevant tested Part A ETL, return, headline-alignment, and coverage tests
  before or alongside implementation.
- Add Part B tests for no-look-ahead weight timing, rebalance-date conventions,
  annualisation factors, optimiser diagnostics, solver fallback policy, sentiment
  lagging, missing-sentiment no-tilt behaviour, required output filenames, and
  Streamlit no-runtime-model constraints.
- Run focused tests after edits, then broader checks when implementation is
  complete:
  - `python -m pytest -q`
  - `python scripts/run_part_b.py`
  - `streamlit run streamlit_app.py`
  - `python scripts/check_handin.py`

## AI Workflow Logging

Maintain the AI workflow pack in `ai/`. For each material AI-assisted step, log:

- the prompt or task request;
- the AI output or proposed method;
- weaknesses, risks, or hallucinations found;
- corrections made by the student or assistant;
- verification commands and results;
- unresolved decisions or assumptions.

Any number, citation, method claim, or app claim must be traceable to the data,
the code, the project brief, or a source the student can verify.
