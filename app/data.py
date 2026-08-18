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

LAZY_ARTIFACTS: dict[str, ArtifactSpec] = {
    "sector_sentiment_index": ArtifactSpec(
        key="sector_sentiment_index",
        relative_path=Path("results/data/sector_sentiment_index.csv"),
        required_columns=frozenset(
            {
                "date",
                "sector",
                "sector_sentiment",
                "active_ticker_count",
                "headline_count",
                "cross_ticker_sentiment_std",
                "possible_ticker_count",
                "active_ticker_share",
                "missing_sector_day",
            }
        ),
        expected_bytes=1_456_429,
        purpose="Signal sector sentiment time series and evidence availability",
    ),
    "sector_sentiment_confidence": ArtifactSpec(
        key="sector_sentiment_confidence",
        relative_path=Path("results/data/sector_sentiment_confidence.csv"),
        required_columns=frozenset(
            {
                "live_rebalance_date",
                "signal_cutoff_date",
                "sector",
                "s21",
                "z_star",
                "b63",
                "a21",
                "confidence",
                "standard_multiplier",
                "confidence_multiplier",
                "raw_tilt",
                "confidence_adjusted_tilt",
                "breadth_observed_ticker_days",
                "breadth_possible_ticker_days",
                "direction_window_start",
                "direction_window_end",
                "breadth_window_start",
                "breadth_window_end",
            }
        ),
        expected_bytes=101_853,
        purpose="Evidence Lens confidence and raw versus adjusted tilt values",
    ),
    "sentiment_weighting_disagreements": ArtifactSpec(
        key="sentiment_weighting_disagreements",
        relative_path=Path("results/tables/sentiment_weighting_disagreements.csv"),
        required_columns=frozenset(
            {
                "date",
                "sector",
                "equal_ticker_sentiment",
                "headline_weighted_sentiment",
                "absolute_difference",
                "sign_reversal",
                "responsible_ticker",
                "sector_headline_count",
                "sector_active_ticker_count",
            }
        ),
        expected_bytes=12_323,
        purpose="Signal aggregation disagreement examples",
    ),
    "sentiment_weighting_comparison": ArtifactSpec(
        key="sentiment_weighting_comparison",
        relative_path=Path("results/tables/sentiment_weighting_comparison.csv"),
        required_columns=frozenset(
            {
                "date",
                "sector",
                "sector_sentiment",
                "headline_weighted_sentiment",
                "absolute_difference",
                "sign_reversal",
            }
        ),
        expected_bytes=1_089_112,
        purpose="Equal-ticker versus headline-weighted direction-change rate",
    ),
    "confidence_lens_attenuation_cases": ArtifactSpec(
        key="confidence_lens_attenuation_cases",
        relative_path=Path("results/tables/confidence_lens_attenuation_cases.csv"),
        required_columns=frozenset(
            {
                "base_method",
                "date",
                "sector",
                "standard_change",
                "confidence_change",
                "z_star",
                "b63",
                "a21",
                "confidence",
                "raw_tilt",
                "confidence_adjusted_tilt",
                "attenuation_ratio",
                "case_type",
            }
        ),
        expected_bytes=1_528,
        purpose="Curated Confidence Lens attenuation examples",
    ),
    "ticker_day_sentiment": ArtifactSpec(
        key="ticker_day_sentiment",
        relative_path=Path("results/data/ticker_day_sentiment.csv"),
        required_columns=frozenset(
            {
                "date",
                "ticker",
                "sector",
                "ticker_sentiment",
                "headline_count",
            }
        ),
        expected_bytes=3_017_800,
        purpose="Lazy constituent marks for curated Evidence cases",
    ),
    "confidence_placebo_comparison": ArtifactSpec(
        key="confidence_placebo_comparison",
        relative_path=Path("results/tables/confidence_placebo_comparison.csv"),
        required_columns=frozenset(
            {
                "base_method",
                "overlay",
                "annualised_return",
                "sharpe_ratio",
                "total_turnover",
                "observation_count",
                "sample_start",
                "sample_end",
            }
        ),
        expected_bytes=5_056,
        purpose="Challenge performance comparison for Base, Standard, placebo, and Confidence",
    ),
    "confidence_placebo_turnover_decomposition": ArtifactSpec(
        key="confidence_placebo_turnover_decomposition",
        relative_path=Path("results/tables/confidence_placebo_turnover_decomposition.csv"),
        required_columns=frozenset(
            {
                "base_method",
                "base_total_turnover",
                "standard_total_turnover",
                "placebo_total_turnover",
                "confidence_total_turnover",
                "standard_to_confidence_turnover_reduction",
                "constant_shrinkage_explained_percent",
            }
        ),
        expected_bytes=828,
        purpose="Challenge turnover and disturbance decomposition",
    ),
    "confidence_placebo_selectivity": ArtifactSpec(
        key="confidence_placebo_selectivity",
        relative_path=Path("results/tables/confidence_placebo_selectivity.csv"),
        required_columns=frozenset(
            {
                "live_rebalance_date",
                "signal_cutoff_date",
                "sector",
                "z_star",
                "standard_tilt",
                "placebo_tilt",
                "confidence_tilt",
                "confidence",
                "c_match",
                "selective_deviation",
                "confidence_group",
            }
        ),
        expected_bytes=107_455,
        purpose="Challenge aggregate signal match and selectivity distribution",
    ),
    "confidence_placebo_quadrants": ArtifactSpec(
        key="confidence_placebo_quadrants",
        relative_path=Path("results/tables/confidence_placebo_quadrants.csv"),
        required_columns=frozenset(
            {
                "quadrant",
                "observation_count",
                "average_confidence",
                "average_abs_placebo_tilt",
                "average_abs_confidence_tilt",
                "average_selective_deviation",
            }
        ),
        expected_bytes=953,
        purpose="Challenge evidence-state summary by breadth and agreement",
    ),
    "confidence_placebo_cases": ArtifactSpec(
        key="confidence_placebo_cases",
        relative_path=Path("results/tables/confidence_placebo_cases.csv"),
        required_columns=frozenset(
            {
                "case_type",
                "base_method",
                "date",
                "sector",
                "z_star",
                "confidence",
                "c_match",
                "placebo_multiplier",
                "confidence_multiplier",
                "selective_deviation",
                "case_selection_rule",
            }
        ),
        expected_bytes=3_677,
        purpose="Challenge real case pair for dynamic attenuation and preservation",
    ),
    "confidence_placebo_sector_year": ArtifactSpec(
        key="confidence_placebo_sector_year",
        relative_path=Path("results/tables/confidence_placebo_sector_year.csv"),
        required_columns=frozenset(
            {
                "scope",
                "bucket",
                "observation_count",
                "average_confidence",
                "average_selective_deviation",
                "proportion_c_below_c_match",
            }
        ),
        expected_bytes=1_002,
        purpose="Optional Challenge sector and year selectivity detail",
    ),
    "fusion_placebo_returns": ArtifactSpec(
        key="fusion_placebo_returns",
        relative_path=Path("results/data/fusion_placebo_returns.csv"),
        required_columns=frozenset(
            {
                "date",
                "gross_return",
                "turnover",
                "transaction_cost",
                "net_return",
                "base_method",
                "overlay",
                "tilt_strength",
                "growth_net",
                "drawdown_net",
            }
        ),
        expected_bytes=847_232,
        purpose="Optional Challenge return-path detail",
    ),
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def startup_registry() -> tuple[ArtifactSpec, ...]:
    return STARTUP_ARTIFACTS


def lazy_registry() -> dict[str, ArtifactSpec]:
    return LAZY_ARTIFACTS.copy()


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


def load_lazy_artifact(key: str, root: Path | None = None) -> pd.DataFrame:
    root = project_root() if root is None else Path(root)
    try:
        spec = LAZY_ARTIFACTS[key]
    except KeyError as exc:
        raise ArtifactValidationError(f"Unknown lazy artifact key: {key}") from exc
    path = resolve_artifact_path(root, spec)
    validate_artifact_file(path, spec)
    return read_artifact(path, spec)


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


@st.cache_data(show_spinner=False)
def load_lazy_artifact_cached(key: str, root: str | None = None) -> pd.DataFrame:
    return load_lazy_artifact(key, Path(root) if root else project_root())
