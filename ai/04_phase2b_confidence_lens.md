# AI Log 04 - Phase 2B Confidence Lens Fusion

## Prompt Recorded

The student requested Phase 2B: a look-ahead-safe sentiment fusion experiment and
SignalScope Confidence Lens. Phase 1 and Phase 2A were frozen. The required
comparison was:

- Base portfolio;
- Standard Sentiment overlay;
- SignalScope Confidence Lens overlay.

The primary base portfolio is Equity Minimum Variance. Equity Maximum Sharpe is a
robustness check. Equal Weight is not used as the primary fusion base. No
parameters were to be tuned against realised returns, and Streamlit was not to be
modified.

## Why The Innovation Was Reduced

Phase 2A found that Evidence/Breadth and Agreement/Disagreement contain distinct
information, while Concentration/Influence overlaps materially with breadth and
disagreement:

- active ticker share versus headline concentration HHI was strongly negative;
- cross-ticker dispersion and maximum leave-one-out influence were strongly
  related;
- disagreement supplied information not captured by headline count or breadth.

For Phase 2B the innovation therefore uses only:

- historical evidence breadth;
- cross-ticker sentiment agreement.

Concentration remains diagnostic metadata, not a third multiplier. This keeps the
fusion layer simpler and avoids adding a redundant dimension merely because it was
computed.

## Formulas

At each monthly rebalance, the signal cutoff is the base portfolio decision date,
which is the final trading day before the live rebalance date.

Raw direction:

- `S21`: trailing 21-trading-day mean sector sentiment from the approved
  equal-ticker sector index, using observations through the signal cutoff only.
- `Z = (S21 - cross-sectional mean) / cross-sectional standard deviation`.
- `Z_star = clip(Z, -2, +2)`.

Standard Sentiment overlay:

- `M_standard = 1 + 0.10 * Z_star`.

Evidence breadth:

- `B63 = observed constituent ticker-days with at least one headline /
  possible constituent ticker-days`.
- The denominator is `63 * 5` for each sector when the full trailing window is
  available and includes no-news ticker-days.

Agreement:

- `D_day`: population standard deviation (`ddof=0`) of available ticker-day VADER
  scores for a sector-day.
- A one-ticker observed day has dispersion zero; low evidence is captured
  separately by B63.
- `A21 = 1 - trailing 21-trading-day mean(D_day)`.

Confidence:

- `C = B63 * A21`, bounded in `[0, 1]`.
- C is evidence confidence only, not probability, accuracy, truth, or predictive
  confidence.

Confidence Lens overlay:

- `M_confidence = 1 + 0.10 * Z_star * C`.

All overlay weights are renormalised to full investment, remain long-only, and do
not introduce zero-weight base assets.

## Timing Conventions

- Base weights come from the existing Phase 1 equity optimiser outputs.
- Sentiment, breadth, and agreement use data through the base weight decision
  date only.
- The live return date is strictly after the signal cutoff.
- No full-sample coverage class, annual coverage rate, empirical quartile class,
  future sentiment, or same-holding-period return is used to form signals.

## Parameter Pre-Specification

Primary tilt strength is `0.10`. Sensitivity diagnostics use only `0.05` and
`0.20`. These are labelled as sensitivity analysis, not model selection. The
21-day direction/agreement window, 63-day breadth window, and `[-2, +2]` clipping
boundary were fixed by the prompt and were not selected from performance.

## Implementation

Implemented in `src/fusion.py`:

- sector confidence signal construction;
- Standard Sentiment overlay;
- SignalScope Confidence Lens overlay;
- paired OOS backtests using base portfolio dates;
- turnover and transaction-cost calculation from final overlay weights;
- comparison metrics and incremental effects;
- falsification diagnostics;
- sensitivity tables;
- four report-ready figures.

Updated `scripts/run_part_b.py` to write Phase 2B artifacts after the existing
Phase 1 and Phase 2A build steps.

## Errors And Corrections

- First real-data build failed because the attenuation-case helper pivoted daily
  returns across all tilt-strength sensitivity runs at once. The fix restricted
  that daily Standard-versus-Confidence comparison to the primary `0.10`
  specification.

No tests were weakened to pass.

## Verification Commands

Commands run from `fins2026/z5367955_projectB`:

- `..\..\.venv\Scripts\python.exe -m pytest -q tests/test_fusion_confidence_lens.py`
  - result: 7 passed.
- `..\..\.venv\Scripts\python.exe scripts\run_part_b.py`
  - first result: failed with duplicate pivot in attenuation-case helper.
  - after correction: Phase 1, Phase 2A, and Phase 2B outputs generated.
- `..\..\.venv\Scripts\python.exe -m pytest -q`
  - result: 27 passed.
- `..\..\.venv\Scripts\python.exe scripts\check_handin.py`
  - result: 21 checks passed, 2 reminders.

The build still prints Streamlit cache warnings when run outside Streamlit; the
provided data guide treats these as harmless when outputs are written.

## Generated Artifacts

Phase 2B CSV outputs:

- `results/data/sector_sentiment_confidence.csv`
- `results/data/fusion_returns.csv`
- `results/data/fusion_weights.csv`
- `results/tables/sentiment_fusion_comparison.csv`
- `results/tables/confidence_lens_summary.csv`
- `results/tables/confidence_lens_attenuation_cases.csv`
- `results/tables/fusion_sensitivity_analysis.csv`

Phase 2B figures:

- `results/figures/fusion_growth_min_variance.png`
- `results/figures/fusion_performance_comparison.png`
- `results/figures/confidence_lens_decomposition.png`
- `results/figures/confidence_lens_attenuation_case.png`

## Falsification Results

Primary Equity Minimum Variance at tilt `0.10`:

- Base Sharpe: about `0.404`.
- Standard Sentiment Sharpe: about `0.389`.
- Confidence Lens Sharpe: about `0.392`.
- Standard added about `0.528` total turnover versus Base.
- Confidence Lens added about `0.288` total turnover versus Base.
- Confidence Lens reduced turnover relative to Standard by about `0.239`, but
  still underperformed Base.

Equity Maximum Sharpe robustness at tilt `0.10`:

- Base Sharpe: about `0.469`.
- Standard Sentiment Sharpe: about `0.463`.
- Confidence Lens Sharpe: about `0.462`.
- Confidence Lens reduced turnover relative to Standard but did not improve
  Sharpe.

Confidence distribution:

- average C: about `0.659`;
- median C: about `0.657`;
- 10th percentile C: about `0.404`;
- 90th percentile C: about `0.842`;
- no rebalance-sector observations had C below `0.10`, so the lens does not
  merely suppress every signal.

The Confidence Lens changes economic behaviour mainly by attenuating sentiment
tilts and reducing incremental turnover/extreme sector changes. The evidence does
not support a performance-improvement claim versus the base portfolios.

## Negative Findings

- Both sentiment overlays underperformed the Base portfolio in the primary
  Minimum Variance experiment.
- The Confidence Lens improved over Standard Sentiment for Minimum Variance, but
  the improvement was not enough to beat the Base portfolio.
- In the Maximum Sharpe robustness check, Confidence Lens slightly underperformed
  Standard Sentiment on Sharpe.

## Robustness Analysis

At tilt strengths `0.05`, `0.10`, and `0.20`, sentiment overlays did not beat the
base portfolios on Sharpe. Higher tilt strength increased the performance drag.
The Confidence Lens consistently reduced the size of the Standard Sentiment
overlay, but this is a behavioural-control result, not alpha evidence.

## Remaining Work

Do not modify Streamlit until the Phase 2B results are reviewed. If used in the
report, the strongest defensible claim is about evidence-aware attenuation and
interpretability, not predictive outperformance.
