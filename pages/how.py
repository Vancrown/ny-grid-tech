"""
pages/how.py — BorrowWatts: How It Works
Rich P2P energy-flow animation closely matching the demo HTML style,
with live animated dots, hub-pulse, neighbor cards, and activity feed.
"""

import dash
from dash import dcc, html, Input, Output, callback

dash.register_page(__name__, path="/how", name="How It Works")

# ── Light palette ──────────────────────────────────────────────────────────
TEAL    = "#0DB8A3"
TEALDK  = "#0a9688"
TEALLT  = "#E8FAF8"
NAVY    = "#0B1F3A"
GOLD    = "#F5A623"
GOLDLT  = "#FDE9C2"
CORAL   = "#FF6B6B"
CORALLT = "#FFE8E8"
GREEN   = "#2DCB7F"
GREENLT = "#D5F5E5"
SKY     = "#38BDF8"
SKYLT   = "#E0F4FF"
PURPLE  = "#8B5CF6"
PURPLT  = "#EDE9FE"
WHITE   = "#FFFFFF"
GRAY50  = "#F9FAFB"
GRAY100 = "#F3F4F6"
GRAY200 = "#E5E7EB"
GRAY400 = "#9CA3AF"
GRAY600 = "#6B7280"
GRAY800 = "#1F2937"

MONO = "'Space Mono','Courier New',monospace"
FONT = "'Nunito','DM Sans',sans-serif"
SANS = "'Nunito Sans','DM Sans',sans-serif"


# ══════════════════════════════════════════════════════════════════════════
# FULL P2P FLOW ANIMATION (closely matches borrowwatt_demo.html)
# ══════════════════════════════════════════════════════════════════════════
P2P_FLOW_HTML = """
<div style="
  position:relative;height:340px;
  background:white;border-radius:16px;
  border:1.5px solid #E5E7EB;
  box-shadow:0 4px 20px rgba(0,0,0,0.07);
  overflow:hidden;
">
  <!-- SVG lines + animated dots -->
  <svg id="flowSvg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;">
    <defs>
      <filter id="glow">
        <feGaussianBlur stdDeviation="2.5" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
    </defs>
  </svg>

  <!-- HUB -->
  <div id="hub" style="
    position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
    width:72px;height:72px;border-radius:50%;
    background:#0B1F3A;border:2.5px solid #0DB8A3;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    z-index:5;cursor:default;
    box-shadow:0 0 0 8px rgba(13,184,163,0.12),0 8px 24px rgba(0,0,0,0.18);
    animation:hubpulse 3s ease-in-out infinite;
  ">
    <span style="font-size:1.4rem;">🏢</span>
    <span style="font-size:0.55rem;font-family:monospace;color:#0DB8A3;font-weight:700;letter-spacing:0.04em;">BESS HUB</span>
  </div>

  <!-- SOLAR node -->
  <div class="flow-node" id="node-solar" style="position:absolute;left:50%;top:6%;transform:translateX(-50%);z-index:4;">
    <div class="node-circle" style="background:#FDE9C2;border:2.5px solid #F5A623;color:#F5A623;">☀️</div>
    <div class="node-label" style="color:#F5A623;">Rooftop Solar</div>
    <div class="node-kw" style="background:#FDE9C2;color:#B7660A;" id="n-solar">+42 kW</div>
  </div>

  <!-- BATTERY node -->
  <div class="flow-node" id="node-batt" style="position:absolute;left:50%;bottom:5%;transform:translateX(-50%);z-index:4;">
    <div class="node-circle" style="background:#E8FAF8;border:2.5px solid #0DB8A3;color:#0DB8A3;">🔋</div>
    <div class="node-label" style="color:#0DB8A3;">Building BESS</div>
    <div class="node-kw" style="background:#E8FAF8;color:#0a9688;" id="n-batt">72% · 144kWh</div>
  </div>

  <!-- GRID node -->
  <div class="flow-node" id="node-grid" style="position:absolute;right:3%;top:50%;transform:translateY(-50%);z-index:4;">
    <div class="node-circle" style="background:#E0F4FF;border:2.5px solid #38BDF8;color:#38BDF8;">🔌</div>
    <div class="node-label" style="color:#38BDF8;">Con Ed Grid</div>
    <div class="node-kw" style="background:#E0F4FF;color:#0369A1;">Backup</div>
  </div>

  <!-- Sophie 3A -->
  <div class="flow-node apt-node" id="node-sophie" style="position:absolute;left:7%;top:50%;transform:translateY(-50%);z-index:4;"
       onclick="openTradeModal('Sophie','3A','buying',0.11,'D7F9F1','2BAF7E')">
    <div class="node-circle" style="background:#D7F9F1;border:2.5px solid #2BAF7E;color:#2BAF7E;">🏠</div>
    <div class="node-label" style="color:#2DCB7F;">Apt 3A · Sophie</div>
    <div class="node-kw" style="background:#D5F5E5;color:#1A8C56;">wants 5 kWh</div>
  </div>

  <!-- Marcus 2C -->
  <div class="flow-node apt-node" id="node-marcus" style="position:absolute;left:14%;top:16%;z-index:4;"
       onclick="openTradeModal('Marcus','2C','selling',0.09,'FDE9C2','E8A020')">
    <div class="node-circle" style="background:#FDE9C2;border:2.5px solid #F5A623;color:#F5A623;">🏠</div>
    <div class="node-label" style="color:#F5A623;">Apt 2C · Marcus</div>
    <div class="node-kw" style="background:#FDE9C2;color:#B7660A;">selling 3 kWh</div>
  </div>

  <!-- Priya 5A -->
  <div class="flow-node apt-node" id="node-priya" style="position:absolute;right:13%;top:16%;z-index:4;"
       onclick="openTradeModal('Priya','5A','buying',0.11,'EDE9FE','8B5CF6')">
    <div class="node-circle" style="background:#EDE9FE;border:2.5px solid #8B5CF6;color:#8B5CF6;">🏠</div>
    <div class="node-label" style="color:#8B5CF6;">Apt 5A · Priya</div>
    <div class="node-kw" style="background:#EDE9FE;color:#6D28D9;">wants 8 kWh</div>
  </div>
</div>

<!-- Trade modal -->
<div id="tradeModal" style="
  display:none;position:fixed;inset:0;z-index:999;
  background:rgba(11,31,58,0.45);backdrop-filter:blur(4px);
  align-items:center;justify-content:center;padding:1rem;
" onclick="if(event.target===this)closeModal()">
  <div style="
    background:white;border-radius:18px;width:100%;max-width:380px;
    box-shadow:0 16px 48px rgba(0,0,0,0.18);
    animation:modalIn 0.22s ease;
  ">
    <div style="padding:1.25rem 1.5rem 0.9rem;border-bottom:1.5px solid #F3F4F6;display:flex;align-items:center;justify-content:space-between;">
      <div style="font-family:monospace;font-weight:800;font-size:1rem;color:#0B1F3A;" id="modal-title">⚡ Trade Energy</div>
      <button onclick="closeModal()" style="background:none;border:none;font-size:1.2rem;cursor:pointer;color:#9CA3AF;">✕</button>
    </div>
    <div style="padding:1.25rem 1.5rem;">
      <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <div style="width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;" id="modal-icon-wrap">🏠</div>
        <div>
          <div style="font-weight:800;font-size:0.88rem;color:#1F2937;" id="modal-neighbor"></div>
          <div style="font-size:0.73rem;color:#9CA3AF;" id="modal-desc"></div>
        </div>
        <div style="margin-left:auto;" id="modal-rate-badge"></div>
      </div>
      <div style="display:flex;align-items:center;gap:0.75rem;background:#F9FAFB;border-radius:10px;padding:0.5rem;margin-bottom:1rem;justify-content:center;">
        <button onclick="adjustAmt(-1)" style="width:34px;height:34px;border-radius:50%;background:white;border:1.5px solid #E5E7EB;font-size:1.1rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;">−</button>
        <div style="text-align:center;">
          <div style="font-family:monospace;font-size:1.8rem;font-weight:900;color:#0B1F3A;min-width:70px;text-align:center;" id="modal-amt">5</div>
          <div style="font-size:0.78rem;color:#9CA3AF;font-weight:600;">kWh</div>
        </div>
        <button onclick="adjustAmt(+1)" style="width:34px;height:34px;border-radius:50%;background:white;border:1.5px solid #E5E7EB;font-size:1.1rem;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;">+</button>
      </div>
      <div style="background:#F9FAFB;border-radius:10px;padding:1rem;border:1.5px solid #E5E7EB;margin-bottom:0.9rem;">
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.82rem;"><span style="color:#6B7280;">Energy amount</span><span style="font-weight:700;" id="ts-kwh">5 kWh</span></div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.82rem;"><span style="color:#6B7280;">P2P rate</span><span style="font-weight:700;" id="ts-rate">$0.11/kWh</span></div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.82rem;"><span style="color:#6B7280;">vs Con Ed retail</span><span style="color:#2DCB7F;font-weight:700;">Save 50% 🎉</span></div>
        <div style="display:flex;justify-content:space-between;padding:6px 0 2px;font-size:0.86rem;font-weight:800;border-top:1.5px dashed #E5E7EB;margin-top:4px;"><span style="color:#6B7280;">Total</span><span style="color:#0DB8A3;" id="ts-total">$0.55</span></div>
      </div>
      <div style="background:#D5F5E5;border-radius:8px;padding:0.65rem;font-size:0.74rem;color:#1A8C56;font-weight:600;margin-bottom:0.9rem;">
        🌿 Avoids <span id="ts-co2">2.3</span> kg CO₂ vs Con Ed
      </div>
    </div>
    <div style="padding:0.75rem 1.5rem 1.25rem;display:flex;gap:0.5rem;">
      <button onclick="closeModal()" style="background:#F3F4F6;color:#6B7280;border:none;border-radius:999px;padding:0.7rem 1.1rem;font-size:0.85rem;font-weight:700;cursor:pointer;">Cancel</button>
      <button onclick="confirmTrade()" style="flex:1;background:#0DB8A3;color:white;border:none;border-radius:999px;padding:0.7rem;font-size:0.88rem;font-weight:800;cursor:pointer;" id="modal-confirm-btn">Confirm Trade ⚡</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div id="bw-toast" style="
  position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%) translateY(80px);
  background:#0B1F3A;color:white;padding:0.7rem 1.5rem;
  border-radius:999px;font-weight:700;font-size:0.84rem;z-index:1000;
  transition:transform 0.3s ease;white-space:nowrap;
  box-shadow:0 8px 24px rgba(0,0,0,0.18);
"></div>

<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Nunito+Sans:wght@400;600&display=swap');

@keyframes hubpulse {
  0%,100%{box-shadow:0 0 0 8px rgba(13,184,163,0.12),0 8px 24px rgba(0,0,0,0.18);}
  50%{box-shadow:0 0 0 16px rgba(13,184,163,0.06),0 8px 24px rgba(0,0,0,0.18);}
}
@keyframes modalIn { from{transform:scale(0.94) translateY(10px);opacity:0} to{transform:scale(1) translateY(0);opacity:1} }
@keyframes ripple { 0%{transform:scale(1);opacity:0.3} 100%{transform:scale(1.35);opacity:0} }

.flow-node { display:flex;flex-direction:column;align-items:center;gap:4px;cursor:default; }
.apt-node { cursor:pointer; }
.apt-node:hover .node-circle { transform:scale(1.1); }
.node-circle {
  width:52px;height:52px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:1.25rem;position:relative;
  box-shadow:0 4px 12px rgba(0,0,0,0.10);
  transition:transform 0.2s;
}
.node-circle::after {
  content:'';position:absolute;inset:-5px;border-radius:50%;
  border:2px solid currentColor;opacity:0.25;
  animation:ripple 2s infinite;
}
.node-label { font-size:0.65rem;font-weight:700;text-align:center;max-width:72px;line-height:1.3; }
.node-kw {
  font-family:monospace;font-size:0.7rem;font-weight:800;
  padding:2px 8px;border-radius:999px;
}
</style>

<script>
var modalAmt=5, modalRate=0.11, modalAction='sell';

function openTradeModal(name,apt,theyWant,rate,avatarBg,avatarColor){
  modalAmt=5; modalRate=rate;
  modalAction = theyWant==='buying'?'sell':'buy';
  document.getElementById('modal-title').textContent =
    modalAction==='sell'?'💚 Sell energy to '+name.split(' ')[0]:'⚡ Buy from '+name.split(' ')[0];
  document.getElementById('modal-neighbor').textContent = name+' · Apt '+apt;
  document.getElementById('modal-desc').textContent =
    theyWant==='buying'?'Wants to buy energy from you':'Has surplus energy for sale';
  var w = document.getElementById('modal-icon-wrap');
  w.style.background='#'+avatarBg; w.style.color='#'+avatarColor;
  document.getElementById('modal-rate-badge').innerHTML =
    '<span style="background:#D5F5E5;color:#1A8C56;padding:3px 10px;border-radius:999px;font-size:0.7rem;font-weight:800;">$'+rate+'/kWh</span>';
  document.getElementById('ts-rate').textContent='$'+rate+'/kWh';
  updateCalc();
  var m=document.getElementById('tradeModal');
  m.style.display='flex';
}
function closeModal(){ document.getElementById('tradeModal').style.display='none'; }
function adjustAmt(d){ modalAmt=Math.max(1,Math.min(20,modalAmt+d)); document.getElementById('modal-amt').textContent=modalAmt; updateCalc(); }
function updateCalc(){
  document.getElementById('ts-kwh').textContent=modalAmt+' kWh';
  document.getElementById('ts-total').textContent='$'+(modalAmt*modalRate).toFixed(2);
  document.getElementById('ts-co2').textContent=(modalAmt*0.46).toFixed(1);
}
function confirmTrade(){
  closeModal();
  var v=modalAction==='sell'?'Sold':'Bought', s=modalAction==='sell'?'+':'-';
  showToast((modalAction==='sell'?'💚 ':'⚡ ')+v+' '+modalAmt+' kWh! '+s+'$'+(modalAmt*modalRate).toFixed(2));
}
function showToast(msg){
  var t=document.getElementById('bw-toast'); t.textContent=msg;
  t.style.transform='translateX(-50%) translateY(0)';
  setTimeout(function(){ t.style.transform='translateX(-50%) translateY(80px)'; },2800);
}

/* Draw animated SVG flow lines */
function drawFlows(){
  var svg=document.getElementById('flowSvg');
  if(!svg) return;
  var container=svg.parentElement;
  var cw=container.offsetWidth, ch=container.offsetHeight;
  var cx=cw/2, cy=ch/2;

  var nodes=[
    {id:'node-solar',  x:cx,       y:ch*0.11, col:'#F5A623'},
    {id:'node-batt',   x:cx,       y:ch*0.88, col:'#0DB8A3'},
    {id:'node-grid',   x:cw*0.94,  y:cy,      col:'#38BDF8'},
    {id:'node-sophie', x:cw*0.10,  y:cy,      col:'#2DCB7F'},
    {id:'node-marcus', x:cw*0.17,  y:ch*0.22, col:'#F5A623'},
    {id:'node-priya',  x:cw*0.83,  y:ch*0.22, col:'#8B5CF6'},
  ];

  svg.innerHTML='';

  nodes.forEach(function(n,i){
    /* line */
    var ln=document.createElementNS('http://www.w3.org/2000/svg','line');
    ln.setAttribute('x1',cx); ln.setAttribute('y1',cy);
    ln.setAttribute('x2',n.x); ln.setAttribute('y2',n.y);
    ln.setAttribute('stroke',n.col); ln.setAttribute('stroke-width','2');
    ln.setAttribute('stroke-opacity','0.35'); ln.setAttribute('stroke-dasharray','7,4');
    svg.appendChild(ln);

    /* animated travelling dot */
    var c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('r','4.5'); c.setAttribute('fill',n.col); c.setAttribute('opacity','0.9');
    var pid='mp'+i;
    var pe=document.createElementNS('http://www.w3.org/2000/svg','path');
    pe.setAttribute('id',pid);
    pe.setAttribute('d','M'+cx+','+cy+' L'+n.x+','+n.y);
    pe.setAttribute('fill','none'); svg.appendChild(pe);
    var am=document.createElementNS('http://www.w3.org/2000/svg','animateMotion');
    am.setAttribute('dur',(1.4+Math.random()*1.4).toFixed(1)+'s');
    am.setAttribute('repeatCount','indefinite');
    var mp=document.createElementNS('http://www.w3.org/2000/svg','mpath');
    mp.setAttributeNS('http://www.w3.org/1999/xlink','href','#'+pid);
    am.appendChild(mp); c.appendChild(am); svg.appendChild(c);
  });
}

/* Ticker */
function tickLive(){
  var el=document.getElementById('n-solar');
  if(el) el.textContent='+'+(38+Math.floor(Math.random()*8))+' kW';
  var bl=document.getElementById('n-batt');
  if(bl){ var p=(68+Math.random()*20).toFixed(0); bl.textContent=p+'% · '+(p*2)+' kWh'; }
}

setTimeout(drawFlows,180);
window.addEventListener('resize',drawFlows);
setInterval(tickLive,4000);
</script>
"""


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════
def pill(text, bg=TEALLT, color=TEAL):
    return html.Span(text, style={
        "background": bg, "color": color, "fontSize": "0.62rem",
        "fontWeight": 800, "padding": "3px 10px", "borderRadius": "999px",
        "letterSpacing": "0.05em", "textTransform": "uppercase",
        "border": f"1.5px solid {color}33",
    })


def step_card(num, title, body, accent=TEAL):
    return html.Div([
        html.Div(str(num), style={
            "width": "32px", "height": "32px", "borderRadius": "50%",
            "background": accent, "color": WHITE,
            "display": "flex", "alignItems": "center", "justifyContent": "center",
            "fontFamily": MONO, "fontWeight": 700, "fontSize": "0.8rem",
            "flexShrink": 0,
        }),
        html.Div([
            html.Div(title, style={"fontWeight": 800, "color": NAVY,
                                   "marginBottom": "3px", "fontSize": "0.9rem"}),
            html.Div(body,  style={"color": GRAY600, "fontSize": "0.82rem", "lineHeight": "1.6"}),
        ]),
    ], style={"display": "flex", "gap": "0.9rem",
              "alignItems": "flex-start", "marginBottom": "1.2rem"})


def faq(q, a):
    return html.Div([
        html.Div(q, style={"fontWeight": 800, "color": NAVY,
                           "fontSize": "0.9rem", "marginBottom": "0.4rem"}),
        html.Div(a, style={"color": GRAY600, "fontSize": "0.83rem", "lineHeight": "1.65"}),
    ], style={
        "background": WHITE, "border": f"1.5px solid {GRAY200}",
        "borderLeft": f"3.5px solid {TEAL}",
        "borderRadius": "10px", "padding": "1.15rem",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.04)",
    })


def mechanism_card(icon, title, body, accent=TEAL):
    return html.Div([
        html.Div(icon, style={"fontSize": "1.6rem", "marginBottom": "0.6rem"}),
        html.Div(title, style={
            "fontFamily": MONO, "color": accent, "fontSize": "0.72rem",
            "fontWeight": 700, "marginBottom": "0.4rem",
            "textTransform": "uppercase", "letterSpacing": "0.06em",
        }),
        html.Div(body, style={"color": GRAY600, "fontSize": "0.83rem", "lineHeight": "1.65"}),
    ], style={
        "background": WHITE, "border": f"1.5px solid {GRAY200}",
        "borderRadius": "12px", "padding": "1.4rem", "flex": 1,
        "boxShadow": "0 2px 6px rgba(0,0,0,0.04)",
    })


def neighbor_row(emoji, name, apt, status, kw_text, action, pill_bg, pill_col, btn_col):
    return html.Div([
        html.Div(emoji, style={
            "width": "36px", "height": "36px", "borderRadius": "50%",
            "background": pill_bg, "display": "flex",
            "alignItems": "center", "justifyContent": "center",
            "fontSize": "1rem", "flexShrink": 0,
        }),
        html.Div([
            html.Div(name, style={"fontWeight": 700, "fontSize": "0.83rem", "color": NAVY}),
            html.Div(apt,  style={"fontSize": "0.7rem", "color": GRAY400, "marginTop": "1px"}),
        ], style={"flex": 1}),
        html.Div([
            html.Span(status, style={
                "background": pill_bg, "color": pill_col,
                "fontSize": "0.62rem", "fontWeight": 800,
                "padding": "2px 8px", "borderRadius": "999px",
                "textTransform": "uppercase", "letterSpacing": "0.04em",
            }),
            html.Div(kw_text, style={"fontSize": "0.78rem", "fontWeight": 700,
                                     "color": GRAY800, "marginTop": "2px", "textAlign": "right"}),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "flex-end", "gap": "2px"}),
        html.Span(action, style={
            "background": btn_col, "color": WHITE,
            "fontSize": "0.7rem", "fontWeight": 700,
            "padding": "4px 12px", "borderRadius": "999px",
            "cursor": "pointer", "flexShrink": 0,
        }),
    ], style={
        "display": "flex", "alignItems": "center", "gap": "0.75rem",
        "padding": "0.8rem 1rem", "background": GRAY50,
        "borderRadius": "10px", "border": f"1.5px solid {GRAY200}",
        "marginBottom": "0.6rem",
        "borderLeft": f"3px solid {btn_col}",
    })


# ══════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════
layout = html.Div(style={"background": GRAY50, "fontFamily": SANS}, children=[

    # Page header
    html.Section(style={
        "background": WHITE, "paddingTop": "88px", "paddingBottom": "2.5rem",
        "paddingLeft": "2rem", "paddingRight": "2rem",
        "borderBottom": f"1.5px solid {GRAY200}",
    }, children=[
        html.Div([
            pill("HOW IT WORKS"),
            html.H1("Energy flows between apartments in real time.",
                style={"fontFamily": MONO, "fontSize": "clamp(1.6rem,4vw,2.5rem)",
                       "color": NAVY, "letterSpacing": "-0.02em",
                       "marginTop": "0.75rem", "marginBottom": "0.75rem"}),
            html.P("Watch the live animation below — solar from the rooftop, "
                   "battery storage from the basement, and peer trades between "
                   "units, matched every 15 minutes by our double-auction engine.",
                style={"color": GRAY600, "fontSize": "0.95rem",
                       "lineHeight": "1.75", "maxWidth": "560px"}),
        ], style={"maxWidth": "1100px", "margin": "0 auto"}),
    ]),

    # ── MAIN: animation left, steps + neighbors right ──────────────────
    html.Section(style={"background": GRAY50, "padding": "3.5rem 2rem"}, children=[
        html.Div([

            # LEFT: animation + live feed
            html.Div([
                html.Iframe(
                    srcDoc=P2P_FLOW_HTML,
                    style={
                        "width": "100%",
                        "height": "980px",
                        "border": "none",
                        "background": "transparent",
                        "display": "block",
                    },
                ),

                # Activity feed below the map
                html.Div([
                    html.Div([
                        html.Div([
                            html.Div("📜 Recent Trades", style={
                                "fontWeight": 800, "fontSize": "0.88rem", "color": NAVY,
                                "fontFamily": MONO,
                            }),
                        ]),
                    ], style={
                        "padding": "0.9rem 1.1rem",
                        "borderBottom": f"1.5px solid {GRAY100}",
                    }),
                    *[html.Div([
                        html.Div(icon, style={
                            "width": "30px", "height": "30px", "borderRadius": "9px",
                            "background": ibg, "display": "flex",
                            "alignItems": "center", "justifyContent": "center",
                            "fontSize": "0.8rem", "flexShrink": 0,
                        }),
                        html.Div([
                            html.Div(main, style={"fontSize": "0.79rem", "fontWeight": 600,
                                                   "color": GRAY800, "lineHeight": 1.4}),
                            html.Div(time, style={"fontSize": "0.67rem", "color": GRAY400, "marginTop": "1px"}),
                        ], style={"flex": 1}),
                        html.Div(amt, style={"fontSize": "0.79rem", "fontWeight": 800, "color": amtcol, "flexShrink": 0}),
                    ], style={
                        "display": "flex", "alignItems": "flex-start", "gap": "0.65rem",
                        "padding": "0.65rem 1.1rem", "borderBottom": f"1px solid {GRAY100}",
                    })
                    for icon,ibg,main,time,amt,amtcol in [
                        ("✅", GREENLT,
                         html.Span(["You sold ", html.Strong("4.2 kWh"), " to Sophie in Apt 3A"]),
                         "2 min ago · Solar surplus", "+$0.46", GREEN),
                        ("⚡", TEALLT,
                         html.Span(["BESS discharged ", html.Strong("12 kWh"), " to building load"]),
                         "18 min ago · Peak avoidance", "$1.32", TEAL),
                        ("☀️", GOLDLT,
                         html.Span(["You bought ", html.Strong("2.8 kWh"), " from Marcus in Apt 2C"]),
                         "1 hr ago · Cheapest rate", "-$0.31", GOLD),
                        ("🏆", PURPLT,
                         html.Span(["Building hit ", html.Strong("100% renewable"), " for 3 hrs straight!"]),
                         "3 hrs ago · New building record", "🎉", PURPLE),
                    ]],
                ], style={
                    "background": WHITE, "borderRadius": "14px",
                    "border": f"1.5px solid {GRAY200}",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
                    "marginTop": "1.25rem", "overflow": "hidden",
                }),
            ], style={"flex": "0 0 auto", "width": "min(550px,100%)"}),

            # RIGHT: steps + neighbour cards
            html.Div([
                # Steps
                html.Div("How the market works", style={
                    "fontFamily": MONO, "color": NAVY, "fontWeight": 700,
                    "fontSize": "0.93rem", "marginBottom": "1.1rem",
                }),
                step_card(1, "Generate",
                    "Rooftop solar panels produce power. Any surplus beyond "
                    "apartment consumption flows to the building BESS hub.", TEAL),
                step_card(2, "Store",
                    "The shared battery stores surplus and discharges during "
                    "NYISO price peaks, earning arbitrage revenue.", GOLD),
                step_card(3, "Match",
                    "Double-auction engine runs every 15 min. Apartments submit "
                    "bids & asks; clearing price always beats Con Ed.", GREEN),
                step_card(4, "Settle",
                    "Micropayments calculated automatically. Sellers earn credits, "
                    "buyers save money, building earns a platform fee.", TEAL),
                step_card(5, "Report",
                    "LL97 compliance reports generated automatically. Every "
                    "peer-traded kWh reduces your carbon intensity score.", PURPLE),

                html.Hr(style={"borderColor": GRAY200, "margin": "1.5rem 0"}),

                # Neighbour cards
                html.Div("Neighbours trading now", style={
                    "fontFamily": MONO, "color": NAVY, "fontWeight": 700,
                    "fontSize": "0.88rem", "marginBottom": "0.9rem",
                    "display": "flex", "alignItems": "center", "gap": "0.5rem",
                }),
                html.Div([
                    html.Span("●", style={"color": GREEN, "fontSize": "0.5rem"}),
                    html.Span(" Live", style={"fontSize": "0.7rem", "fontWeight": 700, "color": GREEN}),
                ], style={"marginBottom": "0.85rem"}),
                neighbor_row("👩","Sophie Chen","Apt 3A · needs energy · EV charging",
                             "Wants to Buy","5 kWh","Sell →",GREENLT,GREEN,TEAL),
                neighbor_row("👨","Marcus Johnson","Apt 2C · has solar surplus",
                             "Selling","3 kWh · $0.09","Buy →",GOLDLT,GOLD,GREEN),
                neighbor_row("👩‍💼","Priya Patel","Apt 5A · HVAC running hot",
                             "Wants to Buy","8 kWh","Sell →",PURPLT,PURPLE,TEAL),
                html.Div([
                    html.Div("🧑", style={
                        "width": "36px", "height": "36px", "borderRadius": "50%",
                        "background": GRAY100, "display": "flex", "alignItems": "center",
                        "justifyContent": "center", "fontSize": "1rem", "flexShrink": 0,
                    }),
                    html.Div([
                        html.Div("James Park", style={"fontWeight": 700, "fontSize": "0.83rem", "color": NAVY}),
                        html.Div("Apt 1B · balanced", style={"fontSize": "0.7rem", "color": GRAY400}),
                    ], style={"flex": 1}),
                    html.Span("Idle", style={
                        "background": GRAY100, "color": GRAY400,
                        "fontSize": "0.62rem", "fontWeight": 800,
                        "padding": "2px 8px", "borderRadius": "999px",
                    }),
                ], style={
                    "display": "flex", "alignItems": "center", "gap": "0.75rem",
                    "padding": "0.8rem 1rem", "background": GRAY50,
                    "borderRadius": "10px", "border": f"1.5px solid {GRAY200}",
                }),
            ], style={"flex": 1, "minWidth": "280px"}),

        ], style={
            "maxWidth": "1100px", "margin": "0 auto",
            "display": "flex", "gap": "2.5rem",
            "alignItems": "flex-start", "flexWrap": "wrap",
        }),
    ]),

    # ── MARKET MECHANISM ─────────────────────────────────────────────────
    html.Section(style={"background": WHITE, "padding": "4rem 2rem"}, children=[
        html.Div([
            pill("THE MARKET MECHANISM"),
            html.H2("Double-auction clearing every 15 minutes.",
                style={"fontFamily": MONO, "fontSize": "clamp(1.2rem,3vw,1.9rem)",
                       "color": NAVY, "marginTop": "0.75rem",
                       "marginBottom": "1.75rem", "letterSpacing": "-0.02em"}),
            html.Div([
                mechanism_card("📨","SUBMIT",
                    "Every apartment submits a bid (buy) or ask (sell) price "
                    "per kWh at each 15-min slot.", TEAL),
                mechanism_card("⚖️","CLEAR",
                    "Bids ≥ asks are matched. Clearing price = midpoint. "
                    "Grid provides any shortfall.", GOLD),
                mechanism_card("💸","SETTLE",
                    "Sellers receive credits, buyers are charged. Net savings "
                    "vs Con Ed posted to the app.", GREEN),
                mechanism_card("📊","REPORT",
                    "LL97 carbon credit automatically logged. NYISO settlement "
                    "reconciled nightly.", PURPLE),
            ], style={"display": "flex", "gap": "1.25rem", "flexWrap": "wrap"}),
        ], style={"maxWidth": "1100px", "margin": "0 auto"}),
    ]),

    # ── FAQ ───────────────────────────────────────────────────────────────
    html.Section(style={"background": GRAY50, "padding": "4rem 2rem"}, children=[
        html.Div([
            pill("FAQ"),
            html.H2("Common questions.",
                style={"fontFamily": MONO, "fontSize": "clamp(1.2rem,3vw,1.9rem)",
                       "color": NAVY, "marginTop": "0.75rem",
                       "marginBottom": "1.75rem", "letterSpacing": "-0.02em"}),
            html.Div([
                faq("Do I need any new hardware?",
                    "No. BorrowWatts works with your existing smart meter and Con Ed AMI data. "
                    "If your building has solar or a BESS we connect to it via API."),
                faq("What if there's no surplus in my building?",
                    "Con Ed remains the fallback. You only trade when there is genuine surplus. "
                    "We never leave you without power."),
                faq("How does the Gurobi optimiser work?",
                    "We solve a linear program every hour: minimise cost of charging minus "
                    "revenue from discharging, subject to SoC bounds, power limits, and ramp "
                    "constraints. Results feed directly into the auction engine."),
                faq("Is this legal in New York?",
                    "Yes. BorrowWatts operates under NYISO's VDER tariff and Con Ed's shared "
                    "billing rules. We handle all regulatory filings on your behalf."),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fill,minmax(420px,1fr))",
                "gap": "1.25rem",
            }),
        ], style={"maxWidth": "1100px", "margin": "0 auto"}),
    ]),

    # ── CTA ───────────────────────────────────────────────────────────────
    html.Section(style={
        "background": NAVY, "padding": "3.5rem 2rem", "textAlign": "center",
    }, children=[
        html.H2("Ready to optimise your building's battery?",
            style={"fontFamily": MONO, "fontSize": "clamp(1.2rem,3vw,1.8rem)",
                   "color": WHITE, "marginBottom": "1.25rem"}),
        dcc.Link(html.Button("Open Battery Arbitrage App →", style={
            "background": TEAL, "color": WHITE, "border": "none",
            "borderRadius": "5px", "padding": "12px 28px",
            "fontSize": "0.88rem", "fontWeight": 800, "cursor": "pointer",
        }), href="/battery"),
    ]),

    # Footer
    html.Footer(style={
        "background": "#060c16", "padding": "2.5rem 2rem", "textAlign": "center",
        "borderTop": "1px solid #1e3a5f",
    }, children=[
        html.Div([
            html.Span("Borrow", style={"color": WHITE, "fontFamily": MONO, "fontWeight": 900}),
            html.Span("Watts",  style={"color": TEAL,  "fontFamily": MONO, "fontWeight": 900}),
        ], style={"marginBottom": "0.4rem"}),
        html.P("NYC's P2P Energy Trading Platform · © 2025 BorrowWatts Inc.",
            style={"color": GRAY400, "fontSize": "0.74rem"}),
        html.P("Built with Dash · Plotly · Gurobi · NYISO API",
            style={"color": "#2a3748", "fontSize": "0.68rem",
                   "marginTop": "3px", "fontFamily": MONO}),
    ]),
])
