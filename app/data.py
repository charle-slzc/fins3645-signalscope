"""Validated startup artifact loading for the SignalScope Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st


EXPECTED_STARTUP_BYTES = 3_429_747

NEVER_LOAD_ARTIFACTS = frozenset(
    {
        Path("results/data/headline_sentiment_scores.csv"),
    }
)

RAW_DATA_SUFFIXES = frozenset({".parquet"})
ALLOWED_ARTIFACT_ROOTS = ("results/data", "results/tables")


class ArtifactValidationError(RuntimeError):
    """Raised when a runtime artifact is missing, malformed, or disallowed."""


@dataclass(frozen=True)
class ArtifactSpec:
    key: str
    relative_path: Path
    required_columns: frozenset[str]
    expected_bytes: int
    purpose: str


@dataclass(frozen=True)
class StartupArtifacts:
    frames: dict[str, pd.DataFrame]
    total_bytes: int
    expected_bytes: int

    @property
    def row_counts(self) -> dict[str, int]:
        return {key: len(frame) for key, frame in self.frames.items()}


STARTUP_ARTIFACTS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        key="performance_metrics",
        relative_path=Path("results/tables/performance_metrics.csv"),
        required_columns=frozenset(
            {
                "fund_family",
                "method",
                "method_type",
                "net_annualised_return",
                "net_annualised_volatility",
                "net_sharpe_ratio",
                "net_max_drawdown",
                "total_turnover",
                "first_live_date",
            }
        ),
        expected_bytes=3_238,
        purpose="fund comparison and headline metrics",
    ),
    ArtifactSpec(
        key="fund_returns",
        relative_path=Path("results/data/fund_returns.csv"),
        required_columns=frozenset(
            {
                "date",
                "fund_family",
                "method",
                "method_type",
                "net_return",
                "growth_net",
                "drawdown_net",
                "live_rebalance_date",
                "decision_date",
            }
        ),
        expected_bytes=1_779_532,
        purpose="fund growth, drawdown, and future allocation blends",
    ),
    ArtifactSpec(
        key="fund_weights",
        relative_path=Path("results/data/fund_weights.csv"),
        required_columns=frozenset(
            {
                "date",
                "fund_family",
                "method",
                "method_type",
                "asset",
                "asset_class",
                "weight",
                "live_rebalance_date",
                "decision_date",
            }
        ),
        expected_bytes=1_596_050,
        purpose="holdings, concentration, and exposure checks",
    ),
    ArtifactSpec(
        key="asset_class_exposure",
        relative_path=Path("results/tables/asset_class_exposure.csv"),
        required_columns=frozenset(
            {"date", "fund_family", "method", "method_type", "asset_class", "exposure"}
        ),
        expected_bytes=30_245,
        purpose="equity and crypto exposure summaries",
    ),
    ArtifactSpec(
        key="first_live_dates",
        relative_path=Path("results/tables/first_live_dates.csv"),
        required_columns=frozenset(
            {
                "fund_family",
                "method",
                "method_type",
                "first_live_date",
                "estimation_window",
                "periods_per_year",
            }
        ),
        expected_bytes=605,
        purpose="first-live dates and methodology disclosure support",
    ),
    ArtifactSpec(
        key="confidence_lens_summary",
        relative_path=Path("results/tables/confidence_lens_summary.csv"),
        required_columns=frozenset(
            {
                "base_method",
                "tilt_strength",
                "average_confidence",
                "tilt_magnitude_reduction",
                "incremental_turnover_standard_vs_base",
                "incremental_turnover_confidence_vs_base",
            }
        ),
        expected_bytes=1_588,
        purpose="headline confidence lens summary for first-read context",
    ),
    ArtifactSpec(
        key="sentiment_disagreement_examples",
        relative_path=Path("results/tables/sentiment_disagreement_examples.csv"),
        required_columns=frozenset(
            {
                "case_type",
                "date",
                "sector",
                "sector_sentiment",
                "cross_ticker_sentiment_std",
                "active_ticker_count",
                "headline_count",
                "lowest_ticker",
                "highest_ticker",
            }
        ),
        expected_bytes=3_357,
        purpose="neutrality and cancellation examples",
    ),
    ArtifactSpec(
        key="sentiment_candidate_cases",
        relative_path=Path("results/tables/sentiment_candidate_cases.csv"),
        required_columns=frozenset(
            {
                "case_type",
                "description",
                "date",
                "sector",
                "sector_sentiment",
                "headline_count",
                "active_ticker_share",
                "dominant_ticker",
                "dominant_ticker_headline_share",
            }
        ),
        expected_bytes=15_132,
        purpose="volume and breadth examples",
    ),
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def startup_registry() -> tuple[ArtifactSpec, ...]:
    return STARTUP_ARTIFACTS


def expected_startup_size() -> int:
    return sum(spec.expected_bytes for spec in STARTUP_ARTIFACTS)


def _normalise_relative_path(path: Path) -> Path:
    return Path(path.as_posix())


def _validate_spec_is_allowed(spec: ArtifactSpec) -> None:
    relative_path = _normalise_relative_path(spec.relative_path)
    relative_string = relative_path.as_posix()
    if relative_path in NEVER_LOAD_ARTIFACTS:
        raise ArtifactValidationError(
            f"{relative_string} is a forbidden runtime artifact and must not be loaded."
        )
    if relative_path.suffix.lower() in RAW_DATA_SUFFIXES:
        raise ArtifactValidationError(
            f"{relative_string} is raw data; SignalScope loads precomputed CSV artifacts only."
        )
    if relative_path.suffix.lower() != ".csv":
        raise ArtifactValidationError(
            f"{relative_string} is not a CSV artifact and cannot be part of startup loading."
        )
    if not relative_string.startswith(ALLOWED_ARTIFACT_ROOTS):
        raise ArtifactValidationError(
            f"{relative_string} is outside the approved results/data and results/tables roots."
        )


def resolve_artifact_path(root: Path, spec: ArtifactSpec) -> Path:
    _validate_spec_is_allowed(spec)
    candidate = (root / spec.relative_path).resolve()
    root_resolved = root.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ArtifactValidationError(
            f"{spec.relative_path.as_posix()} resolves outside the project folder."
        )
    return candidate


def validate_registry(specs: tuple[ArtifactSpec, ...] = STARTUP_ARTIFACTS) -> None:
    keys = [spec.key for spec in specs]
    if len(keys) != len(set(keys)):
        raise ArtifactValidationError("Startup artifact keys must be unique.")
    for spec in specs:
        _validate_spec_is_allowed(spec)


def validate_artifact_file(path: Path, spec: ArtifactSpec) -> int:
    if not path.exists():
        raise ArtifactValidationError(
            f"Missing required startup artifact: {spec.relative_path.as_posix()}. "
            "Run the frozen build pipeline before opening the deployed product."
        )
    if not path.is_file():
        raise ArtifactValidationError(
            f"Startup artifact is not a file: {spec.relative_path.as_posix()}."
        )
    return path.stat().st_size


def read_artifact(path: Path, spec: ArtifactSpec) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - exercised by Streamlit users.
        raise ArtifactValidationError(
            f"Could not read {spec.relative_path.as_posix()} as a CSV artifact."
        ) from exc

    missing = sorted(spec.required_columns.difference(frame.columns))
    if missing:
        missing_text = ", ".join(missing)
        raise ArtifactValidationError(
            f"Malformed startup artifact {spec.relative_path.as_posix()}: "
            f"missing required column(s): {missing_text}."
        )
    if frame.empty:
        raise ArtifactValidationError(
            f"Startup artifact {spec.relative_path.as_posix()} is empty."
        )
    return frame


def load_startup_artifacts(root: Path | None = None) -> StartupArtifacts:
    root = project_root() if root is None else Path(root)
    validate_registry()

    frames: dict[str, pd.DataFrame] = {}
    total_bytes = 0
    for spec in STARTUP_ARTIFACTS:
        path = resolve_artifact_path(root, spec)
        total_bytes += validate_artifact_file(path, spec)
        frames[spec.key] = read_artifact(path, spec)

    return StartupArtifacts(
        frames=frames,
        total_bytes=total_bytes,
        expected_bytes=EXPECTED_STARTUP_BYTES,
    )


@st.cache_data(show_spinner="Loading precomputed SignalScope artifacts...")
def load_startup_artifacts_cached(root: str | None = None) -> StartupArtifacts:
    return load_startup_artifacts(Path(root) if root else project_root())

