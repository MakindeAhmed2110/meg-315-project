"""
Power cycle (Brayton) logic from example: compressor, combustion, turbine, generator.
Inputs: biogas volume (m³), volatile mass (kg), air mass flow (kg/s), pressure ratio,
compressor/turbine/generator efficiencies, ambient air temp (°C).
Outputs: T2, T3, T4 (°C), net electrical power (kWe), thermal input (kW).
"""


def power_cycle_logic(
    biogas_vol_m3: float,
    volatile_mass_kg: float,
    air_mass_flow_kg_s: float,
    pressure_ratio: float,
    eta_compressor: float,
    eta_turbine: float,
    eta_generator: float,
    t_ambient_c: float,
) -> dict:
    """
    Brayton cycle: ambient → compressor → combustion → turbine → exhaust.
    eta_* are 0..1 (e.g. 0.85 for 85%).
    Returns dict with T2_C, T3_C, T4_C, W_Comp, W_Turb, Net_Power_kWe, Thermal_Input_kW.
    """
    T_ambient_K = t_ambient_c + 273.15
    cp_air, cp_gas = 1.005, 1.15  # kJ/(kg·K)
    gamma_air, gamma_gas = 1.4, 1.33

    # Compressor (isentropic then actual)
    T2_s_K = T_ambient_K * (pressure_ratio ** ((gamma_air - 1) / gamma_air))
    T2_actual_K = T_ambient_K + (T2_s_K - T_ambient_K) / eta_compressor
    W_comp_kW = air_mass_flow_kg_s * cp_air * (T2_actual_K - T_ambient_K)

    # Thermal input from biogas + volatiles (example formula)
    LHV_biogas_kJ_m3 = 21_500  # kJ/m³ (example value)
    LHV_volatiles_kJ_kg = 4000
    # biogas_vol_m3: total m³; convert to per-minute for rate. Example: (biogas_vol * 21500)/1440 + (volatile_mass * 4000)/60
    Q_dot_fuel_kW = (
        (biogas_vol_m3 * LHV_biogas_kJ_m3) / 1440.0
        + (volatile_mass_kg * LHV_volatiles_kJ_kg) / 60.0
    )

    # Combustion: T3 = T2 + Q/(m_dot_air * cp_gas)
    T3_actual_K = T2_actual_K + (Q_dot_fuel_kW / (air_mass_flow_kg_s * cp_gas))

    # Turbine (isentropic then actual)
    T4_s_K = T3_actual_K / (pressure_ratio ** ((gamma_gas - 1) / gamma_gas))
    T4_actual_K = T3_actual_K - eta_turbine * (T3_actual_K - T4_s_K)
    W_turbine_kW = air_mass_flow_kg_s * cp_gas * (T3_actual_K - T4_actual_K)

    P_net_mech_kW = W_turbine_kW - W_comp_kW
    P_elec_kWe = P_net_mech_kW * eta_generator

    return {
        "T2_C": T2_actual_K - 273.15,
        "T3_C": T3_actual_K - 273.15,
        "T4_C": T4_actual_K - 273.15,
        "W_Comp_kW": W_comp_kW,
        "W_Turb_kW": W_turbine_kW,
        "Net_Power_kWe": P_elec_kWe,
        "Thermal_Input_kW": Q_dot_fuel_kW,
        "pressure_ratio": pressure_ratio,
        "t_ambient_C": t_ambient_c,
    }
