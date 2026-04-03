import sys

sys.path.append("./Agentics_Energy")
sys.path.append("./Agentics_Energy/agentic_energy")
sys.path.append("./src")
sys.path.append("./src/vis")

import dash
from datetime import datetime, timedelta
from dash import dcc, html, Input, Output, State, callback, no_update, ctx
import dash_bootstrap_components as dbc

from agentic_energy.schemas import BatteryParams, DayInputs, SolveRequest
from agentic_energy.milp import milp_mcp_server
from agentic_energy.data_utils import run_forecast_step
import vis_adj

REGIONS = [
    "CAPITL", 
    "CENTRL", 
    "DUNWOD",
    "GENESE",
    "H_Q",     # PROXY ZONE
    "HUD_VL",
    "LONGIL",
    "MHK_VL",
    "MILLWD",
    "NORTH",
    "NPX",    # PROXY ZONE
    "NYC",
    "O_H",    # PROXY ZONE
    "PJM",    # PROXY ZONE
    "WEST",
]
FORECAST_TYPES = ["LSTM", "RF"]
DATE_MIN = "2025-01-01"
DATE_MAX = "2025-12-31"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="BoroughWatt",
)

sidebar = dbc.Card(
    [
        html.H5("Battery Parameters", className="card-title mb-3"),
        dbc.Label("Capacity (MWh)"),
        dbc.Input(
            id="cap", type="number", value=20, min=0.1, step=0.1, className="mb-2"
        ),
        dbc.Label("Initial SoC"),
        dcc.Slider(
            id="soc_init",
            min=0,
            max=1,
            step=0.01,
            value=0.5,
            marks={0: "0", 0.5: "0.5", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        dbc.Label("Min SoC"),
        dcc.Slider(
            id="soc_min",
            min=0,
            max=1,
            step=0.01,
            value=0,
            marks={0: "0", 0.5: "0.5", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        dbc.Label("Max SoC"),
        dcc.Slider(
            id="soc_max",
            min=0,
            max=1,
            step=0.01,
            value=1,
            marks={0: "0", 0.5: "0.5", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        dbc.Label("Max Charge (MW)"),
        dbc.Input(
            id="cmax", type="number", value=5, min=0.1, step=0.1, className="mb-2"
        ),
        dbc.Label("Max Discharge (MW)"),
        dbc.Input(
            id="dmax", type="number", value=5, min=0.1, step=0.1, className="mb-2"
        ),
        dbc.Label("Charge Efficiency (η_c)"),
        dcc.Slider(
            id="eta_c",
            min=0.5,
            max=1,
            step=0.01,
            value=0.95,
            marks={0.5: "0.5", 0.75: "0.75", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        dbc.Label("Discharge Efficiency (η_d)"),
        dcc.Slider(
            id="eta_d",
            min=0.5,
            max=1,
            step=0.01,
            value=0.95,
            marks={0.5: "0.5", 0.75: "0.75", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        dbc.Label("SoC Target"),
        dcc.Slider(
            id="soc_target",
            min=0,
            max=1,
            step=0.01,
            value=0.5,
            marks={0: "0", 0.5: "0.5", 1: "1"},
            tooltip={"placement": "bottom"},
        ),
        html.Hr(),
        html.H5("Market / Forecast", className="card-title mb-3"),
        dbc.Label("Region"),
        dcc.Dropdown(
            id="region",
            options=[{"label": r, "value": r} for r in REGIONS],
            value="CAPITL",
            clearable=False,
            className="mb-2",
        ),
        html.Div(
            [
                dbc.Label("Date", className="mb-0"),
                dbc.Button(
                    "▶", id="play_btn", size="sm", color="success", outline=True
                ),
            ],
            className="d-flex align-items-center justify-content-between mb-1",
        ),
        dbc.Input(
            id="date_str",
            type="date",
            value="2025-01-01",
            min=DATE_MIN,
            max=DATE_MAX,
            className="mb-2",
        ),
        dbc.Label("Forecast Type"),
        dcc.Dropdown(
            id="forecast_type",
            options=[{"label": f, "value": f} for f in FORECAST_TYPES],
            value="LSTM",
            clearable=False,
            className="mb-2",
        ),
        html.Hr(),
        dbc.Button(
            "Run Optimization", id="run_btn", color="primary", className="w-100"
        ),
        html.Div(id="status_msg", className="mt-2 text-muted small"),
    ],
    body=True,
    className="h-100",
    style={"overflowY": "auto"},
)

content = dbc.Col(
    [
        dbc.Spinner(
            [
                dcc.Graph(id="fig_forecast", style={"height": "320px"}),
                dcc.Graph(id="fig_soc", style={"height": "380px"}),
                dcc.Graph(id="fig_arbitrage", style={"height": "780px"}),
            ],
            color="primary",
        )
    ]
)

app.layout = dbc.Container(
    [
        dcc.Store(id="play_store", data=False),
        dcc.Interval(id="date_interval", interval=1000, disabled=True),
        dbc.Row(
            dbc.Col(
                html.H3(
                    "BoroughWatt - We Empower Your Energy Decisions", className="my-3"
                )
            )
        ),
        dbc.Row(
            [
                dbc.Col(
                    sidebar,
                    width=3,
                    style={"height": "90vh", "position": "sticky", "top": "1rem"},
                ),
                dbc.Col(content, width=9),
            ],
            align="start",
        ),
    ],
    fluid=True,
)


@callback(
    Output("play_store", "data"),
    Input("play_btn", "n_clicks"),
    State("play_store", "data"),
    prevent_initial_call=True,
)
def toggle_play(n_clicks, is_playing):
    return not is_playing


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


@callback(
    Output("fig_forecast", "figure"),
    Output("fig_soc", "figure"),
    Output("fig_arbitrage", "figure"),
    Output("status_msg", "children"),
    Output("date_str", "value"),
    Input("run_btn", "n_clicks"),
    Input("date_interval", "n_intervals"),
    State("date_str", "value"),
    State("play_store", "data"),
    State("cap", "value"),
    State("soc_init", "value"),
    State("soc_min", "value"),
    State("soc_max", "value"),
    State("cmax", "value"),
    State("dmax", "value"),
    State("eta_c", "value"),
    State("eta_d", "value"),
    State("soc_target", "value"),
    State("region", "value"),
    State("forecast_type", "value"),
    prevent_initial_call=True,
)

def run_optimization(
    n_clicks,
    n_intervals,
    date_str,
    is_playing,
    cap,
    soc_init,
    soc_min,
    soc_max,
    cmax,
    dmax,
    eta_c,
    eta_d,
    soc_target,
    region,
    forecast_type,
):
    if ctx.triggered_id == "date_interval":
        if not is_playing:
            raise dash.exceptions.PreventUpdate
        next_d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
        if next_d > datetime.strptime(DATE_MAX, "%Y-%m-%d"):
            raise dash.exceptions.PreventUpdate
        date_str = next_d.strftime("%Y-%m-%d")
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

    day_inputs, actual_df, forecast_df, forecast_plot = run_forecast_step(
        region=region,
        date_str=date_str,
        forecast_type=forecast_type,
        forecast_plot_path="./plots/price_forecast.png",
    )
    if day_inputs is None:
        raise dash.exceptions.PreventUpdate

    solver = "MILP"
    solve_request = SolveRequest(
        battery=battery_params,
        day=day_inputs,
        solver=solver,
        solver_opts=None,
    )
    solve_response = milp_mcp_server.solve_daily_milp(
        batt=battery_params,
        day=day_inputs,
        solver="GUROBI",
        solver_opts=None,
    )

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

    status = f"Done — {region} · {date_str} · {forecast_type} · objective: ${solve_response.objective_cost:.2f}"
    return fig_forecast, fig_soc, fig_arbitrage, status, date_str


if __name__ == "__main__":
    app.run(debug=True, port=8050)
