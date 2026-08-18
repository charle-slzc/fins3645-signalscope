SignalScope Fund graph fix v2

Replace ONLY:
- fins2026/z5367955_projectB/app/charts.py
- fins2026/z5367955_projectB/app/components.py

Why:
1. The screenshot showed Python/app state saying Equity / Equal Weight while the Vega chart still highlighted and labelled Combined / Equal Weight.
2. The chart now gets a state-derived Streamlit component key from selected FundKey + Family focus + Method focus. Any authoritative state change remounts the chart, preventing stale browser-side Vega state from visually surviving.
3. The selected fund gets a dedicated salmon halo layer driven by datum.is_selected.
4. Focus matches are more visually distinct; nonmatching context remains visible.
5. No analytics, src/, results/, Decision logic, or fund coordinates are changed.

After replacement:
python -m pytest -q
python scripts/check_handin.py
git diff --check -- .
git status --short -- src results
streamlit run streamlit_app.py
