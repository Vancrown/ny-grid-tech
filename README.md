# BoroughWatt — Battery Arbitrage Dashboard

An interactive Dash web application that optimises battery energy storage dispatch against day-ahead electricity prices using a MILP solver (Gurobi / CVXPY).

---

## How to Run

```bash
# 1. activate the virtual environment
source .venv/bin/activate   # or: uv venv && uv sync

# 2. launch the dashboard
python app.py
```

Open <http://127.0.0.1:8051> in your browser.

> The app binds to port **8051** and runs in debug mode by default.

---

## Dashboard Overview

The UI is divided into a **left sidebar** (inputs) and a **right panel** (three plots).  
Click **Run Optimization** to solve the battery dispatch for the selected day, or press **▶** to auto-advance through days one at a time.

---

## Adjustable Inputs

### Battery Parameters

| Input                      | ID           | Default | Description                                            |
| -------------------------- | ------------ | ------- | ------------------------------------------------------ |
| Capacity (MWh)             | `cap`        | 20      | Total usable energy storage capacity                   |
| Initial SoC                | `soc_init`   | 0.5     | State-of-Charge at the start of the day (fraction 0–1) |
| Min SoC                    | `soc_min`    | 0.0     | Lower SoC bound — prevents full depletion              |
| Max SoC                    | `soc_max`    | 1.0     | Upper SoC bound — prevents overcharge                  |
| Max Charge (MW)            | `cmax`       | 5       | Maximum power the battery can absorb per interval      |
| Max Discharge (MW)         | `dmax`       | 5       | Maximum power the battery can deliver per interval     |
| Charge Efficiency (η_c)    | `eta_c`      | 0.95    | Round-trip charge efficiency (0.5–1)                   |
| Discharge Efficiency (η_d) | `eta_d`      | 0.95    | Round-trip discharge efficiency (0.5–1)                |
| SoC Target                 | `soc_target` | 0.5     | Desired end-of-day SoC (soft target in objective)      |

### Market / Forecast

| Input         | ID              | Default    | Description                                          |
| ------------- | --------------- | ---------- | ---------------------------------------------------- |
| Region        | `region`        | ITALY      | Energy market region (currently ITALY)               |
| Date          | `date_str`      | 2018-01-01 | Simulation date (range: 2018-01-01 – 2019-12-31)     |
| Forecast Type | `forecast_type` | LSTM       | Price forecast model: `LSTM` or `RF` (Random Forest) |

---

## Plots

### 1 — Price Forecast (`fig_forecast`)

Displays the hourly day-ahead electricity price forecast for the selected date.

- **Blue line** — forecasted price ($/MWh)
- **Dashed gray line** — daily mean price
- **Green shading** — low-price zones (≤ mean − 0.3σ) — optimal charging windows
- **Red shading** — high-price zones (≥ mean + 0.3σ) — optimal discharging windows
- Title summarises price spread, min/max, and the number of low/high zones

### 2 — Price Candles & State-of-Charge (`fig_soc`)

Combines a candlestick price chart with the battery SoC on a dual-axis layout.

- **Candlesticks** — open/close/high/low constructed from consecutive hourly prices; green = price rising, red = price falling
- **▲ Green triangles** — hours when the optimizer charges the battery
- **▼ Red triangles** — hours when the optimizer discharges the battery
- **Purple line (right axis)** — battery SoC in MWh over the day

### 3 — Arbitrage Explanation (`fig_arbitrage`)

A three-panel stacked chart that explains the full dispatch strategy.

| Panel                           | Content                                                                                                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Top — Price Signals**         | Electricity price line with green/red zone shading (same thresholds as Plot 1). Dashed mean line included.                                                            |
| **Middle — Battery Operations** | Bar chart of power flow: positive (red) = discharge MW, negative (green) = charge MW. Dashed lines mark the max charge/discharge power limits.                        |
| **Bottom — Energy Level**       | SoC trajectory in MWh. Gray band = operating range [SoC_min, SoC_max]. Orange/blue dashed lines mark the hard bounds. Green circle = start SoC, red square = end SoC. |

The chart title reports total energy charged, discharged, round-trip efficiency, and the MILP objective value ($).

---

## Application Logic

```
User inputs
    │
    ▼
run_forecast_step()          ← loads CSV data, applies LSTM or RF forecast model
    │ day_inputs (prices, dt)
    ▼
milp_mcp_server.solve_daily_milp()   ← CVXPY / Gurobi MILP solver
    │ charge_MW[], discharge_MW[], soc[], objective_cost
    ▼
vis_adj plot functions       ← returns Plotly figures
    │
    ▼
Dash callback → browser
```

Play mode (▶ button) fires a 1-second interval that increments the date by one day and re-runs the full pipeline automatically.

---

## Dependency Files

| File                                                     | Role                                                                                                 |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `src/vis_adj.py`                                         | All three Plotly figure builders                                                                     |
| `Agentics_Energy/agentic_energy/schemas.py`              | Pydantic data models (`BatteryParams`, `DayInputs`, `SolveRequest`, `SolveResponse`, `PlotResponse`) |
| `Agentics_Energy/agentic_energy/milp/milp_mcp_server.py` | MILP formulation and Gurobi/CVXPY solve logic                                                        |
| `Agentics_Energy/agentic_energy/data_utils.py`           | `run_forecast_step` — data loading + price forecast pipeline                                         |
| `Agentics_Energy/agentic_energy/data_loader.py`          | `EnergyDataLoader` — reads regional CSV files                                                        |
| `Agentics_Energy/agentic_energy/mcp_clients.py`          | MCP client for invoking the forecast server                                                          |

---

## Python Packages

| Package                     | Purpose                                                         |
| --------------------------- | --------------------------------------------------------------- |
| `dash`                      | Web framework and reactive callbacks                            |
| `dash-bootstrap-components` | Bootstrap-styled layout components                              |
| `plotly`                    | Interactive charts                                              |
| `cvxpy`                     | MILP problem formulation                                        |
| `gurobipy`                  | Gurobi solver backend (licence required)                        |
| `numpy`                     | Numerical operations in plot and solver code                    |
| `pandas`                    | Tabular data handling in the data loader                        |
| `pydantic`                  | Schema validation for battery and day parameters                |
| `mcp`                       | Model Context Protocol server/client transport                  |
| `crewai-tools`              | MCP server adapter used by the forecast client                  |
| `agentics-py`               | Internal agentics framework (`AG`) used by MILP and data loader |
| `python-dotenv`             | `.env` loading in `data_loader.py`                              |

Full pinned dependency list is in [`pyproject.toml`](pyproject.toml).

---

## Data

Historical day-ahead price CSVs live in `Agentics_Energy/agentic_energy/data/`.  
The dashboard currently supports the **ITALY** region over **2018–2019**.

> Do not modify the CSV files — they are read-only source data.
