import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Shared design tokens (mirrors app.py palette) ────────────────────────────
_NAVY = "#0a1223"
_DARK = "#0d1728"
_PANEL = "#111827"
_BORDER = "#1e3a5f"
_TEAL = "#10c9a0"
_CORAL = "#ff6b6b"
_GREEN = "#2dcb7f"
_GOLD = "#f5a623"
_SKY = "#38bdf8"
_PURPLE = "#8b5cf6"
_GRAY = "#9ca3af"
_WHITE = "#ffffff"
_FONT = "'DM Sans','Nunito Sans',sans-serif"
_MONO = "'Space Mono','Courier New',monospace"

_BASE_LAYOUT = dict(
    paper_bgcolor=_DARK,
    plot_bgcolor=_PANEL,
    font=dict(family=_FONT, color=_GRAY, size=11),
    margin=dict(l=60, r=24, t=64, b=52),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=_BORDER,
        borderwidth=1,
        font=dict(size=10, color=_GRAY),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    xaxis=dict(
        gridcolor="rgba(30,58,95,0.33)",
        zerolinecolor="rgba(30,58,95,0.33)",
        color=_GRAY,
        showline=True,
        linecolor=_BORDER,
    ),
    yaxis=dict(
        gridcolor="rgba(30,58,95,0.33)",
        zerolinecolor="rgba(30,58,95,0.33)",
        color=_GRAY,
        showline=True,
        linecolor=_BORDER,
    ),
)

_TITLE_STYLE = dict(font=dict(size=13, color=_WHITE, family=_FONT), x=0, xanchor="left")
_AXIS_STYLE = dict(
    gridcolor="rgba(30,58,95,0.33)",
    zerolinecolor="rgba(30,58,95,0.33)",
    color=_GRAY,
    showline=True,
    linecolor=_BORDER,
)

# ── Pre-built rgba fill colours (Plotly rejects 8-digit hex) ─────────────────
_SKY_FILL = "rgba(56,189,248,0.07)"
_TEAL_FILL = "rgba(16,201,160,0.53)"
_CORAL_FILL = "rgba(255,107,107,0.53)"
_PURPLE_FILL = "rgba(139,92,246,0.09)"
_BORDER_GRID = "rgba(30,58,95,0.33)"


def plot_price_forecast_fig(prices, dt_hours):
    T = len(prices)

    if dt_hours == 0.5:
        time_labels = [i * 0.5 for i in range(T)]
        xlabel = "Hour of Day"
    elif dt_hours == 0.25:
        time_labels = [i * 0.25 for i in range(T)]
        xlabel = "Hour of Day"
    else:
        time_labels = list(range(T))
        xlabel = "Hour of Day"

    prices_array = np.array(prices)
    mean_price = float(np.mean(prices_array))
    std_price = float(np.std(prices_array))
    min_price = float(np.min(prices_array))
    max_price = float(np.max(prices_array))
    price_spread = max_price - min_price
    low_threshold = mean_price - 0.3 * std_price
    high_threshold = mean_price + 0.3 * std_price
    num_low = sum(1 for p in prices if p <= low_threshold)
    num_high = sum(1 for p in prices if p >= high_threshold)

    fig = go.Figure()

    for i, price in enumerate(prices):
        if price <= low_threshold:
            fig.add_vrect(
                x0=time_labels[i] - dt_hours / 2,
                x1=time_labels[i] + dt_hours / 2,
                fillcolor=_TEAL,
                opacity=0.10,
                layer="below",
                line_width=0,
            )
        elif price >= high_threshold:
            fig.add_vrect(
                x0=time_labels[i] - dt_hours / 2,
                x1=time_labels[i] + dt_hours / 2,
                fillcolor=_CORAL,
                opacity=0.12,
                layer="below",
                line_width=0,
            )

    fig.add_trace(
        go.Scatter(
            x=time_labels,
            y=list(prices),
            mode="lines+markers",
            name="Forecasted Price",
            line=dict(color=_SKY, width=2.5),
            marker=dict(size=5, color=_SKY),
            fill="tozeroy",
            fillcolor=_SKY_FILL,
        )
    )

    fig.add_hline(
        y=mean_price,
        line_dash="dash",
        line_color=_GRAY,
        line_width=1,
        annotation_text=f"Mean ${mean_price:.2f}/MWh",
        annotation_font_color=_GRAY,
        annotation_font_size=10,
        annotation_position="bottom right",
    )

    layout = {**_BASE_LAYOUT}
    layout["title"] = dict(
        text=(
            f"NYISO Price Forecast  ·  Spread ${price_spread:.2f}/MWh"
            f"  (${min_price:.2f} – ${max_price:.2f})  ·"
            f"  {num_low} charge zones  ·  {num_high} discharge zones"
        ),
        **_TITLE_STYLE,
    )
    layout["xaxis_title"] = xlabel
    layout["yaxis_title"] = "Price ($/MWh)"
    fig.update_layout(**layout)
    fig.update_xaxes(**_AXIS_STYLE)
    fig.update_yaxes(**_AXIS_STYLE)

    return fig


def plot_price_soc_fig(prices, capacity, soc, decision):
    prices = np.array(prices)
    soc = np.array(soc)
    T = len(prices)
    hours = np.arange(T)
    soc_MWh = soc[:-1] * capacity

    opens = np.concatenate([[prices[0]], prices[:-1]])
    closes = prices
    highs = np.maximum(opens, closes)
    lows = np.minimum(opens, closes)

    actions = (
        np.array(decision)
        if decision is not None
        else np.sign(np.diff(soc_MWh, prepend=soc_MWh[0]))
    )

    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=("",),
    )

    fig.add_trace(
        go.Candlestick(
            x=hours,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="Price ($/MWh)",
            increasing_line_color=_TEAL,
            increasing_fillcolor=_TEAL_FILL,
            decreasing_line_color=_CORAL,
            decreasing_fillcolor=_CORAL_FILL,
        ),
        secondary_y=False,
    )

    charge_idx = [i for i, a in enumerate(actions) if a > 0]
    if charge_idx:
        fig.add_trace(
            go.Scatter(
                x=hours[charge_idx],
                y=closes[charge_idx],
                mode="markers",
                name="Charge ▲",
                marker=dict(
                    symbol="triangle-up",
                    size=11,
                    color=_TEAL,
                    line=dict(color=_NAVY, width=1),
                ),
            ),
            secondary_y=False,
        )

    discharge_idx = [i for i, a in enumerate(actions) if a < 0]
    if discharge_idx:
        fig.add_trace(
            go.Scatter(
                x=hours[discharge_idx],
                y=closes[discharge_idx],
                mode="markers",
                name="Discharge ▼",
                marker=dict(
                    symbol="triangle-down",
                    size=11,
                    color=_CORAL,
                    line=dict(color=_NAVY, width=1),
                ),
            ),
            secondary_y=False,
        )

    fig.add_trace(
        go.Scatter(
            x=hours,
            y=soc_MWh,
            mode="lines+markers",
            name="State of Charge (MWh)",
            line=dict(color=_PURPLE, width=2.5),
            marker=dict(size=5, color=_PURPLE),
            fill="tozeroy",
            fillcolor=_PURPLE_FILL,
        ),
        secondary_y=True,
    )

    layout = {**_BASE_LAYOUT}
    layout["title"] = dict(
        text="Price Candles  ·  Battery State of Charge", **_TITLE_STYLE
    )
    layout["xaxis_title"] = "Hour of Day"
    layout["xaxis_rangeslider_visible"] = False
    layout["margin"] = dict(l=60, r=68, t=64, b=52)
    fig.update_layout(**layout)
    fig.update_xaxes(**_AXIS_STYLE)
    fig.update_yaxes(title_text="Price ($/MWh)", secondary_y=False, **_AXIS_STYLE)
    fig.update_yaxes(
        title_text="SoC (MWh)", secondary_y=True, color=_PURPLE, showgrid=False
    )

    return fig


def plot_arbitrage_explanation_fig(
    prices,
    capacity,
    soc_min,
    soc_max,
    cmax_MW,
    dmax_MW,
    dt_hours,
    charge_MW,
    discharge_MW,
    soc,
    objective_cost,
):
    prices = np.array(prices)
    charge_MW = np.array(charge_MW) if charge_MW is not None else np.zeros(len(prices))
    discharge_MW = (
        np.array(discharge_MW) if discharge_MW is not None else np.zeros(len(prices))
    )
    soc = np.array(soc)

    T = len(prices)
    hours = list(range(T))
    soc_MWh = soc[:-1] * capacity

    mean_price = float(np.mean(prices))
    std_price = float(np.std(prices))
    low_threshold = mean_price - 0.25 * std_price
    high_threshold = mean_price + 0.25 * std_price

    soc_min_MWh = soc_min * capacity
    soc_max_MWh = soc_max * capacity
    total_charge = float(np.sum(charge_MW)) * dt_hours
    total_discharge = float(np.sum(discharge_MW)) * dt_hours
    efficiency = (total_discharge / total_charge * 100) if total_charge > 0 else 0.0

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "Price Signal  —  Charge Zones (teal)  ·  Discharge Zones (coral)",
            "Battery Dispatch  —  Discharge (coral +)  ·  Charge (teal −)",
            "State of Charge  —  Must Stay Within Operating Bounds",
        ),
        vertical_spacing=0.07,
        row_heights=[0.32, 0.32, 0.36],
    )

    # ── Panel 1: Price ────────────────────────────────────────────────────
    for i, price in enumerate(prices):
        if price <= low_threshold:
            fig.add_vrect(
                x0=i - 0.4,
                x1=i + 0.4,
                fillcolor=_TEAL,
                opacity=0.10,
                layer="below",
                line_width=0,
                row=1,
                col=1,
            )
        elif price >= high_threshold:
            fig.add_vrect(
                x0=i - 0.4,
                x1=i + 0.4,
                fillcolor=_CORAL,
                opacity=0.12,
                layer="below",
                line_width=0,
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Scatter(
            x=hours,
            y=prices.tolist(),
            mode="lines+markers",
            name="Price ($/MWh)",
            line=dict(color=_SKY, width=2.5),
            marker=dict(size=4, color=_SKY),
            fill="tozeroy",
            fillcolor=_SKY_FILL,
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    fig.add_hline(
        y=mean_price,
        line_dash="dash",
        line_color=_GRAY,
        line_width=1,
        annotation_text=f"Mean ${mean_price:.2f}",
        annotation_font_color=_GRAY,
        annotation_font_size=10,
        annotation_position="bottom right",
        row=1,
        col=1,
    )

    # ── Panel 2: Charge / Discharge bars ─────────────────────────────────
    fig.add_trace(
        go.Bar(
            x=hours,
            y=discharge_MW.tolist(),
            name="Discharge (MW)",
            marker_color=_CORAL,
            marker_line_width=0,
            opacity=0.85,
            showlegend=True,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=hours,
            y=(-charge_MW).tolist(),
            name="Charge (MW)",
            marker_color=_TEAL,
            marker_line_width=0,
            opacity=0.85,
            showlegend=True,
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=dmax_MW,
        line_dash="dot",
        line_color=_CORAL,
        line_width=1,
        annotation_text=f"Max discharge {dmax_MW} MW",
        annotation_font_color=_CORAL,
        annotation_font_size=9,
        annotation_position="top right",
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-cmax_MW,
        line_dash="dot",
        line_color=_TEAL,
        line_width=1,
        annotation_text=f"Max charge {cmax_MW} MW",
        annotation_font_color=_TEAL,
        annotation_font_size=9,
        annotation_position="bottom right",
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_color="rgba(156,163,175,0.27)", line_width=1, row=2, col=1)

    # ── Panel 3: SoC ─────────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=hours + hours[::-1],
            y=[soc_min_MWh] * T + [soc_max_MWh] * T,
            fill="toself",
            fillcolor=_PURPLE_FILL,
            line=dict(color="rgba(0,0,0,0)"),
            name=f"Operating range ({soc_min_MWh:.1f} – {soc_max_MWh:.1f} MWh)",
            showlegend=True,
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=hours,
            y=soc_MWh.tolist(),
            mode="lines+markers",
            name="SoC (MWh)",
            line=dict(color=_PURPLE, width=2.5),
            marker=dict(size=5, color=_PURPLE),
            showlegend=True,
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[0, T - 1],
            y=[float(soc_MWh[0]), float(soc_MWh[-1])],
            mode="markers",
            name="Start / End",
            marker=dict(
                size=11,
                color=[_GREEN, _GOLD],
                symbol=["circle", "square"],
                line=dict(color=_NAVY, width=1.5),
            ),
            showlegend=True,
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=soc_min_MWh,
        line_dash="dot",
        line_color=_GOLD,
        line_width=1,
        annotation_text=f"Min {soc_min_MWh:.1f} MWh",
        annotation_font_color=_GOLD,
        annotation_font_size=9,
        annotation_position="bottom right",
        row=3,
        col=1,
    )
    fig.add_hline(
        y=soc_max_MWh,
        line_dash="dot",
        line_color=_TEAL,
        line_width=1,
        annotation_text=f"Max {soc_max_MWh:.1f} MWh",
        annotation_font_color=_TEAL,
        annotation_font_size=9,
        annotation_position="top right",
        row=3,
        col=1,
    )

    # ── Global layout ─────────────────────────────────────────────────────
    axis_common = dict(
        gridcolor="rgba(30,58,95,0.33)",
        zerolinecolor="rgba(30,58,95,0.33)",
        color=_GRAY,
        showline=True,
        linecolor=_BORDER,
    )

    fig.update_layout(
        **{
            k: v
            for k, v in _BASE_LAYOUT.items()
            if k not in ("xaxis", "yaxis", "margin", "legend")
        },
        title=dict(
            text=(
                f"Battery Arbitrage Strategy  ·  "
                f"Charged {total_charge:.2f} MWh  ·  Discharged {total_discharge:.2f} MWh  ·  "
                f"Round-trip {efficiency:.1f}%  ·  Objective ${objective_cost:.2f}"
            ),
            **_TITLE_STYLE,
        ),
        barmode="relative",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=_BORDER,
            borderwidth=1,
            font=dict(size=10, color=_GRAY),
            orientation="h",
            yanchor="top",
            y=-0.06,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=60, r=24, t=80, b=80),
        height=820,
    )

    for i in range(1, 4):
        fig.update_xaxes(**axis_common, row=i, col=1)
        fig.update_yaxes(**axis_common, row=i, col=1)

    for ann in fig.layout.annotations:
        ann.font.color = _GRAY
        ann.font.size = 11
        ann.font.family = _FONT

    fig.update_xaxes(title_text="Hour of Day", row=3, col=1)
    fig.update_yaxes(title_text="Price ($/MWh)", row=1, col=1)
    fig.update_yaxes(title_text="Power (MW)", row=2, col=1)
    fig.update_yaxes(title_text="SoC (MWh)", row=3, col=1)

    return fig
