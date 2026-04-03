"""
BorrowWatts — NYC MultiFamily P2P Energy Platform
Full Dash web app with:
  • Home      — animated NYC skyline, live kW windows, value props
  • How It Works — animated SVG P2P energy flow
  • Battery App — Gurobi-style battery arbitrage optimizer
Run: python app.py   → http://127.0.0.1:8050
"""

import random, math
import numpy as np
import dash
from dash import dcc, html, Input, Output, State

# ── Colour palette ────────────────────────────────────────────────────────────
TEAL, NAVY, GOLD   = "#10c9a0", "#0a1223", "#f5a623"
CORAL, GREEN, SKY  = "#ff6b6b", "#2dcb7f", "#38bdf8"
PURPLE, GRAY, WHITE= "#8b5cf6", "#9ca3af", "#ffffff"
FONT  = "'DM Sans','Nunito Sans',sans-serif"
MONO  = "'Space Mono','Courier New',monospace"

# ══════════════════════════════════════════════════════════════════════════════
# DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def make_nyiso_prices(seed=42):
    rng = np.random.default_rng(seed)
    h   = np.arange(24)
    p   = (28 + 12*np.sin((h-6)*np.pi/12)
              +  8*np.sin((h-17)*np.pi/4)
              + rng.standard_normal(24)*2)
    return np.clip(p, 18, 58)


def optimise_bess(prices, cap, soc0, soc_min, soc_max, p_chg, p_dis, eta_c, eta_d):
    """Greedy LP proxy (mimics Gurobi output for demo)."""
    n    = len(prices)
    soc  = np.zeros(n+1);  soc[0] = soc0 * cap
    chg  = np.zeros(n);    dis   = np.zeros(n)
    lo   = np.percentile(prices, 38)
    hi   = np.percentile(prices, 72)
    for t in range(n):
        up  = soc_max*cap - soc[t]
        dn  = soc[t] - soc_min*cap
        if prices[t] <= lo and up > 0.5:
            c = min(p_chg, up/eta_c);  chg[t] = c;  soc[t+1] = soc[t] + c*eta_c
        elif prices[t] >= hi and dn > 0.5:
            d = min(p_dis, dn*eta_d);  dis[t] = d;  soc[t+1] = soc[t] - d/eta_d
        else:
            soc[t+1] = soc[t]
    rev    = float((dis * prices/1000).sum())
    cost   = float((chg * prices/1000).sum())
    cycles = float(dis.sum()/cap) if cap>0 else 0
    return dict(soc=soc, chg=chg, dis=dis,
                revenue=round(rev,2), cost=round(cost,2),
                profit=round(rev-cost,2), cycles=round(cycles,2))


# ══════════════════════════════════════════════════════════════════════════════
# SVG GENERATORS
# ══════════════════════════════════════════════════════════════════════════════
def nyc_skyline():
    """Return inline SVG string for the hero section."""
    rng = random.Random(99)
    buildings = [
        (0,210,65,270,"#0c1a2b"),(60,175,85,305,"#0d1d30"),(140,155,52,325,"#0e2035"),
        (187,180,72,300,"#0c1a2b"),(254,158,57,322,"#0d1d30"),(306,138,48,342,"#0e2035"),
        (349,162,95,318,"#0f2136"),(439,125,62,355,"#0c1a2b"),(496,148,82,332,"#0d1d30"),
        (573,138,57,342,"#0c1a2b"),(625,170,78,310,"#0f2136"),(698,152,47,328,"#0d1d30"),
        (740,133,105,347,"#0c1a2b"),(840,165,62,315,"#0e2035"),(897,143,83,337,"#0f2136"),
        (975,128,57,352,"#0c1a2b"),(1027,158,93,322,"#0d1d30"),(1115,138,62,342,"#0c1a2b"),
        (1172,153,82,327,"#0e2035"),(1249,122,57,358,"#0f2136"),(1301,148,105,332,"#0c1a2b"),
        (1401,158,72,322,"#0d1d30"),(1468,143,62,337,"#0c1a2b"),(1525,132,82,348,"#0e2035"),
        # iconic foreground
        (102,105,47,375,"#0f263f"),(149,94,32,386,"#0f263f"),
        (378,82,62,398,"#102746"),(384,68,22,412,"#102746"),
        (725,72,72,408,"#0f263f"),(757,56,20,424,"#0f263f"),
        (1008,88,57,392,"#102746"),(1290,92,67,388,"#0f263f"),
    ]
    rect_els = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" rx="1"/>'
        for x,y,w,h,c in buildings
    )
    # windows
    win_els = []
    for x,y,w,h,_ in buildings[6:]:
        cols = max(1, w//13); rows = max(1, (480-y)//16)
        for r in range(rows):
            for cl in range(cols):
                wx, wy = x+3+cl*12, y+4+r*15
                b = rng.random()
                if b < 0.32:
                    continue
                kw_pos = rng.random() > 0.35
                col = "#f5d97a" if kw_pos else "#f8706a"
                win_els.append(
                    f'<rect x="{wx}" y="{wy}" width="8" height="11" '
                    f'fill="{col}" rx="1" opacity="{min(0.92,b+0.1):.2f}"/>'
                )
    # kW labels
    labels = [
        (130,148,"+8.4 kW",True),(398,115,"+12 kW",True),(748,102,"+6 kW",True),
        (230,188,"-3.1 kW",False),(585,172,"+4.8 kW",True),
        (1028,126,"-1.9 kW",False),(862,158,"+9.2 kW",True),(1312,130,"+5 kW",True),
    ]
    lbl_els = "".join(
        f'<g transform="translate({lx},{ly})">'
        f'<rect x="-3" y="-13" width="{len(txt)*7+8}" height="17" rx="4" fill="{NAVY}" opacity="0.88"/>'
        f'<text font-family="monospace" font-size="10" fill="{TEAL if pos else CORAL}" font-weight="700">{txt}</text>'
        f'</g>'
        for lx,ly,txt,pos in labels
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
  {lbl_els}
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

  <!-- Connector lines -->
  <line x1="350" y1="52" x2="350" y2="172" stroke="#f5a623" stroke-width="2.2" stroke-dasharray="6,4" opacity=".6" marker-end="url(#mb)"/>
  <line x1="350" y1="368" x2="350" y2="248" stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".6" marker-end="url(#ma)"/>
  <line x1="640" y1="210" x2="430" y2="210" stroke="#38bdf8" stroke-width="2" stroke-dasharray="8,5" opacity=".4" marker-end="url(#me)"/>
  <line x1="272" y1="168" x2="158" y2="98"  stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#ma)"/>
  <line x1="268" y1="210" x2="76"  y2="210" stroke="#10c9a0" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#ma)"/>
  <line x1="272" y1="252" x2="156" y2="322" stroke="#f5a623" stroke-width="2.2" stroke-dasharray="6,4" opacity=".7" marker-end="url(#mb)"/>
  <line x1="428" y1="168" x2="542" y2="98"  stroke="#ff6b6b" stroke-width="2.2" stroke-dasharray="6,4" opacity=".65" marker-end="url(#mc)"/>
  <line x1="428" y1="252" x2="542" y2="322" stroke="#8b5cf6" stroke-width="2.2" stroke-dasharray="6,4" opacity=".65" marker-end="url(#md)"/>

  <!-- Animated dots -->
  <circle r="5" fill="#f5a623" opacity=".9"><animateMotion dur="1.8s" repeatCount="indefinite" path="M350,52 L350,182"/></circle>
  <circle r="5" fill="#10c9a0" opacity=".9"><animateMotion dur="2.4s" repeatCount="indefinite" path="M350,368 L350,238"/></circle>
  <circle r="4" fill="#10c9a0" opacity=".85"><animateMotion dur="2.1s" repeatCount="indefinite" begin=".5s" path="M272,168 L158,98"/></circle>
  <circle r="4" fill="#10c9a0" opacity=".85"><animateMotion dur="1.9s" repeatCount="indefinite" begin=".9s" path="M268,210 L76,210"/></circle>
  <circle r="4" fill="#f5a623" opacity=".85"><animateMotion dur="2.3s" repeatCount="indefinite" begin=".3s" path="M272,252 L156,322"/></circle>
  <circle r="4" fill="#ff6b6b" opacity=".8" ><animateMotion dur="2.0s" repeatCount="indefinite" begin="1.1s" path="M428,168 L542,98"/></circle>
  <circle r="4" fill="#8b5cf6" opacity=".8" ><animateMotion dur="2.5s" repeatCount="indefinite" begin=".7s" path="M428,252 L542,322"/></circle>

  <!-- HUB -->
  <circle cx="350" cy="210" r="42" fill="#0a1223" stroke="#10c9a0" stroke-width="2.5"/>
  <circle cx="350" cy="210" r="42" fill="none" stroke="#10c9a0" stroke-width="1.2" opacity=".3">
    <animate attributeName="r" from="42" to="62" dur="2.5s" repeatCount="indefinite"/>
    <animate attributeName="opacity" from=".3" to="0" dur="2.5s" repeatCount="indefinite"/>
  </circle>
  <text x="350" y="205" text-anchor="middle" font-size="18">🏢</text>
  <text x="350" y="222" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="monospace" font-weight="700">BESS HUB</text>

  <!-- SOLAR -->
  <circle cx="350" cy="38" r="29" fill="#1a1800" stroke="#f5a623" stroke-width="2"/>
  <text x="350" y="33" text-anchor="middle" font-size="16">☀️</text>
  <text x="350" y="46" text-anchor="middle" fill="#f5a623" font-size="9" font-family="monospace">SOLAR</text>
  <rect x="314" y="52" width="72" height="15" rx="7" fill="#2a1c00"/>
  <text x="350" y="64" text-anchor="middle" fill="#f5a623" font-size="10" font-family="monospace" font-weight="800">+42 kW</text>

  <!-- BATTERY -->
  <circle cx="350" cy="382" r="29" fill="#001a14" stroke="#10c9a0" stroke-width="2"/>
  <text x="350" y="377" text-anchor="middle" font-size="16">🔋</text>
  <text x="350" y="390" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="monospace">BESS 72%</text>

  <!-- GRID -->
  <circle cx="658" cy="210" r="27" fill="#00101a" stroke="#38bdf8" stroke-width="2"/>
  <text x="658" y="205" text-anchor="middle" font-size="15">🔌</text>
  <text x="658" y="218" text-anchor="middle" fill="#38bdf8" font-size="8" font-family="monospace">CON ED</text>

  <!-- Apt nodes LEFT -->
  <circle cx="140" cy="85" r="25" fill="#001a10" stroke="#10c9a0" stroke-width="2"/>
  <text x="140" y="80" text-anchor="middle" font-size="14">🏠</text>
  <text x="140" y="93" text-anchor="middle" fill="#10c9a0" font-size="8" font-family="monospace">Sophie 3A</text>
  <rect x="112" y="98" width="58" height="14" rx="7" fill="#001a10"/>
  <text x="141" y="110" text-anchor="middle" fill="#10c9a0" font-size="9" font-family="monospace" font-weight="700">wants 5 kWh</text>

  <circle cx="56" cy="210" r="25" fill="#001a10" stroke="#10c9a0" stroke-width="2"/>
  <text x="56" y="205" text-anchor="middle" font-size="14">🏠</text>
  <text x="56" y="218" text-anchor="middle" fill="#10c9a0" font-size="8" font-family="monospace">James 1B</text>
  <rect x="24" y="223" width="64" height="14" rx="7" fill="#001a10"/>
  <text x="56" y="235" text-anchor="middle" fill="#2dcb7f" font-size="9" font-family="monospace" font-weight="700">buying 3 kWh</text>

  <circle cx="138" cy="334" r="25" fill="#1a1200" stroke="#f5a623" stroke-width="2"/>
  <text x="138" y="329" text-anchor="middle" font-size="14">🏠</text>
  <text x="138" y="342" text-anchor="middle" fill="#f5a623" font-size="8" font-family="monospace">Marcus 2C</text>
  <rect x="110" y="347" width="58" height="14" rx="7" fill="#1a1200"/>
  <text x="139" y="359" text-anchor="middle" fill="#f5a623" font-size="9" font-family="monospace" font-weight="700">selling 3 kWh</text>

  <!-- Apt nodes RIGHT -->
  <circle cx="560" cy="85" r="25" fill="#1a0000" stroke="#ff6b6b" stroke-width="2"/>
  <text x="560" y="80" text-anchor="middle" font-size="14">🏠</text>
  <text x="560" y="93" text-anchor="middle" fill="#ff6b6b" font-size="8" font-family="monospace">Priya 5A</text>
  <rect x="532" y="98" width="56" height="14" rx="7" fill="#1a0000"/>
  <text x="560" y="110" text-anchor="middle" fill="#ff6b6b" font-size="9" font-family="monospace" font-weight="700">needs 8 kWh</text>

  <circle cx="560" cy="334" r="25" fill="#0d001a" stroke="#8b5cf6" stroke-width="2"/>
  <text x="560" y="329" text-anchor="middle" font-size="14">🏠</text>
  <text x="560" y="342" text-anchor="middle" fill="#8b5cf6" font-size="8" font-family="monospace">Aisha 7B</text>
  <rect x="532" y="347" width="56" height="14" rx="7" fill="#0d001a"/>
  <text x="560" y="359" text-anchor="middle" fill="#8b5cf6" font-size="9" font-family="monospace" font-weight="700">wants 6 kWh</text>

  <!-- Legend -->
  <rect x="12" y="392" width="300" height="20" rx="6" fill="#ffffff0d"/>
  <circle cx="25" cy="402" r="4" fill="#f5a623"/>
  <text x="33" y="406" fill="#f5a623" font-size="9" font-family="monospace">Solar</text>
  <circle cx="70" cy="402" r="4" fill="#10c9a0"/>
  <text x="78" y="406" fill="#10c9a0" font-size="9" font-family="monospace">P2P Buy</text>
  <circle cx="132" cy="402" r="4" fill="#ff6b6b"/>
  <text x="140" y="406" fill="#ff6b6b" font-size="9" font-family="monospace">Demand</text>
  <circle cx="200" cy="402" r="4" fill="#38bdf8"/>
  <text x="208" y="406" fill="#38bdf8" font-size="9" font-family="monospace">Grid backup</text>
</svg>"""


# ══════════════════════════════════════════════════════════════════════════════
# PLOTLY CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════
BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=FONT, color=GRAY, size=11),
    margin=dict(l=8,r=8,t=38,b=8),
    xaxis=dict(gridcolor="#1e3a5f28", zerolinecolor="#1e3a5f28", color=GRAY),
    yaxis=dict(gridcolor="#1e3a5f28", zerolinecolor="#1e3a5f28", color=GRAY),
    legend=dict(bgcolor="rgba(0,0,0,0)", font_size=10),
)

def build_price_fig(prices):
    import plotly.graph_objects as go
    h   = list(range(24))
    lo  = float(np.percentile(prices,38))
    hi  = float(np.percentile(prices,72))
    mn  = float(prices.mean())
    lo_cnt = int((prices<=lo).sum())
    hi_cnt = int((prices>=hi).sum())
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h, y=prices.tolist(), name="NYISO LMP",
        line=dict(color=SKY,width=2.5), fill="tozeroy",
        fillcolor="rgba(56,189,248,0.06)"))
    fig.add_hrect(y0=float(min(prices))-1, y1=lo,
        fillcolor="rgba(16,201,160,0.09)", line_width=0,
        annotation_text="Charge zone", annotation_font_color=TEAL,
        annotation_position="top left", annotation_font_size=9)
    fig.add_hrect(y0=hi, y1=float(max(prices))+1,
        fillcolor="rgba(255,107,107,0.09)", line_width=0,
        annotation_text="Discharge zone", annotation_font_color=CORAL,
        annotation_position="top left", annotation_font_size=9)
    fig.add_hline(y=mn, line_dash="dash", line_color=GRAY,
        annotation_text=f"Mean ${mn:.1f}/MWh",
        annotation_font_color=GRAY, annotation_position="bottom right",
        annotation_font_size=9)
    spread = float(max(prices)-min(prices))
    fig.update_layout(**BASE, height=230, showlegend=False,
        title=dict(text=(f"Price Forecast — Spread: ${spread:.1f}/MWh "
                         f"(${float(min(prices)):.1f}–${float(max(prices)):.1f}) | "
                         f"Low zones: {lo_cnt} (charge) · High zones: {hi_cnt} (discharge)"),
                   font=dict(size=10,color=GRAY)),
        xaxis_title="Hour of Day", yaxis_title="Price ($/MWh)")
    return fig


def build_dispatch_fig(prices, result, cap):
    import plotly.graph_objects as go
    h    = list(range(24))
    h24  = list(range(25))
    lo   = float(np.percentile(prices,38))
    hi   = float(np.percentile(prices,72))
    colors = [TEAL if p<=lo else CORAL if p>=hi else "#374151" for p in prices]
    fig  = go.Figure()
    fig.add_trace(go.Bar(x=h, y=prices.tolist(), name="Price ($/MWh)",
        marker_color=colors, marker_opacity=0.5, yaxis="y"))
    fig.add_trace(go.Bar(x=h, y=result["chg"].tolist(), name="Charge (MW)",
        marker_color=TEAL, yaxis="y2", offsetgroup=1))
    fig.add_trace(go.Bar(x=h, y=(-result["dis"]).tolist(), name="Discharge (MW)",
        marker_color=CORAL, yaxis="y2", offsetgroup=1))
    fig.add_trace(go.Scatter(x=h24, y=result["soc"].tolist(),
        name=f"SoC (MWh)", mode="lines+markers",
        line=dict(color=PURPLE,width=2.5), marker=dict(size=5,color=PURPLE),
        yaxis="y3"))
    fig.update_layout(**BASE, height=285, barmode="overlay",
        title=dict(text="Price Candles & Battery State-of-Charge",
                   font=dict(size=11,color=GRAY)),
        xaxis=dict(title="Hour of Day", gridcolor="#1e3a5f28", color=GRAY),
        yaxis=dict(title="Price ($/MWh)", gridcolor="#1e3a5f28", color=GRAY),
        yaxis2=dict(title="Power (MW)", overlaying="y", side="right",
                    showgrid=False, color=GRAY),
        yaxis3=dict(title=f"SoC (MWh)", overlaying="y", side="right",
                    position=0.93, showgrid=False, color=PURPLE),
        legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)", font_size=10))
    return fig


def build_soc_fig(result, cap, soc_min, soc_max):
    import plotly.graph_objects as go
    h24 = list(range(25))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h24, y=result["soc"].tolist(),
        name="SoC (MWh)", line=dict(color=PURPLE,width=2.5),
        fill="tozeroy", fillcolor="rgba(139,92,246,0.09)"))
    fig.add_hline(y=soc_max*cap, line_dash="dot", line_color=TEAL,
        annotation_text="Max SoC", annotation_font_color=TEAL,
        annotation_font_size=9, annotation_position="bottom right")
    fig.add_hline(y=soc_min*cap, line_dash="dot", line_color=CORAL,
        annotation_text="Min SoC", annotation_font_color=CORAL,
        annotation_font_size=9, annotation_position="top right")
    fig.update_layout(**BASE, height=200, showlegend=False,
        title=dict(text="Battery State of Charge",
                   font=dict(size=11,color=GRAY)),
        xaxis_title="Hour", yaxis_title="SoC (MWh)")
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# UI COMPONENT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def badge(text, color=TEAL):
    return html.Span(text, style={
        "background":f"{color}22","color":color,"fontSize":"0.6rem",
        "fontWeight":800,"padding":"2px 9px","borderRadius":"20px",
        "border":f"1px solid {color}44","letterSpacing":"0.08em",
    })

def section_lbl(text):
    return html.Div(text, style={
        "fontSize":"0.68rem","letterSpacing":"0.28em","textTransform":"uppercase",
        "color":TEAL,"fontWeight":700,"marginBottom":"0.65rem",
    })

def vcard(icon, title, body, accent=TEAL):
    return html.Div([
        html.Div(icon, style={"fontSize":"1.75rem","marginBottom":"0.7rem"}),
        html.Div(title, style={"fontFamily":MONO,"fontSize":"0.95rem","color":WHITE,
                               "marginBottom":"0.4rem","fontWeight":700}),
        html.Div(body,  style={"fontSize":"0.84rem","color":GRAY,"lineHeight":"1.65"}),
    ], style={
        "background":"#111827","border":"1px solid #1e3a5f",
        "borderRadius":"12px","padding":"1.6rem",
        "borderTop":f"3px solid {accent}",
    })

def step_row(num, title, body):
    return html.Div([
        html.Div(str(num), style={
            "width":"34px","height":"34px","borderRadius":"50%","flexShrink":0,
            "background":NAVY,"color":TEAL,"border":f"2px solid {TEAL}",
            "display":"flex","alignItems":"center","justifyContent":"center",
            "fontFamily":MONO,"fontWeight":700,"fontSize":"0.82rem",
        }),
        html.Div([
            html.Div(title,style={"color":WHITE,"fontWeight":700,
                                  "marginBottom":"3px","fontSize":"0.93rem"}),
            html.Div(body, style={"color":GRAY,"fontSize":"0.83rem","lineHeight":"1.65"}),
        ]),
    ], style={"display":"flex","gap":"1rem","alignItems":"flex-start","marginBottom":"1.2rem"})

def mini_kpi(label, val, col=TEAL):
    return html.Div([
        html.Div(val,   style={"color":col,"fontFamily":MONO,"fontSize":"1.35rem","fontWeight":700}),
        html.Div(label, style={"color":GRAY,"fontSize":"0.7rem","marginTop":"2px"}),
    ], style={
        "background":"#ffffff08","border":"1px solid #1e3a5f33",
        "borderRadius":"8px","padding":"0.8rem 1rem",
        "flex":1,"textAlign":"center",
    })

def slider_row(label, sid, mn, mx, val, step):
    return html.Div([
        html.Div([
            html.Span(label, style={"color":GRAY,"fontSize":"0.8rem"}),
            html.Span(str(val), id=f"{sid}-v",
                style={"color":TEAL,"fontFamily":MONO,"fontSize":"0.8rem","fontWeight":700}),
        ], style={"display":"flex","justifyContent":"space-between","marginBottom":"3px"}),
        dcc.Slider(id=sid, min=mn, max=mx, step=step, value=val, marks=None,
                   tooltip={"always_visible":False}, updatemode="drag"),
    ], style={"marginBottom":"1rem"})


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
skyline_svg = nyc_skyline()   # pre-render once

app = dash.Dash(__name__, suppress_callback_exceptions=True,
    meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}],
    title="BorrowWatts — NYC Energy")
server = app.server

app.layout = html.Div(style={"fontFamily":FONT,"background":NAVY,"color":"#e2e8f0"}, children=[

    # ── NAV ───────────────────────────────────────────────────────────────
    # Global CSS is loaded automatically from assets/styles.css
    html.Nav(style={
        "position":"fixed","top":0,"left":0,"right":0,"zIndex":999,
        "display":"flex","alignItems":"center","justifyContent":"space-between",
        "padding":"0 2.5rem","height":"62px",
        "background":"rgba(10,18,35,0.94)","backdropFilter":"blur(12px)",
        "borderBottom":"1px solid rgba(255,255,255,0.06)",
    }, children=[
        html.Div([
            html.Span("Borrow", style={"color":WHITE,"fontFamily":MONO,"fontWeight":900,"fontSize":"1.38rem"}),
            html.Span("Watts", style={"color":TEAL, "fontFamily":MONO,"fontWeight":900,"fontSize":"1.38rem"}),
            badge("NYC","#10c9a0"),
        ], style={"display":"flex","alignItems":"center","gap":"6px"}),
        html.Div([
            html.A("Home",         href="#home",    style={"color":"rgba(255,255,255,0.65)","fontSize":"0.82rem","fontWeight":700,"letterSpacing":"0.06em"}),
            html.A("How It Works", href="#how",     style={"color":"rgba(255,255,255,0.65)","fontSize":"0.82rem","fontWeight":700,"letterSpacing":"0.06em"}),
            html.A("Battery App",  href="#battery", style={"color":"rgba(255,255,255,0.65)","fontSize":"0.82rem","fontWeight":700,"letterSpacing":"0.06em"}),
        ], style={"display":"flex","gap":"2rem"}),
        html.Button("Get Early Access", style={
            "background":TEAL,"color":NAVY,"border":"none","borderRadius":"4px",
            "padding":"9px 22px","fontSize":"0.8rem","fontWeight":800,
            "letterSpacing":"0.06em","cursor":"pointer",
        }),
    ]),

    html.Main([

        # ══════════════════════════════════════════════════════════════════
        # SECTION 1 — HERO
        # ══════════════════════════════════════════════════════════════════
        html.Section(id="home", style={
            "background":NAVY,"position":"relative","minHeight":"100vh",
            "display":"flex","flexDirection":"column",
            "alignItems":"center","justifyContent":"flex-end",
            "overflow":"hidden","paddingTop":"62px",
            "isolation":"isolate",
        }, children=[

            # Hero copy
            html.Div([
                html.Div("NYC'S ENERGY SHARING NETWORK", style={
                    "fontSize":"0.68rem","letterSpacing":"0.3em","color":TEAL,
                    "fontWeight":700,"marginBottom":"1rem","textAlign":"center",
                }),
                html.H1([
                    "Your building generates power.", html.Br(),
                    html.Span("Your neighbours need it.", style={"color":TEAL}),
                ], style={
                    "fontFamily":MONO,"fontSize":"clamp(2rem,4.5vw,3.5rem)",
                    "color":WHITE,"lineHeight":1.1,"textAlign":"center",
                    "marginBottom":"1.1rem","letterSpacing":"-0.02em",
                }),
                html.P(
                    "BorrowWatts connects multifamily buildings across NYC so residents "
                    "can trade solar & battery energy at half the Con Ed rate — "
                    "powered by real-time P2P auctions and Gurobi optimisation.",
                    style={"color":"rgba(255,255,255,0.6)","fontSize":"1rem",
                           "lineHeight":"1.75","maxWidth":"500px",
                           "margin":"0 auto 1.8rem","textAlign":"center"},
                ),
                html.Div([
                    html.Button("Start Trading", style={
                        "background":TEAL,"color":NAVY,"border":"none",
                        "borderRadius":"4px","padding":"12px 28px",
                        "fontSize":"0.86rem","fontWeight":800,"cursor":"pointer",
                    }),
                    html.Button("How It Works →", style={
                        "background":"transparent","color":WHITE,
                        "border":"1.5px solid rgba(255,255,255,0.28)",
                        "borderRadius":"4px","padding":"12px 28px",
                        "fontSize":"0.86rem","fontWeight":800,"cursor":"pointer",
                    }),
                ], style={"display":"flex","gap":"1rem","justifyContent":"center","flexWrap":"wrap"}),
            ], style={"position":"relative","zIndex":10,"padding":"0 1rem","marginBottom":"18px"}),

            # Live ticker
            html.Div([
                html.Div([
                    html.Span("NYISO Zone J",style={"color":"rgba(255,255,255,0.38)","fontSize":"0.7rem","fontFamily":MONO}),
                    html.Span(id="t-lmp",children="$94.2/MWh",style={"color":TEAL,"fontFamily":MONO,"fontSize":"0.7rem","marginLeft":"5px"}),
                ],style={"display":"flex","alignItems":"center"}),
                html.Div([
                    html.Span("BorrowWatt",style={"color":"rgba(255,255,255,0.38)","fontSize":"0.7rem","fontFamily":MONO}),
                    html.Span("$0.11/kWh",style={"color":GREEN,"fontFamily":MONO,"fontSize":"0.7rem","marginLeft":"5px"}),
                    html.Span("▼ Con Ed",style={"color":GREEN,"fontSize":"0.62rem"}),
                ],style={"display":"flex","alignItems":"center","gap":"3px"}),
                html.Div([
                    html.Span("Con Ed Retail",style={"color":"rgba(255,255,255,0.38)","fontSize":"0.7rem","fontFamily":MONO}),
                    html.Span("$0.22/kWh",style={"color":CORAL,"fontFamily":MONO,"fontSize":"0.7rem","marginLeft":"5px"}),
                ],style={"display":"flex","alignItems":"center"}),
                html.Div([
                    html.Span("Building Solar",style={"color":"rgba(255,255,255,0.38)","fontSize":"0.7rem","fontFamily":MONO}),
                    html.Span(id="t-sol",children="42 kW",style={"color":GOLD,"fontFamily":MONO,"fontSize":"0.7rem","marginLeft":"5px"}),
                ],style={"display":"flex","alignItems":"center"}),
                html.Div([
                    html.Span("Surplus",style={"color":"rgba(255,255,255,0.38)","fontSize":"0.7rem","fontFamily":MONO}),
                    html.Span(id="t-sur",children="18.4 kWh",style={"color":TEAL,"fontFamily":MONO,"fontSize":"0.7rem","marginLeft":"5px"}),
                ],style={"display":"flex","alignItems":"center"}),
            ], style={
                "display":"flex","gap":"2rem","alignItems":"center","flexWrap":"wrap",
                "background":"rgba(0,0,0,0.45)","padding":"8px 2rem",
                "borderTop":"1px solid rgba(255,255,255,0.05)","width":"100%",
                "position":"relative","zIndex":10,
            }),

            # ── Real building photo — full bleed background ──────────────
            html.Img(
                src="/assets/nyc_building.jpeg",
                style={
                    "position":"absolute","inset":0,
                    "width":"100%","height":"100%",
                    "objectFit":"cover","objectPosition":"center 30%",
                    "zIndex":1,
                    # desaturate + darken so text and SVG pop
                    "filter":"saturate(0.45) brightness(0.38)",
                },
            ),
            # Gradient vignette — deepens toward the sky top and bottom
            html.Div(style={
                "position":"absolute","inset":0,"zIndex":2,
                "background":(
                    "linear-gradient("
                    "to bottom,"
                    f"{NAVY}ee 0%,"
                    "rgba(10,18,35,0.55) 38%,"
                    "rgba(10,18,35,0.55) 58%,"
                    f"{NAVY}cc 78%,"
                    f"{NAVY} 100%"
                    ")"
                ),
            }),
            # NYC Skyline SVG — sits on top of photo + vignette
            html.Div(
                dcc.Markdown(skyline_svg, dangerously_allow_html=True),
                style={"position":"absolute","bottom":0,"left":0,"right":0,"zIndex":3}),

            dcc.Interval(id="tick-iv", interval=4000, n_intervals=0),
        ]),

        # ══════════════════════════════════════════════════════════════════
        # SECTION 2 — VALUE PROPS
        # ══════════════════════════════════════════════════════════════════
        html.Section(style={"background":"#f5f6f0","padding":"5rem 2rem"}, children=[
            html.Div([
                section_lbl("WHY BORROWWATTS"),
                html.H2("Cheaper energy. Cleaner grid. Better buildings.",
                    style={"fontFamily":MONO,"fontSize":"clamp(1.5rem,3vw,2.3rem)",
                           "color":NAVY,"marginBottom":"0.75rem","letterSpacing":"-0.02em"}),
                html.P("NYC's multifamily housing sits on untapped solar and battery capacity. "
                       "We make it tradeable — between apartments, floors, and buildings — "
                       "with zero hardware and no utility approval needed.",
                    style={"color":"#555","fontSize":"0.95rem","lineHeight":"1.75","maxWidth":"540px"}),
            ], style={"maxWidth":"1100px","margin":"0 auto 2.5rem"}),

            html.Div([
                vcard("⚡","Real-Time P2P Auctions",
                    "Every 15 minutes our double-auction engine matches buyers and sellers "
                    "within your building at prices 40–55% below Con Ed.",TEAL),
                vcard("🔋","Gurobi Battery Dispatch",
                    "Our LP optimizer (Gurobi) determines the exact charge/discharge schedule "
                    "to maximise arbitrage revenue from NYISO price spreads.",GOLD),
                vcard("🗺️","Grid-Aware Trading",
                    "Trades respect feeder capacity and local marginal prices so your "
                    "building never contributes to grid congestion.",SKY),
                vcard("📋","LL97 Compliance",
                    "Every peer-traded kWh reduces your building's carbon intensity "
                    "and counts toward Local Law 97 targets automatically.",GREEN),
                vcard("🤝","Neighbour-First Matching",
                    "Energy stays hyper-local: floor → building → block. "
                    "Con Ed is only the fallback, not the default.",PURPLE),
                vcard("📱","Resident App",
                    "Tenants see their surplus, place sell offers, and collect "
                    "micropayments directly in the BorrowWatts app.",CORAL),
            ], style={
                "maxWidth":"1100px","margin":"0 auto",
                "display":"grid","gridTemplateColumns":"repeat(auto-fill,minmax(290px,1fr))",
                "gap":"1.25rem",
            }),

            # KPI band
            html.Div([
                html.Div([
                    html.Div("$0.11",   style={"fontFamily":MONO,"fontSize":"2.2rem","color":TEAL,"fontWeight":700}),
                    html.Div("P2P rate / kWh", style={"fontSize":"0.72rem","color":GRAY,"marginTop":"3px","letterSpacing":"0.06em"}),
                ], style={"textAlign":"center","background":"#111827","border":"1px solid #1e3a5f",
                          "borderRadius":"12px","padding":"1.25rem 1.5rem"}),
                html.Div([
                    html.Div("50%",    style={"fontFamily":MONO,"fontSize":"2.2rem","color":GREEN,"fontWeight":700}),
                    html.Div("Savings vs Con Ed", style={"fontSize":"0.72rem","color":GRAY,"marginTop":"3px","letterSpacing":"0.06em"}),
                ], style={"textAlign":"center","background":"#111827","border":"1px solid #1e3a5f",
                          "borderRadius":"12px","padding":"1.25rem 1.5rem"}),
                html.Div([
                    html.Div("100+",   style={"fontFamily":MONO,"fontSize":"2.2rem","color":GOLD,"fontWeight":700}),
                    html.Div("NYC Buildings", style={"fontSize":"0.72rem","color":GRAY,"marginTop":"3px","letterSpacing":"0.06em"}),
                ], style={"textAlign":"center","background":"#111827","border":"1px solid #1e3a5f",
                          "borderRadius":"12px","padding":"1.25rem 1.5rem"}),
                html.Div([
                    html.Div("LL97",   style={"fontFamily":MONO,"fontSize":"2.2rem","color":SKY,"fontWeight":700}),
                    html.Div("Compliant", style={"fontSize":"0.72rem","color":GRAY,"marginTop":"3px","letterSpacing":"0.06em"}),
                ], style={"textAlign":"center","background":"#111827","border":"1px solid #1e3a5f",
                          "borderRadius":"12px","padding":"1.25rem 1.5rem"}),
            ], style={
                "maxWidth":"900px","margin":"3rem auto 0",
                "display":"grid","gridTemplateColumns":"repeat(4,1fr)","gap":"1rem",
                "background":NAVY,"borderRadius":"16px","padding":"2rem",
            }),
        ]),

        # # ══════════════════════════════════════════════════════════════════
        # # SECTION 3 — HOW IT WORKS  (P2P animation)
        # # ══════════════════════════════════════════════════════════════════
        # html.Section(id="how", style={"background":NAVY,"padding":"5rem 2rem"}, children=[
        #     html.Div([
        #         section_lbl("HOW IT WORKS"),
        #         html.H2("Energy flows between apartments in real time.",
        #             style={"fontFamily":MONO,"fontSize":"clamp(1.5rem,3vw,2.3rem)",
        #                    "color":WHITE,"marginBottom":"0.5rem","letterSpacing":"-0.02em"}),
        #         html.P("Solar from the rooftop, battery storage from the basement, "
        #                "and peer trades between units — matched every 15 minutes by our "
        #                "double-auction engine.",
        #             style={"color":GRAY,"fontSize":"0.93rem","lineHeight":"1.75","maxWidth":"500px"}),
        #     ], style={"maxWidth":"1100px","margin":"0 auto 2.5rem"}),

        #     html.Div([
        #         # Animation
        #         html.Div([
        #             dcc.Markdown(P2P_SVG, dangerously_allow_html=True),
        #             html.Div([
        #                 html.Div("🟢  Live", style={"color":GREEN,"fontWeight":700,"fontSize":"0.8rem"}),
        #                 html.Span("Apt 4B sold 4.2 kWh to Sophie in 3A · 2 min ago",
        #                     style={"color":GRAY,"fontSize":"0.78rem","marginLeft":"8px"}),
        #             ], style={"display":"flex","alignItems":"center","marginTop":"1rem",
        #                       "padding":"10px 14px","background":"#ffffff08","borderRadius":"8px"}),
        #             html.Div([
        #                 html.Div("⚡  BESS", style={"color":TEAL,"fontWeight":700,"fontSize":"0.8rem"}),
        #                 html.Span("Discharged 12 kWh during peak · saved $1.32",
        #                     style={"color":GRAY,"fontSize":"0.78rem","marginLeft":"8px"}),
        #             ], style={"display":"flex","alignItems":"center","marginTop":"8px",
        #                       "padding":"10px 14px","background":"#ffffff08","borderRadius":"8px"}),
        #         ], style={"flex":"0 0 auto","width":"min(660px,100%)"}),

        #         # Steps
        #         html.Div([
        #             step_row(1,"Generate",
        #                 "Rooftop solar panels produce power. Surplus beyond apartment "
        #                 "consumption flows to the building BESS hub."),
        #             step_row(2,"Store",
        #                 "The shared battery stores surplus and discharges during NYISO "
        #                 "price peaks, earning arbitrage revenue."),
        #             step_row(3,"Match",
        #                 "Our double-auction engine runs every 15 minutes. Apartments "
        #                 "submit bids & asks; the clearing price always beats Con Ed."),
        #             step_row(4,"Settle",
        #                 "Micropayments are calculated automatically. Sellers earn credits, "
        #                 "buyers save money, building earns a platform fee."),
        #             step_row(5,"Report",
        #                 "LL97 compliance reports generated automatically. Every peer-traded "
        #                 "kWh reduces your carbon intensity score."),
        #         ], style={"flex":1,"minWidth":"260px"}),
        #     ], style={
        #         "maxWidth":"1100px","margin":"0 auto",
        #         "display":"flex","gap":"3rem","alignItems":"flex-start","flexWrap":"wrap",
        #     }),
        # ]),

        # # ══════════════════════════════════════════════════════════════════
        # # SECTION 4 — BATTERY OPTIMIZER APP
        # # ══════════════════════════════════════════════════════════════════
        # html.Section(id="battery", style={"background":"#0d1728","padding":"5rem 2rem"}, children=[
        #     html.Div([
        #         section_lbl("BATTERY ARBITRAGE OPTIMIZER"),
        #         html.H2("Gurobi-powered BESS dispatch.",
        #             style={"fontFamily":MONO,"fontSize":"clamp(1.4rem,3vw,2.2rem)",
        #                    "color":WHITE,"marginBottom":"0.4rem","letterSpacing":"-0.02em"}),
        #         html.P("Adjust battery parameters and see the optimal charge/discharge schedule "
        #                "vs today's NYISO Zone J price forecast. In production we solve the "
        #                "exact LP with Gurobi 11.",
        #             style={"color":GRAY,"fontSize":"0.88rem","lineHeight":"1.75","maxWidth":"600px"}),
        #     ], style={"maxWidth":"1200px","margin":"0 auto 2rem"}),

        #     html.Div([
        #         # ── LEFT PANEL ────────────────────────────────────────────
        #         html.Div([
        #             html.Div("Battery Parameters", style={
        #                 "fontFamily":MONO,"color":WHITE,"fontWeight":700,
        #                 "fontSize":"0.93rem","marginBottom":"1.4rem",
        #                 "borderBottom":"1px solid #1e3a5f","paddingBottom":"0.7rem",
        #             }),
        #             slider_row("Capacity (MWh)",          "s-cap",   1,  100, 20,  1),
        #             slider_row("Initial SoC (fraction)",  "s-soc0",  0,    1, 0.5, 0.05),
        #             slider_row("Min SoC",                 "s-smin",  0,  0.5, 0.1, 0.05),
        #             slider_row("Max SoC",                 "s-smax", 0.5,   1, 0.95,0.05),
        #             slider_row("Max Charge (MW)",         "s-pchg",  0.5, 20, 5,  0.5),
        #             slider_row("Max Discharge (MW)",      "s-pdis",  0.5, 20, 5,  0.5),
        #             slider_row("Charge Efficiency η_c",   "s-ec",   0.7,   1, 0.95,0.01),
        #             slider_row("Discharge Efficiency η_d","s-ed",   0.7,   1, 0.92,0.01),

        #             html.Button("⚡  Optimise Schedule", id="run-btn", n_clicks=0, style={
        #                 "width":"100%","background":TEAL,"color":NAVY,"border":"none",
        #                 "borderRadius":"6px","padding":"12px","fontSize":"0.88rem",
        #                 "fontWeight":800,"cursor":"pointer","marginTop":"1.4rem",
        #                 "letterSpacing":"0.05em",
        #             }),

        #             html.Div(id="kpi-panel", style={"marginTop":"1.4rem"}),

        #             html.Div([
        #                 html.Div("🔧 Tech Stack", style={
        #                     "fontFamily":MONO,"color":TEAL,"fontSize":"0.7rem",
        #                     "fontWeight":700,"marginBottom":"0.4rem","letterSpacing":"0.1em",
        #                 }),
        #                 html.Div("Gurobi 11 · Python · Dash · NYISO API",
        #                     style={"color":GRAY,"fontSize":"0.76rem"}),
        #                 html.Div("min Σ(c_t·p_chg_t) − Σ(c_t·p_dis_t)",
        #                     style={"color":GRAY,"fontSize":"0.73rem","fontFamily":MONO,"marginTop":"4px"}),
        #                 html.Div("s.t. SoC dynamics, power & ramp limits",
        #                     style={"color":GRAY,"fontSize":"0.71rem","fontFamily":MONO}),
        #             ], style={
        #                 "background":"#ffffff07","borderRadius":"8px","padding":"0.9rem",
        #                 "marginTop":"1.1rem","border":"1px solid #1e3a5f33",
        #             }),
        #         ], style={
        #             "background":"#111827","border":"1px solid #1e3a5f",
        #             "borderRadius":"14px","padding":"1.6rem",
        #             "width":"min(310px,100%)","flexShrink":0,
        #         }),

        #         # ── RIGHT: charts ─────────────────────────────────────────
        #         html.Div([
        #             dcc.Graph(id="g-price",    config={"displayModeBar":False},
        #                       style={"marginBottom":"0.75rem"}),
        #             dcc.Graph(id="g-dispatch", config={"displayModeBar":False},
        #                       style={"marginBottom":"0.75rem"}),
        #             dcc.Graph(id="g-soc",      config={"displayModeBar":False}),
        #             dcc.Store(id="px-store",   data=make_nyiso_prices().tolist()),
        #         ], style={"flex":1,"minWidth":0}),

        #     ], style={
        #         "maxWidth":"1200px","margin":"0 auto",
        #         "display":"flex","gap":"1.5rem","alignItems":"flex-start","flexWrap":"wrap",
        #     }),
        # ]),

        # ══════════════════════════════════════════════════════════════════
        # FOOTER
        # ══════════════════════════════════════════════════════════════════
        html.Footer(style={
            "background":"#060c16","padding":"2.5rem 2rem","textAlign":"center",
            "borderTop":"1px solid #1e3a5f",
        }, children=[
            html.Div([
                html.Span("Borrow",style={"color":WHITE,"fontFamily":MONO,"fontWeight":900}),
                html.Span("Watts", style={"color":TEAL, "fontFamily":MONO,"fontWeight":900}),
            ], style={"marginBottom":"0.5rem"}),
            html.P("NYC's P2P Energy Trading Platform · © 2025 BorrowWatts Inc.",
                style={"color":GRAY,"fontSize":"0.76rem"}),
            html.P("Built with Dash · Plotly · Gurobi · NYISO API",
                style={"color":"#2a3748","fontSize":"0.7rem","marginTop":"4px","fontFamily":MONO}),
        ]),
    ]),
])


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

# ── Ticker ────────────────────────────────────────────────────────────────────
@app.callback(
    Output("t-lmp","children"), Output("t-sol","children"), Output("t-sur","children"),
    Input("tick-iv","n_intervals"),
)
def tick(n):
    rng = random.Random(n)
    return (f"${88+rng.uniform(-8,12):.1f}/MWh",
            f"{int(38+rng.uniform(-4,6))} kW",
            f"{15+rng.uniform(-3,5):.1f} kWh")


# ── Slider display values ─────────────────────────────────────────────────────
for sid in ["s-cap","s-soc0","s-smin","s-smax","s-pchg","s-pdis","s-ec","s-ed"]:
    @app.callback(Output(f"{sid}-v","children"), Input(sid,"value"),
                  prevent_initial_call=False)
    def _show(v):
        return str(v)


# ── Battery optimiser ─────────────────────────────────────────────────────────
@app.callback(
    Output("g-price","figure"), Output("g-dispatch","figure"),
    Output("g-soc","figure"),   Output("kpi-panel","children"),
    Input("run-btn","n_clicks"), Input("px-store","data"),
    State("s-cap","value"),  State("s-soc0","value"), State("s-smin","value"),
    State("s-smax","value"), State("s-pchg","value"), State("s-pdis","value"),
    State("s-ec","value"),   State("s-ed","value"),
    prevent_initial_call=False,
)
def run_opt(n, px_data, cap, soc0, smin, smax, pchg, pdis, ec, ed):
    prices = np.array(px_data) if px_data else make_nyiso_prices()
    res    = optimise_bess(prices, cap, soc0, smin, smax, pchg, pdis, ec, ed)

    pf = build_price_fig(prices)
    df = build_dispatch_fig(prices, res, cap)
    sf = build_soc_fig(res, cap, smin, smax)

    kpis = html.Div([
        html.Div([mini_kpi("Revenue", f"${res['revenue']:.2f}", GREEN),
                  mini_kpi("Cost",    f"${res['cost']:.2f}",    CORAL)],
            style={"display":"flex","gap":"0.5rem","marginBottom":"0.5rem"}),
        html.Div([mini_kpi("Net Profit", f"${res['profit']:.2f}", TEAL),
                  mini_kpi("Cycles",     f"{res['cycles']:.2f}",  GOLD)],
            style={"display":"flex","gap":"0.5rem"}),
    ])
    return pf, df, sf, kpis


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=8050)
