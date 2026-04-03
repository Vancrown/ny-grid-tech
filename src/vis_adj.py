import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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

    fig = go.Figure()

    # Shaded low-price zones
    for i, price in enumerate(prices):
        if price <= low_threshold:
            fig.add_vrect(
                x0=time_labels[i] - dt_hours / 2,
                x1=time_labels[i] + dt_hours / 2,
                fillcolor="green",
                opacity=0.15,
                layer="below",
                line_width=0,
            )

    # Shaded high-price zones
    for i, price in enumerate(prices):
        if price >= high_threshold:
            fig.add_vrect(
                x0=time_labels[i] - dt_hours / 2,
                x1=time_labels[i] + dt_hours / 2,
                fillcolor="red",
                opacity=0.15,
                layer="below",
                line_width=0,
            )

    # Price line
    fig.add_trace(
        go.Scatter(
            x=time_labels,
            y=prices,
            mode="lines+markers",
            name="Forecasted Price",
            line=dict(color="#2E86AB", width=2.5),
            marker=dict(size=5),
        )
    )

    # Mean price line
    fig.add_hline(
        y=mean_price,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Mean ${mean_price:.2f}/MWh",
        annotation_position="top right",
    )

    num_low = sum(1 for p in prices if p <= low_threshold)
    num_high = sum(1 for p in prices if p >= high_threshold)

    fig.update_layout(
        title=dict(
            text=(
                f"Price Forecast — Spread: ${price_spread:.2f}/MWh "
                f"(${min_price:.2f}–${max_price:.2f}) | "
                f"Low zones: {num_low} (charge) · High zones: {num_high} (discharge)"
            ),
            font=dict(size=13),
        ),
        xaxis_title=xlabel,
        yaxis_title="Price ($/MWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=20, t=60, b=50),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")

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

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=hours,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="Price",
            increasing_line_color="tab:green" if False else "#26a69a",
            decreasing_line_color="#ef5350",
        ),
        secondary_y=False,
    )

    # Charge markers (triangle up)
    charge_idx = [i for i, a in enumerate(actions) if a > 0]
    if charge_idx:
        fig.add_trace(
            go.Scatter(
                x=hours[charge_idx],
                y=closes[charge_idx],
                mode="markers",
                name="Charge",
                marker=dict(symbol="triangle-up", size=10, color="#26a69a"),
            ),
            secondary_y=False,
        )

    # Discharge markers (triangle down)
    discharge_idx = [i for i, a in enumerate(actions) if a < 0]
    if discharge_idx:
        fig.add_trace(
            go.Scatter(
                x=hours[discharge_idx],
                y=closes[discharge_idx],
                mode="markers",
                name="Discharge",
                marker=dict(symbol="triangle-down", size=10, color="#ef5350"),
            ),
            secondary_y=False,
        )

    # SoC line
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=soc_MWh,
            mode="lines+markers",
            name="SoC (MWh)",
            line=dict(color="#9B59B6", width=2),
            marker=dict(size=4),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Price Candles & Battery State-of-Charge",
        xaxis_title="Hour",
        xaxis_rangeslider_visible=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=60, t=60, b=50),
    )
    fig.update_yaxes(
        title_text="Price ($/MWh)",
        secondary_y=False,
        showgrid=True,
        gridcolor="#eeeeee",
    )
    fig.update_yaxes(title_text="State of Charge (MWh)", secondary_y=True)

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
    charge_MW = np.array(charge_MW) if charge_MW else np.zeros(len(prices))
    discharge_MW = np.array(discharge_MW) if discharge_MW else np.zeros(len(prices))
    soc = np.array(soc)

    T = len(prices)
    hours = list(range(T))

    soc_MWh = soc[:-1] * capacity

    mean_price = float(np.mean(prices))
    std_price = float(np.std(prices))
    low_threshold = mean_price - 0.25 * std_price
    high_threshold = mean_price + 0.25 * std_price

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "Price Signals: Green = Low (Charge), Red = High (Discharge)",
            "Battery Operations: Positive = Discharging, Negative = Charging",
            "Battery Energy Level: Must Stay Within Operating Bounds",
        ),
        vertical_spacing=0.08,
    )

    # --- Panel 1: Prices ---
    # Shaded zones
    for i, price in enumerate(prices):
        if price <= low_threshold:
            fig.add_vrect(
                x0=i - 0.4,
                x1=i + 0.4,
                fillcolor="green",
                opacity=0.2,
                layer="below",
                line_width=0,
                row=1,
                col=1,
            )
        elif price >= high_threshold:
            fig.add_vrect(
                x0=i - 0.4,
                x1=i + 0.4,
                fillcolor="red",
                opacity=0.2,
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
            name="Electricity Price",
            line=dict(color="#2E86AB", width=2.5),
            marker=dict(size=5),
            showlegend=True,
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=mean_price,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Mean ${mean_price:.2f}",
        annotation_position="top right",
        row=1,
        col=1,
    )

    # --- Panel 2: Charge / Discharge bars ---
    fig.add_trace(
        go.Bar(
            x=hours,
            y=discharge_MW.tolist(),
            name="Discharge (MW)",
            marker_color="#E63946",
            opacity=0.8,
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
            marker_color="#06A77D",
            opacity=0.8,
            showlegend=True,
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=dmax_MW,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Max Discharge {dmax_MW}MW",
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-cmax_MW,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Max Charge {cmax_MW}MW",
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_color="black", line_width=1, row=2, col=1)

    # --- Panel 3: SoC ---
    soc_min_MWh = soc_min * capacity
    soc_max_MWh = soc_max * capacity

    fig.add_trace(
        go.Scatter(
            x=hours + hours[::-1],
            y=[soc_min_MWh] * T + [soc_max_MWh] * T,
            fill="toself",
            fillcolor="rgba(150,150,150,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"Operating Range ({soc_min_MWh:.1f}–{soc_max_MWh:.1f} MWh)",
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
            name="SoC",
            line=dict(color="#9B59B6", width=3),
            marker=dict(size=6),
            showlegend=True,
        ),
        row=3,
        col=1,
    )
    fig.add_hline(
        y=soc_min_MWh,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Min {soc_min_MWh:.1f}MWh",
        row=3,
        col=1,
    )
    fig.add_hline(
        y=soc_max_MWh,
        line_dash="dash",
        line_color="darkblue",
        annotation_text=f"Max {soc_max_MWh:.1f}MWh",
        row=3,
        col=1,
    )

    # Start / end markers
    fig.add_trace(
        go.Scatter(
            x=[0, T - 1],
            y=[float(soc_MWh[0]), float(soc_MWh[-1])],
            mode="markers",
            name="Start / End SoC",
            marker=dict(size=12, color=["green", "red"], symbol=["circle", "square"]),
            showlegend=True,
        ),
        row=3,
        col=1,
    )

    total_charge = float(np.sum(charge_MW)) * dt_hours
    total_discharge = float(np.sum(discharge_MW)) * dt_hours
    efficiency = (total_discharge / total_charge * 100) if total_charge > 0 else 0.0

    fig.update_layout(
        title=dict(
            text=(
                f"Battery Arbitrage Strategy | "
                f"Charged: {total_charge:.2f} MWh · Discharged: {total_discharge:.2f} MWh · "
                f"Efficiency: {efficiency:.1f}% · Objective: ${objective_cost:.2f}"
            ),
            font=dict(size=13),
        ),
        barmode="relative",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5
        ),
        margin=dict(l=60, r=20, t=90, b=80),
        height=750,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_xaxes(title_text="Hour of Day", row=3, col=1)
    fig.update_yaxes(title_text="Price ($/MWh)", row=1, col=1)
    fig.update_yaxes(title_text="Power (MW)", row=2, col=1)
    fig.update_yaxes(title_text="SoC (MWh)", row=3, col=1)

    return fig
