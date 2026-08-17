# AI Log 03 - Phase 2A Sentiment Diagnostics

## Prompt Recorded

The student requested a competition-grade diagnostic-only sentiment insight layer.
The work must not modify portfolio weights, tune parameters for returns, or
implement sentiment fusion. The goal is to test whether the standalone sentiment
index contains evidence-structure properties hidden by a conventional average
sentiment pipeline.

## Implementation Scope

Implemented `src/sentiment.py` as a diagnostic-only Station 3 layer:

- VADER headline scoring at build time only.
- Ticker-day sentiment aggregation without filling no-news days.
- Approved equal-ticker sector sentiment index.
- Diagnostic headline-weighted sector index for comparison only.
- Evidence structure diagnostics: active ticker share, headline count,
  headline-share HHI, cross-ticker sentiment dispersion, absolute sentiment
  magnitude, carryover share, and missing sector-days.
- Candidate case register for high-volume/low-breadth, low-volume/broad,
  extreme-sentiment/few-ticker, and moderate-mean/high-disagreement examples.
- Leave-one-ticker-out constituent influence diagnostics.
- Deterministic VADER failure taxonomy from observed corpus patterns.
- Same-day versus carried-over timing diagnostics.
- Pre-declared sector return validation for same-day descriptive association and
  t sentiment to t+1 sector return.
- Year-sector temporal stability diagnostics.
- Innovation reconnaissance table.
- Auditable `results/tables/sentiment_insight_register.csv`.

No changes were made to `src/fusion.py`, portfolio construction, portfolio
weights, or Streamlit views.

## Generated Artifacts

New Phase 2A artifacts:

- `results/data/headline_sentiment_scores.csv`
- `results/data/ticker_day_sentiment.csv`
- `results/data/sector_sentiment_index.csv`
- `results/tables/sentiment_sector_month_diagnostics.csv`
- `results/tables/sentiment_candidate_cases.csv`
- `results/tables/sentiment_weighting_comparison.csv`
- `results/tables/sentiment_weighting_disagreements.csv`
- `results/tables/sentiment_constituent_influence.csv`
- `results/tables/sentiment_constituent_influence_events.csv`
- `results/tables/sentiment_disagreement_examples.csv`
- `results/tables/sentiment_carryover_diagnostic.csv`
- `results/tables/sentiment_vader_failure_taxonomy.csv`
- `results/tables/sentiment_return_validation.csv`
- `results/tables/sentiment_temporal_stability.csv`
- `results/tables/sentiment_innovation_reconnaissance.csv`
- `results/tables/sentiment_insight_register.csv`

## Empirical Findings Captured

- The build scored 146,830 cleaned/aligned headlines and produced 37,962
  ticker-day sentiment observations.
- Equal-ticker and naive headline weighting materially diverged: maximum absolute
  sector-day difference was about 0.408 and 561 sector-days reversed sign.
- Candidate examples were preserved rather than cherry-picked: 18 high-volume /
  low-breadth cases, 20 low-volume / broad-evidence cases, 20 extreme-sentiment /
  few-ticker cases, and 20 moderate-mean / high-disagreement cases.
- Leave-one-ticker-out influence reached about 0.58 in absolute sector sentiment.
- The largest pre-declared lagged sentiment-return association was small, about
  0.101 in absolute correlation, so the validation currently qualifies rather
  than proves any predictive thesis.
- Timing-aware sentiment was the least-supported concept in this phase, while a
  combined evidence/agreement/concentration layer had the broadest diagnostic
  support.

## AI Mistakes Or Weaknesses Found

- The first real-data build surfaced harmless regex group warnings in the VADER
  taxonomy matcher. The patterns were changed to non-capturing groups.
- The first candidate insight register referenced a candidate-cases artifact
  before the runner wrote it. The artifact was added explicitly.
- The first carryover diagnostic wrote timing buckets as tuple strings; the
  grouping was corrected to emit clean labels.

## Verification Commands

Commands run from `fins2026/z5367955_projectB`:

- `..\..\.venv\Scripts\python.exe -m pytest -q tests/test_sentiment_diagnostics.py`
  - result: 3 passed.
- `..\..\.venv\Scripts\python.exe scripts\run_part_b.py`
  - result: Phase 1 portfolio and Phase 2A sentiment diagnostics generated.
- `..\..\.venv\Scripts\python.exe -m pytest -q`
  - result: 20 passed.
- `..\..\.venv\Scripts\python.exe scripts\check_handin.py`
  - result: 21 checks passed, 2 reminders.

The `run_part_b.py` command prints Streamlit cache warnings outside app runtime;
the project data guide identifies those warnings as harmless when the script
finishes and writes outputs.

## Remaining Decisions

Do not start fusion until the Phase 2A findings are reviewed and approved. Any
future Evidence-Aware, Agreement-Aware, Concentration-Aware, Timing-Aware, or
combined overlay must have pre-declared rules and strict no-look-ahead handling.
