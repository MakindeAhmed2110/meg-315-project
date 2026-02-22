"""
Boiler: one-time methane needed (kg) from boiler water mass. No flow rates (no kg/hr).
Energy to heat static water to steam → methane mass needed = Q_startup / (LHV × η).
"""

import numpy as np

# Water inlet (feed) at 25°C
H_WATER_INLET_KJ_KG = 105.0  # kJ/kg
CP_WATER_KJ_KG_K = 4.18     # kJ/(kg·K) for sensible heat

# Saturated steam (vapor) enthalpy h_g (kJ/kg) at temperature °C
STEAM_H_TABLE = [
    (100, 2676),
    (160, 2758),
    (180, 2778),
    (200, 2793),
    (250, 2801),
]
# Saturated liquid enthalpy h_f (kJ/kg) at same temperatures (for latent heat)
STEAM_H_F_TABLE = [
    (100, 419),
    (160, 675),
    (180, 763),
    (200, 852),
    (250, 1085),
]

LHV_METHANE_KJ_KG = 50_000  # kJ/kg (pure methane, mass basis)


def h_saturated_steam_kj_kg(T_C: float) -> float:
    """Saturated steam (vapor) enthalpy (kJ/kg) at temperature T_C. Linear interpolation."""
    temps = np.array([t for t, _ in STEAM_H_TABLE])
    enthalpies = np.array([h for _, h in STEAM_H_TABLE])
    if T_C <= temps[0]:
        return float(enthalpies[0])
    if T_C >= temps[-1]:
        return float(enthalpies[-1])
    return float(np.interp(T_C, temps, enthalpies))


def h_saturated_liquid_kj_kg(T_C: float) -> float:
    """Saturated liquid enthalpy h_f (kJ/kg) at temperature T_C. For latent heat calculation."""
    temps = np.array([t for t, _ in STEAM_H_F_TABLE])
    enthalpies = np.array([h for _, h in STEAM_H_F_TABLE])
    if T_C <= temps[0]:
        return float(enthalpies[0])
    if T_C >= temps[-1]:
        return float(enthalpies[-1])
    return float(np.interp(T_C, temps, enthalpies))


def methane_production_kg_per_day(avg_daily_m3: float, ch4_density_kg_m3: float = 0.657) -> float:
    """Methane from AD: mass per day (kg/day). No per-hour rate."""
    return avg_daily_m3 * ch4_density_kg_m3


def boiler_startup_energy_kj(
    boiler_water_capacity_kg: float,
    T_steam_C: float,
    T_ambient_C: float = 25.0,
) -> tuple[float, float, float]:
    """
    Total energy (kJ) to bring static boiler water from ambient to saturated steam.
    Phase 1: Sensible Q = m * Cp * (T_steam - T_ambient).
    Phase 2: Latent Q = m * (h_steam - h_f) at T_steam.
    Returns (Q_sensible_kj, Q_latent_kj, Q_total_kj).
    """
    m = boiler_water_capacity_kg
    Q_sensible = m * CP_WATER_KJ_KG_K * (T_steam_C - T_ambient_C)
    h_steam = h_saturated_steam_kj_kg(T_steam_C)
    h_f = h_saturated_liquid_kj_kg(T_steam_C)
    Q_latent = m * (h_steam - h_f)
    Q_total = Q_sensible + Q_latent
    return Q_sensible, Q_latent, Q_total


def methane_mass_needed_kg(Q_startup_kj: float, eta_boiler_pct: float, lhv_kj_kg: float = LHV_METHANE_KJ_KG) -> float:
    """One-time methane mass (kg) needed to supply Q_startup energy: Q / (LHV × η)."""
    if eta_boiler_pct <= 0:
        return 0.0
    return Q_startup_kj / (lhv_kj_kg * (eta_boiler_pct / 100.0))


def time_to_steam_minutes(
    Q_startup_kj: float,
    methane_kg_per_day: float,
    eta_boiler_pct: float,
    lhv_kj_kg: float = LHV_METHANE_KJ_KG,
) -> float:
    """
    Time (min) to reach steam when boiler is fed at daily production rate.
    Power = (kg/day / 86400) * LHV * η (kW). Time = Q_startup / power / 60 (min).
    """
    if methane_kg_per_day <= 0 or eta_boiler_pct <= 0:
        return 0.0
    methane_kg_s = methane_kg_per_day / 86400.0
    power_kw = methane_kg_s * lhv_kj_kg * (eta_boiler_pct / 100.0)
    if power_kw <= 0:
        return 0.0
    return (Q_startup_kj / power_kw) / 60.0


def partition_methane_per_day(
    methane_per_day_kg: float,
    methane_needed_kg: float,
) -> dict:
    """
    Division: daily methane split between boiler (for one startup) and collector.
    Boiler gets min(needed, available); rest to collector. All in kg/day.
    """
    if methane_per_day_kg <= 0:
        return {
            "boiler_kg_per_day": 0.0,
            "collector_kg_per_day": 0.0,
            "boiler_pct": 0.0,
            "collector_pct": 100.0,
        }
    boiler_kg = min(methane_needed_kg, methane_per_day_kg)
    collector_kg = methane_per_day_kg - boiler_kg
    boiler_pct = (boiler_kg / methane_per_day_kg) * 100.0
    collector_pct = (collector_kg / methane_per_day_kg) * 100.0
    return {
        "boiler_kg_per_day": boiler_kg,
        "collector_kg_per_day": collector_kg,
        "boiler_pct": boiler_pct,
        "collector_pct": collector_pct,
    }


def boiler_balance(
    eta_boiler_pct: float,
    T_steam_C: float,
    avg_daily_methane_m3: float,
    boiler_water_capacity_kg: float,
    ch4_density_kg_m3: float = 0.657,
) -> dict:
    """
    Boiler: methane needed (kg) from boiler mass only. No flow rates (no kg/hr).
    Returns: methane_needed_kg (one-time), methane_per_day_kg (from AD), time_to_steam_min.
    """
    Q_sens, Q_latent, Q_startup = boiler_startup_energy_kj(
        boiler_water_capacity_kg, T_steam_C
    )
    methane_needed_kg = methane_mass_needed_kg(Q_startup, eta_boiler_pct, LHV_METHANE_KJ_KG)
    methane_per_day_kg = methane_production_kg_per_day(avg_daily_methane_m3, ch4_density_kg_m3)
    time_to_steam_min = time_to_steam_minutes(
        Q_startup, methane_per_day_kg, eta_boiler_pct, LHV_METHANE_KJ_KG
    )
    part = partition_methane_per_day(methane_per_day_kg, methane_needed_kg)

    return {
        "boiler_water_capacity_kg": boiler_water_capacity_kg,
        "Q_startup_kj": Q_startup,
        "Q_sensible_kj": Q_sens,
        "Q_latent_kj": Q_latent,
        "methane_needed_kg": methane_needed_kg,
        "methane_per_day_kg": methane_per_day_kg,
        "startup_time_minutes": time_to_steam_min,
        "boiler_kg_per_day": part["boiler_kg_per_day"],
        "collector_kg_per_day": part["collector_kg_per_day"],
        "boiler_pct": part["boiler_pct"],
        "collector_pct": part["collector_pct"],
        "eta_boiler_pct": eta_boiler_pct,
        "T_steam_C": T_steam_C,
    }
