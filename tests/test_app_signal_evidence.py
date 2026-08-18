import json
from pathlib import Path

import altair as alt
import pandas as pd
import pytest

from app import charts
from app import data
from app import evidence
from app import signal


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_artifact(relative: str) -> pd.DataFrame:
    return pd.read_csv(project_root() / relative)


def test_lazy_registry_keeps_headline_scores_forbidden_and_startup_unchanged():
    startup_paths = {spec.relative_path for spec in data.startup_registry()}
    lazy_paths = {spec.relative_path for spec in data.lazy_registry().values()}

    assert data.expected_startup_size() == data.EXPECTED_STARTUP_BYTES
    assert Path("results/data/headline_sentiment_scores.csv") not in startup_paths
    assert Path("results/data/headline_sentiment_scores.csv") not in lazy_paths
    assert Path("results/data/sector_sentiment_index.csv") in lazy_paths
    assert Path("results/data/sector_sentiment_confidence.csv") in lazy_paths


def test_signal_sector_universe_validation_and_filtering():
    index = read_artifact("results/data/sector_sentiment_index.csv")

    sectors = signal.sector_universe(index)
    tech = signal.signal_series(index, "Tech", "2020")
    recent = signal.signal_series(index, "Tech")

    assert len(sectors) == 10
    assert signal.validate_sector(index, "Missing") == signal.DEFAULT_SECTOR
    assert set(tech["sector"]) == {"Tech"}
    assert tech["date"].dt.year.unique().tolist() == [2020]
    assert recent["date"].dt.year.min() >= 2022
    assert signal.DEFAULT_PERIOD in signal.PERIOD_OPTIONS
    assert "All" in signal.PERIOD_OPTIONS


def test_selected_signal_date_validation_and_no_news_stays_missing():
    index = read_artifact("results/data/sector_sentiment_index.csv")
    series = signal.signal_series(index, "Materials", "All")
    missing = series[series["missing_sector_day"]].iloc[0]

    selected = signal.validate_signal_date(series, "1900-01-01")
    default_without_request = signal.validate_signal_date(series, None)
    row = signal.selected_signal_row(series, str(missing["date"].date()))

    assert selected in signal.available_signal_dates(series)
    assert default_without_request == signal.latest_observed_signal_date(series)
    assert not bool(
        signal.selected_signal_row(series, default_without_request)["missing_sector_day"]
    )
    assert bool(row["missing_sector_day"]) is True
    assert pd.isna(row["sector_sentiment"])
    assert signal.sentiment_direction_label(row["sector_sentiment"]) == "No observed news"
    assert "No observed sector news" in signal.evidence_availability_label(row)
    assert "Materials ·" in signal.status_banner_html("Materials", str(missing["date"].date()), row)
    assert "No observed sector news." in signal.status_banner_html(
        "Materials", str(missing["date"].date()), row
    )


def test_deliberate_no_news_date_is_preserved_when_valid():
    index = read_artifact("results/data/sector_sentiment_index.csv")
    series = signal.signal_series(index, "Materials", "All")
    missing_date = str(series[series["missing_sector_day"]].iloc[-1]["date"].date())

    assert signal.validate_signal_date(series, missing_date) == missing_date
    assert signal.validate_signal_date(series, missing_date, preserve_requested=False) != missing_date


def test_weighting_summary_uses_saved_comparison_artifact():
    comparison = read_artifact("results/tables/sentiment_weighting_comparison.csv")

    summary = signal.weighting_summary(comparison)

    assert summary.total_rows == 10070
    assert summary.finite_paired_days == 9832
    assert summary.missing_or_noncomparable_days == 238
    assert summary.both_nonzero_days == 9391
    assert summary.sign_reversal_days == 561
    assert summary.one_zero_one_nonzero_days == 2
    assert summary.strict_rate_finite_paired == pytest.approx(0.057058584214808784)
    assert summary.strict_rate_both_nonzero == pytest.approx(0.05973804706634011)


def test_evidence_sector_date_and_display_helpers():
    confidence = read_artifact("results/data/sector_sentiment_confidence.csv")
    row = evidence.confidence_row(confidence, "RealEstate", "2021-11-01")

    assert len(evidence.confidence_sectors(confidence)) == 10
    assert evidence.validate_evidence_sector(confidence, "Missing") == signal.DEFAULT_SECTOR
    assert evidence.prior_or_first_evidence_date(confidence, "RealEstate", "2021-10-30") == "2021-10-01"
    assert evidence.prior_or_first_evidence_date(confidence, "RealEstate", "2020-07-09") == "2021-01-04"
    assert evidence.evidence_date_status(confidence, "RealEstate", "2021-10-30") == "between_rebalances"
    assert evidence.evidence_date_status(confidence, "RealEstate", "2020-07-09") == "before_oos"
    assert evidence.breadth_label(row) == "37.8% trailing evidence coverage"
    assert (
        evidence.breadth_detail(row)
        == "119 of 315 possible company-days had news over the trailing 63 trading days"
    )
    assert evidence.agreement_label(float(row["a21"])) == "Signals were aligned"
    assert evidence.confidence_label(float(row["confidence"])) == "Weak evidence support"
    assert evidence.direction_label(0.0) == "Near-neutral trading signal"


def test_evidence_date_transition_messages_are_explicit():
    before = evidence.EvidenceContext(
        sector="Industrials",
        live_rebalance_date="2021-01-04",
        requested_signal_date="2020-07-09",
        date_status="before_oos",
    )
    between = evidence.EvidenceContext(
        sector="RealEstate",
        live_rebalance_date="2021-10-01",
        requested_signal_date="2021-10-30",
        date_status="between_rebalances",
    )

    assert "before the saved OOS portfolio Confidence Lens period" in evidence.date_transition_message(before)
    assert "showing prior saved rebalance 2021-10-01" in evidence.date_transition_message(between)


def test_allocation_effect_frame_prefers_saved_attenuation_case_when_available():
    confidence = read_artifact("results/data/sector_sentiment_confidence.csv")
    attenuation = read_artifact("results/tables/confidence_lens_attenuation_cases.csv")
    row = evidence.confidence_row(confidence, "RealEstate", "2021-11-01")
    case = evidence.get_attenuation_case(attenuation)

    frame = evidence.allocation_effect_frame(row, case)

    assert frame["source"].tolist() == ["standard_change", "confidence_change"]
    assert frame["label"].tolist() == [
        "Raw sentiment sector allocation change",
        "Evidence-adjusted sector allocation change",
    ]
    assert frame["effect"].tolist() == pytest.approx(
        [0.0225259863957884, 0.0081958889867612]
    )


def test_allocation_effect_frame_labels_technical_tilts_when_no_sector_change_case():
    confidence = read_artifact("results/data/sector_sentiment_confidence.csv")
    row = evidence.confidence_row(confidence, "Tech", "2023-12-01")

    frame = evidence.allocation_effect_frame(row, None)

    assert frame["source"].tolist() == ["raw_tilt", "confidence_adjusted_tilt"]
    assert frame["label"].tolist() == [
        "Raw pre-normalisation tilt",
        "Evidence-adjusted pre-normalisation tilt",
    ]


def test_real_neutrality_cancellation_case_values_match_saved_artifacts():
    disagreement = read_artifact("results/tables/sentiment_disagreement_examples.csv")
    case = evidence.get_neutrality_case(disagreement)
    consensus = evidence.get_consensus_case(disagreement)

    assert case["date"] == "2020-07-09"
    assert case["sector"] == "Industrials"
    assert float(case["sector_sentiment"]) == pytest.approx(0.0188888888888889)
    assert float(case["cross_ticker_sentiment_std"]) == pytest.approx(0.7277056687771303)
    assert case["lowest_ticker"] == "MMM"
    assert float(case["lowest_ticker_sentiment"]) == pytest.approx(-0.6808)
    assert case["highest_ticker"] == "CAT"
    assert float(case["highest_ticker_sentiment"]) == pytest.approx(0.7717)

    assert consensus["date"] == "2021-02-25"
    assert consensus["sector"] == "Materials"
    assert float(consensus["sector_sentiment"]) == pytest.approx(0.0)
    assert float(consensus["cross_ticker_sentiment_std"]) == pytest.approx(0.0)


def test_real_volume_breadth_case_values_match_saved_artifacts():
    candidates = read_artifact("results/tables/sentiment_candidate_cases.csv")
    tickers = read_artifact("results/data/ticker_day_sentiment.csv")
    case = evidence.get_volume_case(candidates)
    rows = evidence.ticker_case_rows(tickers, "Tech", "2020-07-24")

    assert case["date"] == "2020-07-24"
    assert case["sector"] == "Tech"
    assert int(case["headline_count"]) == 44
    assert float(case["active_ticker_share"]) == pytest.approx(0.6)
    assert case["dominant_ticker"] == "INTC"
    assert float(case["dominant_ticker_headline_share"]) == pytest.approx(0.636364)
    assert float(case["ticker_headline_share_hhi"]) == pytest.approx(0.521694)
    assert rows.set_index("ticker").loc["INTC", "headline_count"] == 28


def test_real_attenuation_case_values_match_saved_artifacts():
    confidence = read_artifact("results/data/sector_sentiment_confidence.csv")
    attenuation = read_artifact("results/tables/confidence_lens_attenuation_cases.csv")
    row = evidence.confidence_row(confidence, "RealEstate", "2021-11-01")
    case = evidence.get_attenuation_case(attenuation)

    assert row["signal_cutoff_date"] == "2021-10-29"
    assert float(row["z_star"]) == pytest.approx(1.669803459455642)
    assert float(row["b63"]) == pytest.approx(0.3777777777777777)
    assert float(row["a21"]) == pytest.approx(0.901107710891938)
    assert float(row["confidence"]) == pytest.approx(0.3404184685591766)
    assert float(row["raw_tilt"]) == pytest.approx(0.1669803459455642)
    assert float(row["confidence_adjusted_tilt"]) == pytest.approx(0.0568431936462704)

    assert case["base_method"] == "Minimum Variance"
    assert float(case["standard_change"]) == pytest.approx(0.0225259863957884)
    assert float(case["confidence_change"]) == pytest.approx(0.0081958889867612)


def test_new_chart_specs_json_serialise_and_validate():
    specs = [
        charts.sentiment_timeline_spec(),
        charts.allocation_effect_spec(),
        charts.constituent_axis_spec(),
    ]
    for spec in specs:
        json.dumps(spec)
        alt.Chart.from_dict(spec, validate=True)

    timeline = charts.sentiment_timeline_spec()
    assert timeline["vconcat"][0]["layer"][1]["encoding"]["y"]["field"] == "sector_sentiment"
    availability = timeline["vconcat"][1]["layer"][0]
    assert timeline["vconcat"][1]["height"] == 44
    assert availability["mark"]["type"] == "point"
    assert availability["mark"]["shape"] == "square"
    assert availability["mark"]["size"] == 34
    assert availability["encoding"]["y"]["value"] == 21
    assert availability["encoding"]["opacity"]["field"] == "active_ticker_share"
    assert availability["encoding"]["opacity"]["scale"]["range"] == [0.28, 0.95]
    assert availability["encoding"]["tooltip"][1]["field"] == "active_ticker_share"
    allocation = charts.allocation_effect_spec()
    assert allocation["layer"][1]["encoding"]["x"]["field"] == "effect"
    assert "Raw sentiment sector allocation change" in allocation["layer"][1]["encoding"]["y"]["sort"]
    constituent = charts.constituent_axis_spec()
    assert constituent["layer"][2]["encoding"]["x"]["field"] == "ticker_sentiment"
