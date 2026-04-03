"""
BorrowWatts — NYC MultiFamily P2P Energy Platform
Multi-page Dash app:
  /           → Home page
  /how        → How It Works  (P2P animation)
  /battery    → Battery Arbitrage Optimizer
Run: python app.py  →  http://127.0.0.1:8050
"""

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# ── Colour palette ─────────────────────────────────────────────────────────
TEAL, NAVY, GOLD   = "#10c9a0", "#0a1223", "#f5a623"
CORAL, GREEN, SKY  = "#ff6b6b", "#2dcb7f", "#38bdf8"
PURPLE, GRAY, WHITE= "#8b5cf6", "#9ca3af", "#ffffff"
FONT  = "'DM Sans','Nunito Sans',sans-serif"
MONO  = "'Space Mono','Courier New',monospace"

# ── App (use_pages=True enables file-based routing in pages/) ──────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width,initial-scale=1"}],
    title="BorrowWatts — NYC Energy",
)
server = app.server   # expose for gunicorn / deployment


# ── Shared nav bar ─────────────────────────────────────────────────────────
def badge(text, color=TEAL):
    return html.Span(text, style={
        "background": f"{color}22", "color": color, "fontSize": "0.6rem",
        "fontWeight": 800, "padding": "2px 9px", "borderRadius": "20px",
        "border": f"1px solid {color}44", "letterSpacing": "0.08em",
    })


nav = html.Nav(style={
    "position": "fixed", "top": 0, "left": 0, "right": 0, "zIndex": 999,
    "display": "flex", "alignItems": "center", "justifyContent": "space-between",
    "padding": "0 2.5rem", "height": "62px",
    "background": "rgba(255,255,255,0.95)", "backdropFilter": "blur(12px)",
    "borderBottom": "1.5px solid #E5E7EB",
    "boxShadow": "0 1px 8px rgba(0,0,0,0.06)",
}, children=[
    # Logo → home
    dcc.Link(html.Div([
        html.Span("Borrow", style={"color": "#0B1F3A", "fontFamily": MONO,
                                   "fontWeight": 900, "fontSize": "1.38rem",
                                   "letterSpacing": "-0.02em"}),
        html.Span("Watts",  style={"color": "#0DB8A3", "fontFamily": MONO,
                                   "fontWeight": 900, "fontSize": "1.38rem",
                                   "letterSpacing": "-0.02em"}),
        badge("NYC"),
    ], style={"display": "flex", "alignItems": "center", "gap": "4px"}), href="/"),

    # Nav links
    html.Div([
        dcc.Link("Home",         href="/",        className="nav-link"),
        dcc.Link("How It Works", href="/how",     className="nav-link"),
        dcc.Link("Battery App",  href="/battery", className="nav-link"),
    ], style={"display": "flex", "gap": "2rem"}),

    html.Button("Get Early Access", style={
        "background": "#0DB8A3", "color": "white", "border": "none",
        "borderRadius": "4px", "padding": "9px 22px",
        "fontSize": "0.8rem", "fontWeight": 800,
        "letterSpacing": "0.06em", "cursor": "pointer",
    }),
])


# ── Root layout ────────────────────────────────────────────────────────────
app.layout = html.Div(
    style={"fontFamily": FONT, "background": NAVY, "color": "#e2e8f0"},
    children=[
        nav,
        dash.page_container,  # active page renders here
    ],
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
