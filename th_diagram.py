"""
T–H (Temperature–Enthalpy) and H–S (Enthalpy–Entropy) diagrams for the boiler process.
Uses steam table CSVs when available (example-style); fallback to boiler_engine in-code tables.
T–H: sensible heating to (h_f, T_steam), latent plateau, progress marker.
H–S: stretched cycle visualization (sensible, boiling, superheat, return) from example.
"""

import math
import numpy as np
import plotly.graph_objects as go

from boiler_engine import (
    STEAM_H_TABLE,
    STEAM_H_F_TABLE,
    H_WATER_INLET_KJ_KG,
    CP_WATER_KJ_KG_K,
    LHV_METHANE_KJ_KG,
    h_saturated_steam_kj_kg,
    h_saturated_liquid_kj_kg,
)

# Optional: CSV steam tables (from example)
try:
    from steam_tables import get_sat_lookup, get_sup_lookup
    _STEAM_TABLES_AVAILABLE = get_sat_lookup().df is not None
except Exception:
    _STEAM_TABLES_AVAILABLE = False


def _h_inlet_and_saturation( T_ambient_C: float, T_steam_C: float
) -> tuple[float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Get h_inlet, h_f, h_g and saturation curves (h_f_curve, T_f, h_g_curve, T_g).
    Uses CSV tables when available, else boiler_engine tables.
    """
    if _STEAM_TABLES_AVAILABLE:
        sat = get_sat_lookup()
        hf_init, _ = sat.lookup_enthalpy(T_ambient_C)
        h_f = (sat.lookup_enthalpy(T_steam_C)[0]) or h_saturated_liquid_kj_kg(T_steam_C)
        hfg = (sat.lookup_enthalpy(T_steam_C)[1])
        h_g = (h_f + hfg) if hfg is not None else h_saturated_steam_kj_kg(T_steam_C)
        h_inlet = hf_init if hf_init is not None else H_WATER_INLET_KJ_KG
        # Saturation curves from CSV (sample T range)
        temps = np.linspace(0.01, min(T_steam_C + 20, 370), 50)
        h_f_curve = np.array([sat.lookup_enthalpy(t)[0] or 0 for t in temps])
        h_g_curve = np.array([
            (sat.lookup_enthalpy(t)[0] or 0) + (sat.lookup_enthalpy(t)[1] or 0)
            for t in temps
        ])
        T_f = T_g = temps
    else:
        h_inlet = H_WATER_INLET_KJ_KG
        h_f = h_saturated_liquid_kj_kg(T_steam_C)
        h_g = h_saturated_steam_kj_kg(T_steam_C)
        T_f = np.array([t for t, _ in STEAM_H_F_TABLE])
        h_f_curve = np.array([h for _, h in STEAM_H_F_TABLE])
        T_g = np.array([t for t, _ in STEAM_H_TABLE])
        h_g_curve = np.array([h for _, h in STEAM_H_TABLE])
    return h_inlet, h_f, h_g, h_f_curve, T_f, h_g_curve, T_g


def _progress_to_ht(
    Q_progress_kj: float,
    Q_sensible_kj: float,
    Q_latent_kj: float,
    Q_startup_kj: float,
    m_kg: float,
    T_steam_C: float,
    h_f: float,
    h_g: float,
    T_ambient_C: float = 25.0,
    h_inlet: float = 105.0,
) -> tuple[float, float, float | None]:
    """
    Convert energy progress (kJ) to (h, T) and steam quality x.
    Returns (h_current, T_current, x) with x=None if not on plateau.
    """
    if Q_progress_kj <= 0 or m_kg <= 0:
        return h_inlet, T_ambient_C, None
    Q_progress_kj = min(Q_progress_kj, Q_startup_kj)
    if Q_progress_kj <= Q_sensible_kj:
        dQ_per_kg = Q_progress_kj / m_kg
        h_current = h_inlet + dQ_per_kg
        T_current = T_ambient_C + dQ_per_kg / CP_WATER_KJ_KG_K
        return h_current, T_current, None
    T_current = T_steam_C
    Q_into_latent = Q_progress_kj - Q_sensible_kj
    if Q_latent_kj <= 0:
        return h_f, T_steam_C, 0.0
    x = Q_into_latent / Q_latent_kj
    x = max(0.0, min(1.0, x))
    h_current = h_f + x * (h_g - h_f)
    return h_current, T_current, x


def build_th_figure(
    boiler_result: dict,
    T_ambient_C: float = 25.0,
    h_inlet: float | None = None,
) -> go.Figure:
    """
    Build T–H diagram: saturation curves, boiler path (sensible to h_f then latent plateau),
    and current-progress marker. Sensible segment ends at (h_f, T_steam) so the path is continuous.
    """
    m = boiler_result.get("boiler_water_capacity_kg") or 0.0
    Q_startup = boiler_result.get("Q_startup_kj") or 0.0
    Q_sensible_boiler = boiler_result.get("Q_sensible_kj") or 0.0
    Q_latent = boiler_result.get("Q_latent_kj") or 0.0
    boiler_kg_per_day = boiler_result.get("boiler_kg_per_day") or 0.0
    eta_pct = boiler_result.get("eta_boiler_pct") or 85.0
    T_steam_C = boiler_result.get("T_steam_C") or 180.0

    h_inlet_val, h_f, h_g, h_f_curve, T_f, h_g_curve, T_g = _h_inlet_and_saturation(
        T_ambient_C, T_steam_C
    )
    if h_inlet is not None:
        h_inlet_val = h_inlet

    # Diagram-consistent sensible energy so progress marker lies on the path
    Q_sensible_diagram = m * (h_f - h_inlet_val) if m > 0 else Q_sensible_boiler

    # Sensible path: from (h_inlet, T_ambient) to (h_f, T_steam) — meets saturation curve
    n_sens = 20
    T_sens = np.linspace(T_ambient_C, T_steam_C, n_sens)
    dT = (T_steam_C - T_ambient_C) or 1.0
    h_sens = h_inlet_val + (h_f - h_inlet_val) * (T_sens - T_ambient_C) / dT

    n_lat = 15
    h_lat = np.linspace(h_f, h_g, n_lat)
    T_lat = np.full_like(h_lat, T_steam_C)

    Q_total_kj = boiler_kg_per_day * LHV_METHANE_KJ_KG * (eta_pct / 100.0)
    h_prog, T_prog, x_quality = _progress_to_ht(
        Q_total_kj, Q_sensible_diagram, Q_latent, Q_startup, m, T_steam_C, h_f, h_g,
        T_ambient_C=T_ambient_C, h_inlet=h_inlet_val,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=h_f_curve, y=T_f,
            mode="lines",
            name="Sat. liquid (h_f)",
            line=dict(color="royalblue", width=1.5, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=h_g_curve, y=T_g,
            mode="lines",
            name="Sat. vapor (h_g)",
            line=dict(color="darkblue", width=1.5, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=h_sens, y=T_sens,
            mode="lines",
            name="Sensible heating",
            line=dict(color="#e65100", width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=h_lat, y=T_lat,
            mode="lines",
            name="Latent heat",
            line=dict(color="#bf360c", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[h_f], y=[T_steam_C],
            mode="markers+text",
            text=["Liquid (x=0)"],
            textposition="bottom center",
            textfont=dict(size=10),
            marker=dict(symbol="circle-open", size=10, color="#1565c0", line=dict(width=2)),
            name="Liquid (x=0)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[h_g], y=[T_steam_C],
            mode="markers+text",
            text=["Vapor (x=1)"],
            textposition="middle left",
            textfont=dict(size=10),
            marker=dict(symbol="circle-open", size=10, color="#0d47a1", line=dict(width=2)),
            name="Vapor (x=1)",
        )
    )
    prog_text = f"Q={Q_total_kj:,.0f} kJ" if Q_total_kj > 0 else "No methane"
    textpos = "bottom center" if x_quality is not None and x_quality >= 0.99 else "top center"
    x_label = f"Progress (x={x_quality:.2f})" if x_quality is not None else "Progress"
    fig.add_trace(
        go.Scatter(
            x=[h_prog], y=[T_prog],
            mode="markers+text",
            text=[prog_text],
            textposition=textpos,
            textfont=dict(size=10),
            marker=dict(symbol="diamond", size=14, color="#ffab00", line=dict(width=2, color="#ff6f00")),
            name=x_label,
        )
    )

    fig.update_layout(
        title=dict(
            text="T–H diagram: Boiler process and current progress",
            font=dict(size=14),
            x=0.5, xanchor="center", y=0.98, yanchor="top",
        ),
        xaxis_title="Enthalpy h (kJ/kg)",
        yaxis_title="Temperature T (°C)",
        showlegend=True,
        legend=dict(
            orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
            font=dict(size=10), bgcolor="rgba(255,255,255,0.8)", bordercolor="#ccc", borderwidth=1,
        ),
        height=500,
        margin=dict(t=50, b=50, l=60, r=180),
        font=dict(size=11),
    )
    fig.update_xaxes(
        rangemode="tozero", showline=True, linewidth=1.5, linecolor="#333",
        mirror="ticks", zeroline=True, zerolinewidth=1, zerolinecolor="#999",
    )
    fig.update_yaxes(
        showline=True, linewidth=1.5, linecolor="#333",
        mirror="ticks", zeroline=True, zerolinewidth=1, zerolinecolor="#999",
    )
    return fig


def build_hs_figure(
    boiler_result: dict,
    w_init_t: float = 25.0,
    superheat_delta_C: float = 20.0,
    t_cycle_C: float | None = None,
) -> go.Figure | None:
    """
    Build H–S cycle diagram (example-style): state points from steam tables,
    stretched visual coordinates. 1=init, 2=sat liquid, 3=sat vapor, 4=superheat, 5=return.
    Returns None if steam tables are not available.
    """
    if not _STEAM_TABLES_AVAILABLE:
        return None
    sat = get_sat_lookup()
    sup = get_sup_lookup()
    if sat.df is None:
        return None

    w_mass = boiler_result.get("boiler_water_capacity_kg") or 0.0
    T_steam_C = boiler_result.get("T_steam_C") or 180.0
    t_boil = T_steam_C
    pressure = sat.get_sat_pressure(t_boil)
    if pressure is None:
        return None
    t_super = t_boil + superheat_delta_C
    if t_cycle_C is None:
        t_cycle_C = t_boil

    cp_water = 4.18
    cp_steam = 2.03
    T_ref_K = 273.15
    T_boil_K = t_boil + 273.15
    T_super_K = t_super + 273.15
    T_init_K = w_init_t + 273.15
    T_cycle_K = t_cycle_C + 273.15

    hf_init, _ = sat.lookup_enthalpy(w_init_t)
    hf_boil, hfg = sat.lookup_enthalpy(t_boil)
    hg_boil = hf_boil + hfg if hfg is not None else (hf_boil + 2000.0)
    hf_ret, _ = sat.lookup_enthalpy(t_cycle_C)
    if None in (hf_init, hf_boil, hf_ret):
        return None

    h_super_tbl, s_super_tbl = sup.lookup(pressure, t_super)
    h_super = h_super_tbl if h_super_tbl is not None else (hg_boil + cp_steam * (t_super - t_boil))
    sf_init = cp_water * math.log(T_init_K / T_ref_K)
    sf_boil, sg_boil = sat.lookup_entropy(t_boil)
    if None in (sf_boil, sg_boil):
        return None
    s_super = (
        s_super_tbl
        if s_super_tbl is not None
        else sg_boil + cp_steam * math.log(T_super_K / T_boil_K)
    )
    sf_ret_tbl, _ = sat.lookup_entropy(t_cycle_C)
    sf_ret = (
        sf_ret_tbl
        if sf_ret_tbl is not None
        else cp_water * math.log(T_cycle_K / T_ref_K)
    )

    s_sp = [sf_init, sf_boil, sg_boil, s_super, sf_ret]
    h_sp = [hf_init, hf_boil, hg_boil, h_super, hf_ret]
    S_total = [s * w_mass for s in s_sp]
    H_total = [h * w_mass for h in h_sp]

    # Real units (like example image): Total Entropy (kJ/K) vs Total Enthalpy (kJ)
    full_s = S_total + [S_total[0]]
    full_h = H_total + [H_total[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=full_s, y=full_h,
            mode="lines+markers",
            line=dict(color="#1976d2", width=2),
            marker=dict(size=10),
            name="Steam cycle",
        )
    )

    labels = ["1 (Initial)", "2 (Sat)", "3 (Sat.V)", "4 (Superheat)", "5 (Return)"]
    for i, label in enumerate(labels):
        fig.add_annotation(
            x=S_total[i], y=H_total[i],
            text=label,
            showarrow=True,
            arrowhead=2,
            ax=50 if i == 0 else (-50 if i == 2 else 0),
            ay=-40 if i in (0, 1) else (40 if i == 2 else 0),
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#333",
            borderwidth=1,
        )

    s_margin = (max(S_total) - min(S_total)) * 0.1 or 1.0
    h_margin = (max(H_total) - min(H_total)) * 0.1 or 1.0
    fig.update_layout(
        title=dict(
            text="Steam Cycle: h-s Diagram",
            font=dict(size=14),
            x=0.5, xanchor="center", y=0.98, yanchor="top",
        ),
        xaxis_title="Total Entropy (kJ/K)",
        yaxis_title="Total Enthalpy (kJ)",
        showlegend=False,
        height=500,
        margin=dict(t=50, b=50, l=60, r=60),
        font=dict(size=11),
        xaxis=dict(showline=True, linewidth=1.5, linecolor="#333", mirror="ticks", zeroline=True),
        yaxis=dict(showline=True, linewidth=1.5, linecolor="#333", mirror="ticks", zeroline=True),
    )
    fig.update_xaxes(range=[min(S_total) - s_margin, max(S_total) + s_margin])
    fig.update_yaxes(range=[max(0, min(H_total) - h_margin), max(H_total) + h_margin])
    return fig


def build_gas_ts_figure(
    t_amb_C: float = 25.0,
    T2_C: float = 300.0,
    T3_C: float = 1600.0,
    T4_C: float = 1000.0,
    pressure_ratio: float = 10.0,
) -> go.Figure:
    """
    Build Gas Cycle T-s diagram (Brayton). Uses relative entropy (kJ/kg·K) and T (°C).
    Matches example layout: 1 (Atm) -> 2 (Comp) -> 3 (Comb) -> 4 (Turb) -> 1.
    """
    cp_air_g, cp_gas_g, R = 1.005, 1.15, 0.287
    T1_K = t_amb_C + 273.15
    T2_K = T2_C + 273.15
    T3_K = T3_C + 273.15
    T4_K = T4_C + 273.15
    S1 = 0.0
    S2 = S1 + cp_air_g * math.log(T2_K / T1_K) - R * math.log(pressure_ratio)
    S3 = S2 + cp_gas_g * math.log(T3_K / T2_K)
    S4 = S3 + cp_gas_g * math.log(T4_K / T3_K) - R * math.log(1.0 / pressure_ratio)
    S_vals = [S1, S2, S3, S4, S1]
    T_vals = [t_amb_C, T2_C, T3_C, T4_C, t_amb_C]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=S_vals, y=T_vals,
            mode="lines+markers",
            line=dict(color="#c62828", width=2),
            marker=dict(size=10),
            name="Brayton Cycle",
        )
    )
    labels = ["1 (Atm)", "2 (Comp)", "3 (Comb)", "4 (Turb)", ""]
    for i in range(4):
        fig.add_annotation(
            x=S_vals[i], y=T_vals[i],
            text=labels[i],
            showarrow=True,
            arrowhead=2,
            ax=-40 if i in (1, 3) else 40,
            ay=-30 if i in (0, 1) else 30,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#333",
            borderwidth=1,
        )
    s_lo, s_hi = min(S_vals), max(S_vals)
    t_lo, t_hi = min(T_vals), max(T_vals)
    ds = (s_hi - s_lo) * 0.15 or 0.1
    dt = (t_hi - t_lo) * 0.15 or 10.0
    fig.update_layout(
        title=dict(
            text="Gas Cycle: T-s Diagram",
            font=dict(size=14),
            x=0.5, xanchor="center", y=0.98, yanchor="top",
        ),
        xaxis_title="Relative Entropy (kJ/kg·K)",
        yaxis_title="Temperature (°C)",
        showlegend=False,
        height=500,
        margin=dict(t=50, b=50, l=60, r=60),
        font=dict(size=11),
        xaxis=dict(showline=True, linewidth=1.5, linecolor="#333", mirror="ticks"),
        yaxis=dict(showline=True, linewidth=1.5, linecolor="#333", mirror="ticks"),
    )
    fig.update_xaxes(range=[s_lo - ds, s_hi + ds])
    fig.update_yaxes(range=[t_lo - dt, t_hi + dt])
    return fig
