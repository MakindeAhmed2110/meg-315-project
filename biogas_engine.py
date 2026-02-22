"""
Biogas kinetics and methane yield calculations for AD-HTC schematic.
Modular engine for feedstock partitioning, Arrhenius kinetics, and ignition power.
"""

import numpy as np

# Physical constants
R_GAS = 8.314  # J/(mol·K)
Ea_DEFAULT = 60_000  # J/mol (activation energy)
SECONDS_PER_DAY = 86400

# Methane yield from biomass: DM → VS → volume → mass
# Dry Matter (DM) = total mass × (1 - moisture%); e.g. cattle slurry ~6% DM (94% water)
# Volatile Solids (VS) = ~80% of DM (biodegradable fraction)
VS_FRACTION = 0.80  # fraction of dry matter that is volatile solids
SMY = 0.35  # Specific Methane Yield: m³ CH4 per kg VS (standard)
CH4_DENSITY_KG_M3 = 0.657  # methane density at standard conditions (kg/m³); volume → mass

LHV_BIOGAS = 21  # MJ/m³
DEFAULT_METHANE_PURITY = 0.60  # 60% CH4 in biogas
PEAK_TO_AVG_FACTOR = 1.5  # peak daily production / average daily at maturity
HIGH_SOLIDS_WARNING_PCT = 12.0  # warn if final total solids % above this


def water_dilution_mass_balance(
    user_biomass_mass_kg_s: float,
    dry_matter_pct: float,
    added_water_ratio: float,
) -> tuple[float, float, float, float]:
    """
    Mixing strategy: add water by ratio (e.g. 1:2 = 2 kg water per kg biomass).
    Returns (added_water_kg_s, total_slurry_kg_s, final_total_solids_pct, high_solids_warning).
    """
    added_water_kg_s = user_biomass_mass_kg_s * added_water_ratio
    total_slurry_kg_s = user_biomass_mass_kg_s + added_water_kg_s
    if total_slurry_kg_s <= 0:
        return 0.0, user_biomass_mass_kg_s, dry_matter_pct, dry_matter_pct > HIGH_SOLIDS_WARNING_PCT
    # Final solids % = (DM in feed / total slurry) × 100; high % → risk of blockage
    dry_matter_mass_kg_s = user_biomass_mass_kg_s * (dry_matter_pct / 100.0)
    final_total_solids_pct = (dry_matter_mass_kg_s / total_slurry_kg_s) * 100.0
    high_solids = final_total_solids_pct > HIGH_SOLIDS_WARNING_PCT
    return added_water_kg_s, total_slurry_kg_s, final_total_solids_pct, high_solids


def reactor_mass_kg(total_slurry_flow_kg_s: float, retention_days: float) -> float:
    """Reactor capacity = slurry flow × retention time (mass only, no volume)."""
    if retention_days <= 0 or np.isinf(retention_days):
        return 0.0
    return total_slurry_flow_kg_s * retention_days * SECONDS_PER_DAY


def partition_feedstock(total_mass_flow_kg_s: float, moisture_content_pct: float) -> tuple[float, float]:
    """
    Split feedstock: moisture-rich stream → AD; moisture-lean → HTC reactor.
    """
    f_moisture = moisture_content_pct / 100.0
    moisture_rich_biomass_kg_s = total_mass_flow_kg_s * f_moisture  # to AD
    moisture_lean_biomass_kg_s = total_mass_flow_kg_s * (1.0 - f_moisture)  # to HTC
    return moisture_rich_biomass_kg_s, moisture_lean_biomass_kg_s


def reaction_rate_constant_k(A: float, Ea: float, T_K: float) -> float:
    """Arrhenius: k = A × exp(-Ea/(R×T)); rate constant (e.g. 1/day) sets digestion speed."""
    return A * np.exp(-Ea / (R_GAS * T_K))


def days_to_maturity_from_k(k_per_day: float) -> float:
    """Retention time (days to maturity) = 1/k."""
    if k_per_day <= 0:
        return np.inf
    return 1.0 / k_per_day


def celsius_to_kelvin(T_C: float) -> float:
    """Convert ambient temperature from °C to K."""
    return T_C + 273.15


def methane_production(
    moisture_rich_biomass_kg_s: float,
    moisture_content_pct: float,
    days_retention: float,
    smy: float = SMY,
    vs_fraction: float = VS_FRACTION,
) -> tuple[float, float, float, float]:
    """
    Methane from biomass: DM → VS → volume → mass.
    Returns (avg_daily_m3, peak_daily_m3, biogas_over_retention_m3, methane_mass_kg).
    """
    # Step 1: Dry Matter (DM) = feed mass × (1 - moisture%). E.g. 60 kg cattle slurry × 0.06 = 3.6 kg DM
    dry_matter_kg_s = moisture_rich_biomass_kg_s * (1.0 - moisture_content_pct / 100.0)
    # Step 2: Volatile Solids (VS) = ~80% of DM (biodegradable fraction). E.g. 3.6 kg × 0.80 = 2.88 kg VS
    vs_flow_kg_s = dry_matter_kg_s * vs_fraction
    # Step 3: Methane volume = VS × SMY. E.g. 2.88 kg VS × 0.35 m³/kg ≈ 1.008 m³ CH4
    vs_per_day_kg = vs_flow_kg_s * SECONDS_PER_DAY
    avg_daily_m3 = vs_per_day_kg * smy
    peak_daily_m3 = avg_daily_m3 * PEAK_TO_AVG_FACTOR
    biogas_over_retention_m3 = avg_daily_m3 * days_retention if days_retention > 0 and not np.isinf(days_retention) else 0.0
    # Step 4: Mass of methane (kg) = volume × density. E.g. 1.008 m³ × 0.657 kg/m³ ≈ 0.66 kg CH4
    methane_mass_kg = biogas_over_retention_m3 * CH4_DENSITY_KG_M3
    return avg_daily_m3, peak_daily_m3, biogas_over_retention_m3, methane_mass_kg


def ignition_power_kw(peak_daily_m3_per_day: float, lhv_mj_per_m3: float = LHV_BIOGAS) -> float:
    """Thermal power (kW) from burning biogas: peak gas flow × LHV (21 MJ/m³)."""
    peak_m3_per_s = peak_daily_m3_per_day / SECONDS_PER_DAY
    energy_MJ_per_s = peak_m3_per_s * lhv_mj_per_m3
    return energy_MJ_per_s * 1000.0  # MW to kW: MJ/s = MW, 1 MW = 1000 kW


class BiogasKinetics:
    """
    Handles feedstock partitioning, Arrhenius kinetics, methane yield,
    and ignition power for the AD-HTC schematic.
    """

    def __init__(
        self,
        total_mass_flow_kg_s: float,
        moisture_content_pct: float,
        temperature_C: float,
        added_water_ratio: float = 0.0,
        A: float = 1e10,
        Ea: float = Ea_DEFAULT,
    ):
        self.total_mass_flow_kg_s = total_mass_flow_kg_s
        self.moisture_content_pct = moisture_content_pct
        self.temperature_C = temperature_C
        self.added_water_ratio = added_water_ratio
        self.A = A  # pre-exponential factor (1/day)
        self.Ea = Ea

        self._added_water_kg_s: float | None = None
        self._total_slurry_kg_s: float | None = None
        self._final_total_solids_pct: float | None = None
        self._high_solids_warning: bool | None = None
        self._reactor_mass_kg: float | None = None
        self._moisture_rich_kg_s: float | None = None
        self._moisture_lean_kg_s: float | None = None
        self._k_per_day: float | None = None
        self._days_to_maturity: float | None = None
        self._V_total_m3: float | None = None
        self._avg_daily_m3: float | None = None
        self._peak_daily_m3: float | None = None
        self._methane_mass_kg: float | None = None
        self._ignition_power_kw: float | None = None
        self._methane_purity: float = DEFAULT_METHANE_PURITY

    def run(self) -> "BiogasKinetics":
        """Run all calculations: water dilution first, then partitioning, kinetics, methane."""
        dry_matter_pct = 100.0 - self.moisture_content_pct
        (
            self._added_water_kg_s,
            self._total_slurry_kg_s,
            self._final_total_solids_pct,
            self._high_solids_warning,
        ) = water_dilution_mass_balance(
            self.total_mass_flow_kg_s, dry_matter_pct, self.added_water_ratio
        )
        self._moisture_rich_kg_s, self._moisture_lean_kg_s = partition_feedstock(
            self.total_mass_flow_kg_s, self.moisture_content_pct
        )
        T_K = celsius_to_kelvin(self.temperature_C)
        self._k_per_day = reaction_rate_constant_k(self.A, self.Ea, T_K)
        self._days_to_maturity = days_to_maturity_from_k(self._k_per_day)
        self._reactor_mass_kg = reactor_mass_kg(
            self._total_slurry_kg_s, self._days_to_maturity
        )
        self._avg_daily_m3, self._peak_daily_m3, self._V_total_m3, self._methane_mass_kg = methane_production(
            self._moisture_rich_kg_s,
            self.moisture_content_pct,
            self._days_to_maturity,
        )
        self._ignition_power_kw = ignition_power_kw(self._peak_daily_m3)
        return self

    @property
    def added_water_kg_s(self) -> float:
        if self._added_water_kg_s is None:
            self.run()
        return self._added_water_kg_s  # type: ignore

    @property
    def total_slurry_kg_s(self) -> float:
        if self._total_slurry_kg_s is None:
            self.run()
        return self._total_slurry_kg_s  # type: ignore

    @property
    def final_total_solids_pct(self) -> float:
        if self._final_total_solids_pct is None:
            self.run()
        return self._final_total_solids_pct  # type: ignore

    @property
    def high_solids_warning(self) -> bool:
        if self._high_solids_warning is None:
            self.run()
        return self._high_solids_warning  # type: ignore

    @property
    def reactor_mass_kg(self) -> float:
        if self._reactor_mass_kg is None:
            self.run()
        return self._reactor_mass_kg  # type: ignore

    @property
    def moisture_rich_biomass_kg_s(self) -> float:
        if self._moisture_rich_kg_s is None:
            self.run()
        return self._moisture_rich_kg_s  # type: ignore

    @property
    def moisture_lean_biomass_kg_s(self) -> float:
        if self._moisture_lean_kg_s is None:
            self.run()
        return self._moisture_lean_kg_s  # type: ignore

    @property
    def k_per_day(self) -> float:
        if self._k_per_day is None:
            self.run()
        return self._k_per_day  # type: ignore

    @property
    def days_to_maturity(self) -> float:
        if self._days_to_maturity is None:
            self.run()
        return self._days_to_maturity  # type: ignore

    @property
    def V_total_m3(self) -> float:
        if self._V_total_m3 is None:
            self.run()
        return self._V_total_m3  # type: ignore

    @property
    def avg_daily_m3(self) -> float:
        if self._avg_daily_m3 is None:
            self.run()
        return self._avg_daily_m3  # type: ignore

    @property
    def peak_daily_m3(self) -> float:
        if self._peak_daily_m3 is None:
            self.run()
        return self._peak_daily_m3  # type: ignore

    @property
    def methane_mass_kg(self) -> float:
        if self._methane_mass_kg is None:
            self.run()
        return self._methane_mass_kg  # type: ignore

    @property
    def ignition_power_kw(self) -> float:
        if self._ignition_power_kw is None:
            self.run()
        return self._ignition_power_kw  # type: ignore

    @property
    def methane_purity(self) -> float:
        return self._methane_purity

    def to_dict(self) -> dict:
        """Return all outputs as a dict (e.g. for session state or reports)."""
        self.run()
        dry_matter_kg_s = self._moisture_rich_kg_s * (1.0 - self.moisture_content_pct / 100.0)
        days = self._days_to_maturity if not np.isinf(self._days_to_maturity) else 30.0
        volatile_yield_kg = dry_matter_kg_s * days * SECONDS_PER_DAY * 0.3
        return {
            "added_water_kg_s": self._added_water_kg_s,
            "total_slurry_kg_s": self._total_slurry_kg_s,
            "final_total_solids_pct": self._final_total_solids_pct,
            "high_solids_warning": self._high_solids_warning,
            "reactor_mass_kg": self._reactor_mass_kg,
            "moisture_rich_biomass_kg_s": self._moisture_rich_kg_s,
            "moisture_lean_biomass_kg_s": self._moisture_lean_kg_s,
            "k_per_day": self._k_per_day,
            "days_to_maturity": self._days_to_maturity,
            "V_total_m3": self._V_total_m3,
            "avg_daily_m3": self._avg_daily_m3,
            "peak_daily_m3": self._peak_daily_m3,
            "methane_mass_kg": self._methane_mass_kg,
            "ignition_power_kw": self._ignition_power_kw,
            "methane_purity": self._methane_purity,
            "volatile_yield_kg": volatile_yield_kg,
        }
