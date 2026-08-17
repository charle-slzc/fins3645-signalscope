"""Vega-Lite chart specifications for SignalScope Fund and Risk views."""

from __future__ import annotations

import pandas as pd

from app.design import COLORS
from app.funds import METHOD_ORDER


FAMILY_COLORS = {
    "Equity": COLORS["family_equity"],
    "Crypto": COLORS["family_crypto"],
    "Combined": COLORS["family_combined"],
}

METHOD_SHAPES = {
    "Equal Weight": "circle",
    "Minimum Variance": "square",
    "Maximum Sharpe": "triangle-up",
}

FUND_SELECTION_NAME = "fund_pick"


def chart_config() -> dict:
    return {
        "view": {"stroke": "transparent"},
        "axis": {
            "labelColor": COLORS["text_secondary"],
            "titleColor": COLORS["text_primary"],
            "domainColor": COLORS["border"],
            "gridColor": "#263831",
            "tickColor": COLORS["border"],
            "labelFontSize": 12,
            "titleFontSize": 13,
            "titleFontWeight": 700,
        },
        "legend": {
            "labelColor": COLORS["text_secondary"],
            "titleColor": COLORS["text_primary"],
            "titleFontWeight": 700,
            "labelFontSize": 12,
            "titleFontSize": 12,
            "symbolStrokeWidth": 1.2,
        },
        "title": {"color": COLORS["text_primary"]},
        "header": {"labelColor": COLORS["text_secondary"], "titleColor": COLORS["text_primary"]},
    }


def risk_return_spec() -> dict:
    point_encoding = {
        "x": {
            "field": "volatility_pct",
            "type": "quantitative",
            "title": "Annualised volatility",
            "axis": {
                "format": ".0%",
                "grid": True,
                "gridColor": "#263831",
                "labelColor": COLORS["text_secondary"],
                "titleColor": COLORS["text_primary"],
                "titleFontWeight": 700,
                "labelFontSize": 12,
                "titleFontSize": 13,
            },
            "scale": {"zero": False, "nice": True},
        },
        "y": {
            "field": "return_pct",
            "type": "quantitative",
            "title": "Annualised historical OOS return",
            "axis": {
                "format": ".0%",
                "grid": True,
                "gridColor": "#263831",
                "labelColor": COLORS["text_secondary"],
                "titleColor": COLORS["text_primary"],
                "titleFontWeight": 700,
                "labelFontSize": 12,
                "titleFontSize": 13,
            },
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
            "condition": {"test": "datum.is_selected", "value": 230},
            "value": 105,
        },
        "stroke": {
            "condition": {"test": "datum.is_selected", "value": COLORS["action"]},
            "value": COLORS["background"],
        },
        "strokeWidth": {
            "condition": {"test": "datum.is_selected", "value": 3.3},
            "value": 1.1,
        },
        "opacity": {
            "condition": {"test": "datum.is_selected", "value": 1.0},
            "value": 0.74,
        },
        "tooltip": [
            {"field": "fund_label", "type": "nominal", "title": "Fund"},
            {"field": "family_label", "type": "nominal", "title": "Family"},
            {"field": "method", "type": "nominal", "title": "Method"},
            {
                "field": "return_pct",
                "type": "quantitative",
                "title": "Historical OOS annualised return",
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
        ],
    }
    return {
        "background": "transparent",
        "height": 390,
        "layer": [
            {
                "params": [
                    {
                        "name": FUND_SELECTION_NAME,
                        "select": {
                            "type": "point",
                            "fields": ["fund_key"],
                            "on": "click",
                            "clear": "dblclick",
                        },
                    }
                ],
                "mark": {"type": "point", "filled": True, "opacity": 0.9},
                "encoding": point_encoding,
            },
            {
                "transform": [{"filter": "datum.is_selected"}],
                "mark": {
                    "type": "text",
                    "align": "left",
                    "baseline": "middle",
                    "dx": 12,
                    "fontSize": 12,
                    "fontWeight": 700,
                    "color": COLORS["text_primary"],
                },
                "encoding": {
                    "x": point_encoding["x"],
                    "y": point_encoding["y"],
                    "text": {"field": "fund_label", "type": "nominal"},
                },
            },
        ],
        "config": chart_config(),
    }


def time_series_spec(y_field: str, y_title: str, y_format: str, color: str, height: int) -> dict:
    return {
        "background": "transparent",
        "height": height,
        "mark": {"type": "line", "interpolate": "monotone", "strokeWidth": 2.2, "color": color},
        "encoding": {
            "x": {
                "field": "date",
                "type": "temporal",
                "title": None,
                "axis": {"grid": False, "labelColor": COLORS["text_secondary"]},
            },
            "y": {
                "field": y_field,
                "type": "quantitative",
                "title": y_title,
                "axis": {
                    "format": y_format,
                    "grid": True,
                    "gridColor": "#263831",
                    "labelColor": COLORS["text_secondary"],
                    "titleColor": COLORS["text_primary"],
                },
            },
            "tooltip": [
                {"field": "date", "type": "temporal", "title": "Date"},
                {"field": y_field, "type": "quantitative", "title": y_title, "format": y_format},
                {"field": "net_return", "type": "quantitative", "title": "Daily net return", "format": ".2%"},
            ],
        },
        "config": chart_config(),
    }


def growth_spec() -> dict:
    return time_series_spec(
        y_field="growth_net_display",
        y_title="Growth of $1",
        y_format="$.2f",
        color=COLORS["signal"],
        height=320,
    )


def drawdown_spec() -> dict:
    return {
        "background": "transparent",
        "height": 190,
        "mark": {
            "type": "area",
            "line": {"strokeWidth": 1.4, "color": COLORS["negative"]},
            "color": COLORS["negative"],
            "opacity": 0.64,
        },
        "encoding": {
            "x": {
                "field": "date",
                "type": "temporal",
                "title": None,
                "axis": {"grid": False, "labelColor": COLORS["text_secondary"]},
            },
            "y": {
                "field": "drawdown_net_display",
                "type": "quantitative",
                "title": "Drawdown",
                "axis": {
                    "format": ".0%",
                    "grid": True,
                    "gridColor": "#263831",
                    "labelColor": COLORS["text_secondary"],
                    "titleColor": COLORS["text_primary"],
                },
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
        "config": chart_config(),
    }


def holdings_spec(holdings: pd.DataFrame) -> dict:
    domain = holdings["asset"].tolist()
    return {
        "background": "transparent",
        "height": max(210, min(390, 32 * len(domain))),
        "mark": {"type": "bar", "cornerRadiusEnd": 3, "color": COLORS["family_combined"]},
        "encoding": {
            "x": {
                "field": "weight",
                "type": "quantitative",
                "title": "Portfolio weight",
                "axis": {
                    "format": ".0%",
                    "grid": True,
                    "gridColor": "#263831",
                    "labelColor": COLORS["text_secondary"],
                    "titleColor": COLORS["text_primary"],
                },
            },
            "y": {
                "field": "asset",
                "type": "nominal",
                "title": None,
                "sort": domain,
                "axis": {"labelLimit": 150, "labelColor": COLORS["text_secondary"]},
            },
            "tooltip": [
                {"field": "asset", "type": "nominal", "title": "Holding"},
                {"field": "asset_class", "type": "nominal", "title": "Asset class"},
                {"field": "weight", "type": "quantitative", "title": "Weight", "format": ".1%"},
            ],
        },
        "config": chart_config(),
    }


def exposure_spec() -> dict:
    return {
        "background": "transparent",
        "height": 78,
        "layer": [
            {
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
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "middle",
                    "fontWeight": 700,
                    "fontSize": 12,
                    "color": "#0d1412",
                },
                "encoding": {
                    "x": {
                        "field": "exposure",
                        "type": "quantitative",
                        "stack": "center",
                    },
                    "y": {"value": 28},
                    "text": {"field": "exposure_label", "type": "nominal"},
                    "detail": {"field": "asset_class_label", "type": "nominal"},
                },
            },
        ],
        "config": chart_config() | {"legend": chart_config()["legend"] | {"orient": "bottom", "title": None}},
    }
