"""
pages/battery.py — BorrowWatts Battery Arbitrage Optimizer
Uses the real Gurobi MILP engine from agentic_energy + NYISO forecast data.
"""

import sys
sys.path.append("./Agentics_Energy")
sys.path.append("./Agentics_Energy/agentic_energy")
sys.path.append("./src")
sys.path.append("./src/vis")

from datetime import datetime, timedelta

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback, ctx

from agentic_energy.schemas import BatteryParams
from agentic_energy.milp import milp_mcp_server
from agentic_energy.data_utils import run_forecast_step
import vis_adj

dash.register_page(__name__, path="/battery", name="Battery App")

# ── Palette (keep in sync with app.py) ────────────────────────────────────
TEAL, NAVY, GOLD   = "#10c9a0", "#0a1223", "#f5a623"
CORAL, GREEN, SKY  = "#ff6b6b", "#2dcb7f", "#38bdf8"
PURPLE, GRAY, WHITE= "#8b5cf6", "#9ca3af", "#ffffff"
MONO  = "'Space Mono','Courier New',monospace"
FONT  = "'DM Sans','Nunito Sans',sans-serif"

REGIONS = [
    "CAPITL","CENTRL","DUNWOD","GENESE",
    "H_Q","HUD_VL","LONGIL","MHK_VL","MILLWD",
    "NORTH","NPX","NYC","O_H","PJM","WEST",
]
FORECAST_TYPES = ["LSTM", "RF"]
DATE_MIN = "2025-01-01"
DATE_MAX = "2025-12-31"


# ══════════════════════════════════════════════════════════════════════════
# HELPER: labelled slider row
# ══════════════════════════════════════════════════════════════════════════
def slider_block(label, sid, mn, mx, val, step):
    return html.Div([
        html.Div([
            html.Span(label,    style={"color": GRAY, "fontSize": "0.8rem"}),
            html.Span(str(val), id=f"{sid}-lbl",
                style={"color": TEAL, "fontFamily": MONO,
                       "fontSize": "0.8rem", "fontWeight": 700}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "3px"}),
        dcc.Slider(
            id=sid, min=mn, max=mx, step=step, value=val,
            marks={mn: str(mn), round((mn+mx)/2, 2): str(round((mn+mx)/2, 2)),
                   mx: str(mx)},
            tooltip={"placement": "bottom", "always_visible": False},
        ),
    ], style={"marginBottom": "1rem"})


def num_input(label, sid, val):
    return html.Div([
        html.Span(label, style={"color": GRAY, "fontSize": "0.8rem",
                                "display": "block", "marginBottom": "4px"}),
        dbc.Input(
            id=sid, type="number", value=val, min=0.1, step=0.1,
            style={"background": "#0a1223", "color": WHITE,
                   "border": "1px solid #1e3a5f", "borderRadius": "6px",
                   "fontSize": "0.85rem", "marginBottom": "1rem"},
        ),
    ])


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
sidebar = html.Div([

    html.Div("Battery Parameters", style={
        "fontFamily": MONO, "color": WHITE, "fontWeight": 700,
        "fontSize": "0.93rem", "marginBottom": "1.25rem",
        "borderBottom": "1px solid #1e3a5f", "paddingBottom": "0.7rem",
    }),

    num_input("Capacity (MWh)",    "cap",  20),
    slider_block("Initial SoC",            "soc_init",  0,   1,    0.5,  0.01),
    slider_block("Min SoC",                "soc_min",   0,   1,    0.0,  0.01),
    slider_block("Max SoC",                "soc_max",   0,   1,    1.0,  0.01),
    num_input("Max Charge (MW)",   "cmax",  5),
    num_input("Max Discharge (MW)","dmax",  5),
    slider_block("Charge Efficiency η_c",  "eta_c",     0.5, 1,    0.95, 0.01),
    slider_block("Discharge Efficiency η_d","eta_d",    0.5, 1,    0.95, 0.01),
    slider_block("SoC Target",             "soc_target",0,   1,    0.5,  0.01),

    html.Hr(style={"borderColor": "#1e3a5f", "margin": "1.25rem 0"}),

    html.Div("Market / Forecast", style={
        "fontFamily": MONO, "color": WHITE, "fontWeight": 700,
        "fontSize": "0.93rem", "marginBottom": "1.25rem",
    }),

    html.Span("Region", style={"color": GRAY, "fontSize": "0.8rem",
                               "display": "block", "marginBottom": "4px"}),
    dcc.Dropdown(
        id="region",
        options=[{"label": r, "value": r} for r in REGIONS],
        value="CAPITL", clearable=False,
        className="bw-dropdown",
        style={"marginBottom": "1rem"},
    ),

    html.Div([
        html.Span("Date", style={"color": GRAY, "fontSize": "0.8rem"}),
        dbc.Button("▶", id="play_btn", size="sm", color="success", outline=True,
                   style={"padding": "2px 10px", "fontSize": "0.75rem",
                          "borderColor": TEAL, "color": TEAL}),
    ], style={"display": "flex", "justifyContent": "space-between",
              "alignItems": "center", "marginBottom": "4px"}),
    dbc.Input(
        id="date_str", type="date", value="2025-01-01",
        min=DATE_MIN, max=DATE_MAX,
        style={"background": "#0a1223", "color": WHITE,
               "border": "1px solid #1e3a5f", "borderRadius": "6px",
               "fontSize": "0.85rem", "marginBottom": "1rem"},
    ),

    html.Span("Forecast Type", style={"color": GRAY, "fontSize": "0.8rem",
                                      "display": "block", "marginBottom": "4px"}),
    dcc.Dropdown(
        id="forecast_type",
        options=[{"label": f, "value": f} for f in FORECAST_TYPES],
        value="LSTM", clearable=False,
        className="bw-dropdown",
        style={"marginBottom": "1.25rem"},
    ),

    html.Hr(style={"borderColor": "#1e3a5f", "margin": "0 0 1.25rem"}),

    html.Button("⚡  Run Optimisation", id="run_btn", n_clicks=0, style={
        "width": "100%", "background": TEAL, "color": NAVY, "border": "none",
        "borderRadius": "6px", "padding": "12px", "fontSize": "0.88rem",
        "fontWeight": 800, "cursor": "pointer", "letterSpacing": "0.05em",
    }),

    html.Div(id="status_msg", style={
        "marginTop": "0.75rem", "color": GRAY, "fontSize": "0.75rem",
        "fontFamily": MONO, "lineHeight": "1.6",
    }),

    html.Div([
        html.Div("🔧  Tech Stack", style={
            "fontFamily": MONO, "color": TEAL, "fontSize": "0.7rem",
            "fontWeight": 700, "marginBottom": "0.5rem",
            "letterSpacing": "0.1em",
        }),
        html.Div("Gurobi 11 · MILP · NYISO LBMP API",
            style={"color": GRAY, "fontSize": "0.76rem", "marginBottom": "4px"}),
        html.Div("min  Σ c_t·p_chg_t  −  Σ c_t·p_dis_t",
            style={"color": GRAY, "fontSize": "0.72rem",
                   "fontFamily": MONO, "marginBottom": "3px"}),
        html.Div("s.t. SoC dynamics, power & ramp limits",
            style={"color": GRAY, "fontSize": "0.7rem", "fontFamily": MONO}),
    ], style={
        "background": "#ffffff07", "borderRadius": "8px", "padding": "0.9rem",
        "marginTop": "1rem", "border": "1px solid #1e3a5f33",
    }),

], style={
    "background": "#111827", "border": "1px solid #1e3a5f",
    "borderRadius": "14px", "padding": "1.6rem",
    "height": "100%", "overflowY": "auto",
})


# ══════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════
layout = html.Div([

    # Page header
    html.Section(style={
        "background": NAVY, "paddingTop": "100px", "paddingBottom": "2.5rem",
        "paddingLeft": "2rem", "paddingRight": "2rem",
        "borderBottom": "1px solid #1e3a5f",
    }, children=[
        html.Div([
            html.Div("BATTERY ARBITRAGE OPTIMIZER", style={
                "fontSize": "0.68rem", "letterSpacing": "0.28em",
                "textTransform": "uppercase", "color": TEAL,
                "fontWeight": 700, "marginBottom": "0.65rem",
            }),
            html.H1("Gurobi-powered BESS dispatch.", style={
                "fontFamily": MONO,
                "fontSize": "clamp(1.6rem,4vw,2.8rem)",
                "color": WHITE, "letterSpacing": "-0.02em",
                "marginBottom": "0.75rem",
            }),
            html.P(
                "Select a NYISO region, date and forecast model. "
                "Adjust battery parameters, then hit Run Optimisation — "
                "the exact MILP is solved with Gurobi 11 and results "
                "are displayed in real time.",
                style={"color": GRAY, "fontSize": "0.95rem",
                       "lineHeight": "1.75", "maxWidth": "640px"},
            ),
        ], style={"maxWidth": "1200px", "margin": "0 auto"}),
    ]),

    # App body: sidebar + charts
    html.Section(style={"background": "#0d1728", "padding": "2.5rem 2rem"}, children=[
        html.Div([

            # Sticky sidebar column
            html.Div(sidebar, style={
                "width": "min(300px,100%)", "flexShrink": 0,
                "position": "sticky", "top": "80px",
                "maxHeight": "calc(100vh - 100px)",
            }),

            # Charts column
            dbc.Spinner(html.Div([
                dcc.Graph(id="fig_forecast",
                          config={"displayModeBar": False},
                          style={"height": "320px", "marginBottom": "0.75rem"}),
                dcc.Graph(id="fig_soc",
                          config={"displayModeBar": False},
                          style={"height": "380px", "marginBottom": "0.75rem"}),
                dcc.Graph(id="fig_arbitrage",
                          config={"displayModeBar": False},
                          style={"height": "780px"}),
            ], style={"flex": 1, "minWidth": 0}), color=TEAL),

        ], style={
            "maxWidth": "1200px", "margin": "0 auto",
            "display": "flex", "gap": "1.5rem",
            "alignItems": "flex-start", "flexWrap": "wrap",
        }),
    ]),

    # Hidden Dash stores
    dcc.Store(id="play_store", data=False),
    dcc.Interval(id="date_interval", interval=1000, disabled=True),

    # Footer
    html.Footer(style={
        "background": "#060c16", "padding": "2.5rem 2rem",
        "textAlign": "center", "borderTop": "1px solid #1e3a5f",
    }, children=[
        html.Div([
            html.Span("Borrow", style={"color": WHITE, "fontFamily": MONO, "fontWeight": 900}),
            html.Span("Watts",  style={"color": TEAL,  "fontFamily": MONO, "fontWeight": 900}),
        ], style={"marginBottom": "0.5rem"}),
        html.P("NYC's P2P Energy Trading Platform · © 2025 BorrowWatts Inc.",
            style={"color": GRAY, "fontSize": "0.76rem"}),
        html.P("Built with Dash · Plotly · Gurobi · NYISO API",
            style={"color": "#2a3748", "fontSize": "0.7rem",
                   "marginTop": "4px", "fontFamily": MONO}),
    ]),
])


# ══════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════════════════════════════════

# Live slider value labels
for _sid in ["soc_init", "soc_min", "soc_max", "eta_c", "eta_d", "soc_target"]:
    @callback(Output(f"{_sid}-lbl", "children"), Input(_sid, "value"))
    def _lbl(v):
        return str(round(v, 2))


# Play / pause toggle
@callback(
    Output("play_store", "data"),
    Input("play_btn", "n_clicks"),
    State("play_store", "data"),
    prevent_initial_call=True,
)
def toggle_play(_, is_playing):
    return not is_playing


# Enable / disable date auto-advance interval
@callback(
    Output("date_interval", "disabled"),
    Output("play_btn", "children"),
    Input("play_store", "data"),
    Input("date_str", "value"),
)
def sync_interval(is_playing, date_str):
    if is_playing and date_str < DATE_MAX:
        return False, "⏸"
    return True, "▶"


# Main optimisation
@callback(
    Output("fig_forecast",  "figure"),
    Output("fig_soc",       "figure"),
    Output("fig_arbitrage", "figure"),
    Output("status_msg",    "children"),
    Output("date_str",      "value"),
    Input("run_btn",        "n_clicks"),
    Input("date_interval",  "n_intervals"),
    State("date_str",       "value"),
    State("play_store",     "data"),
    State("cap",            "value"),
    State("soc_init",       "value"),
    State("soc_min",        "value"),
    State("soc_max",        "value"),
    State("cmax",           "value"),
    State("dmax",           "value"),
    State("eta_c",          "value"),
    State("eta_d",          "value"),
    State("soc_target",     "value"),
    State("region",         "value"),
    State("forecast_type",  "value"),
    prevent_initial_call=True,
)
def run_optimization(
    n_clicks, n_intervals,
    date_str, is_playing,
    cap, soc_init, soc_min, soc_max,
    cmax, dmax, eta_c, eta_d, soc_target,
    region, forecast_type,
):
    # Advance date in playback mode
    if ctx.triggered_id == "date_interval":
        if not is_playing:
            raise dash.exceptions.PreventUpdate
        next_d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
        if next_d > datetime.strptime(DATE_MAX, "%Y-%m-%d"):
            raise dash.exceptions.PreventUpdate
        date_str = next_d.strftime("%Y-%m-%d")

    # Build battery params schema
    battery_params = BatteryParams(
        capacity_MWh=cap,
        soc_init=soc_init,
        soc_min=soc_min,
        soc_max=soc_max,
        cmax_MW=cmax,
        dmax_MW=dmax,
        eta_c=eta_c,
        eta_d=eta_d,
        soc_target=soc_target,
    )

    # Run forecast
    day_inputs, actual_df, forecast_df, forecast_plot = run_forecast_step(
        region=region,
        date_str=date_str,
        forecast_type=forecast_type,
        forecast_plot_path="./plots/price_forecast.png",
    )
    if day_inputs is None:
        raise dash.exceptions.PreventUpdate

    # Solve MILP with Gurobi
    solve_response = milp_mcp_server.solve_daily_milp(
        batt=battery_params,
        day=day_inputs,
        solver="GUROBI",
        solver_opts=None,
    )

    # Build Plotly figures via vis_adj
    fig_forecast = vis_adj.plot_price_forecast_fig(
        prices=day_inputs.prices_buy,
        dt_hours=day_inputs.dt_hours,
    )
    fig_soc = vis_adj.plot_price_soc_fig(
        prices=day_inputs.prices_buy,
        capacity=battery_params.capacity_MWh,
        soc=solve_response.soc,
        decision=solve_response.decision,
    )
    fig_arbitrage = vis_adj.plot_arbitrage_explanation_fig(
        prices=day_inputs.prices_buy,
        capacity=battery_params.capacity_MWh,
        soc_min=battery_params.soc_min,
        soc_max=battery_params.soc_max,
        cmax_MW=battery_params.cmax_MW,
        dmax_MW=battery_params.dmax_MW,
        dt_hours=day_inputs.dt_hours,
        charge_MW=solve_response.charge_MW,
        discharge_MW=solve_response.discharge_MW,
        soc=solve_response.soc,
        objective_cost=solve_response.objective_cost,
    )

    status = (
        f"✅ {region} · {date_str} · {forecast_type} · "
        f"objective: ${solve_response.objective_cost:.2f}"
    )
    return fig_forecast, fig_soc, fig_arbitrage, status, date_str
