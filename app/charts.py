"""Vega-Lite chart specifications for SignalScope Fund and Risk views."""

from __future__ import annotations

import pandas as pd

from app.funds import METHOD_ORDER


FAMILY_COLORS = {
    "Equity": "#5f7d5d",
    "Crypto": "#8a6f4d",
    "Combined": "#496f82",
}

METHOD_SHAPES = {
    "Equal Weight": "circle",
    "Minimum Variance": "square",
    "Maximum Sharpe": "triangle-up",
}


def risk_return_spec() -> dict:
    return {
        "height": 390,
        "mark": {"type": "point", "filled": True, "opacity": 0.9},
        "encoding": {
            "x": {
                "field": "volatility_pct",
                "type": "quantitative",
                "title": "Annualised volatility",
                "axis": {"format": ".0%", "grid": True},
                "scale": {"zero": False, "nice": True},
            },
            "y": {
                "field": "return_pct",
                "type": "quantitative",
                "title": "Annualised historical OOS return",
                "axis": {"format": ".0%", "grid": True},
                "scale": {"zero": False, "nice": True},
            },
            "color": {
                "field": "family_label",
                "type": "nominal",
                "title": "Family",
                "scale": {
                    "domain": list(FAMILY_COLORS),
                    "range": list(FAMILY_COLORS.values()),
                },
            },
            "shape": {
                "field": "method",
                "type": "nominal",
                "title": "Method",
                "scale": {
                    "domain": list(METHOD_ORDER),
                    "range": [METHOD_SHAPES[method] for method in METHOD_ORDER],
                },
            },
            "size": {
                "condition": {"test": "datum.selected", "value": 230},
                "value": 105,
                "legend": None,
            },
            "stroke": {
                "condition": {"test": "datum.selected", "value": "#17211d"},
                "value": "#ffffff",
            },
            "strokeWidth": {
                "condition": {"test": "datum.selected", "value": 2.8},
                "value": 0.9,
            },
            "tooltip": [
                {"field": "fund_label", "type": "nominal", "title": "Fund"},
                {
                    "field": "return_pct",
                    "type": "quantitative",
                    "title": "Annualised return",
                    "format": ".1%",
                },
                {
                    "field": "volatility_pct",
                    "type": "quantitative",
                    "title": "Volatility",
                    "format": ".1%",
                },
                {
                    "field": "net_sharpe_ratio",
                    "type": "quantitative",
                    "title": "Sharpe",
                    "format": ".2f",
                },
                {
                    "field": "drawdown_pct",
                    "type": "quantitative",
                    "title": "Max drawdown",
                    "format": ".1%",
                },
                {"field": "method_type", "type": "nominal", "title": "Method type"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#5f6d66", "titleColor": "#17211d"},
            "legend": {"labelColor": "#17211d", "titleColor": "#5f6d66"},
        },
    }


def time_series_spec(y_field: str, y_title: str, y_format: str, color: str, height: int) -> dict:
    return {
        "height": height,
        "mark": {"type": "line", "interpolate": "monotone", "strokeWidth": 2.2, "color": color},
        "encoding": {
            "x": {
                "field": "date",
                "type": "temporal",
                "title": None,
                "axis": {"grid": False},
            },
            "y": {
                "field": y_field,
                "type": "quantitative",
                "title": y_title,
                "axis": {"format": y_format, "grid": True},
            },
            "tooltip": [
                {"field": "date", "type": "temporal", "title": "Date"},
                {"field": y_field, "type": "quantitative", "title": y_title, "format": y_format},
                {"field": "net_return", "type": "quantitative", "title": "Daily net return", "format": ".2%"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#5f6d66", "titleColor": "#17211d"},
        },
    }


def growth_spec() -> dict:
    return time_series_spec(
        y_field="growth_net_display",
        y_title="Growth of $1",
        y_format="$.2f",
        color="#2c6f8f",
        height=320,
    )


def drawdown_spec() -> dict:
    return {
        "height": 190,
        "mark": {"type": "area", "line": {"strokeWidth": 1.4}, "color": "#ad3f3f", "opacity": 0.62},
        "encoding": {
            "x": {"field": "date", "type": "temporal", "title": None, "axis": {"grid": False}},
            "y": {
                "field": "drawdown_net_display",
                "type": "quantitative",
                "title": "Drawdown",
                "axis": {"format": ".0%", "grid": True},
            },
            "tooltip": [
                {"field": "date", "type": "temporal", "title": "Date"},
                {
                    "field": "drawdown_net_display",
                    "type": "quantitative",
                    "title": "Drawdown",
                    "format": ".1%",
                },
                {"field": "net_return", "type": "quantitative", "title": "Daily net return", "format": ".2%"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#5f6d66", "titleColor": "#17211d"},
        },
    }


def holdings_spec(holdings: pd.DataFrame) -> dict:
    domain = holdings["asset"].tolist()
    return {
        "height": max(210, min(390, 32 * len(domain))),
        "mark": {"type": "bar", "cornerRadiusEnd": 3, "color": "#496f82"},
        "encoding": {
            "x": {
                "field": "weight",
                "type": "quantitative",
                "title": "Portfolio weight",
                "axis": {"format": ".0%", "grid": True},
            },
            "y": {
                "field": "asset",
                "type": "nominal",
                "title": None,
                "sort": domain,
                "axis": {"labelLimit": 150},
            },
            "tooltip": [
                {"field": "asset", "type": "nominal", "title": "Holding"},
                {"field": "asset_class", "type": "nominal", "title": "Asset class"},
                {"field": "weight", "type": "quantitative", "title": "Weight", "format": ".1%"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#17211d", "titleColor": "#5f6d66"},
        },
    }


def exposure_spec() -> dict:
    return {
        "height": 78,
        "mark": {"type": "bar", "cornerRadius": 4},
        "encoding": {
            "x": {
                "field": "exposure",
                "type": "quantitative",
                "stack": "normalize",
                "title": None,
                "axis": {"format": ".0%"},
            },
            "y": {"value": 28},
            "color": {
                "field": "asset_class_label",
                "type": "nominal",
                "title": "Asset class",
                "scale": {
                    "domain": ["Crypto", "Equity"],
                    "range": [FAMILY_COLORS["Crypto"], FAMILY_COLORS["Equity"]],
                },
            },
            "tooltip": [
                {"field": "asset_class_label", "type": "nominal", "title": "Asset class"},
                {"field": "exposure", "type": "quantitative", "title": "Exposure", "format": ".1%"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#5f6d66", "titleColor": "#17211d"},
            "legend": {"orient": "bottom", "labelColor": "#17211d", "title": None},
        },
    }

