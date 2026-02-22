"""
AD-HTC Fuel-Enhanced Gas Power Cycle schematic.
Layout and animation match example-2: fixed viewBox (960×620), explicit coordinates,
SVG animateMotion particles, CSS glow/fan/pump. Values injected from report/boiler/power.
"""

import json
import html

def _s(v, default="—"):
    if v is None:
        return default
    if isinstance(v, float):
        return f"{v:,.2f}" if v < 1e6 else f"{v:,.0f}"
    return str(v)


def build_schematic_html(report: dict | None, boiler_result: dict | None, power_result: dict | None) -> str:
    data = {
        "natural": {
            "avg_m3_day": _s(report.get("avg_daily_m3") if report else None),
            "power_kw": _s(report.get("ignition_power_kw") if report else None),
        } if report else {},
        "boiler": {
            "water_kg": _s(boiler_result.get("boiler_water_capacity_kg") if boiler_result else None),
            "T_steam_C": _s(boiler_result.get("T_steam_C") if boiler_result else None),
        } if boiler_result else {},
        "power": {"net_kwe": _s(power_result.get("Net_Power_kWe") if power_result else None)} if power_result else {},
    }
    data_escaped = html.escape(json.dumps(data, ensure_ascii=False))

    # Same structure as example-2: viewBox 960 620, explicit coords, animateMotion, CSS glow
    html_str = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: linear-gradient(135deg, #0f1117 0%, #1a1d29 100%); overflow: hidden; }}
svg {{ width: 100%; height: 100%; display: block; }}
.box {{ stroke-width: 2; rx: 4; ry: 4; }}
.box-label {{ fill: #fff; font-weight: 700; font-size: 12px; text-anchor: middle; dominant-baseline: central; }}
.box-sub {{ fill: rgba(255,255,255,0.65); font-size: 10px; text-anchor: middle; dominant-baseline: central; }}
.ext-label {{ fill: rgba(255,255,255,0.85); font-size: 11px; font-weight: 600; }}
.pipe {{ fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }}
.pipe-bg {{ fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
.particle {{ opacity: 0.85; }}
@keyframes glow-green {{ 0%,100% {{ filter: drop-shadow(0 0 3px #198754); }} 50% {{ filter: drop-shadow(0 0 14px #22c55e); }} }}
@keyframes glow-orange {{ 0%,100% {{ filter: drop-shadow(0 0 3px #e8590c); }} 50% {{ filter: drop-shadow(0 0 14px #fd7e14); }} }}
@keyframes glow-blue {{ 0%,100% {{ filter: drop-shadow(0 0 3px #0d6efd); }} 50% {{ filter: drop-shadow(0 0 14px #3b82f6); }} }}
@keyframes glow-red {{ 0%,100% {{ filter: drop-shadow(0 0 3px #dc3545); }} 50% {{ filter: drop-shadow(0 0 14px #ef4444); }} }}
@keyframes glow-teal {{ 0%,100% {{ filter: drop-shadow(0 0 3px #0dcaf0); }} 50% {{ filter: drop-shadow(0 0 14px #22d3ee); }} }}
@keyframes glow-purple {{ 0%,100% {{ filter: drop-shadow(0 0 3px #6610f2); }} 50% {{ filter: drop-shadow(0 0 14px #a855f7); }} }}
@keyframes glow-gold {{ 0%,100% {{ filter: drop-shadow(0 0 3px #ffc107); }} 50% {{ filter: drop-shadow(0 0 14px #facc15); }} }}
.g-ad {{ animation: glow-green 3s ease-in-out infinite; }}
.g-boiler {{ animation: glow-orange 3s ease-in-out infinite 0.3s; }}
.g-reactor {{ animation: glow-blue 3s ease-in-out infinite 0.6s; }}
.g-collector {{ animation: glow-teal 3s ease-in-out infinite 0.9s; }}
.g-combust {{ animation: glow-red 3s ease-in-out infinite 1.2s; }}
.g-comp {{ animation: glow-purple 3s ease-in-out infinite 1.5s; }}
.g-turb {{ animation: glow-gold 3s ease-in-out infinite 1.8s; }}
@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
.fan {{ animation: spin 2s linear infinite; transform-origin: center; }}
@keyframes pump-pulse {{ 0%,100% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} }}
.pump-sym {{ animation: pump-pulse 1.5s ease-in-out infinite; }}
</style>
</head>
<body>
<script type="application/json" id="schematic-data">{data_escaped}</script>
<svg viewBox="0 0 960 620" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="a-w" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="rgba(255,255,255,0.6)"/></marker>
    <marker id="a-g" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#22c55e"/></marker>
    <marker id="a-o" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#fd7e14"/></marker>
    <marker id="a-b" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#3b82f6"/></marker>
    <marker id="a-t" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#22d3ee"/></marker>
    <marker id="a-r" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#ef4444"/></marker>
    <marker id="a-p" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#a0a0a0"/></marker>
  </defs>

  <!-- RIGHT: Biomass Feedstock label -->
  <text x="810" y="108" class="ext-label" text-anchor="start" fill="#22c55e">Biomass</text>
  <text x="810" y="124" class="ext-label" text-anchor="start" fill="#22c55e">Feedstock</text>
  <path d="M805,118 L730,118" class="pipe" stroke="#22c55e" marker-end="url(#a-g)"/>

  <!-- AD box (right top) -->
  <g class="g-ad">
    <rect x="640" y="92" width="90" height="52" class="box" fill="#198754" stroke="#22c55e"/>
    <text x="685" y="118" class="box-label">AD</text>
    <text id="val-ad" x="685" y="132" class="box-sub">—</text>
  </g>

  <!-- LEFT: HTC Steam Cycle (Boiler + Reactor) -->
  <text x="200" y="165" class="ext-label" text-anchor="middle" fill="#3b82f6" font-size="12">HTC Steam Cycle</text>
  <g class="g-boiler">
    <rect x="225" y="68" width="110" height="48" class="box" fill="#e8590c" stroke="#fd7e14"/>
    <text x="280" y="92" class="box-label">Boiler</text>
    <text id="val-boiler" x="280" y="106" class="box-sub">—</text>
  </g>
  <g class="g-reactor">
    <rect x="225" y="195" width="110" height="48" class="box" fill="#0d6efd" stroke="#3b82f6"/>
    <text x="280" y="219" class="box-label">Reactor</text>
    <text id="val-reactor" x="280" y="233" class="box-sub">—</text>
  </g>
  <g class="pump-sym">
    <circle cx="145" cy="155" r="18" fill="none" stroke="#3b82f6" stroke-width="2"/>
    <polygon points="137,145 153,155 137,165" fill="#3b82f6" opacity="0.8"/>
  </g>
  <path d="M335,92 L370,92 L370,219 L335,219" class="pipe-bg"/>
  <path d="M335,92 L370,92 L370,219 L335,219" class="pipe" stroke="#fd7e14" marker-end="url(#a-o)"/>
  <path d="M225,219 L145,219 L145,173" class="pipe-bg"/>
  <path d="M225,219 L145,219 L145,173" class="pipe" stroke="#3b82f6"/>
  <path d="M145,137 L145,92 L225,92" class="pipe-bg"/>
  <path d="M145,137 L145,92 L225,92" class="pipe" stroke="#3b82f6" marker-end="url(#a-b)"/>
  <circle r="4" fill="#fd7e14" class="particle"><animateMotion dur="4s" repeatCount="indefinite" path="M335,92 L370,92 L370,219 L335,219"/></circle>
  <circle r="4" fill="#fd7e14" class="particle"><animateMotion dur="4s" repeatCount="indefinite" begin="1.3s" path="M335,92 L370,92 L370,219 L335,219"/></circle>
  <circle r="4" fill="#3b82f6" class="particle"><animateMotion dur="4s" repeatCount="indefinite" path="M225,219 L145,219 L145,92 L225,92"/></circle>
  <circle r="4" fill="#3b82f6" class="particle"><animateMotion dur="4s" repeatCount="indefinite" begin="1.3s" path="M225,219 L145,219 L145,92 L225,92"/></circle>

  <text x="20" y="212" class="ext-label" fill="#22c55e">Biomass</text>
  <text x="20" y="228" class="ext-label" fill="#22c55e">Feedstock</text>
  <path d="M95,219 L225,219" class="pipe" stroke="#22c55e" marker-end="url(#a-g)"/>
  <text x="280" y="280" class="ext-label" text-anchor="middle" fill="#a0a0a0" font-size="10">Volatile Matters</text>
  <text x="280" y="295" class="ext-label" text-anchor="middle" fill="#a0a0a0" font-size="10">and Feedstock Waste</text>
  <path d="M280,243 L280,270" class="pipe" stroke="#a0a0a0" marker-end="url(#a-p)"/>

  <!-- AD to Boiler (top pipe) -->
  <path d="M640,105 L400,105 L400,92 L335,92" class="pipe-bg"/>
  <path d="M640,105 L400,105 L400,92 L335,92" class="pipe" stroke="#22c55e" marker-end="url(#a-g)"/>
  <circle r="4" fill="#22c55e" class="particle"><animateMotion dur="3s" repeatCount="indefinite" path="M640,105 L400,105 L400,92 L335,92"/></circle>
  <circle r="4" fill="#22c55e" class="particle"><animateMotion dur="3s" repeatCount="indefinite" begin="1s" path="M640,105 L400,105 L400,92 L335,92"/></circle>

  <!-- CENTER: Enhanced Biogas Collector -->
  <g class="g-collector">
    <rect x="490" y="175" width="100" height="62" class="box" fill="#0e7490" stroke="#22d3ee"/>
    <text x="540" y="198" class="box-label" font-size="10">Enhanced</text>
    <text x="540" y="213" class="box-label" font-size="10">Biogas</text>
    <text x="540" y="228" class="box-label" font-size="10">Collector</text>
  </g>
  <path d="M685,144 L685,170 L590,170 L590,175" class="pipe-bg"/>
  <path d="M685,144 L685,170 L590,170 L590,175" class="pipe" stroke="#22d3ee" marker-end="url(#a-t)"/>
  <path d="M370,160 L490,160 L490,195" class="pipe-bg"/>
  <path d="M370,160 L490,160 L490,195" class="pipe" stroke="#22d3ee" marker-end="url(#a-t)"/>
  <circle r="3.5" fill="#22d3ee" class="particle"><animateMotion dur="2.5s" repeatCount="indefinite" path="M685,144 L685,170 L590,170 L590,175"/></circle>
  <circle r="3.5" fill="#22d3ee" class="particle"><animateMotion dur="2.5s" repeatCount="indefinite" begin="0.8s" path="M685,144 L685,170 L590,170 L590,175"/></circle>
  <circle r="3.5" fill="#22d3ee" class="particle"><animateMotion dur="2.5s" repeatCount="indefinite" path="M370,160 L490,160 L490,195"/></circle>
  <text x="740" y="198" class="ext-label" fill="#22d3ee" font-size="10">Biogas Distribution</text>
  <text x="740" y="213" class="ext-label" fill="#22d3ee" font-size="10">to Building Envelopes</text>
  <path d="M590,206 L730,206" class="pipe" stroke="#22d3ee" marker-end="url(#a-t)"/>
  <circle r="3" fill="#22d3ee" class="particle"><animateMotion dur="2s" repeatCount="indefinite" path="M590,206 L730,206"/></circle>

  <!-- Biogas Combustion Chamber -->
  <g class="g-combust">
    <rect x="470" y="310" width="140" height="55" class="box" fill="#b91c1c" stroke="#ef4444"/>
    <text x="540" y="330" class="box-label" font-size="11">Biogas Combustion</text>
    <text x="540" y="348" class="box-label" font-size="11">Chamber</text>
  </g>
  <path d="M540,237 L540,310" class="pipe-bg"/>
  <path d="M540,237 L540,310" class="pipe" stroke="#ef4444" marker-end="url(#a-r)"/>
  <circle r="4" fill="#ef4444" class="particle"><animateMotion dur="2s" repeatCount="indefinite" path="M540,237 L540,310"/></circle>
  <circle r="4" fill="#ef4444" class="particle"><animateMotion dur="2s" repeatCount="indefinite" begin="0.7s" path="M540,237 L540,310"/></circle>

  <!-- GAS TURBINE CYCLE: Compressor + Turbine + Generator -->
  <line x1="250" y1="475" x2="750" y2="475" stroke="rgba(255,255,255,0.15)" stroke-width="4" stroke-dasharray="12 6"/>
  <g class="g-comp">
    <polygon points="290,440 380,425 380,525 290,510" fill="#6610f2" stroke="#a855f7" stroke-width="2"/>
    <text x="335" y="475" class="box-label" font-size="11">Compressor</text>
  </g>
  <g class="g-turb">
    <polygon points="620,425 710,440 710,510 620,525" fill="#d97706" stroke="#fbbf24" stroke-width="2"/>
    <text x="665" y="475" class="box-label" font-size="11">Turbine</text>
  </g>
  <rect x="720" y="450" width="90" height="50" class="box" fill="#0e7490" stroke="#22d3ee"/>
  <text x="765" y="468" class="box-label" font-size="10">Generator</text>
  <text id="val-gen" x="765" y="482" class="box-sub">—</text>
  <g class="fan" style="transform-origin: 750px 475px;">
    <line x1="735" y1="475" x2="765" y2="475" stroke="#fbbf24" stroke-width="2.5"/>
    <line x1="750" y1="460" x2="750" y2="490" stroke="#fbbf24" stroke-width="2.5"/>
    <line x1="739" y1="464" x2="761" y2="486" stroke="#fbbf24" stroke-width="2.5"/>
    <line x1="761" y1="464" x2="739" y2="486" stroke="#fbbf24" stroke-width="2.5"/>
  </g>
  <path d="M540,365 L540,425" class="pipe-bg"/>
  <path d="M540,365 L540,425" class="pipe" stroke="#ef4444" marker-end="url(#a-r)"/>
  <path d="M380,460 L470,460 L470,337" class="pipe-bg"/>
  <path d="M380,460 L470,460 L470,337" class="pipe" stroke="#a855f7" marker-end="url(#a-r)"/>
  <path d="M610,337 L610,460 L620,460" class="pipe-bg"/>
  <path d="M610,337 L610,460 L620,460" class="pipe" stroke="#ef4444"/>
  <path d="M710,475 L720,475" class="pipe" stroke="#fbbf24" marker-end="url(#a-t)"/>
  <circle r="4" fill="#a855f7" class="particle"><animateMotion dur="2.5s" repeatCount="indefinite" path="M380,460 L470,460 L470,337"/></circle>
  <circle r="4" fill="#a855f7" class="particle"><animateMotion dur="2.5s" repeatCount="indefinite" begin="0.8s" path="M380,460 L470,460 L470,337"/></circle>
  <circle r="4" fill="#ef4444" class="particle"><animateMotion dur="2s" repeatCount="indefinite" path="M610,337 L610,460 L620,460"/></circle>
  <circle r="4" fill="#ef4444" class="particle"><animateMotion dur="2s" repeatCount="indefinite" begin="0.7s" path="M610,337 L610,460 L620,460"/></circle>

  <text x="220" y="568" class="ext-label" fill="#a0a0a0">Air ↗</text>
  <path d="M260,555 L290,520" class="pipe" stroke="rgba(255,255,255,0.3)" marker-end="url(#a-p)"/>
  <circle r="3" fill="rgba(255,255,255,0.4)" class="particle"><animateMotion dur="1.8s" repeatCount="indefinite" path="M260,555 L290,520"/></circle>
  <circle r="3" fill="rgba(255,255,255,0.4)" class="particle"><animateMotion dur="1.8s" repeatCount="indefinite" begin="0.6s" path="M260,555 L290,520"/></circle>
  <text x="770" y="568" class="ext-label" fill="#a0a0a0">Exhaust Gases</text>
  <path d="M710,520 L760,555" class="pipe" stroke="rgba(255,255,255,0.3)" marker-end="url(#a-p)"/>
  <circle r="3" fill="rgba(255,255,255,0.3)" class="particle"><animateMotion dur="1.8s" repeatCount="indefinite" path="M710,520 L760,555"/></circle>
  <circle r="3" fill="rgba(255,255,255,0.3)" class="particle"><animateMotion dur="1.8s" repeatCount="indefinite" begin="0.6s" path="M710,520 L760,555"/></circle>
</svg>
<script>
(function() {{
  var D = document.getElementById('schematic-data').textContent;
  var data = JSON.parse(D);
  document.getElementById('val-ad').textContent = (data.natural && data.natural.avg_m3_day ? data.natural.avg_m3_day + ' m³/day' : '—');
  document.getElementById('val-boiler').textContent = (data.boiler && data.boiler.water_kg ? data.boiler.water_kg + ' kg · ' + (data.boiler.T_steam_C || '—') + '°C' : '—');
  document.getElementById('val-reactor').textContent = (data.natural && data.natural.power_kw ? data.natural.power_kw + ' kW' : '—');
  document.getElementById('val-gen').textContent = (data.power && data.power.net_kwe ? data.power.net_kwe + ' kWe' : '—');
}})();
</script>
</body>
</html>'''
    return html_str
