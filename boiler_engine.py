"""
Boiler thermal energy balance and methane partitioning (Boiler vs Enhanced Biogas Collector).
Uses AD methane production rate and boiler inputs to compute fuel demand and split.
"""

import numpy as np

# Water inlet (feed) at 25°C
H_WATER_INLET_KJ_KG = 105.0  # kJ/kg

# Saturated steam enthalpy (kJ/kg) at temperature °C – for interpolation
STEAM_H_TABLE = [
    (100, 2676),
    (160, 2758),
    (180, 2778),
    (200, 2793),
    (250, 2801),
]

LHV_METHANE_KJ_KG = 50_000  # kJ/kg (pure methane, mass basis)


def h_saturated_steam_kj_kg(T_C: float) -> float:
    """Saturated steam enthalpy (kJ/kg) at temperature T_C. Linear interpolation from table."""
    temps = np.array([t for t, _ in STEAM_H_TABLE])
    enthalpies = np.array([h for _, h in STEAM_H_TABLE])
    if T_C <= temps[0]:
        return float(enthalpies[0])
    if T_C >= temps[-1]:
        return float(enthalpies[-1])
    return float(np.interp(T_C, temps, enthalpies))


def boiler_thermal_load_kw(
    m_water_kg_hr: float,
    T_steam_C: float,
    h_water_in_kj_kg: float = H_WATER_INLET_KJ_KG,
) -> tuple[float, float]:
    """
    Thermal load (kW) and enthalpy rise (Δh kJ/kg).
    Q = m_water_kg_hr * Δh / 3600 (kW).
    """
    h_steam = h_saturated_steam_kj_kg(T_steam_C)
    delta_h = h_steam - h_water_in_kj_kg
    heat_load_kw = (m_water_kg_hr * delta_h) / 3600.0
    return heat_load_kw, delta_h


def methane_demand_kg_hr(
    heat_load_kw: float,
    eta_boiler: float,
    lhv_kj_kg: float = LHV_METHANE_KJ_KG,
) -> float:
    """
    Mass flow of methane (kg/hr) required for the boiler.
    m_methane = (Q_kw * 3600) / (LHV * eta)  =>  m_methane_kg_hr = Q_kw * 3600 / (LHV * eta).
    Or from user formula: m = (m_water * Δh) / (LHV * eta); Q = m_water * Δh / 3600 => m_water*Δh = Q*3600, so m = Q*3600/(LHV*eta).
    """
    if eta_boiler <= 0:
        return 0.0
    return (heat_load_kw * 3600.0) / (lhv_kj_kg * (eta_boiler / 100.0))


def total_methane_production_kg_hr(avg_daily_m3: float, ch4_density_kg_m3: float = 0.657) -> float:
    """Convert average daily methane volume (m³/day) to mass flow rate (kg/hr)."""
    kg_per_day = avg_daily_m3 * ch4_density_kg_m3
    return kg_per_day / 24.0


def partition_methane(
    total_methane_kg_hr: float,
    boiler_demand_kg_hr: float,
) -> dict:
    """
    Split methane: Boiler (parasitic) vs Collector (available fuel).
    Returns dict with boiler_kg_hr, collector_kg_hr, boiler_pct, collector_pct, insufficient.
    """
    if total_methane_kg_hr <= 0:
        return {
            "boiler_kg_hr": 0.0,
            "collector_kg_hr": 0.0,
            "boiler_pct": 0.0,
            "collector_pct": 100.0,
            "insufficient": boiler_demand_kg_hr > 0,
        }
    boiler_kg_hr = min(boiler_demand_kg_hr, total_methane_kg_hr)
    collector_kg_hr = total_methane_kg_hr - boiler_kg_hr
    boiler_pct = (boiler_kg_hr / total_methane_kg_hr) * 100.0
    collector_pct = (collector_kg_hr / total_methane_kg_hr) * 100.0
    # Only treat as insufficient when demand exceeds production by >1% (avoids rounding/display noise)
    insufficient = boiler_demand_kg_hr > total_methane_kg_hr * 1.01
    return {
        "boiler_kg_hr": boiler_kg_hr,
        "collector_kg_hr": collector_kg_hr,
        "boiler_pct": boiler_pct,
        "collector_pct": collector_pct,
        "insufficient": insufficient,
    }


def boiler_balance(
    m_water_kg_hr: float,
    eta_boiler_pct: float,
    T_steam_C: float,
    avg_daily_methane_m3: float,
    ch4_density_kg_m3: float = 0.657,
) -> dict:
    """
    Full boiler thermal balance and methane split.
    Returns dict: heat_load_kw, delta_h_kj_kg, methane_demand_kg_hr, total_methane_kg_hr,
    boiler_kg_hr, collector_kg_hr, boiler_pct, collector_pct, insufficient.
    """
    heat_load_kw, delta_h = boiler_thermal_load_kw(m_water_kg_hr, T_steam_C)
    demand_kg_hr = methane_demand_kg_hr(heat_load_kw, eta_boiler_pct)
    total_methane_kg_hr = total_methane_production_kg_hr(avg_daily_methane_m3, ch4_density_kg_m3)
    part = partition_methane(total_methane_kg_hr, demand_kg_hr)
    return {
        "heat_load_kw": heat_load_kw,
        "delta_h_kj_kg": delta_h,
        "methane_demand_kg_hr": demand_kg_hr,
        "total_methane_kg_hr": total_methane_kg_hr,
        "boiler_kg_hr": part["boiler_kg_hr"],
        "collector_kg_hr": part["collector_kg_hr"],
        "boiler_pct": part["boiler_pct"],
        "collector_pct": part["collector_pct"],
        "insufficient": part["insufficient"],
    }
