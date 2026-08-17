"""Station 3 sentiment index and diagnostic evidence layer.

This module is diagnostic-only. It scores aligned headlines, builds the approved
equal-ticker sector sentiment index, and writes transparent evidence-structure
diagnostics. It does not alter portfolio weights or implement sentiment fusion.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np
import pandas as pd

from src import features


NEAR_ZERO_THRESHOLD = 0.05
EXTREME_SENTIMENT_THRESHOLD = 0.30
MATERIAL_INFLUENCE_THRESHOLD = 0.10


@dataclass(frozen=True)
class SentimentDiagnostics:
    """All Phase 2A sentiment diagnostic artifacts."""

    headline_scores: pd.DataFrame
    ticker_day_sentiment: pd.DataFrame
    sector_sentiment_index: pd.DataFrame
    sector_month_diagnostics: pd.DataFrame
    candidate_cases: pd.DataFrame
    weighting_comparison: pd.DataFrame
    weighting_disagreements: pd.DataFrame
    constituent_influence: pd.DataFrame
    constituent_influence_events: pd.DataFrame
    disagreement_examples: pd.DataFrame
    carryover_diagnostic: pd.DataFrame
    vader_failure_taxonomy: pd.DataFrame
    return_validation: pd.DataFrame
    temporal_stability: pd.DataFrame
    innovation_reconnaissance: pd.DataFrame
    insight_register: pd.DataFrame


def _sentiment_analyser():
    """Create a VADER analyser, downloading the lexicon only for build scripts."""

    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "nltk is required for build-time sentiment scoring; install requirements-dev.txt"
        ) from exc

    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        import nltk

        nltk.download("vader_lexicon", quiet=True)
        return SentimentIntensityAnalyzer()


def _sector_universe(equity_prices: pd.DataFrame) -> pd.DataFrame:
    universe = (
        equity_prices.loc[:, ["ticker", "sector"]]
        .drop_duplicates()
        .sort_values(["sector", "ticker"])
        .reset_index(drop=True)
    )
    conflicts = universe.groupby("ticker")["sector"].nunique()
    conflicts = conflicts[conflicts > 1]
    if not conflicts.empty:
        raise ValueError(f"ticker has conflicting sector labels: {conflicts.index[:5].tolist()}")
    return universe


def score_headlines(
    headlines: pd.DataFrame,
    trading_calendar,
) -> pd.DataFrame:
    """Align and score cleaned headlines with VADER at headline level."""

    aligned = features.align_headlines_to_trading_calendar(headlines, trading_calendar).aligned
    if aligned.empty:
        return pd.DataFrame(
            columns=[
                "source_date",
                "trading_date",
                "days_shifted",
                "mapping_status",
                "ticker",
                "sector",
                "title",
                "compound",
                "positive",
                "neutral",
                "negative",
            ]
        )

    analyser = _sentiment_analyser()
    scored = aligned.copy()
    scores = scored["text_raw"].map(analyser.polarity_scores)
    score_frame = pd.DataFrame(scores.tolist(), index=scored.index)
    scored["compound"] = score_frame["compound"].astype(float)
    scored["positive"] = score_frame["pos"].astype(float)
    scored["neutral"] = score_frame["neu"].astype(float)
    scored["negative"] = score_frame["neg"].astype(float)
    scored["is_carryover"] = scored["days_shifted"].gt(0)
    scored["is_near_zero"] = scored["compound"].abs().le(NEAR_ZERO_THRESHOLD)
    return scored.sort_values(["trading_date", "sector", "ticker", "source_date", "title"]).reset_index(drop=True)


def ticker_day_sentiment(headline_scores: pd.DataFrame) -> pd.DataFrame:
    """Aggregate headline scores to ticker-day scores without filling no-news days."""

    if headline_scores.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "sector",
                "ticker_sentiment",
                "headline_count",
                "same_day_headline_count",
                "carryover_headline_count",
                "carryover_share",
                "headline_sentiment_std",
                "headline_sentiment_iqr",
            ]
        )

    grouped = (
        headline_scores.groupby(["trading_date", "ticker", "sector"], sort=True)
        .agg(
            ticker_sentiment=("compound", "mean"),
            headline_count=("compound", "size"),
            same_day_headline_count=("is_carryover", lambda s: int((~s).sum())),
            carryover_headline_count=("is_carryover", "sum"),
            headline_sentiment_std=("compound", lambda s: float(s.std(ddof=1)) if len(s) > 1 else 0.0),
            headline_sentiment_iqr=("compound", lambda s: float(s.quantile(0.75) - s.quantile(0.25))),
        )
        .reset_index()
        .rename(columns={"trading_date": "date"})
    )
    grouped["carryover_headline_count"] = grouped["carryover_headline_count"].astype(int)
    grouped["carryover_share"] = grouped["carryover_headline_count"] / grouped["headline_count"]
    grouped["absolute_ticker_sentiment"] = grouped["ticker_sentiment"].abs()
    return grouped


def _headline_hhi(ticker_counts: pd.Series) -> float:
    total = float(ticker_counts.sum())
    if total <= 0:
        return np.nan
    shares = ticker_counts.astype(float) / total
    return float((shares**2).sum())


def sector_sentiment_index(
    ticker_scores: pd.DataFrame,
    sector_universe: pd.DataFrame,
    trading_calendar,
) -> pd.DataFrame:
    """Build the approved equal-ticker sector index and evidence diagnostics."""

    calendar = pd.DatetimeIndex(pd.to_datetime(pd.Series(trading_calendar))).normalize().drop_duplicates().sort_values()
    sectors = sector_universe["sector"].drop_duplicates().sort_values()
    complete = (
        pd.MultiIndex.from_product([calendar, sectors], names=["date", "sector"])
        .to_frame(index=False)
        .sort_values(["date", "sector"])
    )
    possible = sector_universe.groupby("sector", sort=True)["ticker"].nunique().rename("possible_ticker_count")

    if ticker_scores.empty:
        output = complete.merge(possible, on="sector", how="left")
        for column in [
            "sector_sentiment",
            "active_ticker_count",
            "headline_count",
            "active_ticker_share",
            "ticker_headline_share_hhi",
            "cross_ticker_sentiment_std",
            "cross_ticker_sentiment_iqr",
            "absolute_sector_sentiment",
            "carryover_share",
            "same_day_headline_count",
            "carryover_headline_count",
            "dominant_ticker",
            "dominant_ticker_headline_share",
        ]:
            output[column] = np.nan
        return output

    sector_day = (
        ticker_scores.groupby(["date", "sector"], sort=True)
        .agg(
            sector_sentiment=("ticker_sentiment", "mean"),
            active_ticker_count=("ticker", "nunique"),
            headline_count=("headline_count", "sum"),
            cross_ticker_sentiment_std=(
                "ticker_sentiment",
                lambda s: float(s.std(ddof=1)) if len(s) > 1 else 0.0,
            ),
            cross_ticker_sentiment_iqr=(
                "ticker_sentiment",
                lambda s: float(s.quantile(0.75) - s.quantile(0.25)),
            ),
            same_day_headline_count=("same_day_headline_count", "sum"),
            carryover_headline_count=("carryover_headline_count", "sum"),
        )
        .reset_index()
    )

    ticker_counts = ticker_scores.pivot_table(
        index=["date", "sector"],
        columns="ticker",
        values="headline_count",
        aggfunc="sum",
        fill_value=0,
    )
    hhi = ticker_counts.apply(_headline_hhi, axis=1).rename("ticker_headline_share_hhi").reset_index()
    dominant = ticker_counts.idxmax(axis=1).rename("dominant_ticker").reset_index()
    dominant_share = (
        ticker_counts.max(axis=1).div(ticker_counts.sum(axis=1)).rename("dominant_ticker_headline_share").reset_index()
    )

    sector_day = sector_day.merge(hhi, on=["date", "sector"], how="left")
    sector_day = sector_day.merge(dominant, on=["date", "sector"], how="left")
    sector_day = sector_day.merge(dominant_share, on=["date", "sector"], how="left")
    output = complete.merge(sector_day, on=["date", "sector"], how="left").merge(possible, on="sector", how="left")

    count_columns = [
        "active_ticker_count",
        "headline_count",
        "same_day_headline_count",
        "carryover_headline_count",
    ]
    output[count_columns] = output[count_columns].fillna(0).astype(int)
    output["active_ticker_share"] = output["active_ticker_count"] / output["possible_ticker_count"]
    output["absolute_sector_sentiment"] = output["sector_sentiment"].abs()
    output["carryover_share"] = np.where(
        output["headline_count"].gt(0),
        output["carryover_headline_count"] / output["headline_count"],
        np.nan,
    )
    output["missing_sector_day"] = output["headline_count"].eq(0)
    return output.sort_values(["date", "sector"]).reset_index(drop=True)


def sector_month_diagnostics(sector_index: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sector-date diagnostics to sector-month observations."""

    working = sector_index.copy()
    working["month"] = pd.to_datetime(working["date"]).dt.to_period("M").astype(str)
    return (
        working.groupby(["month", "sector"], sort=True)
        .agg(
            sector_sentiment_mean=("sector_sentiment", "mean"),
            absolute_sentiment_mean=("absolute_sector_sentiment", "mean"),
            headline_count=("headline_count", "sum"),
            active_ticker_count_mean=("active_ticker_count", "mean"),
            active_ticker_share_mean=("active_ticker_share", "mean"),
            ticker_headline_share_hhi_mean=("ticker_headline_share_hhi", "mean"),
            sentiment_disagreement_std_mean=("cross_ticker_sentiment_std", "mean"),
            sentiment_disagreement_iqr_mean=("cross_ticker_sentiment_iqr", "mean"),
            missing_sector_days=("missing_sector_day", "sum"),
        )
        .reset_index()
    )


def weighting_comparison(
    headline_scores: pd.DataFrame,
    ticker_scores: pd.DataFrame,
    sector_index: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare approved equal-ticker and diagnostic headline-weighted indices."""

    naive = (
        headline_scores.groupby(["trading_date", "sector"], sort=True)
        .agg(headline_weighted_sentiment=("compound", "mean"))
        .reset_index()
        .rename(columns={"trading_date": "date"})
    )
    comparison = sector_index.loc[
        :, ["date", "sector", "sector_sentiment", "headline_count", "active_ticker_count", "dominant_ticker"]
    ].merge(naive, on=["date", "sector"], how="left")
    comparison["difference_headline_minus_equal_ticker"] = (
        comparison["headline_weighted_sentiment"] - comparison["sector_sentiment"]
    )
    comparison["absolute_difference"] = comparison["difference_headline_minus_equal_ticker"].abs()
    comparison["sign_reversal"] = (
        comparison["headline_weighted_sentiment"].notna()
        & comparison["sector_sentiment"].notna()
        & (np.sign(comparison["headline_weighted_sentiment"]) != np.sign(comparison["sector_sentiment"]))
        & comparison["headline_weighted_sentiment"].ne(0)
        & comparison["sector_sentiment"].ne(0)
    )

    correlations = []
    for sector, group in comparison.groupby("sector", sort=True):
        valid = group[["sector_sentiment", "headline_weighted_sentiment"]].dropna()
        correlations.append(
            {
                "date": pd.NaT,
                "sector": sector,
                "sector_sentiment": np.nan,
                "headline_weighted_sentiment": np.nan,
                "difference_headline_minus_equal_ticker": np.nan,
                "absolute_difference": np.nan,
                "sign_reversal": False,
                "headline_count": int(group["headline_count"].sum()),
                "active_ticker_count": np.nan,
                "dominant_ticker": "CORRELATION_SUMMARY",
                "pearson_correlation": valid["sector_sentiment"].corr(
                    valid["headline_weighted_sentiment"],
                    method="pearson",
                )
                if len(valid) >= 3
                else np.nan,
                "spearman_correlation": valid["sector_sentiment"].corr(
                    valid["headline_weighted_sentiment"],
                    method="spearman",
                )
                if len(valid) >= 3
                else np.nan,
                "observation_count": int(len(valid)),
            }
        )
    comparison["pearson_correlation"] = np.nan
    comparison["spearman_correlation"] = np.nan
    comparison["observation_count"] = np.nan
    comparison = pd.concat([comparison, pd.DataFrame(correlations)], ignore_index=True)

    ticker_context = ticker_scores.loc[:, ["date", "sector", "ticker", "headline_count", "ticker_sentiment"]]
    top_disagreements = (
        comparison.loc[comparison["absolute_difference"].notna()]
        .sort_values("absolute_difference", ascending=False)
        .head(100)
    )
    rows = []
    for _, row in top_disagreements.iterrows():
        contributors = ticker_context.loc[
            ticker_context["date"].eq(row["date"]) & ticker_context["sector"].eq(row["sector"])
        ].copy()
        if contributors.empty:
            continue
        contributors["headline_share"] = contributors["headline_count"] / contributors["headline_count"].sum()
        contributors["weighted_contribution"] = contributors["headline_share"] * contributors["ticker_sentiment"]
        top = contributors.sort_values("headline_share", ascending=False).iloc[0]
        rows.append(
            {
                "date": row["date"],
                "sector": row["sector"],
                "equal_ticker_sentiment": row["sector_sentiment"],
                "headline_weighted_sentiment": row["headline_weighted_sentiment"],
                "absolute_difference": row["absolute_difference"],
                "sign_reversal": row["sign_reversal"],
                "responsible_ticker": top["ticker"],
                "responsible_ticker_headline_share": top["headline_share"],
                "responsible_ticker_sentiment": top["ticker_sentiment"],
                "sector_headline_count": row["headline_count"],
                "sector_active_ticker_count": row["active_ticker_count"],
            }
        )
    return comparison.sort_values(["sector", "date"], na_position="last").reset_index(drop=True), pd.DataFrame(rows)


def constituent_influence(ticker_scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leave-one-ticker-out sensitivity diagnostics for each sector."""

    rows = []
    for (date, sector), group in ticker_scores.groupby(["date", "sector"], sort=True):
        full = float(group["ticker_sentiment"].mean())
        for _, ticker_row in group.iterrows():
            remaining = group.loc[group["ticker"].ne(ticker_row["ticker"]), "ticker_sentiment"]
            if remaining.empty:
                loo = np.nan
                change = np.nan
            else:
                loo = float(remaining.mean())
                change = full - loo
            rows.append(
                {
                    "date": date,
                    "sector": sector,
                    "ticker": ticker_row["ticker"],
                    "full_sector_sentiment": full,
                    "leave_one_out_sentiment": loo,
                    "influence": change,
                    "absolute_influence": abs(change) if pd.notna(change) else np.nan,
                    "ticker_sentiment": ticker_row["ticker_sentiment"],
                    "ticker_headline_count": ticker_row["headline_count"],
                    "active_ticker_count": len(group),
                }
            )
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, detail

    summary = (
        detail.groupby(["sector", "ticker"], sort=True)
        .agg(
            observation_count=("absolute_influence", "count"),
            average_influence=("influence", "mean"),
            average_absolute_influence=("absolute_influence", "mean"),
            maximum_absolute_influence=("absolute_influence", "max"),
        )
        .reset_index()
    )
    sector_rank = summary.groupby("sector")["maximum_absolute_influence"].rank(method="first", ascending=False)
    summary["most_influential_ticker_in_sector"] = sector_rank.eq(1)

    events = detail.loc[detail["absolute_influence"].ge(MATERIAL_INFLUENCE_THRESHOLD)].copy()
    if events.empty:
        events = detail.sort_values("absolute_influence", ascending=False).head(100).copy()
    else:
        events = events.sort_values("absolute_influence", ascending=False).head(100)
    return summary, events.reset_index(drop=True)


def disagreement_examples(sector_index: pd.DataFrame, ticker_scores: pd.DataFrame) -> pd.DataFrame:
    """Find cases where similar means hide neutral versus cancelling evidence."""

    near_zero = sector_index.loc[
        sector_index["sector_sentiment"].abs().le(NEAR_ZERO_THRESHOLD)
        & sector_index["active_ticker_count"].ge(2)
    ].copy()
    rows = []
    neutral_cases = near_zero.sort_values("cross_ticker_sentiment_std", ascending=True).head(15)
    cancelling_cases = near_zero.sort_values("cross_ticker_sentiment_std", ascending=False).head(15)
    for label, cases in [("near_zero_low_dispersion", neutral_cases), ("near_zero_high_dispersion", cancelling_cases)]:
        for _, row in cases.iterrows():
            tickers = ticker_scores.loc[
                ticker_scores["date"].eq(row["date"]) & ticker_scores["sector"].eq(row["sector"])
            ].sort_values("ticker_sentiment")
            rows.append(
                {
                    "case_type": label,
                    "date": row["date"],
                    "sector": row["sector"],
                    "sector_sentiment": row["sector_sentiment"],
                    "cross_ticker_sentiment_std": row["cross_ticker_sentiment_std"],
                    "cross_ticker_sentiment_iqr": row["cross_ticker_sentiment_iqr"],
                    "active_ticker_count": row["active_ticker_count"],
                    "headline_count": row["headline_count"],
                    "lowest_ticker": tickers.iloc[0]["ticker"] if not tickers.empty else "",
                    "lowest_ticker_sentiment": tickers.iloc[0]["ticker_sentiment"] if not tickers.empty else np.nan,
                    "highest_ticker": tickers.iloc[-1]["ticker"] if not tickers.empty else "",
                    "highest_ticker_sentiment": tickers.iloc[-1]["ticker_sentiment"] if not tickers.empty else np.nan,
                }
            )
    return pd.DataFrame(rows)


def carryover_diagnostic(headline_scores: pd.DataFrame) -> pd.DataFrame:
    """Compare same-day and carried-over headline sentiment properties."""

    working = headline_scores.copy()
    working["timing_bucket"] = np.where(working["is_carryover"], "carried_over", "same_day")
    rows = []
    for key, group in working.groupby("timing_bucket", sort=True):
        rows.append(
            {
                "scope": "overall",
                "sector": "ALL",
                "timing_bucket": key,
                "headline_count": len(group),
                "average_compound": group["compound"].mean(),
                "average_absolute_compound": group["compound"].abs().mean(),
                "near_zero_share": group["is_near_zero"].mean(),
            }
        )
    for (sector, bucket), group in working.groupby(["sector", "timing_bucket"], sort=True):
        rows.append(
            {
                "scope": "sector",
                "sector": sector,
                "timing_bucket": bucket,
                "headline_count": len(group),
                "average_compound": group["compound"].mean(),
                "average_absolute_compound": group["compound"].abs().mean(),
                "near_zero_share": group["is_near_zero"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(["scope", "sector", "timing_bucket"]).reset_index(drop=True)


_FAILURE_PATTERNS: tuple[tuple[str, str, str, str], ...] = (
    (
        "financial_words_domain_specific",
        r"\b(?:guidance|margin|miss|beat|beats|yield|downgrade|upgrade|overweight|underweight)\b",
        "Financial wording can carry domain-specific tone that generic lexical scoring may miss.",
        "The economic meaning depends on finance usage rather than general English tone.",
    ),
    (
        "earnings_beats_misses",
        r"\b(?:earnings|eps|revenue|profit|sales).{0,50}\b(?:beat|beats|miss|misses|tops|falls short|surprise)\b|\b(?:beat|beats|miss|misses|tops|falls short).{0,50}\b(?:earnings|eps|revenue|profit|sales)\b",
        "Earnings headlines often mix expectations, levels, and surprises.",
        "A lexical model may not know whether the key news is the reported number or the expectation benchmark.",
    ),
    (
        "upgrades_downgrades",
        r"\b(?:upgrade|upgraded|downgrade|downgraded|raises rating|cuts rating|price target)\b",
        "Analyst-action language has finance-specific polarity.",
        "Generic sentiment may underweight institutional phrases such as rating and target changes.",
    ),
    (
        "litigation_regulatory",
        r"\b(?:lawsuit|sues|sued|settlement|probe|investigation|regulator|sec|doj|antitrust|fine)\b",
        "Legal and regulatory headlines can be economically material even when written neutrally.",
        "The wording may describe process rather than emotional tone.",
    ),
    (
        "ma_language",
        r"\b(?:acquire|acquires|acquisition|merger|takeover|deal|buyout|bid)\b",
        "M&A words can be good or bad depending on acquirer, target, price, and financing.",
        "The title alone may not identify who benefits economically.",
    ),
    (
        "negation",
        r"\b(?:not|no|never|without|fails to|failed to|cannot|can't|won't)\b",
        "Negation can reverse meaning or reduce confidence.",
        "Lexical scoring is fragile when short headlines combine negation with sentiment words.",
    ),
    (
        "numerical_statements",
        r"\b\d+(?:\.\d+)?%|\$\d+|\bq[1-4]\b|\bfy\d{2,4}\b",
        "Numbers often carry the economic signal.",
        "VADER does not know whether a numeric surprise is large relative to expectations.",
    ),
    (
        "comparative_language",
        r"\b(?:more than|less than|above|below|higher|lower|rises|falls|jumps|drops|slumps|lags|outperforms|underperforms)\b",
        "Comparative wording depends on the benchmark and direction.",
        "General polarity can miss whether a comparison is economically favourable.",
    ),
    (
        "mixed_information",
        r"\b(?:but|despite|although|while|however)\b",
        "Mixed headlines can contain offsetting positive and negative information.",
        "One compound score can hide multiple economic signals in the same title.",
    ),
    (
        "punctuation_intensity",
        r"!|\?|[A-Z]{3,}",
        "Punctuation and uppercase can change VADER intensity.",
        "Intensity markers may reflect headline style as much as economic content.",
    ),
    (
        "context_dependent_title",
        r"\b(?:watch|what to know|why|ahead|preview|seen|set to|report says|sources say)\b",
        "Some titles signal that the economics are in missing article context.",
        "Headline-only scoring cannot read the article body or event details.",
    ),
)


def vader_failure_taxonomy(headline_scores: pd.DataFrame) -> pd.DataFrame:
    """Build a deterministic model-risk map from observed corpus patterns."""

    rows = []
    working = headline_scores.sort_values(["trading_date", "sector", "ticker", "title"]).copy()
    for category, pattern, interpretation, struggle in _FAILURE_PATTERNS:
        matches = working.loc[working["title"].str.contains(pattern, flags=re.IGNORECASE, regex=True, na=False)].copy()
        if matches.empty:
            continue
        matches["score_abs"] = matches["compound"].abs()
        example = matches.sort_values(["score_abs", "trading_date", "ticker", "title"]).iloc[0]
        rows.append(
            {
                "failure_category": category,
                "observed_match_count": int(len(matches)),
                "example_date": example["trading_date"],
                "ticker": example["ticker"],
                "sector": example["sector"],
                "example_headline": example["title"],
                "vader_compound": example["compound"],
                "intuitive_interpretation": interpretation,
                "why_lexical_model_may_struggle": struggle,
            }
        )
    return pd.DataFrame(rows).sort_values("failure_category").reset_index(drop=True)


def return_validation(sector_index: pd.DataFrame, equity_returns: pd.DataFrame) -> pd.DataFrame:
    """Pre-declared same-day and t+1 sector-return validation diagnostics."""

    sector_returns = (
        equity_returns.groupby(["date", "sector"], sort=True)["daily_return"]
        .mean()
        .reset_index()
        .rename(columns={"daily_return": "sector_return"})
    )
    joined = sector_index.loc[:, ["date", "sector", "sector_sentiment"]].merge(
        sector_returns, on=["date", "sector"], how="left"
    )
    joined = joined.sort_values(["sector", "date"])
    joined["sector_return_tplus1"] = joined.groupby("sector")["sector_return"].shift(-1)

    rows = []
    for sector, group in joined.groupby("sector", sort=True):
        same = group[["sector_sentiment", "sector_return"]].dropna()
        lagged = group[["sector_sentiment", "sector_return_tplus1"]].dropna()
        for horizon, frame, return_column in [
            ("same_day_descriptive", same, "sector_return"),
            ("sentiment_t_to_return_tplus1", lagged, "sector_return_tplus1"),
        ]:
            rows.append(
                {
                    "sector": sector,
                    "horizon": horizon,
                    "observation_count": int(len(frame)),
                    "pearson_correlation": frame["sector_sentiment"].corr(frame[return_column], method="pearson")
                    if len(frame) >= 3
                    else np.nan,
                    "spearman_correlation": frame["sector_sentiment"].corr(frame[return_column], method="spearman")
                    if len(frame) >= 3
                    else np.nan,
                    "interpretation_scope": "descriptive_not_trading_rule",
                }
            )
    return pd.DataFrame(rows)


def temporal_stability(sector_index: pd.DataFrame) -> pd.DataFrame:
    """Report yearly stability of sentiment and evidence structure by sector."""

    working = sector_index.copy()
    working["year"] = pd.to_datetime(working["date"]).dt.year
    return (
        working.groupby(["year", "sector"], sort=True)
        .agg(
            mean_sector_sentiment=("sector_sentiment", "mean"),
            sentiment_volatility=("sector_sentiment", "std"),
            average_active_ticker_share=("active_ticker_share", "mean"),
            headline_volume=("headline_count", "sum"),
            average_headline_concentration_hhi=("ticker_headline_share_hhi", "mean"),
            missing_sector_days=("missing_sector_day", "sum"),
            observed_sector_days=("missing_sector_day", lambda s: int((~s).sum())),
        )
        .reset_index()
    )


def _candidate_case_table(sector_index: pd.DataFrame) -> pd.DataFrame:
    observed = sector_index.loc[~sector_index["missing_sector_day"]].copy()
    rows = []
    if observed.empty:
        return pd.DataFrame()
    q_hi_vol = observed["headline_count"].quantile(0.90)
    q_lo_vol = observed["headline_count"].quantile(0.25)
    q_hi_breadth = observed["active_ticker_share"].quantile(0.75)
    q_lo_breadth = observed["active_ticker_share"].quantile(0.25)
    q_hi_disagreement = observed["cross_ticker_sentiment_std"].quantile(0.90)

    specs = [
        (
            "high_volume_low_breadth",
            observed["headline_count"].ge(q_hi_vol) & observed["active_ticker_share"].le(q_lo_breadth),
            "headline volume is high but active-ticker breadth is low",
        ),
        (
            "low_volume_broad_evidence",
            observed["headline_count"].le(q_lo_vol) & observed["active_ticker_share"].ge(q_hi_breadth),
            "headline volume is low but evidence is broad across constituents",
        ),
        (
            "extreme_sentiment_few_tickers",
            observed["absolute_sector_sentiment"].ge(EXTREME_SENTIMENT_THRESHOLD)
            & observed["active_ticker_share"].le(q_lo_breadth),
            "average sentiment is extreme but driven by few tickers",
        ),
        (
            "moderate_sentiment_high_disagreement",
            observed["sector_sentiment"].abs().le(0.10)
            & observed["cross_ticker_sentiment_std"].ge(q_hi_disagreement),
            "average sentiment is moderate despite strong disagreement",
        ),
    ]
    for case_type, mask, description in specs:
        cases = observed.loc[mask].sort_values(
            ["headline_count", "cross_ticker_sentiment_std"], ascending=False
        ).head(20)
        for _, row in cases.iterrows():
            rows.append(
                {
                    "case_type": case_type,
                    "description": description,
                    "date": row["date"],
                    "sector": row["sector"],
                    "sector_sentiment": row["sector_sentiment"],
                    "headline_count": row["headline_count"],
                    "active_ticker_share": row["active_ticker_share"],
                    "ticker_headline_share_hhi": row["ticker_headline_share_hhi"],
                    "cross_ticker_sentiment_std": row["cross_ticker_sentiment_std"],
                    "dominant_ticker": row["dominant_ticker"],
                    "dominant_ticker_headline_share": row["dominant_ticker_headline_share"],
                }
            )
    return pd.DataFrame(rows)


def innovation_reconnaissance(
    sector_index: pd.DataFrame,
    weighting: pd.DataFrame,
    influence_summary: pd.DataFrame,
    carryover: pd.DataFrame,
    disagreement: pd.DataFrame,
) -> pd.DataFrame:
    """Assess candidate innovation concepts from Phase 2A evidence only."""

    observed = sector_index.loc[~sector_index["missing_sector_day"]]
    high_low_cases = _candidate_case_table(sector_index)
    sign_reversal_count = int(weighting["sign_reversal"].fillna(False).sum())
    max_influence = float(influence_summary["maximum_absolute_influence"].max()) if not influence_summary.empty else np.nan
    same_carry = carryover.loc[carryover["scope"].eq("overall")]
    carryover_gap = np.nan
    if len(same_carry["timing_bucket"].unique()) == 2:
        pivot = same_carry.pivot_table(index="scope", columns="timing_bucket", values="average_absolute_compound")
        if {"carried_over", "same_day"}.issubset(pivot.columns):
            carryover_gap = float(pivot["carried_over"].iloc[0] - pivot["same_day"].iloc[0])

    evidence_breadth_cases = int(
        high_low_cases["case_type"].isin(["high_volume_low_breadth", "low_volume_broad_evidence"]).sum()
    ) if not high_low_cases.empty else 0
    disagreement_cases = int(disagreement["case_type"].eq("near_zero_high_dispersion").sum()) if not disagreement.empty else 0
    concentration_cases = int(
        observed["ticker_headline_share_hhi"].ge(observed["ticker_headline_share_hhi"].quantile(0.90)).sum()
    )

    specs = [
        (
            "Evidence-Aware Sentiment",
            evidence_breadth_cases,
            "Headline volume and active breadth produce distinct sector-day cases.",
            "Could separate broad sector news from concentrated firm-specific news.",
            "Any trading use must compute evidence through t-1 only.",
            "medium",
            "Adds transparent evidence context beyond an average score.",
            "Directly supports innovation and interpretation criteria.",
        ),
        (
            "Agreement-Aware Sentiment",
            disagreement_cases,
            "Near-zero sector means include high-dispersion cancellation cases.",
            "Could distinguish consensus neutrality from offsetting positive and negative signals.",
            "Ticker-level dispersion must be lagged before any trading use.",
            "medium",
            "Preserves information hidden by a single average score.",
            "Strong fit for structural insight and app explanation.",
        ),
        (
            "Concentration-Aware Sentiment",
            concentration_cases + int(pd.notna(max_influence) and max_influence >= MATERIAL_INFLUENCE_THRESHOLD),
            "Sector sentiment can be sensitive to dominant ticker headline shares and leave-one-out influence.",
            "Could flag when a sector signal is effectively a constituent-specific signal.",
            "Dominance and influence must be computed only from available historical or same-day diagnostic data.",
            "medium",
            "Tests aggregation-design fragility directly.",
            "Strong fit for technical defensibility and innovation.",
        ),
        (
            "Timing-Aware Sentiment",
            int(abs(carryover_gap) > 0.01) if pd.notna(carryover_gap) else 0,
            "Same-day and carried-over headline buckets can differ in composition or magnitude.",
            "Could help users understand calendar-alignment information piles.",
            "Do not infer causality; any trading use needs strict next-day availability.",
            "low",
            "Mostly improves transparency unless differences are large.",
            "Useful for methodology explanation; weaker as a standalone innovation.",
        ),
        (
            "Combined Evidence/Agreement/Concentration Layer",
            evidence_breadth_cases + disagreement_cases + concentration_cases + sign_reversal_count,
            "Multiple diagnostics show aggregation structure can matter.",
            "Could present average sentiment alongside breadth, agreement, and dominance checks.",
            "Combining dimensions into a score would require pre-declared rules and OOS validation.",
            "high",
            "Substantial incremental context over a conventional index.",
            "Best aligned if final implementation remains simple and auditable.",
        ),
    ]
    rows = []
    for concept, count, motivation, interpretation, lookahead, complexity, value, rubric in specs:
        rows.append(
            {
                "concept": concept,
                "empirical_motivation": motivation,
                "supporting_observation_count": count,
                "possible_economic_interpretation": interpretation,
                "look_ahead_risk": lookahead,
                "implementation_complexity": complexity,
                "incremental_value_over_conventional_index": value,
                "rubric_relevance": rubric,
                "evidence_currently_justifies_implementation": bool(count > 0),
            }
        )
    return pd.DataFrame(rows)


def insight_register(
    sector_index: pd.DataFrame,
    weighting: pd.DataFrame,
    influence_summary: pd.DataFrame,
    carryover: pd.DataFrame,
    return_validation_frame: pd.DataFrame,
    temporal: pd.DataFrame,
    taxonomy: pd.DataFrame,
    disagreement: pd.DataFrame,
    innovation: pd.DataFrame,
) -> pd.DataFrame:
    """Create the auditable register linking diagnostics to report claims."""

    observed = sector_index.loc[~sector_index["missing_sector_day"]]
    candidate_cases = _candidate_case_table(sector_index)
    high_volume_low_breadth = (
        int(candidate_cases["case_type"].eq("high_volume_low_breadth").sum()) if not candidate_cases.empty else 0
    )
    low_volume_broad = (
        int(candidate_cases["case_type"].eq("low_volume_broad_evidence").sum()) if not candidate_cases.empty else 0
    )
    sign_reversals = int(weighting["sign_reversal"].fillna(False).sum())
    max_weighting_gap = float(weighting["absolute_difference"].max(skipna=True))
    max_influence = float(influence_summary["maximum_absolute_influence"].max()) if not influence_summary.empty else np.nan
    high_dispersion_zero = int(disagreement["case_type"].eq("near_zero_high_dispersion").sum()) if not disagreement.empty else 0
    lagged = return_validation_frame.loc[
        return_validation_frame["horizon"].eq("sentiment_t_to_return_tplus1")
    ].copy()
    max_lag_abs = float(
        lagged[["pearson_correlation", "spearman_correlation"]].abs().max(axis=1).max(skipna=True)
    ) if not lagged.empty else np.nan
    yearly_headline_range = (
        temporal.groupby("sector")["headline_volume"].agg(lambda s: int(s.max() - s.min())).max()
        if not temporal.empty
        else np.nan
    )
    best_supported = innovation.sort_values("supporting_observation_count", ascending=False).iloc[0]
    weak_supported = innovation.sort_values("supporting_observation_count", ascending=True).iloc[0]

    rows = [
        {
            "insight_id": "SENT-001",
            "question": "Are headline volume and active-ticker breadth empirically distinct?",
            "metric/evidence": "candidate case counts for high-volume/low-breadth and low-volume/broad evidence",
            "observed result": f"{high_volume_low_breadth} high-volume/low-breadth and {low_volume_broad} low-volume/broad cases",
            "stance": "SUPPORTS" if high_volume_low_breadth + low_volume_broad > 0 else "NEUTRAL",
            "relevant artifact": "results/tables/sentiment_candidate_cases.csv",
            "robust_enough_for_report": high_volume_low_breadth + low_volume_broad > 0,
            "limitation": "Thresholds are descriptive quantiles, not tuned return predictors.",
        },
        {
            "insight_id": "SENT-002",
            "question": "Does headline weighting materially disagree with equal-ticker weighting?",
            "metric/evidence": "absolute differences and sign reversals",
            "observed result": f"max absolute difference {max_weighting_gap:.4f}; sign reversals {sign_reversals}",
            "stance": "SUPPORTS" if sign_reversals > 0 or max_weighting_gap >= 0.10 else "QUALIFIES",
            "relevant artifact": "results/tables/sentiment_weighting_comparison.csv",
            "robust_enough_for_report": bool(sign_reversals > 0 or max_weighting_gap >= 0.10),
            "limitation": "Naive headline weighting is diagnostic only and not the approved production index.",
        },
        {
            "insight_id": "SENT-003",
            "question": "Can one constituent materially change a sector signal?",
            "metric/evidence": "leave-one-ticker-out maximum absolute influence",
            "observed result": f"maximum absolute influence {max_influence:.4f}",
            "stance": "SUPPORTS" if pd.notna(max_influence) and max_influence >= MATERIAL_INFLUENCE_THRESHOLD else "QUALIFIES",
            "relevant artifact": "results/tables/sentiment_constituent_influence.csv",
            "robust_enough_for_report": bool(pd.notna(max_influence) and max_influence >= MATERIAL_INFLUENCE_THRESHOLD),
            "limitation": "High influence is sensitivity, not evidence of manipulation or bias.",
        },
        {
            "insight_id": "SENT-004",
            "question": "Does near-zero sentiment mean neutrality or cancellation?",
            "metric/evidence": "near-zero sector-days ranked by cross-ticker dispersion",
            "observed result": f"{high_dispersion_zero} high-dispersion near-zero examples retained",
            "stance": "SUPPORTS" if high_dispersion_zero > 0 else "NEUTRAL",
            "relevant artifact": "results/tables/sentiment_disagreement_examples.csv",
            "robust_enough_for_report": high_dispersion_zero > 0,
            "limitation": "Examples diagnose structure but do not establish a trading signal.",
        },
        {
            "insight_id": "SENT-005",
            "question": "Do carried-over headlines differ from same-day headlines?",
            "metric/evidence": "timing-bucket average compound and absolute compound",
            "observed result": "same-day and carried-over timing buckets are reported separately",
            "stance": "QUALIFIES",
            "relevant artifact": "results/tables/sentiment_carryover_diagnostic.csv",
            "robust_enough_for_report": True,
            "limitation": "Calendar timing is descriptive; no causal interpretation is claimed.",
        },
        {
            "insight_id": "SENT-006",
            "question": "Is there a pre-declared lagged sentiment-return relationship?",
            "metric/evidence": "sector-level Pearson/Spearman correlations for t sentiment to t+1 returns",
            "observed result": f"largest absolute lagged correlation {max_lag_abs:.4f}",
            "stance": "QUALIFIES" if pd.notna(max_lag_abs) and max_lag_abs < 0.15 else "SUPPORTS",
            "relevant artifact": "results/tables/sentiment_return_validation.csv",
            "robust_enough_for_report": True,
            "limitation": "No arbitrary lag search; correlations are descriptive and not proof of predictability.",
        },
        {
            "insight_id": "SENT-007",
            "question": "Does sentiment/evidence behaviour change across years?",
            "metric/evidence": "year-sector sentiment and evidence summary",
            "observed result": f"largest within-sector annual headline-volume range {yearly_headline_range}",
            "stance": "QUALIFIES",
            "relevant artifact": "results/tables/sentiment_temporal_stability.csv",
            "robust_enough_for_report": True,
            "limitation": "No external event narrative is introduced here.",
        },
        {
            "insight_id": "SENT-008",
            "question": "Which VADER weaknesses are observed in this corpus?",
            "metric/evidence": "deterministic category matches and example headlines",
            "observed result": f"{len(taxonomy)} observed model-risk categories",
            "stance": "SUPPORTS" if len(taxonomy) else "NEUTRAL",
            "relevant artifact": "results/tables/sentiment_vader_failure_taxonomy.csv",
            "robust_enough_for_report": len(taxonomy) > 0,
            "limitation": "Categories are plausible model-risk diagnostics, not manually corrected labels.",
        },
        {
            "insight_id": "SENT-009",
            "question": "Which innovation concept is best supported by the data?",
            "metric/evidence": "innovation reconnaissance supporting observation counts",
            "observed result": f"{best_supported['concept']} has the largest support count",
            "stance": "SUPPORTS",
            "relevant artifact": "results/tables/sentiment_innovation_reconnaissance.csv",
            "robust_enough_for_report": True,
            "limitation": "Phase 2A does not implement or validate any trading overlay.",
        },
        {
            "insight_id": "SENT-010",
            "question": "Which promising concept is least supported at this stage?",
            "metric/evidence": "innovation reconnaissance supporting observation counts",
            "observed result": f"{weak_supported['concept']} has the smallest support count",
            "stance": "CHALLENGES",
            "relevant artifact": "results/tables/sentiment_innovation_reconnaissance.csv",
            "robust_enough_for_report": True,
            "limitation": "Weak Phase 2A support does not rule out later usefulness under a pre-declared design.",
        },
    ]
    return pd.DataFrame(rows)


def build_sentiment_diagnostics(
    cleaned_headlines: pd.DataFrame,
    equity_prices: pd.DataFrame,
    equity_returns: pd.DataFrame,
) -> SentimentDiagnostics:
    """Build the complete Phase 2A diagnostic-only sentiment evidence layer."""

    trading_calendar = pd.DatetimeIndex(equity_prices["date"].drop_duplicates()).sort_values()
    universe = _sector_universe(equity_prices)
    headline_scores = score_headlines(cleaned_headlines, trading_calendar)
    ticker_scores = ticker_day_sentiment(headline_scores)
    sector_index = sector_sentiment_index(ticker_scores, universe, trading_calendar)
    month = sector_month_diagnostics(sector_index)
    candidate_cases = _candidate_case_table(sector_index)
    weighting, disagreements = weighting_comparison(headline_scores, ticker_scores, sector_index)
    influence, influence_events = constituent_influence(ticker_scores)
    disagreement = disagreement_examples(sector_index, ticker_scores)
    carryover = carryover_diagnostic(headline_scores)
    taxonomy = vader_failure_taxonomy(headline_scores)
    validation = return_validation(sector_index, equity_returns)
    stability = temporal_stability(sector_index)
    innovation = innovation_reconnaissance(sector_index, weighting, influence, carryover, disagreement)
    register = insight_register(
        sector_index,
        weighting,
        influence,
        carryover,
        validation,
        stability,
        taxonomy,
        disagreement,
        innovation,
    )
    return SentimentDiagnostics(
        headline_scores=headline_scores,
        ticker_day_sentiment=ticker_scores,
        sector_sentiment_index=sector_index,
        sector_month_diagnostics=month,
        candidate_cases=candidate_cases,
        weighting_comparison=weighting,
        weighting_disagreements=disagreements,
        constituent_influence=influence,
        constituent_influence_events=influence_events,
        disagreement_examples=disagreement,
        carryover_diagnostic=carryover,
        vader_failure_taxonomy=taxonomy,
        return_validation=validation,
        temporal_stability=stability,
        innovation_reconnaissance=innovation,
        insight_register=register,
    )


__all__ = [
    "SentimentDiagnostics",
    "build_sentiment_diagnostics",
    "carryover_diagnostic",
    "constituent_influence",
    "return_validation",
    "score_headlines",
    "sector_month_diagnostics",
    "sector_sentiment_index",
    "temporal_stability",
    "ticker_day_sentiment",
    "vader_failure_taxonomy",
    "weighting_comparison",
]
