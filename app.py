"""
Streamlit UI for AD-HTC biogas kinetics: inputs, Sankey diagram, and KPI dashboard.
Stores ignition_power_kw in session state for use in h-s chart (next phase).
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from biogas_engine import BiogasKinetics, CH4_DENSITY_KG_M3
from boiler_engine import boiler_balance

# Biomass type → moisture % and water-to-biomass mixing ratio (added_water_ratio)
# Cattle: already liquid; Food: 1:1; Manure: 1:1.2; Grass/silage: 1:1.5; Agri residue: 1:2
BIOMASS_TYPES = {
    "cattle": {"label": "Cattle / slurry (dung)", "moisture_pct": 94.0, "added_water_ratio": 0.0},
    "food_waste": {"label": "Food waste", "moisture_pct": 77.0, "added_water_ratio": 1.0},
    "manure": {"label": "Manure (Pig/Chicken)", "moisture_pct": 72.0, "added_water_ratio": 1.2},
    "grass_silage": {"label": "Grass / silage", "moisture_pct": 72.0, "added_water_ratio": 1.5},
    "agricultural_residue": {"label": "Agricultural residue", "moisture_pct": 15.0, "added_water_ratio": 2.0},
}


def init_session_state():
    if "ignition_power_kw" not in st.session_state:
        st.session_state.ignition_power_kw = None
    if "report" not in st.session_state:
        st.session_state.report = None
    if "boiler_result" not in st.session_state:
        st.session_state.boiler_result = None


def build_sankey(moisture_rich_kg_s: float, moisture_lean_kg_s: float) -> go.Figure:
    """Sankey: Biomass splits into AD (moisture-rich) and HTC (moisture-lean)."""
    total = moisture_rich_kg_s + moisture_lean_kg_s
    if total <= 0:
        total = 1
    # Node indices: 0 = Biomass, 1 = AD, 2 = HTC
    source = [0, 0]
    target = [1, 2]
    value = [moisture_rich_kg_s, moisture_lean_kg_s]
    label = ["Biomass Feedstock", "AD (moisture-rich)", "HTC (moisture-lean)"]
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=label,
                    color=["#2e7d32", "#1565c0", "#ef6c00"],
                ),
                link=dict(
                    source=source,
                    target=target,
                    value=value,
                    color="rgba(100,100,100,0.3)",
                ),
            )
        ]
    )
    fig.update_layout(
        title="Feedstock partitioning: AD vs HTC",
        font=dict(size=12),
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# Convert user mass flow to kg/s for engine
def to_kg_s(value: float, unit: str) -> float:
    if unit == "kg/s":
        return value
    if unit == "kg/hr":
        return value / 3600.0
    if unit == "kg/day":
        return value / 86400.0
    return value


def render_input_section():
    with st.container():
        st.markdown("#### Parameters")
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
                    help="Use kg/day or kg/hr for campus/small scale; kg/s for large scale.",
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
                st.write("")  # spacing
                submitted = st.form_submit_button("Analyze")
    return mass_flow, moisture, temp, submitted, biomass_type_key


def _fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}" if v < 1e6 else f"{v:,.0f}"
    return str(v)


def _fmt_flow_kg_s(v):
    """Format flow in kg/s: show kg/hr when small so it doesn't display as 0.00."""
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "—"
    if not isinstance(v, (int, float)):
        return str(v)
    if abs(v) < 0.01 and v != 0:
        return f"{v * 3600:,.2f} kg/hr"
    return f"{v:,.4f} kg/s"


def render_report(report: dict):
    r = report

    # ----- Alert -----
    if r.get("high_solids_warning"):
        st.warning("**High Solid Content – Risk of Blockage**")

    # ----- Key results: 5 metric cards -----
    st.markdown("### Key results")
    days = r.get("days_to_maturity")
    days_str = f"{days:.1f} days" if days != np.inf and days < 1e6 else "—"
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Days to maturity", days_str, help="Retention time from Arrhenius (1/k)")
    with c2:
        st.metric("Reactor capacity (mass)", f"{_fmt(r.get('reactor_mass_kg'))} kg", help="Slurry mass in reactor: flow × retention time")
    with c3:
        st.metric("Average daily", f"{_fmt(r.get('avg_daily_m3'))} m³/day", help="Mean daily production")
    with c4:
        st.metric("Gas at maturity", f"{_fmt(r.get('peak_daily_m3'))} m³/day", help="Peak daily production")
    with c5:
        st.metric("Power generated", f"{_fmt(r.get('ignition_power_kw'))} kW", help="Ignition / thermal power")

    st.markdown("---")

    # ----- Detail sections in expanders -----
    with st.expander("Inputs & water dilution", expanded=False):
        st.markdown("**Inputs**")
        st.markdown(f"- Biomass type: **{r.get('biomass_type', '—')}**")
        st.markdown(f"- Moisture used: **{r.get('moisture_pct_used', '—')}%**")
        st.markdown(f"- Water dilution: **1:{r.get('added_water_ratio', 0)}** (biomass : water)")
        st.markdown("**Water dilution (mass balance)**")
        st.markdown(f"- Added water: **{_fmt_flow_kg_s(r.get('added_water_kg_s'))}**")
        st.markdown(f"- Total slurry: **{_fmt_flow_kg_s(r.get('total_slurry_kg_s'))}**")
        st.markdown(f"- Final total solids: **{_fmt(r.get('final_total_solids_pct'))}%**")
        st.markdown(f"- Required reactor mass: **{_fmt(r.get('reactor_mass_kg'))}** kg")

    with st.expander("Feedstock partitioning & kinetics", expanded=False):
        st.markdown("**Partitioning**")
        st.markdown(f"- To AD (moisture-rich): **{_fmt_flow_kg_s(r.get('moisture_rich_biomass_kg_s'))}**")
        st.markdown(f"- To HTC (moisture-lean): **{_fmt_flow_kg_s(r.get('moisture_lean_biomass_kg_s'))}**")
        st.markdown("**Digestion kinetics**")
        st.markdown(f"- Rate constant (k): **{_fmt(r.get('k_per_day'))}** /day")
        st.markdown(f"- Days to maturity: **{_fmt(r.get('days_to_maturity'))}** days")

    with st.expander("Methane production & quality", expanded=False):
        st.markdown("**Production (steady-state continuous flow)**")
        st.markdown(f"- Average daily: **{_fmt(r.get('avg_daily_m3'))}** m³/day")
        st.markdown(f"- Peak daily (at maturity): **{_fmt(r.get('peak_daily_m3'))}** m³/day")
        st.markdown(f"- Biogas over one retention period: **{_fmt(r.get('V_total_m3'))}** m³")
        st.markdown(f"- Mass of methane (CH4) over retention: **{_fmt(r.get('methane_mass_kg'))}** kg (volume × 0.657 kg/m³)")
        st.markdown("**Quality & power**")
        st.markdown(f"- Methane purity: **{r.get('methane_purity', 0) * 100:.0f}%**")
        st.markdown(f"- Ignition power: **{_fmt(r.get('ignition_power_kw'))}** kW")

    # ----- Sankey -----
    st.markdown("### Feedstock flow")
    st.caption("Biomass split: AD (moisture-rich) vs HTC (moisture-lean)")
    fig = build_sankey(
        r["moisture_rich_biomass_kg_s"],
        r["moisture_lean_biomass_kg_s"],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_boiler_section(report: dict):
    """Boiler thermal balance: input form, then summary table and methane distribution donut."""
    st.markdown("---")
    st.markdown("## Boiler Thermal Balance")
    st.caption("Heat-to-fuel tradeoff: methane to boiler (parasitic) vs Enhanced Biogas Collector (available fuel).")

    with st.form("boiler_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            m_water_kg_hr = st.number_input(
                "Water feed rate (kg/hr)",
                min_value=0.0,
                max_value=10000.0,
                value=None,
                step=10.0,
                key="boiler_water",
                placeholder="e.g. 100",
            )
        with col2:
            eta_boiler = st.number_input(
                "Boiler efficiency (%)",
                min_value=0,
                max_value=99,
                value=None,
                step=1,
                key="boiler_eta",
                placeholder="e.g. 85",
            )
        with col3:
            T_steam = st.number_input(
                "Steam temperature target (°C)",
                min_value=0.0,
                max_value=350.0,
                value=None,
                step=5.0,
                key="boiler_T_steam",
                placeholder="e.g. 180",
            )
        boiler_submitted = st.form_submit_button("Update Boiler")

    # Run balance only when user clicks Update Boiler; all fields must be filled (no defaults)
    if boiler_submitted:
        if m_water_kg_hr is not None and eta_boiler is not None and T_steam is not None:
            avg_daily_m3 = report.get("avg_daily_m3", 0) or 0
            res = boiler_balance(
                m_water_kg_hr=m_water_kg_hr,
                eta_boiler_pct=eta_boiler,
                T_steam_C=T_steam,
                avg_daily_methane_m3=avg_daily_m3,
                ch4_density_kg_m3=CH4_DENSITY_KG_M3,
            )
            st.session_state.boiler_result = res
        else:
            st.error("Please fill all boiler fields (water feed rate, efficiency, steam temperature).")

    if st.session_state.boiler_result is not None:
        r = st.session_state.boiler_result
        if r.get("insufficient"):
            total_kg_hr = r.get("total_methane_kg_hr") or 0
            demand_kg_hr = r.get("methane_demand_kg_hr") or 0
            if total_kg_hr <= 0:
                st.warning("**No methane from AD in this run.** Run **Analyze** with biomass input above, or increase biomass so that methane production is positive.")
            else:
                st.warning(
                    f"**Insufficient methane:** boiler demand (**{demand_kg_hr:,.2f}** kg/hr) exceeds AD production (**{total_kg_hr:,.2f}** kg/hr). "
                    "Reduce water feed rate or increase biomass input."
                )

        st.markdown("### Summary")
        st.dataframe(
            {
                "Metric": [
                    "Boiler thermal load (kW)",
                    "Methane demand (boiler) (kg/hr)",
                    "Total methane from AD (kg/hr)",
                    "To boiler (parasitic) (kg/hr)",
                    "To collector (available fuel) (kg/hr)",
                    "Boiler (%)",
                    "Collector (%)",
                ],
                "Value": [
                    f"{r['heat_load_kw']:,.1f}",
                    f"{r['methane_demand_kg_hr']:,.2f}",
                    f"{r['total_methane_kg_hr']:,.2f}",
                    f"{r['boiler_kg_hr']:,.2f}",
                    f"{r['collector_kg_hr']:,.2f}",
                    f"{r['boiler_pct']:,.1f}",
                    f"{r['collector_pct']:,.1f}",
                ],
            },
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Methane distribution")
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["To boiler (parasitic)", "To collector (available)"],
                    values=[r["boiler_kg_hr"], r["collector_kg_hr"]],
                    hole=0.6,
                    marker=dict(colors=["#ef6c00", "#2e7d32"]),
                )
            ]
        )
        fig.update_layout(
            title="Methane distribution",
            showlegend=True,
            height=350,
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)


def main():
    st.set_page_config(page_title="AD-HTC Biogas Kinetics", layout="wide")
    init_session_state()

    st.title("AD-HTC Biogas Kinetics")
    st.caption("Feedstock partitioning, methane yield, and ignition power from the AD-HTC schematic.")

    mass_flow, moisture, temp, submitted, biomass_type_key = render_input_section()

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
        st.session_state.ignition_power_kw = report["ignition_power_kw"]
        st.session_state.boiler_result = None  # recalc boiler after new analysis

    if st.session_state.report is not None:
        st.markdown("---")
        st.markdown("## Report")
        render_report(st.session_state.report)
        render_boiler_section(st.session_state.report)


if __name__ == "__main__":
    main()
