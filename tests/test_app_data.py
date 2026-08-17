from pathlib import Path

import pandas as pd
import pytest

from app import data


def test_startup_registry_resolves_existing_project_artifacts():
    root = Path(__file__).resolve().parent.parent
    data.validate_registry()

    paths = [data.resolve_artifact_path(root, spec) for spec in data.startup_registry()]

    assert len(paths) == 8
    assert all(path.exists() for path in paths)
    assert data.expected_startup_size() == data.EXPECTED_STARTUP_BYTES


def test_startup_artifacts_load_with_required_columns():
    root = Path(__file__).resolve().parent.parent

    artifacts = data.load_startup_artifacts(root)

    assert artifacts.total_bytes == data.EXPECTED_STARTUP_BYTES
    assert artifacts.expected_bytes == data.EXPECTED_STARTUP_BYTES
    assert set(artifacts.frames) == {spec.key for spec in data.startup_registry()}
    for spec in data.startup_registry():
        assert spec.required_columns.issubset(artifacts.frames[spec.key].columns)


def test_missing_artifact_raises_clear_validation_error(tmp_path):
    spec = data.ArtifactSpec(
        key="missing",
        relative_path=Path("results/tables/missing.csv"),
        required_columns=frozenset({"date"}),
        expected_bytes=1,
        purpose="test missing file",
    )
    path = data.resolve_artifact_path(tmp_path, spec)

    with pytest.raises(data.ArtifactValidationError, match="Missing required startup artifact"):
        data.validate_artifact_file(path, spec)


def test_malformed_artifact_reports_missing_columns(tmp_path):
    path = tmp_path / "artifact.csv"
    pd.DataFrame({"date": ["2021-01-01"]}).to_csv(path, index=False)
    spec = data.ArtifactSpec(
        key="malformed",
        relative_path=Path("results/tables/malformed.csv"),
        required_columns=frozenset({"date", "fund_family"}),
        expected_bytes=1,
        purpose="test malformed file",
    )

    with pytest.raises(data.ArtifactValidationError, match="fund_family"):
        data.read_artifact(path, spec)


def test_never_load_artifact_is_not_registered_and_is_rejected():
    registry_paths = {spec.relative_path for spec in data.startup_registry()}

    assert Path("results/data/headline_sentiment_scores.csv") not in registry_paths

    forbidden = data.ArtifactSpec(
        key="headline_scores",
        relative_path=Path("results/data/headline_sentiment_scores.csv"),
        required_columns=frozenset({"title"}),
        expected_bytes=45_327_317,
        purpose="forbidden headline audit data",
    )
    with pytest.raises(data.ArtifactValidationError, match="forbidden runtime artifact"):
        data.validate_registry((forbidden,))


def test_app_modules_do_not_import_raw_or_analytical_dependencies():
    root = Path(__file__).resolve().parent.parent
    app_sources = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app").glob("*.py"))
    entrypoint = (root / "streamlit_app.py").read_text(encoding="utf-8")
    combined = app_sources + "\n" + entrypoint

    forbidden_tokens = (
        "src.data_access",
        "from src import data_access",
        "load_equity_prices",
        "load_crypto_prices",
        "load_news_headlines",
        "nltk",
        "SentimentIntensityAnalyzer",
        "scipy.optimize",
        "run_backtest",
    )
    for token in forbidden_tokens:
        assert token not in combined
