"""Station 3A portfolio construction and walk-forward OOS backtests."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import scipy.optimize as scipy_opt


METHOD_EQUAL_WEIGHT = "Equal Weight"
METHOD_MIN_VARIANCE = "Minimum Variance"
METHOD_MAX_SHARPE = "Maximum Sharpe"
METHODS = (METHOD_EQUAL_WEIGHT, METHOD_MIN_VARIANCE, METHOD_MAX_SHARPE)
BENCHMARK_METHODS = frozenset({METHOD_EQUAL_WEIGHT})
OPTIMISATION_METHODS = frozenset({METHOD_MIN_VARIANCE, METHOD_MAX_SHARPE})

FAMILY_EQUITY = "Equity-only"
FAMILY_CRYPTO = "Crypto-only"
FAMILY_COMBINED = "Combined"

ANNUALISATION = {
    FAMILY_EQUITY: 252,
    FAMILY_CRYPTO: 365,
    FAMILY_COMBINED: 252,
}
ESTIMATION_WINDOWS = {
    FAMILY_EQUITY: 252,
    FAMILY_CRYPTO: 365,
    FAMILY_COMBINED: 252,
}
RISK_FREE_RATE_ANNUAL = 0.0
TRANSACTION_COST_RATE = 0.001
CONDITION_NUMBER_THRESHOLD = 1e10
REGULARISATION_SCALE = 1e-8
WEIGHT_TOLERANCE = 1e-8


@dataclass(frozen=True)
class BacktestResult:
    """Outputs from one fund-family/method backtest."""

    fund_returns: pd.DataFrame
    fund_weights: pd.DataFrame
    diagnostics: pd.DataFrame
    turnover: pd.DataFrame
    asset_class_exposure: pd.DataFrame
    first_live_date: pd.Timestamp


@dataclass(frozen=True)
class PortfolioSuite:
    """Combined outputs across all Phase 1 portfolio families and methods."""

    fund_returns: pd.DataFrame
    fund_weights: pd.DataFrame
    performance_metrics: pd.DataFrame
    diagnostics: pd.DataFrame
    turnover: pd.DataFrame
    asset_class_exposure: pd.DataFrame
    first_live_dates: pd.DataFrame


def method_type(method: str) -> str:
    """Return whether a method is a benchmark or optimiser."""

    if method in BENCHMARK_METHODS:
        return "benchmark"
    if method in OPTIMISATION_METHODS:
        return "optimisation"
    raise ValueError(f"unknown portfolio method: {method!r}")


def _sorted_returns(returns: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("returns must use a DatetimeIndex")
    if returns.index.has_duplicates:
        raise ValueError("returns index must be unique")
    sorted_returns = returns.copy()
    sorted_returns.index = pd.to_datetime(sorted_returns.index)
    sorted_returns = sorted_returns.sort_index().sort_index(axis=1)
    return sorted_returns.apply(pd.to_numeric, errors="coerce")


def _eligible_assets(window: pd.DataFrame, min_observations: int) -> list[str]:
    finite = window.replace([np.inf, -np.inf], np.nan)
    counts = finite.notna().sum(axis=0)
    eligible = counts[counts >= min_observations].index.tolist()
    if not eligible:
        raise ValueError("no eligible assets with sufficient historical observations")
    return eligible


def _equal_weights(assets: list[str]) -> pd.Series:
    if not assets:
        raise ValueError("cannot form Equal Weight portfolio with no assets")
    return pd.Series(1.0 / len(assets), index=assets, dtype=float)


def _regularised_covariance(window: pd.DataFrame) -> tuple[np.ndarray, float, float]:
    cov = window.cov().to_numpy(dtype=float)
    if not np.isfinite(cov).all():
        raise ValueError("covariance matrix contains non-finite values")
    if cov.shape == (1, 1):
        condition = 1.0
    else:
        condition = float(np.linalg.cond(cov))
    jitter = 0.0
    if not np.isfinite(condition) or condition > CONDITION_NUMBER_THRESHOLD:
        diag = np.diag(cov)
        scale = float(np.nanmean(diag)) if len(diag) else 0.0
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0
        jitter = scale * REGULARISATION_SCALE
        cov = cov + np.eye(cov.shape[0]) * jitter
        condition = float(np.linalg.cond(cov)) if cov.shape != (1, 1) else 1.0
    return cov, condition, jitter


def _validate_weights(weights: np.ndarray, asset_count: int) -> tuple[bool, str, np.ndarray]:
    if weights.shape != (asset_count,):
        return False, "wrong weight vector shape", weights
    if not np.isfinite(weights).all():
        return False, "non-finite weights", weights
    if weights.min(initial=0.0) < -WEIGHT_TOLERANCE:
        return False, "negative weight below tolerance", weights
    if weights.max(initial=0.0) > 1.0 + WEIGHT_TOLERANCE:
        return False, "weight above upper bound", weights
    weight_sum = float(weights.sum())
    if abs(weight_sum - 1.0) > 1e-6:
        return False, "weights do not sum to one", weights
    clipped = np.clip(weights, 0.0, 1.0)
    clipped_sum = clipped.sum()
    if clipped_sum <= 0:
        return False, "all weights are zero after clipping", weights
    return True, "validated", clipped / clipped_sum


def _optimise_weights(window: pd.DataFrame, method: str) -> tuple[pd.Series, dict[str, object]]:
    assets = list(window.columns)
    asset_count = len(assets)
    if method == METHOD_EQUAL_WEIGHT:
        weights = _equal_weights(assets)
        return weights, {
            "solver_success": True,
            "solver_status": "benchmark",
            "solver_message": "Equal Weight benchmark",
            "objective_value": np.nan,
            "covariance_condition": np.nan,
            "regularisation_jitter": 0.0,
            "fallback_used": False,
            "fallback_reason": "",
        }

    cov, condition, jitter = _regularised_covariance(window)
    means = window.mean(axis=0).to_numpy(dtype=float)
    if not np.isfinite(means).all():
        raise ValueError("expected-return vector contains non-finite values")

    x0 = np.full(asset_count, 1.0 / asset_count)
    bounds = [(0.0, 1.0)] * asset_count
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def variance_objective(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    def negative_sharpe_objective(w: np.ndarray) -> float:
        variance = float(w @ cov @ w)
        if variance <= 0 or not np.isfinite(variance):
            return 1e9
        expected = float(means @ w)
        return -expected / np.sqrt(variance)

    objective = variance_objective if method == METHOD_MIN_VARIANCE else negative_sharpe_objective
    result = scipy_opt.minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12, "disp": False},
    )

    valid, validation_message, cleaned = _validate_weights(np.asarray(result.x, dtype=float), asset_count)
    solver_success = bool(result.success) and valid
    fallback_reason = ""
    if solver_success:
        weights = pd.Series(cleaned, index=assets, dtype=float)
    else:
        weights = _equal_weights(assets)
        fallback_reason = (
            f"solver_success={bool(result.success)}; "
            f"message={getattr(result, 'message', 'unknown')}; validation={validation_message}"
        )

    objective_value = float(objective(cleaned if valid else weights.to_numpy(dtype=float)))
    return weights, {
        "solver_success": solver_success,
        "solver_status": int(getattr(result, "status", -1)),
        "solver_message": str(getattr(result, "message", "")),
        "objective_value": objective_value,
        "covariance_condition": condition,
        "regularisation_jitter": jitter,
        "fallback_used": not solver_success,
        "fallback_reason": fallback_reason,
    }


def calculate_turnover(
    previous_weights: pd.Series | None,
    target_weights: pd.Series,
) -> float:
    """Calculate dollar turnover as sum of absolute active-weight changes.

    The initial rebalance is measured from cash, so turnover equals one for a
    fully invested long-only portfolio.
    """

    if previous_weights is None or previous_weights.empty:
        previous = pd.Series(dtype=float)
    else:
        previous = previous_weights.astype(float)
    current = target_weights.astype(float)
    assets = previous.index.union(current.index)
    return float((current.reindex(assets, fill_value=0.0) - previous.reindex(assets, fill_value=0.0)).abs().sum())


def _live_rebalance_positions(index: pd.DatetimeIndex, estimation_window: int) -> list[int]:
    if len(index) <= estimation_window:
        raise ValueError("not enough observations for the requested estimation window")
    positions: list[int] = []
    first_live = estimation_window
    positions.append(first_live)
    last_period = index[first_live].to_period("M")
    for position in range(first_live + 1, len(index)):
        period = index[position].to_period("M")
        if period != last_period:
            positions.append(position)
            last_period = period
    return positions


def _asset_class_for(asset: str, asset_class_map: dict[str, str] | None) -> str:
    if asset_class_map and asset in asset_class_map:
        return asset_class_map[asset]
    return "crypto" if asset.endswith("-USD") else "equity"


def _drawdown(returns: pd.Series) -> pd.Series:
    growth = (1.0 + returns.fillna(0.0)).cumprod()
    peak = growth.cummax()
    return growth / peak - 1.0


def oos_backtest(
    returns: pd.DataFrame,
    method: str = METHOD_MIN_VARIANCE,
    *,
    fund_family: str = FAMILY_COMBINED,
    estimation_window: int = 252,
    periods_per_year: int = 252,
    transaction_cost_rate: float = TRANSACTION_COST_RATE,
    asset_class_map: dict[str, str] | None = None,
) -> BacktestResult:
    """Run a monthly walk-forward OOS backtest with strict lagged estimation."""

    method_type_value = method_type(method)
    wide = _sorted_returns(returns)
    live_positions = _live_rebalance_positions(wide.index, estimation_window)
    live_position_set = set(live_positions)
    first_live_date = wide.index[live_positions[0]]

    current_weights: pd.Series | None = None
    current_metadata: dict[str, object] | None = None
    previous_weights: pd.Series | None = None
    next_rebalance_by_pos = {position: position for position in live_positions}

    return_rows: list[dict[str, object]] = []
    weight_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    turnover_rows: list[dict[str, object]] = []
    exposure_rows: list[dict[str, object]] = []

    for position in range(live_positions[0], len(wide)):
        live_date = wide.index[position]
        rebalance_today = position in live_position_set
        turnover = 0.0
        transaction_cost = 0.0

        if rebalance_today:
            estimation = wide.iloc[position - estimation_window : position]
            eligible_assets = _eligible_assets(estimation, estimation_window)
            estimation = estimation.loc[:, eligible_assets]
            weights, diagnostics = _optimise_weights(estimation, method)
            turnover = calculate_turnover(previous_weights, weights)
            transaction_cost = transaction_cost_rate * turnover
            decision_date = wide.index[position - 1]
            current_weights = weights
            previous_weights = weights
            current_metadata = {
                "live_rebalance_date": live_date,
                "decision_date": decision_date,
                "estimation_start": estimation.index[0],
                "estimation_end": estimation.index[-1],
                "asset_count": len(eligible_assets),
            }

            min_weight = float(weights.min()) if len(weights) else np.nan
            max_weight = float(weights.max()) if len(weights) else np.nan
            diagnostic_rows.append(
                {
                    "fund_family": fund_family,
                    "method": method,
                    "method_type": method_type_value,
                    "live_rebalance_date": live_date,
                    "decision_date": decision_date,
                    "estimation_start": estimation.index[0],
                    "estimation_end": estimation.index[-1],
                    "estimation_window": estimation_window,
                    "periods_per_year": periods_per_year,
                    "eligible_asset_count": len(eligible_assets),
                    "valid_observation_count": int(estimation.notna().sum().min()),
                    "solver_success": diagnostics["solver_success"],
                    "solver_status": diagnostics["solver_status"],
                    "solver_message": diagnostics["solver_message"],
                    "objective_value": diagnostics["objective_value"],
                    "weight_sum": float(weights.sum()),
                    "weight_sum_residual": float(weights.sum() - 1.0),
                    "min_weight": min_weight,
                    "max_weight": max_weight,
                    "covariance_condition": diagnostics["covariance_condition"],
                    "regularisation_jitter": diagnostics["regularisation_jitter"],
                    "fallback_used": diagnostics["fallback_used"],
                    "fallback_reason": diagnostics["fallback_reason"],
                    "constraints": "long_only; fully_invested; no_leverage",
                }
            )
            turnover_rows.append(
                {
                    "fund_family": fund_family,
                    "method": method,
                    "method_type": method_type_value,
                    "live_rebalance_date": live_date,
                    "decision_date": decision_date,
                    "turnover": turnover,
                    "transaction_cost_rate": transaction_cost_rate,
                    "transaction_cost": transaction_cost,
                }
            )
            for asset, weight in weights.items():
                weight_rows.append(
                    {
                        "date": live_date,
                        "fund_family": fund_family,
                        "method": method,
                        "method_type": method_type_value,
                        "asset": asset,
                        "asset_class": _asset_class_for(asset, asset_class_map),
                        "weight": float(weight),
                        "live_rebalance_date": live_date,
                        "decision_date": decision_date,
                        "estimation_start": estimation.index[0],
                        "estimation_end": estimation.index[-1],
                        "estimation_window": estimation_window,
                    }
                )
            exposure = (
                pd.DataFrame(
                    {
                        "asset": weights.index,
                        "weight": weights.to_numpy(dtype=float),
                        "asset_class": [_asset_class_for(asset, asset_class_map) for asset in weights.index],
                    }
                )
                .groupby("asset_class", sort=True)["weight"]
                .sum()
            )
            for asset_class, exposure_weight in exposure.items():
                exposure_rows.append(
                    {
                        "date": live_date,
                        "fund_family": fund_family,
                        "method": method,
                        "method_type": method_type_value,
                        "asset_class": asset_class,
                        "exposure": float(exposure_weight),
                    }
                )

        if current_weights is None or current_metadata is None:
            continue

        live_returns = wide.loc[live_date, current_weights.index]
        missing_return_asset_count = int(live_returns.isna().sum())
        gross_return = (
            np.nan
            if missing_return_asset_count
            else float(live_returns.to_numpy(dtype=float) @ current_weights.to_numpy(dtype=float))
        )
        net_return = np.nan if pd.isna(gross_return) else gross_return - transaction_cost
        return_rows.append(
            {
                "date": live_date,
                "fund_family": fund_family,
                "method": method,
                "method_type": method_type_value,
                "gross_return": gross_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
                "net_return": net_return,
                "live_rebalance_date": current_metadata["live_rebalance_date"],
                "decision_date": current_metadata["decision_date"],
                "estimation_start": current_metadata["estimation_start"],
                "estimation_end": current_metadata["estimation_end"],
                "asset_count": current_metadata["asset_count"],
                "missing_return_asset_count": missing_return_asset_count,
            }
        )

    fund_returns = pd.DataFrame(return_rows)
    if not fund_returns.empty:
        fund_returns["growth_gross"] = (
            fund_returns.groupby(["fund_family", "method"], sort=False)["gross_return"]
            .transform(lambda s: (1.0 + s.fillna(0.0)).cumprod())
        )
        fund_returns["growth_net"] = (
            fund_returns.groupby(["fund_family", "method"], sort=False)["net_return"]
            .transform(lambda s: (1.0 + s.fillna(0.0)).cumprod())
        )
        fund_returns["drawdown_gross"] = (
            fund_returns.groupby(["fund_family", "method"], sort=False)["gross_return"]
            .transform(_drawdown)
        )
        fund_returns["drawdown_net"] = (
            fund_returns.groupby(["fund_family", "method"], sort=False)["net_return"]
            .transform(_drawdown)
        )

    return BacktestResult(
        fund_returns=fund_returns,
        fund_weights=pd.DataFrame(weight_rows),
        diagnostics=pd.DataFrame(diagnostic_rows),
        turnover=pd.DataFrame(turnover_rows),
        asset_class_exposure=pd.DataFrame(exposure_rows),
        first_live_date=first_live_date,
    )


def performance_metrics(
    daily_returns: pd.Series,
    periods_per_year: int = 252,
    risk_free_rate_annual: float = RISK_FREE_RATE_ANNUAL,
) -> dict[str, float | int | pd.Timestamp]:
    """Calculate annualised return, volatility, Sharpe ratio, and max drawdown."""

    returns = pd.Series(daily_returns).dropna().astype(float)
    if returns.empty:
        return {
            "observation_count": 0,
            "sample_start": pd.NaT,
            "sample_end": pd.NaT,
            "total_return": np.nan,
            "annualised_return": np.nan,
            "annualised_volatility": np.nan,
            "sharpe_ratio": np.nan,
            "max_drawdown": np.nan,
        }
    growth = (1.0 + returns).cumprod()
    total_return = float(growth.iloc[-1] - 1.0)
    annualised_return = float(growth.iloc[-1] ** (periods_per_year / len(returns)) - 1.0)
    annualised_volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year))
    sharpe = (
        (annualised_return - risk_free_rate_annual) / annualised_volatility
        if annualised_volatility > 0
        else np.nan
    )
    drawdown = growth / growth.cummax() - 1.0
    return {
        "observation_count": int(len(returns)),
        "sample_start": returns.index.min() if isinstance(returns.index, pd.DatetimeIndex) else pd.NaT,
        "sample_end": returns.index.max() if isinstance(returns.index, pd.DatetimeIndex) else pd.NaT,
        "total_return": total_return,
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "sharpe_ratio": float(sharpe) if pd.notna(sharpe) else np.nan,
        "max_drawdown": float(drawdown.min()),
    }


def _metrics_table(results: list[BacktestResult]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for result in results:
        returns = result.fund_returns
        for (family, method), group in returns.groupby(["fund_family", "method"], sort=True):
            periods = ANNUALISATION[family]
            gross = performance_metrics(group.set_index("date")["gross_return"], periods)
            net = performance_metrics(group.set_index("date")["net_return"], periods)
            rows.append(
                {
                    "fund_family": family,
                    "method": method,
                    "method_type": method_type(method),
                    "periods_per_year": periods,
                    "risk_free_rate_annual": RISK_FREE_RATE_ANNUAL,
                    "transaction_cost_rate": TRANSACTION_COST_RATE,
                    "observation_count": net["observation_count"],
                    "sample_start": net["sample_start"],
                    "sample_end": net["sample_end"],
                    "gross_total_return": gross["total_return"],
                    "gross_annualised_return": gross["annualised_return"],
                    "gross_annualised_volatility": gross["annualised_volatility"],
                    "gross_sharpe_ratio": gross["sharpe_ratio"],
                    "gross_max_drawdown": gross["max_drawdown"],
                    "net_total_return": net["total_return"],
                    "net_annualised_return": net["annualised_return"],
                    "net_annualised_volatility": net["annualised_volatility"],
                    "net_sharpe_ratio": net["sharpe_ratio"],
                    "net_max_drawdown": net["max_drawdown"],
                    "total_transaction_cost": float(group["transaction_cost"].sum()),
                    "total_turnover": float(group["turnover"].sum()),
                    "first_live_date": result.first_live_date,
                }
            )
    return pd.DataFrame(rows).sort_values(["fund_family", "method"]).reset_index(drop=True)


def _first_live_dates(results: list[BacktestResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        first = result.fund_returns.iloc[0]
        rows.append(
            {
                "fund_family": first["fund_family"],
                "method": first["method"],
                "method_type": first["method_type"],
                "first_live_date": result.first_live_date,
                "estimation_window": int(first["asset_count"] * 0 + result.diagnostics.iloc[0]["estimation_window"]),
                "periods_per_year": ANNUALISATION[first["fund_family"]],
            }
        )
    return pd.DataFrame(rows).sort_values(["fund_family", "method"]).reset_index(drop=True)


def build_portfolio_suite(return_panels, methods: tuple[str, ...] = METHODS) -> PortfolioSuite:
    """Build Phase 1 funds for equity-only, crypto-only, and combined families."""

    family_inputs = {
        FAMILY_EQUITY: return_panels.equity_wide,
        FAMILY_CRYPTO: return_panels.crypto_native_wide,
        FAMILY_COMBINED: return_panels.combined_wide,
    }
    asset_maps = {
        FAMILY_EQUITY: {asset: "equity" for asset in return_panels.equity_wide.columns},
        FAMILY_CRYPTO: {asset: "crypto" for asset in return_panels.crypto_native_wide.columns},
        FAMILY_COMBINED: {
            **{asset: "equity" for asset in return_panels.equity_wide.columns},
            **{asset: "crypto" for asset in return_panels.crypto_native_wide.columns},
        },
    }

    results: list[BacktestResult] = []
    for family, returns in family_inputs.items():
        for method in methods:
            results.append(
                oos_backtest(
                    returns,
                    method=method,
                    fund_family=family,
                    estimation_window=ESTIMATION_WINDOWS[family],
                    periods_per_year=ANNUALISATION[family],
                    transaction_cost_rate=TRANSACTION_COST_RATE,
                    asset_class_map=asset_maps[family],
                )
            )

    fund_returns = pd.concat([result.fund_returns for result in results], ignore_index=True)
    fund_weights = pd.concat([result.fund_weights for result in results], ignore_index=True)
    diagnostics = pd.concat([result.diagnostics for result in results], ignore_index=True)
    turnover = pd.concat([result.turnover for result in results], ignore_index=True)
    exposure = pd.concat([result.asset_class_exposure for result in results], ignore_index=True)
    metrics = _metrics_table(results)
    first_live = _first_live_dates(results)

    return PortfolioSuite(
        fund_returns=fund_returns.sort_values(["fund_family", "method", "date"]).reset_index(drop=True),
        fund_weights=fund_weights.sort_values(["fund_family", "method", "date", "asset"]).reset_index(drop=True),
        performance_metrics=metrics,
        diagnostics=diagnostics.sort_values(["fund_family", "method", "live_rebalance_date"]).reset_index(drop=True),
        turnover=turnover.sort_values(["fund_family", "method", "live_rebalance_date"]).reset_index(drop=True),
        asset_class_exposure=exposure.sort_values(["fund_family", "method", "date", "asset_class"]).reset_index(drop=True),
        first_live_dates=first_live,
    )


__all__ = [
    "ANNUALISATION",
    "BENCHMARK_METHODS",
    "ESTIMATION_WINDOWS",
    "FAMILY_COMBINED",
    "FAMILY_CRYPTO",
    "FAMILY_EQUITY",
    "METHODS",
    "METHOD_EQUAL_WEIGHT",
    "METHOD_MAX_SHARPE",
    "METHOD_MIN_VARIANCE",
    "OPTIMISATION_METHODS",
    "RISK_FREE_RATE_ANNUAL",
    "TRANSACTION_COST_RATE",
    "BacktestResult",
    "PortfolioSuite",
    "build_portfolio_suite",
    "calculate_turnover",
    "method_type",
    "oos_backtest",
    "performance_metrics",
]
