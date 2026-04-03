import sys

sys.path.append("./Agentics_Energy")
sys.path.append("./Agentics_Energy/agentic_energy")
sys.path.append("./src")

import random
import numpy as np
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

from agentic_energy.schemas import BatteryParams, DayInputs, SolveRequest
from agentic_energy.milp import milp_mcp_server
from agentic_energy.data_utils import run_forecast_step
import vis_adj

# ── Colour palette ────────────────────────────────────────────────────────────
TEAL, NAVY, GOLD = "#10c9a0", "#0a1223", "#f5a623"
CORAL, GREEN, SKY = "#ff6b6b", "#2dcb7f", "#38bdf8"
PURPLE, GRAY, WHITE = "#8b5cf6", "#9ca3af", "#ffffff"
FONT = "'Inter','Roboto',sans-serif"
MONO = "Arial,sans-serif"

REGIONS = [
    "CAPITL",
    "CENTRL",
    "DUNWOD",
    "GENESE",
    "H_Q",
    "HUD_VL",
    "LONGIL",
    "MHK_VL",
    "MILLWD",
    "NORTH",
    "NPX",
    "NYC",
    "O_H",
    "PJM",
    "WEST",
]
FORECAST_TYPES = ["LSTM", "RF"]
DATE_MIN = "2025-01-01"
DATE_MAX = "2025-12-31"


# ══════════════════════════════════════════════════════════════════════════════
# SVG GENERATORS
# ══════════════════════════════════════════════════════════════════════════════
def nyc_skyline():
    rng = random.Random(99)
    buildings = [
        (0, 210, 65, 270, "#0c1a2b"),
        (60, 175, 85, 305, "#0d1d30"),
        (140, 155, 52, 325, "#0e2035"),
        (187, 180, 72, 300, "#0c1a2b"),
        (254, 158, 57, 322, "#0d1d30"),
        (306, 138, 48, 342, "#0e2035"),
        (349, 162, 95, 318, "#0f2136"),
        (439, 125, 62, 355, "#0c1a2b"),
        (496, 148, 82, 332, "#0d1d30"),
        (573, 138, 57, 342, "#0c1a2b"),
        (625, 170, 78, 310, "#0f2136"),
        (698, 152, 47, 328, "#0d1d30"),
        (740, 133, 105, 347, "#0c1a2b"),
        (840, 165, 62, 315, "#0e2035"),
        (897, 143, 83, 337, "#0f2136"),
        (975, 128, 57, 352, "#0c1a2b"),
        (1027, 158, 93, 322, "#0d1d30"),
        (1115, 138, 62, 342, "#0c1a2b"),
        (1172, 153, 82, 327, "#0e2035"),
        (1249, 122, 57, 358, "#0f2136"),
        (1301, 148, 105, 332, "#0c1a2b"),
        (1401, 158, 72, 322, "#0d1d30"),
        (1468, 143, 62, 337, "#0c1a2b"),
        (1525, 132, 82, 348, "#0e2035"),
        (102, 105, 47, 375, "#0f263f"),
        (149, 94, 32, 386, "#0f263f"),
        (378, 82, 62, 398, "#102746"),
        (384, 68, 22, 412, "#102746"),
        (725, 72, 72, 408, "#0f263f"),
        (757, 56, 20, 424, "#0f263f"),
        (1008, 88, 57, 392, "#102746"),
        (1290, 92, 67, 388, "#0f263f"),
    ]
    rect_els = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" rx="1"/>'
        for x, y, w, h, c in buildings
    )
    win_els = []
    for x, y, w, h, _ in buildings[6:]:
        cols = max(1, w // 13)
        rows = max(1, (480 - y) // 16)
        for r in range(rows):
            for cl in range(cols):
                wx, wy = x + 3 + cl * 12, y + 4 + r * 15
                b = rng.random()
                if b < 0.32:
                    continue
                kw_pos = rng.random() > 0.35
                col = "#f5d97a" if kw_pos else "#f8706a"
                win_els.append(
                    f'<rect x="{wx}" y="{wy}" width="8" height="11" '
                    f'fill="{col}" rx="1" opacity="{min(0.92, b + 0.1):.2f}"/>'
                )
    labels = [
        (130, 148, "+8.4 kW", True),
        (398, 115, "+12 kW", True),
        (748, 102, "+6 kW", True),
        (230, 188, "-3.1 kW", False),
        (585, 172, "+4.8 kW", True),
        (1028, 126, "-1.9 kW", False),
        (862, 158, "+9.2 kW", True),
        (1312, 130, "+5 kW", True),
    ]
    lbl_els = "".join(
        f'<g transform="translate({lx},{ly})">'
        f'<rect x="-3" y="-13" width="{len(txt)*7+8}" height="17" rx="4" fill="{NAVY}" opacity="0.88"/>'
        f'<text font-family="Arial,sans-serif" font-size="10" fill="{TEAL if pos else CORAL}" font-weight="700">{txt}</text>'
        f"</g>"
        for lx, ly, txt, pos in labels
    )
    stars = "".join(
        f'<circle cx="{rng.randint(0,1540)}" cy="{rng.randint(0,100)}" '
        f'r="{rng.uniform(0.4,1.7):.1f}" fill="white" opacity="{rng.uniform(0.25,0.85):.2f}"/>'
        for _ in range(100)
    )
    return f"""
<svg viewBox="0 0 1540 500" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;display:block;vertical-align:bottom;">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#04090f"/>
      <stop offset="55%" stop-color="#0d1b36"/>
      <stop offset="100%" stop-color="#0d2a1e"/>
    </linearGradient>
    <linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{TEAL}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{NAVY}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1540" height="500" fill="url(#bg)"/>
  {stars}
  <ellipse cx="1460" cy="55" rx="22" ry="22" fill="#fff9e0" opacity="0.9"/>
  {rect_els}
  {"".join(win_els)}
  <rect x="0" y="480" width="1540" height="20" fill="{NAVY}"/>
  <rect x="0" y="478" width="1540" height="60" fill="url(#wg)"/>
</svg>"""


P2P_SVG = """
<svg viewBox="0 0 700 420" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:680px;display:block;margin:0 auto;">
  <defs>
    <radialGradient id="hg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#10c9a0" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#10c9a0" stop-opacity="0"/>
    </radialGradient>
    <marker id="ma" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#10c9a0"/></marker>
    <marker id="mb" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#f5a623"/></marker>
    <marker id="mc" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#ff6b6b"/></marker>
    <marker id="md" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#8b5cf6"/></marker>
    <marker id="me" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#38bdf8"/></marker>
  </defs>
  <rect width="700" height="420" rx="16" fill="#0d1728"/>
  <circle cx="350" cy="210" r="80" fill="url(#hg)"/>
  <line x1="350" y1="52" x2="350" y2="172" stroke="#f5a623" stroke-width="2.2" stroke-dasharray="6,4" opacity=".6" marker-end="url(#mb)"/>
  <line x1="350" y1="368" x2="350" y2="248" stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".6" marker-end="url(#ma)"/>
  <line x1="640" y1="210" x2="430" y2="210" stroke="#38bdf8" stroke-width="2" stroke-dasharray="8,5" opacity=".4" marker-end="url(#me)"/>
  <line x1="272" y1="168" x2="158" y2="98"  stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#ma)"/>
  <line x1="268" y1="210" x2="76"  y2="210" stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#ma)"/>
  <line x1="272" y1="252" x2="156" y2="322" stroke="#f5a623" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#mb)"/>
  <line x1="428" y1="168" x2="542" y2="98"  stroke="#ff6b6b" stroke-width="2.2" stroke-dasharray="6,4" opacity=".65" marker-end="url(#mc)"/>
  <line x1="428" y1="252" x2="542" y2="322" stroke="#8b5cf6" stroke-width="2.2" stroke-dasharray="6,4" opacity=".65" marker-end="url(#md)"/>
  <circle r="5" fill="#f5a623" opacity=".9"><animateMotion dur="1.8s" repeatCount="indefinite" path="M350,52 L350,182"/></circle>
  <circle r="5" fill="#10c9a0" opacity=".9"><animateMotion dur="2.4s" repeatCount="indefinite" path="M350,368 L350,238"/></circle>
  <circle r="4" fill="#10c9a0" opacity=".85"><animateMotion dur="2.1s" repeatCount="indefinite" begin=".5s" path="M272,168 L158,98"/></circle>
  <circle r="4" fill="#10c9a0" opacity=".85"><animateMotion dur="1.9s" repeatCount="indefinite" begin=".9s" path="M268,210 L76,210"/></circle>
  <circle r="4" fill="#f5a623" opacity=".85"><animateMotion dur="2.3s" repeatCount="indefinite" begin=".3s" path="M272,252 L156,322"/></circle>
  <circle r="4" fill="#ff6b6b" opacity=".8" ><animateMotion dur="2.0s" repeatCount="indefinite" begin="1.1s" path="M428,168 L542,98"/></circle>
  <circle r="4" fill="#8b5cf6" opacity=".8" ><animateMotion dur="2.5s" repeatCount="indefinite" begin=".7s" path="M428,252 L542,322"/></circle>
  <circle cx="350" cy="210" r="42" fill="#0a1223" stroke="#10c9a0" stroke-width="2.5"/>
  <circle cx="350" cy="210" r="42" fill="none" stroke="#10c9a0" stroke-width="1.2" opacity=".3">
    <animate attributeName="r" from="42" to="62" dur="2.5s" repeatCount="indefinite"/>
    <animate attributeName="opacity" from=".3" to="0" dur="2.5s" repeatCount="indefinite"/>
  </circle>
  <text x="350" y="205" text-anchor="middle" font-size="18">🏢</text>
  <text x="350" y="222" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="Arial,sans-serif" font-weight="700">BESS HUB</text>
  <circle cx="350" cy="38" r="29" fill="#1a1800" stroke="#f5a623" stroke-width="2"/>
  <text x="350" y="33" text-anchor="middle" font-size="16">☀️</text>
  <text x="350" y="46" text-anchor="middle" fill="#f5a623" font-size="9" font-family="Arial,sans-serif">SOLAR</text>
  <rect x="314" y="52" width="72" height="15" rx="7" fill="#2a1c00"/>
  <text x="350" y="64" text-anchor="middle" fill="#f5a623" font-size="10" font-family="Arial,sans-serif" font-weight="800">+42 kW</text>
  <circle cx="350" cy="382" r="29" fill="#001a14" stroke="#10c9a0" stroke-width="2"/>
  <text x="350" y="377" text-anchor="middle" font-size="16">🔋</text>
  <text x="350" y="390" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="Arial,sans-serif">BESS 72%</text>
  <circle cx="658" cy="210" r="27" fill="#00101a" stroke="#38bdf8" stroke-width="2"/>
  <text x="658" y="205" text-anchor="middle" font-size="15">🔌</text>
  <text x="658" y="218" text-anchor="middle" fill="#38bdf8" font-size="8" font-family="Arial,sans-serif">CON ED</text>
  <circle cx="140" cy="85" r="25" fill="#001a10" stroke="#10c9a0" stroke-width="2"/>
  <text x="140" y="80" text-anchor="middle" font-size="14">🏠</text>
  <text x="140" y="93" text-anchor="middle" fill="#10c9a0" font-size="8" font-family="Arial,sans-serif">Sophie 3A</text>
  <rect x="112" y="98" width="58" height="14" rx="7" fill="#001a10"/>
  <text x="141" y="110" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="Arial,sans-serif" font-weight="700">wants 5 kWh</text>
  <circle cx="56" cy="210" r="25" fill="#001a10" stroke="#10c9a0" stroke-width="2"/>
  <text x="56" y="205" text-anchor="middle" font-size="14">🏠</text>
  <text x="56" y="218" text-anchor="middle" fill="#10c9a0" font-size="8" font-family="Arial,sans-serif">James 1B</text>
  <rect x="24" y="223" width="64" height="14" rx="7" fill="#001a10"/>
  <text x="56" y="235" text-anchor="middle" fill="#2dcb7f" font-size="9" font-family="Arial,sans-serif" font-weight="700">buying 3 kWh</text>
  <circle cx="138" cy="334" r="25" fill="#1a1200" stroke="#f5a623" stroke-width="2"/>
  <text x="138" y="329" text-anchor="middle" font-size="14">🏠</text>
  <text x="138" y="342" text-anchor="middle" fill="#f5a623" font-size="8" font-family="Arial,sans-serif">Marcus 2C</text>
  <rect x="110" y="347" width="58" height="14" rx="7" fill="#1a1200"/>
  <text x="139" y="359" text-anchor="middle" fill="#f5a623" font-size="9" font-family="Arial,sans-serif" font-weight="700">selling 3 kWh</text>
  <circle cx="560" cy="85" r="25" fill="#1a0000" stroke="#ff6b6b" stroke-width="2"/>
  <text x="560" y="80" text-anchor="middle" font-size="14">🏠</text>
  <text x="560" y="93" text-anchor="middle" fill="#ff6b6b" font-size="8" font-family="Arial,sans-serif">Priya 5A</text>
  <rect x="532" y="98" width="56" height="14" rx="7" fill="#1a0000"/>
  <text x="560" y="110" text-anchor="middle" fill="#ff6b6b" font-size="9" font-family="Arial,sans-serif" font-weight="700">needs 8 kWh</text>
  <circle cx="560" cy="334" r="25" fill="#0d001a" stroke="#8b5cf6" stroke-width="2"/>
  <text x="560" y="329" text-anchor="middle" font-size="14">🏠</text>
  <text x="560" y="342" text-anchor="middle" fill="#8b5cf6" font-size="8" font-family="Arial,sans-serif">Aisha 7B</text>
  <rect x="532" y="347" width="56" height="14" rx="7" fill="#0d001a"/>
  <text x="560" y="359" text-anchor="middle" fill="#8b5cf6" font-size="9" font-family="Arial,sans-serif" font-weight="700">wants 6 kWh</text>
  <rect x="12" y="392" width="300" height="20" rx="6" fill="#ffffff0d"/>
  <circle cx="25" cy="402" r="4" fill="#f5a623"/>
  <text x="33" y="406" fill="#f5a623" font-size="9" font-family="Arial,sans-serif">Solar</text>
  <circle cx="70" cy="402" r="4" fill="#10c9a0"/>
  <text x="78" y="406" fill="#10c9a0" font-size="9" font-family="Arial,sans-serif">P2P Buy</text>
  <circle cx="132" cy="402" r="4" fill="#ff6b6b"/>
  <text x="140" y="406" fill="#ff6b6b" font-size="9" font-family="Arial,sans-serif">Demand</text>
  <circle cx="200" cy="402" r="4" fill="#38bdf8"/>
  <text x="208" y="406" fill="#38bdf8" font-size="9" font-family="Arial,sans-serif">Grid backup</text>
</svg>"""


# ══════════════════════════════════════════════════════════════════════════════
# UI COMPONENT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def badge(text, color=TEAL):
    return html.Span(
        text,
        style={
            "background": f"{color}22",
            "color": color,
            "fontSize": "0.6rem",
            "fontWeight": 800,
            "padding": "2px 9px",
            "borderRadius": "20px",
            "border": f"1px solid {color}44",
            "letterSpacing": "0.08em",
        },
    )


def section_lbl(text):
    return html.Div(
        text,
        style={
            "fontSize": "0.68rem",
            "letterSpacing": "0.28em",
            "textTransform": "uppercase",
            "color": TEAL,
            "fontWeight": 700,
            "marginBottom": "0.65rem",
        },
    )


def vcard(icon, title, body, accent=TEAL):
    return html.Div(
        [
            html.Div(icon, style={"fontSize": "1.75rem", "marginBottom": "0.7rem"}),
            html.Div(
                title,
                style={
                    "fontFamily": MONO,
                    "fontSize": "0.95rem",
                    "color": WHITE,
                    "marginBottom": "0.4rem",
                    "fontWeight": 700,
                },
            ),
            html.Div(
                body, style={"fontSize": "0.84rem", "color": GRAY, "lineHeight": "1.65"}
            ),
        ],
        style={
            "background": "#111827",
            "border": "1px solid #1e3a5f",
            "borderRadius": "12px",
            "padding": "1.6rem",
            "borderTop": f"3px solid {accent}",
        },
    )


def step_row(num, title, body):
    return html.Div(
        [
            html.Div(
                str(num),
                style={
                    "width": "34px",
                    "height": "34px",
                    "borderRadius": "50%",
                    "flexShrink": 0,
                    "background": NAVY,
                    "color": TEAL,
                    "border": f"2px solid {TEAL}",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "fontFamily": MONO,
                    "fontWeight": 700,
                    "fontSize": "0.82rem",
                },
            ),
            html.Div(
                [
                    html.Div(
                        title,
                        style={
                            "color": WHITE,
                            "fontWeight": 700,
                            "marginBottom": "3px",
                            "fontSize": "0.93rem",
                        },
                    ),
                    html.Div(
                        body,
                        style={
                            "color": GRAY,
                            "fontSize": "0.83rem",
                            "lineHeight": "1.65",
                        },
                    ),
                ]
            ),
        ],
        style={
            "display": "flex",
            "gap": "1rem",
            "alignItems": "flex-start",
            "marginBottom": "1.2rem",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUTS
# ══════════════════════════════════════════════════════════════════════════════
skyline_svg = nyc_skyline()


def home_layout():
    return html.Div(
        [
            # ── HERO ──────────────────────────────────────────────────────────
            html.Section(
                style={
                    "background": NAVY,
                    "position": "relative",
                    "minHeight": "72vh",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "flex-end",
                    "paddingBottom": "1rem",
                    "overflow": "hidden",
                    "isolation": "isolate",
                },
                children=[
                    html.Div(
                        [
                            html.Div(
                                "NYC'S ENERGY SHARING NETWORK",
                                style={
                                    "fontSize": "0.68rem",
                                    "letterSpacing": "0.3em",
                                    "color": TEAL,
                                    "fontWeight": 700,
                                    "marginBottom": "1.4rem",
                                },
                            ),
                            html.H1(
                                [
                                    "Borrow Watts from",
                                    html.Br(),
                                    html.Span(
                                        "Neighbours",
                                        style={"color": TEAL},
                                    ),
                                ],
                                style={
                                    "fontFamily": MONO,
                                    "fontSize": "clamp(2.4rem,5.5vw,4.8rem)",
                                    "color": WHITE,
                                    "lineHeight": 1.05,
                                    "marginBottom": "1.4rem",
                                    "letterSpacing": "-0.03em",
                                    "fontWeight": 900,
                                },
                            ),
                            html.P(
                                "BorrowWatt is an Energy-Optimization-as-a-Service (EOAS) platform that lets residents trade "
                                "excess electricity within their building — cutting bills, reducing grid strain, and "
                                "making clean energy actionable for everyone.",
                                style={
                                    "color": "rgba(255,255,255,0.55)",
                                    "fontSize": "1rem",
                                    "lineHeight": "1.75",
                                    "maxWidth": "460px",
                                    "marginBottom": "2.2rem",
                                    "margin": "0 auto 2.2rem",
                                },
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Resident →",
                                        id="hero-how-btn",
                                        style={
                                            "background": TEAL,
                                            "color": NAVY,
                                            "border": "none",
                                            "borderRadius": "999px",
                                            "padding": "14px 34px",
                                            "fontSize": "0.92rem",
                                            "fontWeight": 800,
                                            "cursor": "pointer",
                                            "fontFamily": FONT,
                                            "letterSpacing": "0.01em",
                                        },
                                    ),
                                    html.Button(
                                        "Optimize →",
                                        id="hero-battery-btn",
                                        style={
                                            "background": "rgba(255,255,255,0.08)",
                                            "color": WHITE,
                                            "border": "1.5px solid rgba(255,255,255,0.25)",
                                            "borderRadius": "999px",
                                            "padding": "14px 34px",
                                            "fontSize": "0.92rem",
                                            "fontWeight": 800,
                                            "cursor": "pointer",
                                            "fontFamily": FONT,
                                            "backdropFilter": "blur(4px)",
                                            "letterSpacing": "0.01em",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "1rem",
                                    "flexWrap": "wrap",
                                    "justifyContent": "center",
                                },
                            ),
                        ],
                        style={
                            "position": "relative",
                            "zIndex": 10,
                            "padding": "0 clamp(1.5rem, 6vw, 5rem)",
                            "marginBottom": "18px",
                            "width": "50%",
                            "minWidth": "320px",
                            "alignSelf": "center",
                            "textAlign": "center",
                        },
                    ),
                    # Live ticker
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "NYISO Zone J",
                                        style={
                                            "color": "rgba(255,255,255,0.38)",
                                            "fontSize": "0.82rem",
                                            "fontFamily": MONO,
                                        },
                                    ),
                                    html.Span(
                                        id="t-lmp",
                                        children="$94.2/MWh",
                                        style={
                                            "color": TEAL,
                                            "fontFamily": MONO,
                                            "fontSize": "0.82rem",
                                            "marginLeft": "5px",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Borrow Watts",
                                        style={
                                            "color": "rgba(255,255,255,0.38)",
                                            "fontSize": "0.82rem",
                                            "fontFamily": MONO,
                                        },
                                    ),
                                    html.Span(
                                        "$0.11/kWh",
                                        style={
                                            "color": GREEN,
                                            "fontFamily": MONO,
                                            "fontSize": "0.82rem",
                                            "marginLeft": "5px",
                                        },
                                    ),
                                    html.Span(
                                        "▼ Con Ed",
                                        style={"color": GREEN, "fontSize": "0.72rem"},
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "3px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Con Ed Retail",
                                        style={
                                            "color": "rgba(255,255,255,0.38)",
                                            "fontSize": "0.82rem",
                                            "fontFamily": MONO,
                                        },
                                    ),
                                    html.Span(
                                        "$0.22/kWh",
                                        style={
                                            "color": CORAL,
                                            "fontFamily": MONO,
                                            "fontSize": "0.82rem",
                                            "marginLeft": "5px",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Building Solar",
                                        style={
                                            "color": "rgba(255,255,255,0.38)",
                                            "fontSize": "0.82rem",
                                            "fontFamily": MONO,
                                        },
                                    ),
                                    html.Span(
                                        id="t-sol",
                                        children="42 kW",
                                        style={
                                            "color": GOLD,
                                            "fontFamily": MONO,
                                            "fontSize": "0.82rem",
                                            "marginLeft": "5px",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Surplus",
                                        style={
                                            "color": "rgba(255,255,255,0.38)",
                                            "fontSize": "0.82rem",
                                            "fontFamily": MONO,
                                        },
                                    ),
                                    html.Span(
                                        id="t-sur",
                                        children="18.4 kWh",
                                        style={
                                            "color": TEAL,
                                            "fontFamily": MONO,
                                            "fontSize": "0.82rem",
                                            "marginLeft": "5px",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "2rem",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "flexWrap": "wrap",
                            "background": "rgba(0,0,0,0.45)",
                            "padding": "20px 2rem 8px",
                            "borderTop": "1px solid rgba(255,255,255,0.05)",
                            "width": "100%",
                            "position": "relative",
                            "zIndex": 10,
                        },
                    ),
                    html.Img(
                        src="/assets/nyc_building.jpeg",
                        style={
                            "position": "absolute",
                            "inset": 0,
                            "width": "100%",
                            "height": "100%",
                            "objectFit": "cover",
                            "objectPosition": "center 30%",
                            "zIndex": 1,
                            "filter": "saturate(0.45) brightness(0.38)",
                        },
                    ),
                    html.Div(
                        style={
                            "position": "absolute",
                            "inset": 0,
                            "zIndex": 2,
                            "background": (
                                f"linear-gradient(to bottom,{NAVY}ee 0%,"
                                "rgba(10,18,35,0.55) 38%,rgba(10,18,35,0.55) 58%,"
                                f"{NAVY}cc 78%,{NAVY} 100%)"
                            ),
                        }
                    ),
                    html.Div(
                        dcc.Markdown(skyline_svg, dangerously_allow_html=True),
                        style={
                            "position": "absolute",
                            "bottom": 0,
                            "left": 0,
                            "right": 0,
                            "zIndex": 3,
                        },
                    ),
                ],
            ),
            # ── VALUE PROPS ───────────────────────────────────────────────────
            html.Section(
                style={"background": "#f5f6f0", "padding": "5rem 2rem"},
                children=[
                    html.Div(
                        [
                            section_lbl("WHY BORROWWATTS"),
                            html.H2(
                                "Cheaper energy. Cleaner grid. Better buildings.",
                                style={
                                    "fontFamily": MONO,
                                    "fontSize": "clamp(1.5rem,3vw,2.3rem)",
                                    "color": NAVY,
                                    "marginBottom": "0.75rem",
                                    "letterSpacing": "-0.02em",
                                },
                            ),
                            html.P(
                                "NYC's multifamily housing sits on untapped solar and battery capacity. "
                                "We make it tradeable — between apartments, floors, and buildings — "
                                "with zero hardware and no utility approval needed.",
                                style={
                                    "color": "#555",
                                    "fontSize": "0.95rem",
                                    "lineHeight": "1.75",
                                    "maxWidth": "540px",
                                },
                            ),
                        ],
                        style={"maxWidth": "1100px", "margin": "0 auto 2.5rem"},
                    ),
                    html.Div(
                        [
                            vcard(
                                "⚡",
                                "Real-Time P2P Auctions",
                                "Every 15 minutes our double-auction engine matches buyers and sellers "
                                "within your building at prices 40–55% below Con Ed.",
                                TEAL,
                            ),
                            vcard(
                                "🔋",
                                "Gurobi Battery Dispatch",
                                "Our LP optimizer (Gurobi) determines the exact charge/discharge schedule "
                                "to maximise arbitrage revenue from NYISO price spreads.",
                                GOLD,
                            ),
                            vcard(
                                "🗺️",
                                "Grid-Aware Trading",
                                "Trades respect feeder capacity and local marginal prices so your "
                                "building never contributes to grid congestion.",
                                SKY,
                            ),
                            vcard(
                                "📋",
                                "LL97 Compliance",
                                "Every peer-traded kWh reduces your building's carbon intensity "
                                "and counts toward Local Law 97 targets automatically.",
                                GREEN,
                            ),
                            vcard(
                                "🤝",
                                "Neighbour-First Matching",
                                "Energy stays hyper-local: floor → building → block. "
                                "Con Ed is only the fallback, not the default.",
                                PURPLE,
                            ),
                            vcard(
                                "📱",
                                "Resident App",
                                "Tenants see their surplus, place sell offers, and collect "
                                "micropayments directly in the Borrow Watts app.",
                                CORAL,
                            ),
                        ],
                        style={
                            "maxWidth": "1100px",
                            "margin": "0 auto",
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fill,minmax(290px,1fr))",
                            "gap": "1.25rem",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "$0.11",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "2.2rem",
                                            "color": TEAL,
                                            "fontWeight": 700,
                                        },
                                    ),
                                    html.Div(
                                        "P2P rate / kWh",
                                        style={
                                            "fontSize": "0.72rem",
                                            "color": GRAY,
                                            "marginTop": "3px",
                                            "letterSpacing": "0.06em",
                                        },
                                    ),
                                ],
                                style={
                                    "textAlign": "center",
                                    "background": "#111827",
                                    "border": "1px solid #1e3a5f",
                                    "borderRadius": "12px",
                                    "padding": "1.25rem 1.5rem",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "50%",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "2.2rem",
                                            "color": GREEN,
                                            "fontWeight": 700,
                                        },
                                    ),
                                    html.Div(
                                        "Savings vs Con Ed",
                                        style={
                                            "fontSize": "0.72rem",
                                            "color": GRAY,
                                            "marginTop": "3px",
                                            "letterSpacing": "0.06em",
                                        },
                                    ),
                                ],
                                style={
                                    "textAlign": "center",
                                    "background": "#111827",
                                    "border": "1px solid #1e3a5f",
                                    "borderRadius": "12px",
                                    "padding": "1.25rem 1.5rem",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "100+",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "2.2rem",
                                            "color": GOLD,
                                            "fontWeight": 700,
                                        },
                                    ),
                                    html.Div(
                                        "NYC Buildings",
                                        style={
                                            "fontSize": "0.72rem",
                                            "color": GRAY,
                                            "marginTop": "3px",
                                            "letterSpacing": "0.06em",
                                        },
                                    ),
                                ],
                                style={
                                    "textAlign": "center",
                                    "background": "#111827",
                                    "border": "1px solid #1e3a5f",
                                    "borderRadius": "12px",
                                    "padding": "1.25rem 1.5rem",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "LL97",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "2.2rem",
                                            "color": SKY,
                                            "fontWeight": 700,
                                        },
                                    ),
                                    html.Div(
                                        "Compliant",
                                        style={
                                            "fontSize": "0.72rem",
                                            "color": GRAY,
                                            "marginTop": "3px",
                                            "letterSpacing": "0.06em",
                                        },
                                    ),
                                ],
                                style={
                                    "textAlign": "center",
                                    "background": "#111827",
                                    "border": "1px solid #1e3a5f",
                                    "borderRadius": "12px",
                                    "padding": "1.25rem 1.5rem",
                                },
                            ),
                        ],
                        style={
                            "maxWidth": "900px",
                            "margin": "3rem auto 0",
                            "display": "grid",
                            "gridTemplateColumns": "repeat(4,1fr)",
                            "gap": "1rem",
                            "background": NAVY,
                            "borderRadius": "16px",
                            "padding": "2rem",
                        },
                    ),
                ],
            ),
            # ── FOOTER ────────────────────────────────────────────────────────
            _footer(),
        ]
    )


def how_layout():
    _BDR = "#1e3a5f"
    _PNL = "#111827"
    _card_style = {
        "background": _PNL,
        "border": f"1px solid {_BDR}",
        "borderRadius": "14px",
        "overflow": "hidden",
    }

    def _card_hdr(icon, icon_bg, title, right=None):
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            icon,
                            style={
                                "width": "28px",
                                "height": "28px",
                                "borderRadius": "8px",
                                "background": icon_bg,
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "fontSize": "0.9rem",
                                "flexShrink": 0,
                            },
                        ),
                        html.Span(
                            title,
                            style={
                                "fontWeight": 700,
                                "fontSize": "0.88rem",
                                "color": WHITE,
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                ),
                html.Div(
                    right or "",
                    style={"fontSize": "0.7rem", "color": GRAY, "fontWeight": 600},
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "0.75rem 1.1rem",
                "borderBottom": f"1px solid {_BDR}55",
            },
        )

    def _stat_card(icon, icon_bg, label, value, value_color, trend):
        return html.Div(
            [
                html.Div(
                    icon,
                    style={
                        "width": "38px",
                        "height": "38px",
                        "borderRadius": "10px",
                        "background": icon_bg,
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "1.1rem",
                        "flexShrink": 0,
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            label,
                            style={
                                "fontSize": "0.7rem",
                                "color": GRAY,
                                "fontWeight": 600,
                                "marginBottom": "2px",
                            },
                        ),
                        html.Div(
                            value,
                            style={
                                "fontFamily": MONO,
                                "fontSize": "1.1rem",
                                "fontWeight": 800,
                                "color": value_color,
                                "marginBottom": "3px",
                            },
                        ),
                        html.Div(
                            trend,
                            style={
                                "fontSize": "0.67rem",
                                "fontWeight": 700,
                                "color": GREEN,
                                "background": f"{GREEN}15",
                                "padding": "1px 7px",
                                "borderRadius": "999px",
                                "display": "inline-block",
                            },
                        ),
                    ],
                ),
            ],
            style={
                "display": "flex",
                "gap": "0.75rem",
                "alignItems": "center",
                "background": _PNL,
                "border": f"1px solid {_BDR}",
                "borderRadius": "12px",
                "padding": "0.9rem 1rem",
                "flex": 1,
            },
        )

    def _act_item(icon, icon_bg, main_children, sub, amount, amount_color):
        return html.Div(
            [
                html.Div(
                    icon,
                    style={
                        "width": "30px",
                        "height": "30px",
                        "borderRadius": "8px",
                        "background": icon_bg,
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "0.85rem",
                        "flexShrink": 0,
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            main_children,
                            style={"fontSize": "0.81rem", "color": "#e2e8f0"},
                        ),
                        html.Div(
                            sub,
                            style={
                                "fontSize": "0.69rem",
                                "color": GRAY,
                                "marginTop": "2px",
                            },
                        ),
                    ],
                    style={"flex": 1},
                ),
                html.Div(
                    amount,
                    style={
                        "fontSize": "0.82rem",
                        "fontWeight": 700,
                        "color": amount_color,
                        "fontFamily": MONO,
                        "flexShrink": 0,
                    },
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "0.65rem",
                "padding": "0.6rem 0",
                "borderBottom": f"1px solid {_BDR}44",
            },
        )

    def _neighbor_row(avatar, name, apt_text, pill_text, pill_color, qty):
        return html.Div(
            [
                html.Div(
                    avatar,
                    style={
                        "width": "34px",
                        "height": "34px",
                        "borderRadius": "50%",
                        "background": f"{pill_color}18",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "fontSize": "1rem",
                        "flexShrink": 0,
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            name,
                            style={
                                "fontSize": "0.82rem",
                                "color": WHITE,
                                "fontWeight": 700,
                            },
                        ),
                        html.Div(apt_text, style={"fontSize": "0.7rem", "color": GRAY}),
                    ],
                    style={"flex": 1},
                ),
                html.Div(
                    [
                        html.Div(
                            pill_text,
                            style={
                                "fontSize": "0.64rem",
                                "fontWeight": 800,
                                "color": pill_color,
                                "background": f"{pill_color}18",
                                "padding": "2px 8px",
                                "borderRadius": "999px",
                                "border": f"1px solid {pill_color}33",
                                "marginBottom": "2px",
                                "textAlign": "right",
                            },
                        ),
                        html.Div(
                            qty,
                            style={
                                "fontSize": "0.7rem",
                                "color": GRAY,
                                "textAlign": "right",
                            },
                        ),
                    ],
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "0.65rem",
                "padding": "0.6rem 0",
                "borderBottom": f"1px solid {_BDR}44",
            },
        )

    # ── Stat row ──────────────────────────────────────────────────────────────
    stats_row = html.Div(
        [
            _stat_card(
                "☀️", f"{TEAL}18", "Solar Generating", "42 kW", TEAL, "▲ peak hours"
            ),
            _stat_card(
                "💰", f"{GOLD}18", "Earned Today (P2P)", "$4.82", GOLD, "▲ 3 trades"
            ),
            _stat_card(
                "🌿", f"{GREEN}18", "CO₂ Avoided", "12.4 kg", GREEN, "▲ vs grid"
            ),
        ],
        style={
            "display": "flex",
            "gap": "0.75rem",
            "marginBottom": "1rem",
            "flexWrap": "wrap",
        },
    )

    # ── Live Energy Flow card (iframe — JS drawFlows, dark theme) ────────────────
    _flow_iframe_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#111827;overflow:hidden;}
@keyframes hubpulse{
  0%,100%{box-shadow:0 0 0 6px rgba(16,201,160,0.18),0 6px 20px rgba(0,0,0,0.5);}
  50%    {box-shadow:0 0 0 16px rgba(16,201,160,0.05),0 6px 20px rgba(0,0,0,0.5);}
}
@keyframes ripple{0%{transform:scale(1);opacity:0.3}100%{transform:scale(1.4);opacity:0}}
.flow-node{display:flex;flex-direction:column;align-items:center;gap:4px;}
.apt-node{cursor:pointer;}
.apt-node:hover .node-circle{transform:scale(1.1);}
.node-circle{
  width:52px;height:52px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:1.25rem;position:relative;
  box-shadow:0 4px 14px rgba(0,0,0,0.45);
  transition:transform 0.2s;
}
.node-circle::after{
  content:'';position:absolute;inset:-5px;border-radius:50%;
  border:2px solid currentColor;opacity:0.22;
  animation:ripple 2.2s infinite;
}
.node-label{font-size:0.62rem;font-weight:700;text-align:center;max-width:72px;line-height:1.3;font-family:Arial,sans-serif;}
.node-kw{font-family:Arial,sans-serif;font-size:0.65rem;font-weight:800;padding:2px 8px;border-radius:999px;}
</style>
</head>
<body>
<div style="position:relative;height:340px;background:#111827;overflow:hidden;">
  <svg id="flowSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;">
    <defs>
      <radialGradient id="hglow" cx="50%" cy="50%" r="40%">
        <stop offset="0%" stop-color="#10c9a0" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#10c9a0" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <ellipse id="hubglow" cx="0" cy="0" rx="88" ry="74" fill="url(#hglow)"/>
  </svg>

  <div id="hub" style="
    position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
    width:72px;height:72px;border-radius:50%;
    background:#0a1223;border:2.5px solid #10c9a0;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    z-index:5;animation:hubpulse 3s ease-in-out infinite;
  ">
    <span style="font-size:1.4rem;">🏢</span>
    <span style="font-size:0.52rem;font-family:Arial,sans-serif;color:#10c9a0;font-weight:700;letter-spacing:0.06em;margin-top:2px;">BESS HUB</span>
  </div>

  <div class="flow-node" id="node-solar" style="position:absolute;left:50%;top:5%;transform:translateX(-50%);z-index:4;">
    <div class="node-circle" style="background:#1a1800;border:2.5px solid #f5a623;color:#f5a623;">☀️</div>
    <div class="node-label" style="color:#f5a623;">Rooftop Solar</div>
    <div class="node-kw" style="background:#1a1800;color:#f5a623;" id="n-solar">+42 kW</div>
  </div>

  <div class="flow-node" id="node-batt" style="position:absolute;left:50%;bottom:4%;transform:translateX(-50%);z-index:4;">
    <div class="node-circle" style="background:#001a14;border:2.5px solid #10c9a0;color:#10c9a0;">🔋</div>
    <div class="node-label" style="color:#10c9a0;">Building BESS</div>
    <div class="node-kw" style="background:#001a14;color:#10c9a0;" id="n-batt">72% · 144kWh</div>
  </div>

  <div class="flow-node" id="node-grid" style="position:absolute;right:3%;top:50%;transform:translateY(-50%);z-index:4;">
    <div class="node-circle" style="background:#00101a;border:2.5px solid #38bdf8;color:#38bdf8;">🔌</div>
    <div class="node-label" style="color:#38bdf8;">Con Ed Grid</div>
    <div class="node-kw" style="background:#00101a;color:#38bdf8;">Backup</div>
  </div>

  <div class="flow-node apt-node" id="node-sophie" style="position:absolute;left:7%;top:50%;transform:translateY(-50%);z-index:4;">
    <div class="node-circle" style="background:#001a10;border:2.5px solid #2dcb7f;color:#2dcb7f;">🏠</div>
    <div class="node-label" style="color:#2dcb7f;">Sophie · 3A</div>
    <div class="node-kw" style="background:#001a10;color:#2dcb7f;">wants 5 kWh</div>
  </div>

  <div class="flow-node apt-node" id="node-marcus" style="position:absolute;left:14%;top:14%;z-index:4;">
    <div class="node-circle" style="background:#1a1200;border:2.5px solid #f5a623;color:#f5a623;">🏠</div>
    <div class="node-label" style="color:#f5a623;">Marcus · 2C</div>
    <div class="node-kw" style="background:#1a1200;color:#f5a623;">selling 3 kWh</div>
  </div>

  <div class="flow-node apt-node" id="node-priya" style="position:absolute;right:13%;top:14%;z-index:4;">
    <div class="node-circle" style="background:#1a0008;border:2.5px solid #8b5cf6;color:#8b5cf6;">🏠</div>
    <div class="node-label" style="color:#8b5cf6;">Priya · 5A</div>
    <div class="node-kw" style="background:#1a0008;color:#8b5cf6;">wants 8 kWh</div>
  </div>
</div>

<script>
function drawFlows(){
  var svg=document.getElementById('flowSvg');
  if(!svg) return;
  var cw=svg.parentElement.offsetWidth, ch=svg.parentElement.offsetHeight;
  var cx=cw/2, cy=ch/2;
  document.getElementById('hubglow').setAttribute('cx',cx);
  document.getElementById('hubglow').setAttribute('cy',cy);
  var nodes=[
    {id:'node-solar', col:'#f5a623'},
    {id:'node-batt',  col:'#10c9a0'},
    {id:'node-grid',  col:'#38bdf8'},
    {id:'node-sophie',col:'#2dcb7f'},
    {id:'node-marcus',col:'#f5a623'},
    {id:'node-priya', col:'#8b5cf6'},
  ];
  var old=svg.querySelectorAll('.fl');
  old.forEach(function(e){e.remove();});
  nodes.forEach(function(n,i){
    var el=document.getElementById(n.id);
    if(!el) return;
    var r=el.getBoundingClientRect();
    var pr=svg.parentElement.getBoundingClientRect();
    var nx=r.left-pr.left+r.width/2, ny=r.top-pr.top+r.height/2;
    var ln=document.createElementNS('http://www.w3.org/2000/svg','line');
    ln.setAttribute('class','fl');
    ln.setAttribute('x1',cx);ln.setAttribute('y1',cy);
    ln.setAttribute('x2',nx);ln.setAttribute('y2',ny);
    ln.setAttribute('stroke',n.col);ln.setAttribute('stroke-width','1.8');
    ln.setAttribute('stroke-opacity','0.38');ln.setAttribute('stroke-dasharray','6,4');
    svg.appendChild(ln);
    var pid='mp'+i;
    var pe=document.createElementNS('http://www.w3.org/2000/svg','path');
    pe.setAttribute('id',pid);pe.setAttribute('class','fl');
    pe.setAttribute('d','M'+cx+','+cy+' L'+nx+','+ny);
    pe.setAttribute('fill','none');svg.appendChild(pe);
    var c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('class','fl');c.setAttribute('r','4');
    c.setAttribute('fill',n.col);c.setAttribute('opacity','0.92');
    var am=document.createElementNS('http://www.w3.org/2000/svg','animateMotion');
    am.setAttribute('dur',(1.5+i*0.28).toFixed(1)+'s');
    am.setAttribute('repeatCount','indefinite');am.setAttribute('begin',(i*0.35).toFixed(1)+'s');
    var mp=document.createElementNS('http://www.w3.org/2000/svg','mpath');
    mp.setAttributeNS('http://www.w3.org/1999/xlink','href','#'+pid);
    am.appendChild(mp);c.appendChild(am);svg.appendChild(c);
  });
}
function tickLive(){
  var s=document.getElementById('n-solar');
  if(s) s.textContent='+'+(38+Math.floor(Math.random()*8))+' kW';
  var b=document.getElementById('n-batt');
  if(b){var p=(68+Math.random()*20).toFixed(0);b.textContent=p+'% · '+(p*2)+' kWh';}
}
setTimeout(drawFlows,120);
window.addEventListener('resize',drawFlows);
setInterval(tickLive,4000);
</script>
</body>
</html>"""

    flow_card = html.Div(
        [
            _card_hdr(
                "🗺️",
                f"{TEAL}18",
                "Live Energy Flow · Floor 4",
                "Real-time · 15-min match",
            ),
            html.Iframe(
                srcDoc=_flow_iframe_html,
                style={
                    "width": "100%",
                    "height": "348px",
                    "border": "none",
                    "display": "block",
                    "borderRadius": "0 0 4px 4px",
                },
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                "🟢  Live",
                                style={
                                    "color": GREEN,
                                    "fontWeight": 700,
                                    "fontSize": "0.8rem",
                                },
                            ),
                            html.Span(
                                "Apt 4B sold 4.2 kWh to Sophie in 3A · 2 min ago",
                                style={
                                    "color": GRAY,
                                    "fontSize": "0.78rem",
                                    "marginLeft": "8px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "marginTop": "0.75rem",
                            "padding": "9px 14px",
                            "background": "#ffffff08",
                            "borderRadius": "8px",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                "⚡  BESS",
                                style={
                                    "color": TEAL,
                                    "fontWeight": 700,
                                    "fontSize": "0.8rem",
                                },
                            ),
                            html.Span(
                                "Discharged 12 kWh during peak · saved $1.32",
                                style={
                                    "color": GRAY,
                                    "fontSize": "0.78rem",
                                    "marginLeft": "8px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "marginTop": "8px",
                            "padding": "9px 14px",
                            "background": "#ffffff08",
                            "borderRadius": "8px",
                        },
                    ),
                ],
                style={"padding": "0.5rem 1.1rem 0.75rem"},
            ),
        ],
        style={**_card_style, "marginBottom": "1rem"},
    )

    # ── Recent Trades card ─────────────────────────────────────────────────────
    trades_card = html.Div(
        [
            _card_hdr("📜", f"{PURPLE}18", "Recent Trades", "See all →"),
            html.Div(
                [
                    _act_item(
                        "✅",
                        f"{GREEN}18",
                        [
                            html.Span("You sold "),
                            html.Strong("4.2 kWh", style={"color": WHITE}),
                            html.Span(" to Sophie in Apt 3A"),
                        ],
                        "2 min ago · Solar surplus",
                        "+$0.46",
                        GREEN,
                    ),
                    _act_item(
                        "⚡",
                        f"{TEAL}18",
                        [
                            html.Span("BESS discharged "),
                            html.Strong("12 kWh", style={"color": WHITE}),
                            html.Span(" to building load"),
                        ],
                        "18 min ago · Peak avoidance",
                        "$1.32",
                        TEAL,
                    ),
                    _act_item(
                        "☀️",
                        f"{GOLD}18",
                        [
                            html.Span("You bought "),
                            html.Strong("2.8 kWh", style={"color": WHITE}),
                            html.Span(" from Marcus in Apt 2C"),
                        ],
                        "1 hr ago · Cheapest rate today",
                        "-$0.31",
                        GOLD,
                    ),
                    _act_item(
                        "🏆",
                        f"{PURPLE}18",
                        [
                            html.Span("Building hit "),
                            html.Strong("100% renewable", style={"color": WHITE}),
                            html.Span(" for 3 hours!"),
                        ],
                        "3 hrs ago · New building record",
                        "🎉",
                        PURPLE,
                    ),
                ],
                style={"padding": "0.25rem 1.1rem"},
            ),
        ],
        style={**_card_style, "marginBottom": "1rem"},
    )

    # ── Neighbors Trading Now card ─────────────────────────────────────────────
    neighbors_card = html.Div(
        [
            _card_hdr(
                "👥",
                f"{GREEN}18",
                "Neighbors Trading Now",
                html.Div(
                    [
                        html.Span("● ", style={"color": GREEN, "fontSize": "0.7rem"}),
                        html.Span(
                            "Live",
                            style={
                                "color": GREEN,
                                "fontSize": "0.68rem",
                                "fontWeight": 700,
                            },
                        ),
                    ]
                ),
            ),
            html.Div(
                [
                    _neighbor_row(
                        "👩",
                        "Sophie Chen",
                        "Apt 3A · needs energy · EV charging",
                        "Wants to Buy",
                        TEAL,
                        "5 kWh",
                    ),
                    _neighbor_row(
                        "👨",
                        "Marcus Johnson",
                        "Apt 2C · has solar surplus",
                        "Selling",
                        GOLD,
                        "3 kWh · $0.09",
                    ),
                    _neighbor_row(
                        "👩‍💼",
                        "Priya Patel",
                        "Apt 5A · HVAC running hot",
                        "Wants to Buy",
                        PURPLE,
                        "8 kWh",
                    ),
                    _neighbor_row(
                        "🧑", "James Park", "Apt 1B · balanced", "Idle", GRAY, "—"
                    ),
                ],
                style={"padding": "0.25rem 1.1rem"},
            ),
        ],
        style=_card_style,
    )

    # ── My Energy card ─────────────────────────────────────────────────────────
    my_energy_card = html.Div(
        [
            _card_hdr("⚡", f"{TEAL}18", "My Energy · Apt 4B"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                "72%",
                                style={
                                    "fontFamily": MONO,
                                    "fontSize": "2rem",
                                    "fontWeight": 900,
                                    "color": TEAL,
                                },
                            ),
                            html.Div(
                                "Charged", style={"fontSize": "0.72rem", "color": GRAY}
                            ),
                            html.Div(
                                "Battery · 72 kWh available",
                                style={
                                    "fontSize": "0.7rem",
                                    "color": GRAY,
                                    "marginTop": "4px",
                                },
                            ),
                        ],
                        style={"textAlign": "center", "padding": "0.75rem 0 0.5rem"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "+42 kW",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "1rem",
                                            "fontWeight": 900,
                                            "color": GREEN,
                                        },
                                    ),
                                    html.Div(
                                        "Generating",
                                        style={
                                            "fontSize": "0.65rem",
                                            "fontWeight": 700,
                                            "color": GREEN,
                                        },
                                    ),
                                ],
                                style={
                                    "background": f"{GREEN}12",
                                    "borderRadius": "10px",
                                    "padding": "0.6rem",
                                    "textAlign": "center",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        "-8 kW",
                                        style={
                                            "fontFamily": MONO,
                                            "fontSize": "1rem",
                                            "fontWeight": 900,
                                            "color": CORAL,
                                        },
                                    ),
                                    html.Div(
                                        "Using",
                                        style={
                                            "fontSize": "0.65rem",
                                            "fontWeight": 700,
                                            "color": CORAL,
                                        },
                                    ),
                                ],
                                style={
                                    "background": f"{CORAL}12",
                                    "borderRadius": "10px",
                                    "padding": "0.6rem",
                                    "textAlign": "center",
                                },
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "1fr 1fr",
                            "gap": "0.5rem",
                            "marginBottom": "0.75rem",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                "✨ You have surplus to share!",
                                style={
                                    "fontSize": "0.72rem",
                                    "color": TEAL,
                                    "fontWeight": 700,
                                    "marginBottom": "2px",
                                },
                            ),
                            html.Div(
                                "+15.7 kWh",
                                style={
                                    "fontFamily": MONO,
                                    "fontSize": "1.2rem",
                                    "fontWeight": 900,
                                    "color": WHITE,
                                },
                            ),
                            html.Div(
                                "available to sell to neighbors",
                                style={"fontSize": "0.68rem", "color": GRAY},
                            ),
                        ],
                        style={
                            "background": f"{TEAL}0d",
                            "borderRadius": "10px",
                            "padding": "0.75rem",
                            "border": f"1.5px dashed {TEAL}44",
                            "marginBottom": "0.75rem",
                            "textAlign": "center",
                        },
                    ),
                    html.Button(
                        "💚 Offer Energy to Neighbors",
                        style={
                            "width": "100%",
                            "background": f"{TEAL}22",
                            "color": TEAL,
                            "border": f"1.5px solid {TEAL}55",
                            "borderRadius": "8px",
                            "padding": "0.6rem",
                            "fontSize": "0.85rem",
                            "fontWeight": 700,
                            "cursor": "pointer",
                            "fontFamily": FONT,
                        },
                    ),
                ],
                style={"padding": "0.25rem 1.1rem 1rem"},
            ),
        ],
        style={**_card_style, "marginBottom": "1.5rem"},
    )

    # ── Columns ────────────────────────────────────────────────────────────────
    left_col = html.Div(
        [stats_row, flow_card, trades_card, neighbors_card],
        style={"flex": "0 0 auto", "width": "min(660px, 100%)"},
    )

    right_col = html.Div(
        [
            my_energy_card,
            step_row(
                1,
                "Generate",
                "Rooftop solar panels produce power. Surplus beyond apartment consumption flows to the building BESS hub.",
            ),
            step_row(
                2,
                "Store",
                "The shared battery stores surplus and discharges during NYISO price peaks, earning arbitrage revenue.",
            ),
            step_row(
                3,
                "Match",
                "Our double-auction engine runs every 15 minutes. Apartments submit bids & asks; the clearing price always beats Con Ed.",
            ),
            step_row(
                4,
                "Settle",
                "Micropayments are calculated automatically. Sellers earn credits, buyers save money, building earns a platform fee.",
            ),
            step_row(
                5,
                "Report",
                "LL97 compliance reports generated automatically. Every peer-traded kWh reduces your carbon intensity score.",
            ),
        ],
        style={"flex": 1, "minWidth": "260px"},
    )

    return html.Div(
        [
            html.Section(
                style={
                    "background": NAVY,
                    "padding": "5rem 2rem",
                    "minHeight": "100vh",
                },
                children=[
                    html.Div(
                        [
                            section_lbl("HOW IT WORKS"),
                            html.H2(
                                "Energy flows between apartments in real time.",
                                style={
                                    "fontFamily": MONO,
                                    "fontSize": "clamp(1.5rem,3vw,2.3rem)",
                                    "color": WHITE,
                                    "marginBottom": "0.5rem",
                                    "letterSpacing": "-0.02em",
                                },
                            ),
                            html.P(
                                "Solar from the rooftop, battery storage from the basement, "
                                "and peer trades between units — matched every 15 minutes by our double-auction engine.",
                                style={
                                    "color": GRAY,
                                    "fontSize": "0.93rem",
                                    "lineHeight": "1.75",
                                    "maxWidth": "500px",
                                },
                            ),
                        ],
                        style={"maxWidth": "1100px", "margin": "0 auto 2.5rem"},
                    ),
                    html.Div(
                        [left_col, right_col],
                        style={
                            "maxWidth": "1100px",
                            "margin": "0 auto",
                            "display": "flex",
                            "gap": "3rem",
                            "alignItems": "flex-start",
                            "flexWrap": "wrap",
                        },
                    ),
                ],
            ),
            _footer(),
        ]
    )


def battery_layout():
    sidebar = dbc.Card(
        [
            html.H5(
                "Battery Parameters",
                className="card-title mb-3",
                style={"color": WHITE, "fontFamily": MONO},
            ),
            dbc.Label("Capacity (MWh)", style={"color": GRAY, "fontSize": "0.82rem"}),
            dbc.Input(
                id="cap",
                type="number",
                value=20,
                min=0.1,
                step=0.1,
                className="mb-2 batt-input",
            ),
            dbc.Label("Initial SoC", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Slider(
                id="soc_init",
                min=0,
                max=1,
                step=0.01,
                value=0.5,
                marks={0: "0", 0.5: "0.5", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            dbc.Label("Min SoC", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Slider(
                id="soc_min",
                min=0,
                max=1,
                step=0.01,
                value=0,
                marks={0: "0", 0.5: "0.5", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            dbc.Label("Max SoC", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Slider(
                id="soc_max",
                min=0,
                max=1,
                step=0.01,
                value=1,
                marks={0: "0", 0.5: "0.5", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            dbc.Label("Max Charge (MW)", style={"color": GRAY, "fontSize": "0.82rem"}),
            dbc.Input(
                id="cmax",
                type="number",
                value=5,
                min=0.1,
                step=0.1,
                className="mb-2 batt-input",
            ),
            dbc.Label(
                "Max Discharge (MW)", style={"color": GRAY, "fontSize": "0.82rem"}
            ),
            dbc.Input(
                id="dmax",
                type="number",
                value=5,
                min=0.1,
                step=0.1,
                className="mb-2 batt-input",
            ),
            dbc.Label(
                "Charge Efficiency (η_c)", style={"color": GRAY, "fontSize": "0.82rem"}
            ),
            dcc.Slider(
                id="eta_c",
                min=0.5,
                max=1,
                step=0.01,
                value=0.95,
                marks={0.5: "0.5", 0.75: "0.75", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            dbc.Label(
                "Discharge Efficiency (η_d)",
                style={"color": GRAY, "fontSize": "0.82rem"},
            ),
            dcc.Slider(
                id="eta_d",
                min=0.5,
                max=1,
                step=0.01,
                value=0.95,
                marks={0.5: "0.5", 0.75: "0.75", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            dbc.Label("SoC Target", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Slider(
                id="soc_target",
                min=0,
                max=1,
                step=0.01,
                value=0.5,
                marks={0: "0", 0.5: "0.5", 1: "1"},
                tooltip={"placement": "bottom"},
            ),
            html.Hr(style={"borderColor": "#1e3a5f"}),
            html.H5(
                "Market / Forecast",
                className="card-title mb-3",
                style={"color": WHITE, "fontFamily": MONO},
            ),
            dbc.Label("Region", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Dropdown(
                id="region",
                options=[{"label": r, "value": r} for r in REGIONS],
                value="CAPITL",
                clearable=False,
                className="mb-2 batt-dropdown",
            ),
            html.Div(
                [
                    dbc.Label(
                        "Date",
                        className="mb-0",
                        style={"color": GRAY, "fontSize": "0.82rem"},
                    ),
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
                className="mb-2 batt-input",
            ),
            dbc.Label("Forecast Type", style={"color": GRAY, "fontSize": "0.82rem"}),
            dcc.Dropdown(
                id="forecast_type",
                options=[{"label": f, "value": f} for f in FORECAST_TYPES],
                value="LSTM",
                clearable=False,
                className="mb-2 batt-dropdown",
            ),
            html.Hr(style={"borderColor": "#1e3a5f"}),
            dbc.Button(
                "Run Optimization",
                id="run_btn",
                color="primary",
                className="w-100",
                style={
                    "background": TEAL,
                    "borderColor": TEAL,
                    "color": NAVY,
                    "fontWeight": 800,
                    "fontFamily": MONO,
                },
            ),
            html.Div(
                id="status_msg",
                className="mt-2 text-muted small",
                style={"color": GRAY, "fontSize": "0.75rem"},
            ),
        ],
        body=True,
        className="batt-sidebar h-100",
        style={
            "overflowY": "auto",
            "background": "#111827",
            "border": "1px solid #1e3a5f",
            "borderRadius": "14px",
        },
    )

    content = dbc.Col(
        [
            html.Div(
                id="charts-placeholder",
                children=[
                    html.Div("⚡", style={"fontSize": "3rem", "marginBottom": "1rem"}),
                    html.Div(
                        "Run the Optimizer",
                        style={
                            "fontFamily": MONO,
                            "fontSize": "1.2rem",
                            "color": WHITE,
                            "fontWeight": 700,
                            "marginBottom": "0.5rem",
                        },
                    ),
                    html.Div(
                        "Configure battery parameters, pick a date & region, then hit ▶ Run Optimization to see the arbitrage strategy.",
                        style={
                            "fontSize": "0.88rem",
                            "color": GRAY,
                            "maxWidth": "380px",
                            "lineHeight": "1.7",
                        },
                    ),
                    html.Div(
                        [
                            badge("📊 Price Forecast", TEAL),
                            badge("🔋 State of Charge", PURPLE),
                            badge("💰 Arbitrage", GOLD),
                        ],
                        style={
                            "display": "flex",
                            "gap": "0.5rem",
                            "marginTop": "1.2rem",
                            "flexWrap": "wrap",
                            "justifyContent": "center",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "minHeight": "480px",
                    "border": "1px dashed #1e3a5f",
                    "borderRadius": "14px",
                    "background": "#111827",
                    "textAlign": "center",
                    "padding": "3rem",
                },
            ),
            dbc.Spinner(
                html.Div(
                    id="charts-container",
                    children=[
                        dcc.Graph(id="fig_forecast", style={"height": "320px"}),
                        dcc.Graph(id="fig_soc", style={"height": "380px"}),
                        dcc.Graph(id="fig_arbitrage", style={"height": "780px"}),
                    ],
                    style={"display": "none"},
                ),
                color="primary",
            ),
        ]
    )

    return html.Div(
        style={"background": "#0d1728", "padding": "5rem 2rem", "minHeight": "100vh"},
        children=[
            dbc.Container(
                [
                    dbc.Row(
                        dbc.Col(
                            [
                                section_lbl("BATTERY ARBITRAGE OPTIMIZER"),
                                html.H2(
                                    "Gurobi-powered BESS dispatch.",
                                    style={
                                        "fontFamily": MONO,
                                        "fontSize": "clamp(1.4rem,3vw,2.2rem)",
                                        "color": WHITE,
                                        "marginBottom": "0.4rem",
                                        "letterSpacing": "-0.02em",
                                    },
                                ),
                                html.P(
                                    "Adjust battery parameters and see the optimal charge/discharge schedule "
                                    "vs NYISO price forecasts. Solved with Gurobi MILP.",
                                    style={
                                        "color": GRAY,
                                        "fontSize": "0.88rem",
                                        "lineHeight": "1.75",
                                        "maxWidth": "600px",
                                        "marginBottom": "2rem",
                                    },
                                ),
                            ]
                        )
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                sidebar,
                                width=3,
                                style={
                                    "height": "90vh",
                                    "position": "sticky",
                                    "top": "1rem",
                                },
                            ),
                            dbc.Col(content, width=9),
                        ],
                        align="start",
                    ),
                ],
                fluid=True,
            ),
            _footer(),
        ],
    )


def _footer():
    return html.Footer(
        style={
            "background": "#060c16",
            "padding": "2.5rem 2rem",
            "textAlign": "center",
            "borderTop": "1px solid #1e3a5f",
        },
        children=[
            html.Div(
                [
                    html.Span(
                        "Borrow",
                        style={"color": WHITE, "fontFamily": MONO, "fontWeight": 900},
                    ),
                    html.Span(
                        "Watts",
                        style={"color": TEAL, "fontFamily": MONO, "fontWeight": 900},
                    ),
                ],
                style={"marginBottom": "0.5rem"},
            ),
            html.P(
                "NYC's P2P Energy Trading Platform · © 2026 Borrow Watts Inc.",
                style={"color": GRAY, "fontSize": "0.76rem"},
            ),
            html.P(
                "Built with Dash · Plotly · Gurobi · NYISO API",
                style={
                    "color": "#2a3748",
                    "fontSize": "0.7rem",
                    "marginTop": "4px",
                    "fontFamily": MONO,
                },
            ),
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap",
    ],
    meta_tags=[{"name": "viewport", "content": "width=device-width,initial-scale=1"}],
    title="Borrow Watts — NYC Energy",
)
server = app.server

app.layout = html.Div(
    style={"fontFamily": FONT, "background": NAVY, "color": "#e2e8f0"},
    children=[
        # ── FIXED NAVBAR ──────────────────────────────────────────────────────
        html.Nav(
            id="main-nav",
            style={
                "position": "fixed",
                "top": 0,
                "left": 0,
                "right": 0,
                "zIndex": 999,
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "0 2.5rem",
                "height": "62px",
                "background": "rgba(10,18,35,0.94)",
                "backdropFilter": "blur(12px)",
                "borderBottom": "1px solid rgba(255,255,255,0.06)",
            },
            children=[
                html.Div(
                    [
                        html.Span(
                            "Borrow",
                            style={
                                "color": WHITE,
                                "fontFamily": MONO,
                                "fontWeight": 900,
                                "fontSize": "1.38rem",
                            },
                        ),
                        html.Span(
                            "Watts",
                            style={
                                "color": TEAL,
                                "fontFamily": MONO,
                                "fontWeight": 900,
                                "fontSize": "1.38rem",
                            },
                        ),
                        badge("NYC", "#10c9a0"),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "6px"},
                ),
                html.Div(
                    [
                        html.Button(
                            "Home", id="nav-home", className="nav-btn nav-btn-active"
                        ),
                        html.Button("How It Works", id="nav-how", className="nav-btn"),
                        html.Button(
                            "Battery App", id="nav-battery", className="nav-btn"
                        ),
                    ],
                    style={"display": "flex", "gap": "0.25rem"},
                ),
                html.Button("Get Early Access", className="nav-cta"),
            ],
        ),
        # ── PAGE SECTIONS (all rendered; visibility toggled by callback) ───────
        html.Div(id="page-home", children=home_layout(), style={"paddingTop": "62px"}),
        html.Div(id="page-how", children=how_layout(), style={"display": "none"}),
        html.Div(
            id="page-battery", children=battery_layout(), style={"display": "none"}
        ),
        # ── GLOBAL STORES / INTERVALS ─────────────────────────────────────────
        dcc.Interval(id="tick-iv", interval=4000, n_intervals=0),
        dcc.Store(id="play_store", data=False),
        dcc.Interval(id="date_interval", interval=1000, disabled=True),
        dcc.Store(id="active-tab", data="home"),
    ],
)


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════


@app.callback(
    Output("page-home", "style"),
    Output("page-how", "style"),
    Output("page-battery", "style"),
    Output("nav-home", "className"),
    Output("nav-how", "className"),
    Output("nav-battery", "className"),
    Output("active-tab", "data"),
    Input("nav-home", "n_clicks"),
    Input("nav-how", "n_clicks"),
    Input("nav-battery", "n_clicks"),
    Input("hero-how-btn", "n_clicks"),
    Input("hero-battery-btn", "n_clicks"),
    State("active-tab", "data"),
    prevent_initial_call=True,
)
def switch_tab(n_home, n_how, n_battery, n_hero_how, n_hero_battery, current_tab):
    triggered = ctx.triggered_id
    if triggered in ("nav-how", "hero-how-btn"):
        tab = "how"
    elif triggered in ("nav-battery", "hero-battery-btn"):
        tab = "battery"
    else:
        tab = "home"

    hidden = {"display": "none"}
    visible_home = {"paddingTop": "62px"}
    visible_other = {}

    styles = {
        "home": [visible_home, hidden, hidden],
        "how": [hidden, visible_other, hidden],
        "battery": [hidden, hidden, visible_other],
    }[tab]

    classes = {
        "home": ["nav-btn nav-btn-active", "nav-btn", "nav-btn"],
        "how": ["nav-btn", "nav-btn nav-btn-active", "nav-btn"],
        "battery": ["nav-btn", "nav-btn", "nav-btn nav-btn-active"],
    }[tab]

    return (*styles, *classes, tab)


@app.callback(
    Output("t-lmp", "children"),
    Output("t-sol", "children"),
    Output("t-sur", "children"),
    Input("tick-iv", "n_intervals"),
)
def tick(n):
    rng = random.Random(n)
    return (
        f"${88 + rng.uniform(-8, 12):.1f}/MWh",
        f"{int(38 + rng.uniform(-4, 6))} kW",
        f"{15 + rng.uniform(-3, 5):.1f} kWh",
    )


@app.callback(
    Output("play_store", "data"),
    Input("play_btn", "n_clicks"),
    State("play_store", "data"),
    prevent_initial_call=True,
)
def toggle_play(n_clicks, is_playing):
    return not is_playing


@app.callback(
    Output("date_interval", "disabled"),
    Output("play_btn", "children"),
    Input("play_store", "data"),
    Input("date_str", "value"),
)
def sync_interval(is_playing, date_str):
    if is_playing and date_str < DATE_MAX:
        return False, "⏸"
    return True, "▶"


@app.callback(
    Output("fig_forecast", "figure"),
    Output("fig_soc", "figure"),
    Output("fig_arbitrage", "figure"),
    Output("status_msg", "children"),
    Output("date_str", "value"),
    Output("charts-placeholder", "style"),
    Output("charts-container", "style"),
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
    return (
        fig_forecast,
        fig_soc,
        fig_arbitrage,
        status,
        date_str,
        {"display": "none"},
        {"display": "block"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
