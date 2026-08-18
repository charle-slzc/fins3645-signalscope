# AI Log 13 - Station 4 Phase 4F.1 Deployment Cleanup

## Objective

Prepare the completed SignalScope product for deployment cleanup without adding
features, redesigning the UI, changing analytical methodology, modifying saved
analytical values, or beginning final report prose.

Scope remained limited to:

- README rewrite;
- Python-version reproducibility marker and deployment note;
- requirements review;
- cache cleanup;
- deployment smoke checks;
- runtime artifact contract verification;
- final cleanup documentation.

No files under `src/` or `results/` were modified.

## Deployment Model

SignalScope is prepared to deploy with the Project B folder as its own repository
root. In that shape, the hosted Streamlit main file is:

```text
streamlit_app.py
```

The deployment root should include:

- `streamlit_app.py`
- `.streamlit/config.toml`
- `requirements.txt`
- `app/`
- `src/`
- `scripts/`
- `results/`
- `tests/`
- `ai/`
- `planning/`
- `report/`

Nested invocation from the parent `fins-agent` repository remains supported for
local compatibility, but the safer public deployment model is Project B as its
own repository root because `.streamlit/config.toml` then sits at the deployed
repo root.

## README Rewrite

`README.md` was rewritten from starter text into a concise product and technical
README for SignalScope.

It now documents:

- the product thesis: "See the signal. Inspect the evidence.";
- the six-stage journey: Fund, Risk, Signal, Evidence, Decision, Challenge;
- the honest research conclusion that generic headline sentiment did not replace
  price-based construction;
- the Confidence Lens as an evidence-aware signal-governance layer, not an alpha
  engine, forecast model, or recommendation engine;
- exact local app commands from the Project B root;
- analytical reproduction scripts;
- the precomputed app boundary;
- methodology snapshot;
- deployment entrypoint and repository-root layout;
- rubric traceability.

No report prose was drafted.

## Python-Version Decision

Inspection found:

- parent repo `.python-version`: `3.13`;
- parent repo `pyproject.toml`: `requires-python = ">=3.13,<3.14"`;
- Project B previously had no project-level Python marker;
- installed/tested local interpreter: Python `3.13.13`;
- installed/tested Streamlit: `1.58.0`;
- `requirements.txt`: `streamlit>=1.50,<2`.

Decision:

- add Project B `.python-version` containing `3.13` for local reproducibility and
  consistency with the parent repo tooling;
- do not add `runtime.txt`, because the current project evidence and Streamlit
  deployment guide use a browser deployment setting for Python selection;
- document in README that Streamlit Community Cloud should be configured with
  Python 3.13 in Advanced settings.

## Requirements Decision

`requirements.txt` was reviewed against runtime and analytical imports.

Runtime app imports use:

- `streamlit`
- `pandas`
- `numpy`

Reproduction/build scripts and analytical source also use:

- `scipy`
- `pyarrow`
- `requests`
- `matplotlib`
- `nltk` from `requirements-dev.txt`

Decision:

- no dependency changes were made;
- no Windows-only packages were present;
- broad lower bounds remain acceptable for this cleanup phase because they
  preserve analytical reproducibility and match the frozen product spec;
- `nltk` remains out of deploy requirements and in `requirements-dev.txt`.

Verification:

```text
No broken requirements found.
```

## Cache Cleanup

Removed generated junk inside Project B:

- `__pycache__/`
- `*.pyc`
- `.pytest_cache/` if present

No source files, saved results, tests, AI logs, or required app artifacts were
deleted.

Final `scripts/check_handin.py` no longer reports a pycache reminder.

## Startup Artifact Bytes

Startup registry verification:

```text
startup_bytes 3429747
expected_bytes 3429747
startup_keys performance_metrics,fund_returns,fund_weights,asset_class_exposure,first_live_dates,confidence_lens_summary,sentiment_disagreement_examples,sentiment_candidate_cases
```

Startup remains exactly `3,429,747` bytes.

## Lazy Artifacts

Lazy registry verification:

```text
confidence_lens_attenuation_cases
confidence_placebo_cases
confidence_placebo_comparison
confidence_placebo_quadrants
confidence_placebo_sector_year
confidence_placebo_selectivity
confidence_placebo_turnover_decomposition
fusion_placebo_returns
sector_sentiment_confidence
sector_sentiment_index
sentiment_weighting_comparison
sentiment_weighting_disagreements
ticker_day_sentiment
```

Signal, Evidence, and Challenge deeper data remains lazy.

Forbidden headline-level artifact check:

```text
headline_in_startup False
headline_in_lazy False
```

`results/data/headline_sentiment_scores.csv` remains outside both startup and
lazy registries.

## Large Research Artifact

`results/data/headline_sentiment_scores.csv` was not deleted.

Measured size:

```text
headline_research_bytes 45327317
```

It remains documented as:

- a research/audit artifact;
- not startup-loaded;
- not lazy-loaded;
- explicitly denied by the app data registry boundary.

Measured project size after final cache cleanup, README/Python-marker changes,
and this deployment log:

```text
total_repo_bytes 69148748
runtime_startup_bytes 3429747
headline_research_bytes 45327317
```

No deletion decision was made without deployment evidence.

## Fresh-Session Six-Page Check

Explicit fresh-session AppTest run:

```text
Fund ok
Risk ok
Signal ok
Evidence ok
Decision ok
Challenge ok
```

Each journey stage can render from a fresh session state.

## Streamlit Smoke Checks

Project B root:

```text
python -m streamlit run streamlit_app.py
project_root_http_status=200
```

Parent repo root nested invocation:

```text
python -m streamlit run fins2026/z5367955_projectB/streamlit_app.py
parent_root_http_status=200
```

Verification used the repo virtualenv Python executable because the unactivated
PATH `python` did not have Streamlit installed. This corresponds to the README
model after dependencies are installed or the virtualenv is activated.

## Tests

Full test suite:

```text
110 passed in 23.57s
```

## Hand-In Checker

Checker result after final cache cleanup:

```text
22 checks passed.
1 reminder(s):
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

The remaining warning is expected because report work has not started in this
phase.

## Frozen Analytics Verification

Command:

```text
git status --short -- src results
```

Result:

```text
<no output>
```

No analytical source files or saved result artifacts changed.

## Remaining Steps Before Public Deployment

Before public hand-in:

1. Commit the Project B repository contents.
2. Push Project B as its own GitHub repository root.
3. Configure Streamlit Community Cloud with main file `streamlit_app.py` and
   Python 3.13.
4. Confirm the deployed URL loads in a fresh browser.
5. Make the repository public at hand-in.
6. Complete final report work in a later phase and export `report/report.pdf`.

Phase 4F.1 deployment cleanup is complete.
