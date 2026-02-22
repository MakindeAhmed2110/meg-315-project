"""
Streamlit UI for AD-HTC biogas kinetics: step-by-step flow.
Step 1: Initial parameters → results. Step 2: Boiler details. Step 3: Power cycle. Step 4: Graphs.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from biogas_engine import BiogasKinetics, CH4_DENSITY_KG_M3
from boiler_engine import boiler_balance
from power_cycle_engine import power_cycle_logic
from th_diagram import build_hs_figure, build_gas_ts_figure
from schematic_html import build_schematic_html

# Biomass type → moisture % and water-to-biomass mixing ratio
BIOMASS_TYPES = {
    "cattle": {"label": "Cattle / slurry (dung)", "moisture_pct": 94.0, "added_water_ratio": 0.0},
    "food_waste": {"label": "Food waste", "moisture_pct": 77.0, "added_water_ratio": 1.0},
    "manure": {"label": "Manure (Pig/Chicken)", "moisture_pct": 72.0, "added_water_ratio": 1.2},
    "grass_silage": {"label": "Grass / silage", "moisture_pct": 72.0, "added_water_ratio": 1.5},
    "agricultural_residue": {"label": "Agricultural residue", "moisture_pct": 15.0, "added_water_ratio": 2.0},
}

STEP_LABELS = [
    "1. Initial parameters",
    "2. Results",
    "3. Boiler details",
    "4. Combustion & power cycle",
    "5. Thermodynamic diagrams",
    "6. Schematic",
]


def init_session_state():
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "report" not in st.session_state:
        st.session_state.report = None
    if "boiler_result" not in st.session_state:
        st.session_state.boiler_result = None
    if "power_cycle_result" not in st.session_state:
        st.session_state.power_cycle_result = None
    if "menu_open" not in st.session_state:
        st.session_state.menu_open = True


def to_kg_s(value: float, unit: str) -> float:
    if unit == "kg/s":
        return value
    if unit == "kg/hr":
        return value / 3600.0
    if unit == "kg/day":
        return value / 86400.0
    return value


def _fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}" if v < 1e6 else f"{v:,.0f}"
    return str(v)


def _step_summary(step_index: int) -> str:
    """Short result summary for a step (for nav menu)."""
    if step_index == 0:
        return "Enter biomass, flow, temperature"
    if step_index == 1:
        r = st.session_state.report
        if not r:
            return "—"
        return f"{_fmt(r.get('avg_daily_m3'))} m³/day · {_fmt(r.get('ignition_power_kw'))} kW"
    if step_index == 2:
        b = st.session_state.boiler_result
        if not b:
            return "—"
        return f"{b.get('boiler_water_capacity_kg', 0):.0f} kg · {b.get('T_steam_C', 0):.0f}°C"
    if step_index == 3:
        p = st.session_state.power_cycle_result
        if not p:
            return "—"
        return f"{p.get('Net_Power_kWe', 0):,.1f} kWe"
    if step_index == 4:
        return "Steam h–s & Gas T–s"
    if step_index == 5:
        return "Animated schematic"
    return ""


def render_left_nav():
    """Left panel (30% width): hamburger + list of steps with results; clicking a step navigates."""
    report = st.session_state.report
    boiler = st.session_state.boiler_result
    power = st.session_state.power_cycle_result
    step = st.session_state.current_step
    if st.button("☰ Close menu", key="nav_toggle"):
        st.session_state.menu_open = False
        st.rerun()
    st.markdown("---")
    st.markdown("**Navigate**")
    for i, label in enumerate(STEP_LABELS):
        is_current = step == i
        can_go = (
            i == 0
            or (i == 1 and report is not None)
            or (i == 2 and report is not None)
            or (i == 3 and boiler is not None)
            or (i == 4 and power is not None)
            or (i == 5 and power is not None)
        )
        if st.button(label, key=f"nav_step_{i}", disabled=not can_go or is_current):
            st.session_state.current_step = i
            st.rerun()
        summary = _step_summary(i)
        if summary and summary != "—":
            st.caption(f"  → {summary}")
    st.markdown("---")
    st.caption(f"*Current: {STEP_LABELS[step]}*")


def render_step_indicator():
    """Show current step; optional Back to previous step."""
    step = st.session_state.current_step
    st.caption(f"**Current step:** {STEP_LABELS[step]}")
    if step > 0:
        if st.button("← Back to previous step", key="back_btn"):
            st.session_state.current_step = step - 1
            st.rerun()


# --- Step 0: Initial parameters form ---
def render_step0_initial_params():
    st.markdown("##### 1. Initial parameters")
    st.caption("Biomass type, flow, and temperature. Click **Analyze** to run kinetics.")
    with st.form("biomass_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            biomass_type_key = st.selectbox(
                "Biomass type",
                options=list(BIOMASS_TYPES.keys()),
                format_func=lambda k: BIOMASS_TYPES[k]["label"],
                key="biomass_type",
            )
            flow_unit = st.selectbox(
                "Mass flow unit",
                options=["kg/day", "kg/hr", "kg/s"],
                index=0,
                key="flow_unit",
            )
            mass_flow_user = st.number_input(
                f"Biomass feedstock mass ({flow_unit})",
                min_value=0.01,
                max_value=1e7 if flow_unit == "kg/day" else (5e5 if flow_unit == "kg/hr" else 500.0),
                value=60.0 if flow_unit == "kg/day" else (5.0 if flow_unit == "kg/hr" else 5.0),
                step=1.0 if flow_unit != "kg/s" else 0.1,
                format="%.2f" if flow_unit == "kg/s" else "%.0f",
                key="mass_flow",
            )
            mass_flow = to_kg_s(mass_flow_user, flow_unit)
            moisture = BIOMASS_TYPES[biomass_type_key]["moisture_pct"]
            dry_pct = 100.0 - moisture
            st.caption(f"Dry matter: {dry_pct:.0f}% · Water: {moisture:.0f}%")
        with col2:
            temp = st.number_input(
                "Surrounding temperature (°C)",
                min_value=-10.0,
                max_value=50.0,
                value=25.0,
                step=0.5,
                key="temp",
            )
        with col3:
            st.write("")
            submitted = st.form_submit_button("Analyze")
        if submitted:
            added_water_ratio = BIOMASS_TYPES[biomass_type_key]["added_water_ratio"]
            engine = BiogasKinetics(
                total_mass_flow_kg_s=mass_flow,
                moisture_content_pct=moisture,
                temperature_C=temp,
                added_water_ratio=added_water_ratio,
            )
            report = engine.to_dict()
            report["biomass_type"] = BIOMASS_TYPES[biomass_type_key]["label"]
            report["moisture_pct_used"] = moisture
            report["added_water_ratio"] = added_water_ratio
            st.session_state.report = report
            st.session_state.boiler_result = None
            st.session_state.power_cycle_result = None
            st.session_state.current_step = 1
            st.rerun()


# --- Step 1: Results page ---
def render_step1_results():
    r = st.session_state.report
    if r.get("high_solids_warning"):
        st.warning("**High solid content – risk of blockage**")
    st.markdown("### Step 1 results")
    days = r.get("days_to_maturity")
    days_str = f"{days:.1f} days" if days != np.inf and days < 1e6 else "—"
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Days to maturity", days_str)
    with c2:
        st.metric("Reactor capacity (mass)", f"{_fmt(r.get('reactor_mass_kg'))} kg")
    with c3:
        st.metric("Average daily", f"{_fmt(r.get('avg_daily_m3'))} m³/day")
    with c4:
        st.metric("Gas at maturity", f"{_fmt(r.get('peak_daily_m3'))} m³/day")
    with c5:
        st.metric("Power generated", f"{_fmt(r.get('ignition_power_kw'))} kW")
    st.success("Initial parameters calculated. Proceed to **Boiler details**.")
    if st.button("Next: Boiler details →"):
        st.session_state.current_step = 2
        st.rerun()


# --- Step 2: Boiler details form ---
def render_step2_boiler():
    st.markdown("##### 3. Boiler details")
    st.caption("Efficiency, steam temperature, and boiler water mass. Methane needed for one startup is derived from mass.")
    report = st.session_state.report
    with st.form("boiler_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            eta_boiler = st.number_input(
                "Boiler efficiency (%)",
                min_value=1,
                max_value=99,
                value=85,
                step=1,
                key="boiler_eta",
            )
        with col2:
            T_steam = st.number_input(
                "Steam temperature (°C)",
                min_value=50.0,
                max_value=350.0,
                value=180.0,
                step=5.0,
                key="boiler_T_steam",
            )
        with col3:
            boiler_capacity_kg = st.number_input(
                "Boiler water capacity (kg)",
                min_value=1.0,
                max_value=100000.0,
                value=200.0,
                step=10.0,
                key="boiler_capacity",
            )
        submitted = st.form_submit_button("Update Boiler")
    if submitted:
        avg_daily_m3 = report.get("avg_daily_m3", 0) or 0
        res = boiler_balance(
            eta_boiler_pct=eta_boiler,
            T_steam_C=T_steam,
            avg_daily_methane_m3=avg_daily_m3,
            boiler_water_capacity_kg=boiler_capacity_kg,
            ch4_density_kg_m3=CH4_DENSITY_KG_M3,
        )
        st.session_state.boiler_result = res
        st.success("Boiler updated. Proceed to **Combustion & power cycle**.")
    if st.session_state.boiler_result is not None:
        r = st.session_state.boiler_result
        st.dataframe(
            {
                "Metric": [
                    "Boiler water (kg)",
                    "Energy for one startup (kJ)",
                    "Methane needed (kg)",
                    "Methane from AD (kg/day)",
                    "Time to steam (min)",
                ],
                "Value": [
                    f"{r.get('boiler_water_capacity_kg', 0):,.1f}",
                    f"{r.get('Q_startup_kj', 0):,.0f}",
                    f"{r.get('methane_needed_kg', 0):,.3f}",
                    f"{r.get('methane_per_day_kg', 0):,.2f}",
                    f"{r.get('startup_time_minutes', 0):,.1f}",
                ],
            },
            width="stretch",
            hide_index=True,
        )
        if st.button("Next: Combustion & power cycle →"):
            st.session_state.current_step = 3
            st.rerun()


# --- Step 3: Power cycle form ---
def render_step3_power_cycle():
    st.markdown("##### 4. Combustion and power cycle")
    st.caption("Compressor, turbine, generator efficiencies; air mass flow; pressure ratio; ambient temperature.")
    report = st.session_state.report
    with st.form("power_cycle_form"):
        c1, c2 = st.columns(2)
        with c1:
            eta_comp = st.number_input("Compressor efficiency (%)", min_value=1, max_value=99, value=75, step=1, key="eta_comp")
            eta_turb = st.number_input("Turbine efficiency (%)", min_value=1, max_value=99, value=85, step=1, key="eta_turb")
            eta_gen = st.number_input("Generator efficiency (%)", min_value=1, max_value=99, value=94, step=1, key="eta_gen")
        with c2:
            air_mass_flow = st.number_input("Air mass flow (kg/s)", min_value=0.01, max_value=100.0, value=0.5, step=0.1, key="air_flow")
            pressure_ratio = st.number_input("Pressure ratio", min_value=1.5, max_value=30.0, value=10.0, step=0.5, key="pr")
            t_amb_air = st.number_input("Ambient air temperature (°C)", min_value=-20.0, max_value=50.0, value=25.0, step=0.5, key="t_amb_air")
        submitted = st.form_submit_button("Calculate power cycle")
    if submitted:
        biogas_vol = report.get("V_total_m3") or report.get("avg_daily_m3", 0) * 30
        volatile_kg = report.get("volatile_yield_kg", 0) or (report.get("reactor_mass_kg", 0) * 0.05)
        res = power_cycle_logic(
            biogas_vol_m3=float(biogas_vol),
            volatile_mass_kg=float(volatile_kg),
            air_mass_flow_kg_s=air_mass_flow,
            pressure_ratio=pressure_ratio,
            eta_compressor=eta_comp / 100.0,
            eta_turbine=eta_turb / 100.0,
            eta_generator=eta_gen / 100.0,
            t_ambient_c=t_amb_air,
        )
        st.session_state.power_cycle_result = res
        st.success("Power cycle calculated. Proceed to **Thermodynamic diagrams**.")
    if st.session_state.power_cycle_result is not None:
        r = st.session_state.power_cycle_result
        st.metric("Net electrical power", f"{r.get('Net_Power_kWe', 0):,.2f} kWe")
        st.caption(f"T2 (compressor exit): {r.get('T2_C', 0):.1f} °C · T3 (firing): {r.get('T3_C', 0):.1f} °C · T4 (turbine exit): {r.get('T4_C', 0):.1f} °C")
        if st.button("Next: View thermodynamic diagrams →"):
            st.session_state.current_step = 4
            st.rerun()


# --- Step 4: Two graphs side by side + T–H ---
def render_step4_graphs():
    st.markdown("##### 5. Thermodynamic cycle diagrams")
    boiler_result = st.session_state.boiler_result
    power_result = st.session_state.power_cycle_result
    col_steam, col_gas = st.columns(2)
    with col_steam:
        st.markdown("**Steam cycle: h–s diagram**")
        if boiler_result is not None:
            hs_fig = build_hs_figure(boiler_result)
            if hs_fig is not None:
                st.plotly_chart(hs_fig, width="stretch")
            else:
                st.caption("Steam h–s requires steam table CSVs in the project folder.")
        else:
            st.info("Complete Boiler details (Step 3) to see the steam cycle.")
    with col_gas:
        st.markdown("**Gas cycle: T–s diagram**")
        if power_result is not None:
            gas_fig = build_gas_ts_figure(
                t_amb_C=power_result.get("t_ambient_C", 25.0),
                T2_C=power_result.get("T2_C", 300),
                T3_C=power_result.get("T3_C", 1600),
                T4_C=power_result.get("T4_C", 1000),
                pressure_ratio=power_result.get("pressure_ratio", 10.0),
            )
            st.plotly_chart(gas_fig, width="stretch")
        else:
            st.info("Complete Combustion & power cycle (Step 4) to see the gas cycle.")
    st.caption("Left: Steam cycle (Total Entropy vs Total Enthalpy). Right: Gas cycle (Brayton) T–s.")


# --- Step 5: Animated schematic (HTML/JS) ---
def render_step5_schematic():
    st.markdown("##### 6. Biogas Pro schematic")
    st.caption("Animated process flow with your calculated values. Natural AD → Methane → Boiler → Reactor → Combustion → Turbine → Generator.")
    report = st.session_state.report
    boiler_result = st.session_state.boiler_result
    power_result = st.session_state.power_cycle_result
    html_content = build_schematic_html(report, boiler_result, power_result)
    st.components.v1.html(html_content, height=580, scrolling=False)
    if st.button("← Back to thermodynamic diagrams"):
        st.session_state.current_step = 4
        st.rerun()
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("← Back to power cycle"):
            st.session_state.current_step = 3
            st.rerun()
    with col_b2:
        if st.button("Next: Schematic →"):
            st.session_state.current_step = 5
            st.rerun()


def main():
    st.set_page_config(page_title="AD-HTC Biogas Kinetics", layout="wide")
    init_session_state()

    st.markdown("""
        <style>
        .stMarkdown h5 { margin-top: 0.5rem; margin-bottom: 0.25rem; padding: 0.5rem 0.75rem; background: #f0f2f6; border: 1px solid #e0e0e0; border-radius: 6px; font-weight: 600; color: #31333F; }
        [data-testid="stSidebar"] { min-width: 0; }
        </style>
    """, unsafe_allow_html=True)

    step = st.session_state.current_step
    menu_open = st.session_state.menu_open

    # Hamburger when menu is closed: show button to open menu
    if not menu_open:
        if st.button("☰ Menu", key="hamburger_open"):
            st.session_state.menu_open = True
            st.rerun()
        st.markdown("---")

    if menu_open:
        col_nav, col_main = st.columns([0.30, 0.70])
        with col_nav:
            render_left_nav()
        with col_main:
            _render_main_content(step)
    else:
        _render_main_content(step)


def _render_main_content(step: int):
    """Title + step indicator + current step content."""
    st.title("AD-HTC Biogas Kinetics")
    st.caption("Step-by-step: initial parameters → results → boiler → power cycle → thermodynamic diagrams.")

    if step == 0:
        render_step0_initial_params()
        return

    render_step_indicator()
    st.markdown("---")

    if step == 1:
        render_step1_results()
    elif step == 2:
        render_step2_boiler()
    elif step == 3:
        render_step3_power_cycle()
    elif step == 4:
        render_step4_graphs()
    else:
        render_step5_schematic()


if __name__ == "__main__":
    main()
