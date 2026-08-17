# AI Log 07 - Station 4 Phase 4A Foundation

## Objective

Implement only Station 4 Phase 4A: the production Streamlit foundation for
SignalScope. This phase establishes the app shell, cached startup artifact
loading, runtime validation, visual design system, stateful journey navigation,
first-screen hierarchy, responsive structure, and focused tests.

It does not implement Fund charts, Risk fact sheets, Signal charts, Evidence
Lens, Allocation Builder, or Model Challenge.

## Files Changed

- `streamlit_app.py`
- `app/__init__.py`
- `app/data.py`
- `app/design.py`
- `app/navigation.py`
- `app/components.py`
- `tests/test_app_data.py`
- `ai/07_station4_phase4a_foundation.md`

No frozen analytical source files or existing analytical outputs were modified.

## Architectural Choices

`streamlit_app.py` is now a thin orchestration entrypoint. It configures the
page, installs the design system, loads validated startup artifacts, renders the
journey selector, and delegates the active view to app components.

The new `app/` package separates responsibilities:

- `app/data.py`: artifact registry, path guardrails, required-column validation,
  and Streamlit-cached startup loading.
- `app/design.py`: SignalScope copy, truth labels, color semantics, and scoped
  CSS.
- `app/navigation.py`: stateful conditional journey navigation.
- `app/components.py`: Phase 4A UI primitives and polished future-stage states.

Product UI helpers were deliberately kept out of the frozen analytical `src/`
modules.

## Artifact Loading Contract

Startup loads only these approved compact CSV artifacts:

- `results/tables/performance_metrics.csv`
- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/tables/asset_class_exposure.csv`
- `results/tables/first_live_dates.csv`
- `results/tables/confidence_lens_summary.csv`
- `results/tables/sentiment_disagreement_examples.csv`
- `results/tables/sentiment_candidate_cases.csv`

The measured startup size is `3,429,747` bytes, matching the approved contract.

The data module rejects forbidden runtime artifacts, raw Parquet files, non-CSV
artifacts, and files outside `results/data` or `results/tables`. It validates
existence, non-empty CSV content, and required columns. It does not silently
substitute data.

`results/data/headline_sentiment_scores.csv` is explicitly excluded from the
startup registry and rejected if someone tries to register it.

## Navigation Approach

Navigation is locked to:

`Fund | Risk | Signal | Evidence | Decision | Challenge`

The app uses `st.session_state["view"]` as the source of truth and renders only
the selected journey stage. It uses `st.segmented_control` when available in the
installed Streamlit version, with `st.radio(horizontal=True)` as the compatible
fallback.

No generic Home, Funds, Sentiment, Data, or About tabs were used.

## Design-System Choices

The design system implements a restrained financial-product aesthetic with:

- high-contrast ink, muted text, white panels, and subtle linework;
- distinct signal semantics using negative-to-positive color;
- distinct evidence-confidence semantics using an amber evidence rail;
- neutral control semantics using gray;
- consistent 8px panel radius, light borders, and compact labels;
- deploy-safe system fonts;
- tabular/numeric readiness without default metric-card walls.

No decorative 3D effects, gratuitous gradients, formulas above the fold, or
methodology tables were added.

## Responsive Choices

The Phase 4A layout avoids mandatory wide tables and fixed-width structures.
The first-screen structural panels use Streamlit columns plus scoped CSS that
stacks the reserved canvases on narrow viewports. Truth labels wrap and become
full-width on mobile.

## Tests Added

`tests/test_app_data.py` covers:

- approved startup artifact paths resolve;
- required startup artifacts exist;
- expected startup size matches the contract;
- required columns are present;
- missing artifact handling;
- malformed artifact handling;
- `headline_sentiment_scores.csv` is not in the startup registry and is rejected;
- app modules do not introduce raw-data, `data_access`, NLTK/VADER, optimizer, or
  backtest dependencies.

## Tests Run

- `..\..\.venv\Scripts\python.exe -m pytest -q tests/test_app_data.py`
  - result: `6 passed in 2.72s`
- `..\..\.venv\Scripts\python.exe -m pytest -q`
  - result: `38 passed in 15.96s`
- `..\..\.venv\Scripts\python.exe scripts\check_handin.py`
  - result: `21 checks passed`
  - expected reminders: delete `__pycache__/` and `*.pyc` before zipping; no
    `report/report.pdf` yet.

## Deployment Smoke Result

Bounded local smoke-start command:

- `..\..\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless true --server.port 8765 --browser.gatherUsageStats false`

Result:

- Streamlit started successfully.
- Local HTTP request to `http://localhost:8765` returned status `200`.
- The process was stopped after the smoke check.
- Streamlit stderr included the expected startup line:
  `Uvicorn server started on 0.0.0.0:8765`.

## Deferred To Later Phases

- Phase 4B: Fund comparison chart, ranked fund tiles, Risk fact sheets,
  growth/drawdown charts, holdings, exposure, and concentration warnings.
- Phase 4C: Signal chart, Evidence Lens, neutrality/cancellation explorer, and
  volume/breadth panel.
- Phase 4D: Allocation Builder and precomputed historical blends.
- Phase 4E: Model Challenge and matched-shrinkage falsification view.
- Phase 4F: final responsive/deployment polish.
- Phase 4G: broader app interaction tests and final deploy verification.

## Analytical Freeze Confirmation

Phase 4A changed only app-layer files, tests, and this AI log. Frozen analytical
source files and existing analytical outputs were not edited.
