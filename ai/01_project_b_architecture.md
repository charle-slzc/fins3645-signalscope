# AI Log 01 - Project B Architecture And Methodology

## Original Read-Only Audit

The initial audit read the complete Project B starter materials before any edits.
It identified that the starter was intentionally incomplete:

- `src/features.py`, `src/portfolios.py`, `src/sentiment.py`, and `src/fusion.py`
  contained `NotImplementedError` stubs.
- `scripts/run_part_b.py` only loaded equity and crypto data and contained TODOs
  for returns, funds, sentiment, fusion, and artifacts.
- `streamlit_app.py` was a thin starter that loaded equity prices and displayed
  TODO messages for funds and sentiment.
- `AGENTS.md` and `CLAUDE.md` were placeholder AI instruction files.
- The required Part B output files were not yet present beyond `.gitkeep`
  placeholders.

The audit also flagged key methodological risks: look-ahead bias, equity/crypto
calendar mismatch, annualisation errors, solver failures, headline-only sentiment
noise, VADER deployment constraints, and the danger of making Streamlit recompute
heavy modelling work.

## Current Methodology Prompt

The student then provided project-specific methodological decisions:

- Equal Weight is a benchmark only and does not count as an optimisation method.
- Minimum Variance and Maximum Sharpe are mandatory optimisation methods.
- Risk Parity is only a possible later extension.
- Annualisation factors are 252 for equity-only native funds, 365 for crypto-only
  native funds, and 252 for combined funds on the equity calendar.
- Crypto returns must be calculated on the native seven-day crypto calendar before
  alignment to equity trading dates.
- Sentiment must not be forward-filled or backfilled.
- Sector sentiment must retain evidence counts.
- A missing lagged sentiment signal implies no trading tilt.
- All trading features, including future Evidence-Aware Sentiment coverage
  features, must use information available only through `t-1`.
- The full-sample Part A 2020-2023 coverage rates/classes must not be used in an
  OOS trading backtest.

## Part A Reuse Audit

The student's own Part A folder, `../z5367955_projectA`, was read in read-only
mode. Reusable tested components were found in:

- `src/etl.py`: cleaning functions for equities, crypto, and headlines, plus
  structured audit dataclasses and load wrappers.
- `src/features.py`: native daily returns, crypto-to-equity return alignment,
  headline trading-day alignment, headline panel assembly, descriptive coverage
  tables, token utilities, and full-sample News Evidence Coverage.
- `src/outputs.py`: deterministic artifact-writing patterns.
- `src/visuals.py`: report-ready figure construction and writing patterns.
- `src/finance_lexicon.py`: validated descriptive finance vocabulary.

The full-sample News Evidence Coverage functions can be reused for descriptive
diagnostics only. They cannot be used directly as OOS trading features because
their full-sample rates/classes include future observations.

## Key Decisions Captured

- Project B work is confined to `z5367955_projectB`.
- Project A can be read but not edited.
- `AGENTS.md` now enforces the approved no-look-ahead, calendar, annualisation,
  sentiment, artifact, Streamlit, and AI-logging rules.
- `planning/part_b_methodology_spec.md` now acts as the implementation contract.
- No analytical code was implemented in this step.

## Ambiguities And Unresolved Decisions

The following must be approved before coding:

- estimation-window type and length;
- rebalance frequency and exact date rule;
- risk-free-rate convention;
- transaction-cost assumption;
- portfolio constraints, including any weight caps;
- optimiser fallback policy;
- covariance regularisation policy;
- missing-return handling inside estimation windows;
- base equity method for sentiment fusion;
- sentiment tilt strength;
- sentiment clipping/scaling rule;
- sector-neutral versus unconstrained sentiment overlay;
- Evidence-Aware Sentiment coverage lookback;
- Evidence-Aware Sentiment denominator;
- Evidence-Aware Sentiment scaling function;
- Evidence-Aware Sentiment minimum evidence threshold.

## What Was Changed

- Replaced the placeholder `AGENTS.md` with project-specific agent instructions.
- Created `planning/part_b_methodology_spec.md`.
- Created this AI log at `ai/01_project_b_architecture.md`.

## Verification

This step was intentionally documentation-only. No portfolio, sentiment, fusion,
or Streamlit code was implemented. No Project A files were edited.

Follow-up verification after this edit should confirm:

- the placeholder phrase is gone from `AGENTS.md`;
- the methodology spec and AI log exist;
- `scripts/check_handin.py` recognises `AGENTS.md` as non-placeholder, while
  expected result/report warnings remain until analytical work is implemented.
