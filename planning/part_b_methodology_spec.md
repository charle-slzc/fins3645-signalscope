# Part B Methodology Specification

This is an implementation contract for `z5367955_projectB`. It is not the final
report. Analytical implementation must follow this file unless the student
approves a later change.

## Phase 1 Locked Decisions

The Station 3A portfolio phase now has approved settings:

- estimation windows: 252 native observations for equity-only funds, 365 native
  observations for crypto-only funds, and 252 common equity-calendar observations
  for combined funds;
- rebalance: monthly, with weights estimated through the previous observation
  and becoming live on the next valid observation;
- risk-free rate: 0 percent annual;
- transaction cost: 10 basis points per dollar of turnover, deducted on the
  rebalance return date;
- turnover: sum of absolute changes in active portfolio weights, with initial
  turnover measured from cash;
- constraints: long-only, fully invested, no leverage;
- covariance: sample covariance, with deterministic scale-aware diagonal
  regularisation only when needed for numerical stability;
- fallback: deterministic Equal Weight over eligible assets on optimiser failure,
  with a diagnostic record.

## 1. End-To-End Data Flow

1. Load raw hosted data only through `src/data_access.py`.
2. Clean equity prices, crypto prices, and news headlines using reusable Part A
   ETL logic where appropriate.
3. Compute equity returns on the native equity trading calendar from `adjClose`.
4. Compute crypto returns on the native seven-day crypto calendar from `adjClose`.
5. Align already-computed crypto returns to the equity trading calendar for the
   combined fund.
6. Build equity-only, crypto-only, and combined return panels for portfolio
   construction.
7. Run walk-forward OOS backtests for the Equal Weight benchmark and mandatory
   Minimum Variance and Maximum Sharpe optimisation methods.
8. Save fund returns, fund weights, metrics, diagnostics, and report figures under
   deterministic `results/` paths.
9. Clean, deduplicate, and align headlines to same or next observed equity trading
   day.
10. Score aligned headlines at build time, aggregate to ticker-day sentiment, then
    build standalone sector sentiment indices with evidence counts.
11. Lag sentiment by at least one trading day before any trading use.
12. Test the standard sentiment-fusion overlay against the corresponding base
    equity fund and save before-vs-after artifacts.
13. Streamlit reads precomputed `results/` artifacts and presents the investor
    journey without recomputing models.

## 2. Equity, Crypto And Combined Calendar Conventions

- Equity-only native funds use the observed equity trading calendar.
- Crypto-only native funds use the seven-day crypto calendar, after removing
  observations after `2023-12-31`.
- Combined funds use the common equity trading calendar.
- Crypto returns must be calculated before alignment to equity dates.
- Combined panels must not compute returns from merged price levels.
- Weekend-only crypto return observations are excluded from combined-fund trading
  because the combined fund is evaluated on equity trading dates.

## 3. Annualisation Conventions

- Equity-only native fund: 252 periods per year.
- Crypto-only native fund: 365 periods per year.
- Combined fund evaluated on common equity trading calendar: 252 periods per year.
- Any asset-level descriptive statistics must state whether they use native or
  common-calendar observations.

## 4. Portfolio Benchmark And Method Definitions

- Equal Weight is a benchmark only.
- Equal Weight does not count toward the two required optimisation methods.
- Mandatory optimisation method 1: Minimum Variance.
- Mandatory optimisation method 2: Maximum Sharpe.
- Risk Parity is a possible later extension and must not be implemented until
  explicitly requested.

Minimum Variance should minimise estimated portfolio variance under the approved
constraints. Maximum Sharpe should maximise estimated excess-return-per-unit-risk
under the approved constraints and risk-free-rate convention.

## 5. Walk-Forward OOS Timeline

For every OOS return date, the backtest must:

- select the estimation sample ending strictly before the return date being
  traded;
- estimate inputs using only historical observations inside the approved window;
- compute weights on approved rebalance dates only;
- carry the most recent valid weights between rebalance dates;
- start live OOS performance only after the first estimation window is complete.

The first live backtest date is determined by the approved Phase 1 estimation
window for each family.

## 6. Rebalance-Date And Weight-Application Convention

The convention to implement after approval:

- determine rebalance dates from the relevant trading calendar;
- estimate weights using data available through `t-1`;
- apply the newly formed weights to returns from `t` onward;
- hold weights until the next rebalance date;
- record both the weight decision date and the first return date affected.

Phase 1 uses monthly rebalancing.

## 7. Estimation-Window Rule

Phase 1 uses trailing rolling windows:

- equity-only: trailing 252 native equity-return observations;
- crypto-only: trailing 365 native crypto-return observations;
- combined: trailing 252 common equity-calendar return observations.

Eligibility rule: an asset must have finite returns for every observation in the
estimation window to enter that rebalance. Missing returns are not zero-filled.
Fund starts are calendar-native: equity and combined funds start after 252
eligible return observations; crypto starts after 365 native return observations.

## 8. Risk-Free-Rate Rule

Phase 1 uses a 0 percent annual risk-free rate. No external risk-free-rate series
is used.

## 9. Transaction-Cost Rule

Phase 1 uses a turnover-based cost:

- turnover is `sum(abs(new_weight - previous_weight))` across the union of old
  and new eligible assets;
- the initial rebalance is measured from cash, so turnover is 1.0 for a fully
  invested long-only fund;
- cost is `0.001 * turnover`;
- cost is deducted from net return on the live rebalance date;
- gross return, turnover, transaction cost, and net return are all preserved.

## 10. Portfolio Constraints

Phase 1 constraints:

- fully invested weights summing to 1.0;
- long-only weights between 0.0 and 1.0;
- no leverage;
- no shorting;
- no arbitrary asset caps;
- no equity/crypto sleeve constraints.

Implementation must expose constraints in outputs or diagnostics so the report
can state them clearly.

## 11. Solver Failure And Fallback Policy

Every optimisation run must record diagnostics:

- fund family;
- method;
- rebalance date;
- estimation start and end dates;
- asset count and valid observation count;
- solver success flag;
- solver status/message;
- objective value;
- weight-sum residual;
- minimum and maximum weight;
- covariance regularisation or condition diagnostic;
- fallback used flag and fallback reason.

Phase 1 failure policy: failed Minimum Variance or Maximum Sharpe optimisations
fall back deterministically to Equal Weight over that rebalance's eligible
assets. The fallback remains in the main fund return stream, but every fallback
must be visible in diagnostics. Do not silently replace a failed optimiser with
Equal Weight.

## 12. Headline Alignment And Sentiment Timing

- Deduplicate headlines on `ticker`, `date`, and `title`.
- Preserve raw headline text for VADER; do not strip casing, punctuation,
  negation, or stopwords before scoring.
- Convert headline dates from timezone-aware UTC to tz-naive daily dates.
- Align every headline to the same observed equity trading day if possible, else
  the next observed equity trading day.
- Headlines after the final observed trading day remain unmatched and are not
  forced into 2024 trading.
- Sentiment aligned to trading day `t` is not tradable until at least trading day
  `t+1`.

## 13. No-News Treatment

- Do not forward-fill sentiment.
- Do not backfill sentiment.
- A ticker-day with no headline has missing sentiment, not neutral sentiment.
- Sector sentiment should average only tickers with observed news for that sector
  date.
- Sector sentiment outputs must preserve active ticker count and headline count.
- For trading overlays, missing lagged sentiment means no sentiment tilt for that
  ticker.

## 14. Standalone Sector Sentiment Construction

The standalone sentiment index should:

- score aligned headlines at build time;
- aggregate headline scores to ticker-day scores;
- aggregate ticker-day scores to sector-day scores by equal-weighting observed
  ticker scores within each sector;
- include evidence columns such as active ticker count, headline count, and
  possible ticker count;
- keep missing sector-day scores missing when no ticker in the sector has news;
- save to `results/data/sector_sentiment_index.csv`.

Validation should report coverage, neutral-score share if VADER is used, and
sector differences in evidence depth.

## 15. Standard Sentiment-Fusion Design To Test

The baseline fusion design to test, after unresolved parameters are approved:

- use the base equity fund weights from a mandatory optimisation method;
- join lagged ticker-day sentiment available through `t-1`;
- apply a bounded cross-sectional tilt toward higher lagged sentiment and away
  from lower lagged sentiment;
- leave a ticker un-tilted when its lagged sentiment is missing;
- renormalise weights under approved constraints;
- compare base versus sentiment-augmented performance using the same OOS dates,
  costs, annualisation, and metrics.

Unresolved before coding:

- base method to tilt;
- sentiment score used in the tilt;
- tilt strength;
- clipping/winsorisation rule, if any;
- whether the overlay is sector-neutral or allowed to alter sector exposures.

## 16. Evidence-Aware Sentiment Concept

The potential innovation is an Evidence-Aware Sentiment overlay extending the
Part A News Evidence Coverage Layer. It may use dynamically measured historical
headline evidence to scale or gate sentiment tilts.

Strict look-ahead-safe requirements:

- do not use full-sample 2020-2023 Part A coverage rates/classes in any trading
  backtest;
- compute any coverage feature using only data available through `t-1`;
- use an approved trailing or expanding window;
- define the evidence denominator before coding;
- preserve active ticker count/headline count so low-evidence signals can be
  audited;
- save a diagnostic table showing the dynamic coverage feature by date/ticker or
  date/sector;
- compare the evidence-aware overlay against both the base fund and the standard
  sentiment overlay.

Unresolved before coding:

- coverage lookback;
- coverage denominator;
- coverage scaling function;
- minimum evidence threshold;
- whether coverage scales ticker-level or sector-level sentiment.

## 17. Required Output Artifact Contract

Required exact files:

- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/data/sector_sentiment_index.csv`
- `results/tables/performance_metrics.csv`

Required report/app supporting artifacts:

- growth-of-one-dollar figure comparing methods;
- drawdown figure for at least one fund;
- portfolio-weights-over-time figure across methods for at least one fund;
- Sharpe or return-vs-risk barplot across funds and methods;
- sentiment-index time-series figure for equity sectors;
- fusion before-vs-after comparison table and figure;
- optimiser diagnostics table;
- methodology/config table capturing annualisation, constraints, estimation
  window, rebalance rule, risk-free rate, and transaction-cost assumption.

Artifact rules:

- use ISO dates;
- sort rows and columns deterministically;
- write CSVs without indexes;
- preserve exact fund and method labels;
- keep raw data out of the repository;
- keep app-readable artifacts committed under `results/`.

## 18. Test Plan

Port or adapt these Part A tests:

- `tests/test_etl.py`: schema enforcement, date normalisation, crypto sample cap,
  duplicate price rows, conflicting ticker-date rows, numeric conversion,
  headline deduplication, publisher preservation, equity missing-date calendar,
  crypto complete-calendar audit, real data audit counts.
- `tests/test_features.py`: native daily returns, no cross-ticker returns, first
  ticker observation excluded, duplicate ticker-date rejection, crypto returns
  before equity-calendar alignment, no forward-fill during alignment, ticker
  collision rejection, native descriptive statistics, headline same/holiday/
  weekend/trailing alignment, full price calendar for headline alignment,
  deterministic text aggregation, sector conflict rejection, coverage universe
  denominators, descriptive token and lexicon counts.
- `tests/test_outputs.py`: deterministic CSV writing, exact filenames, no raw CSV
  or Parquet outside `results/`, no object cells, ISO date exports.

Add new Part B tests:

- Equal Weight labelled as benchmark only.
- Minimum Variance and Maximum Sharpe both present for combined fund.
- Annualisation factor is 252 for equity and combined funds, 365 for crypto-only
  native funds.
- Each OOS return uses weights estimated from data ending before that return.
- Rebalance weights are applied only from the first approved live return date.
- Solver diagnostics exist for every optimisation rebalance.
- Solver fallback policy is explicit and detectable.
- Sentiment used for trading is lagged by at least one trading day.
- Missing lagged sentiment leaves weights untilted for affected tickers.
- Sector sentiment preserves active ticker and headline counts.
- Required artifact filenames are created.
- `streamlit_app.py` does not import `nltk`, run VADER, or call backtest
  functions.

## 19. Remaining Methodological Decisions Requiring Approval

Resolve these before sentiment/fusion coding:

- base equity method for sentiment fusion;
- sentiment tilt strength;
- sentiment clipping or scaling rule;
- sector-neutral versus unconstrained sentiment overlay;
- Evidence-Aware Sentiment coverage lookback;
- Evidence-Aware Sentiment denominator;
- Evidence-Aware Sentiment scaling function;
- Evidence-Aware Sentiment minimum evidence threshold.

## Part A Reuse Contract

| Source file/function | Purpose | Part B destination | Copy unchanged? | Part B-specific modification | Tests worth porting |
|---|---|---|---|---|---|
| `src/etl.py::clean_equity_prices` | Clean equity OHLCV, normalise dates, enforce schema, dedupe, audit integrity. | `src/etl.py` | Mostly yes | Keep audit outputs available for Part B diagnostics; no report-only wording required. | `test_required_schemas_are_enforced`, `test_cleaned_dates_are_tz_naive_daily_values`, `test_price_outputs_are_unique_by_ticker_date`, `test_conflicting_equity_ticker_date_rows_raise_value_error`, `test_real_data_audit_counts_remain_unchanged` |
| `src/etl.py::clean_crypto_prices` | Clean crypto OHLCV, cap after `2023-12-31`, dedupe, audit complete daily calendar. | `src/etl.py` | Yes | Preserve native seven-day calendar for crypto-only funds before combined alignment. | `test_crypto_cap_removes_expected_source_rows`, `test_crypto_missing_dates_use_complete_daily_calendar_after_cap`, `test_conflicting_crypto_ticker_date_rows_raise_value_error` |
| `src/etl.py::clean_news_headlines` | Clean headlines, normalise UTC dates, dedupe only ticker-date-title, preserve raw fields. | `src/etl.py` | Yes | Feed Part B sentiment after alignment; do not add sentiment here. | `test_headline_deduplication_uses_ticker_date_title_only`, `test_multiple_different_headlines_on_one_ticker_date_are_preserved`, `test_missing_publisher_rows_are_preserved_and_audited` |
| `src/etl.py::build_station1_data` and load wrappers | Load all clean source data through `data_access`. | `src/etl.py` and `scripts/run_part_b.py` | Mostly yes | Part B runner should use it as the data foundation, then continue to portfolios and sentiment. | `test_real_data_audit_counts_remain_unchanged` |
| `src/features.py::daily_returns` | Compute simple returns within ticker on native calendar. | `src/features.py` | Yes | Use for equity and crypto before any combined alignment; portfolio code may pivot from its output. | `test_daily_returns_are_sorted_within_ticker_and_preserve_metadata`, `test_ticker_boundaries_do_not_create_cross_ticker_returns`, `test_first_observation_per_ticker_is_excluded`, `test_daily_returns_raise_on_duplicate_ticker_dates` |
| `src/features.py::align_crypto_to_equity_calendar` | Reindex native crypto returns to observed equity return dates and join with equity returns. | `src/features.py` | Yes | Combined fund uses 252 annualisation after this alignment; crypto-only fund must still use native panel. | `test_crypto_returns_are_calculated_before_equity_calendar_alignment`, `test_alignment_uses_equity_dates_excludes_weekends_and_does_not_forward_fill`, `test_alignment_raises_on_ticker_collision` |
| `src/features.py::build_return_panels` | Build equity, crypto, and combined return panels. | `src/features.py` | Yes | May need extended metadata for Part B annualisation and fund family labels. | `test_real_station1_data_builds_return_panels` |
| `src/features.py::align_headlines_to_trading_calendar` | Map headlines to same or next observed equity trading day and retain unmatched rows. | `src/features.py` | Yes | Part B sentiment must lag aligned trading dates before trading use. | `test_headline_alignment_same_day_weekend_holiday_and_trailing_rows`, `test_headline_alignment_uses_full_price_calendar_not_return_calendar` |
| `src/features.py::assemble_headline_panel` | Build deterministic ticker-sector trading-day text panel with counts and raw text. | `src/features.py` | Mostly yes | Sentiment scoring should consume this panel; no forward-fill or scoring added here. | `test_text_raw_preserves_title_and_newline_aggregation_is_deterministic`, `test_panel_counts_publishers_missing_values_and_sector_conflicts`, `test_no_sentiment_score_columns_exist_in_text_outputs` |
| `src/features.py::daily_news_flow` | Daily counts of headlines, active tickers, sectors, and non-trading-day carry-in. | `src/features.py` or `src/sentiment.py` diagnostics | Yes | Useful for sentiment evidence diagnostics and app context, not directly tradable unless lagged. | `test_coverage_tables_use_complete_calendar_and_universe_denominators` |
| `src/features.py::ticker_coverage_table` and `sector_coverage_table` | Full-sample descriptive coverage tables. | Report diagnostics only | Yes for descriptive/report use | Must not be used as trading features in OOS backtests. | `test_coverage_tables_use_complete_calendar_and_universe_denominators` |
| `src/features.py::build_news_evidence_coverage` | Part A full-sample News Evidence Coverage Layer. | Report/app descriptive layer only; possible design reference for dynamic extension | No for trading | Full-sample rates/classes leak future information if used in OOS trading. A new dynamic through-`t-1` coverage feature is required for trading use. | Coverage tests are worth adapting, but expected full-sample values should not govern OOS trading logic. |
| `src/features.py::tokenize_text`, `word_count`, `vocabulary_count`, `top_terms`, `lexicon_match_counts` | Deterministic descriptive text utilities. | `src/features.py` and sentiment diagnostics | Mostly yes | Do not preprocess VADER input with these tokenizers; VADER needs raw text. | `test_tokenizer_top_terms_and_lexicon_counts_are_descriptive_only`, `test_no_sentiment_score_columns_exist_in_text_outputs` |
| `src/finance_lexicon.py::validate_course_mini_finance_lexicon` | Validated finance vocabulary for descriptive membership counts. | Optional sentiment diagnostics or later lexicon extension reference | Yes for validation; not sufficient as sentiment model | Current Part A lexicon excludes tone and is descriptive only. Any Part B sentiment lexicon must define polarity/score separately and be logged. | `test_embedded_lexicon_has_exactly_82_entries`, `test_canonical_word_list_checksum_validates`, `test_no_runtime_api_exposes_tone_label_mappings` |
| `src/outputs.py` deterministic writing helpers | Stable CSV writing, ISO dates, no object cells, exact artifact manifest pattern. | New Part B outputs module or runner helper | Pattern yes, filenames no | Part B has different required artifacts and should not reuse Part A manifests unchanged. | `test_write_outputs_is_deterministic_and_reopens`, `test_written_dates_use_iso_format`, `test_required_filenames_exist_after_write` |
| `src/visuals.py` style constants and figure-writing pattern | Report-ready figure style and PNG export pattern. | Optional Part B visual helpers | Pattern yes | Figure content must be Part B specific; visual palette may be reused if still coherent. | `test_each_figure_has_required_text_axes_size_and_font`, `test_write_figures_creates_exact_pngs_and_reopens` |
