# SignalScope

See the signal. Inspect the evidence.

SignalScope is an evidence-first multi-asset portfolio research product for
FINS3645 Project B. It combines systematic equity portfolios, systematic crypto
portfolios, combined equity + crypto portfolios, sector news sentiment, evidence
confidence, portfolio look-through, and model falsification in one Streamlit
product.

The product is built around a deliberately skeptical research conclusion:
SignalScope did not find evidence that generic headline sentiment should replace
price-based portfolio construction. The Confidence Lens is therefore positioned
as an evidence-aware signal-governance layer, not an alpha engine, forecast model,
or recommendation engine. Matched-shrinkage falsification showed that a simpler
constant control reproduced much of the economic shrinkage effect, while dynamic
Confidence retained value in deciding where signals were muted or preserved.

## Product Journey

- **Fund**: compare systematic Equity, Crypto, and Combined funds.
- **Risk**: inspect fact sheets, holdings, concentration, turnover, and exposure.
- **Signal**: inspect standalone sector news sentiment over time.
- **Evidence**: separate sentiment direction from breadth and agreement of evidence.
- **Decision**: allocate across fund sleeves and inspect underlying look-through.
- **Challenge**: test whether the Confidence Lens earns its added complexity.

## Method Snapshot

- Equity funds use a 252-observation native equity estimation window.
- Crypto funds use a 365-observation native crypto estimation window.
- Combined funds use 252 common equity-calendar observations.
- Rebalancing is monthly.
- Portfolios are long-only, fully invested, and use no leverage.
- Risk-free rate is 0%.
- Transaction cost is 10 bps per dollar of turnover.
- Sentiment used for trading is lagged by at least one trading day.
- Equal Weight is the benchmark.
- Minimum Variance and Maximum Sharpe are the optimisation methods.

## Run The App

Use the Project B folder as the repository root. The app was tested with Python
3.13.13 and Streamlit 1.58.0.

Windows PowerShell:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The Streamlit entrypoint is:

```text
streamlit_app.py
```

## Reproduce The Analysis

Install both runtime and build dependencies before reproducing saved artifacts:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/run_part_b.py
```

The reproducible build scripts are:

- `scripts/run_part_b.py`: Station 3 portfolios, sentiment artifacts, Confidence
  Lens artifacts, and primary saved outputs.
- `scripts/run_phase2c.py`: matched-shrinkage placebo and falsification outputs.
- `scripts/check_handin.py`: mechanical submission and deployment checks.

## Precomputed App Boundary

The hosted Streamlit app reads precomputed saved artifacts from `results/`.
It does not run:

- portfolio optimisation;
- historical backtests;
- VADER scoring;
- NLTK;
- raw-data API access;
- custom Decision backtests.

This boundary is deliberate: it keeps deployment responsive, preserves the frozen
methodology, and makes the app reproducible from committed artifacts rather than
from hidden runtime computation.

The headline-level file `results/data/headline_sentiment_scores.csv` is a
research/audit artifact. It is about 45.3 MB, is never startup-loaded, is never
lazy-loaded, and is explicitly denied by the app data registry.

## Deployment

Recommended deployment layout: push the contents of this Project B folder as its
own repository root. In that layout, `.streamlit/config.toml`, `requirements.txt`,
and `streamlit_app.py` all live at the repository root.

Streamlit Community Cloud fields:

- Main file: `streamlit_app.py`
- Python version: select Python 3.13 in Advanced settings
- Secrets: none required

If the app is deployed from a larger parent repository instead, keep in mind that
Community Cloud runs from the repository root and only one `.streamlit/config.toml`
is used. The Project B folder is therefore the safer deployment root.

## Project Contents

- `streamlit_app.py`: thin Streamlit entrypoint.
- `.streamlit/`: Streamlit theme and server configuration.
- `app/`: Streamlit views, chart specs, data registry, and UI helpers.
- `src/`: analytical source used to build saved outputs.
- `scripts/`: reproducible build and submission-check scripts.
- `results/`: committed precomputed artifacts used by the app and report.
- `tests/`: analytical and Streamlit AppTest checks.
- `ai/`: AI workflow logs.
- `planning/`: frozen methodology and product specifications.
- `report/`: report planning and final report location.

## Rubric Traceability

SignalScope visibly includes Equity, Crypto, and Combined funds; an Equal Weight
benchmark; Minimum Variance and Maximum Sharpe optimisation; walk-forward
out-of-sample methodology; transaction costs; sector sentiment; the Evidence
Lens; allocation across funds; model challenge/falsification; and a Streamlit
app ready for public deployment after final checks.
