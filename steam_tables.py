"""
Steam table lookups from CSV (from example/). Used for T–H and H–S diagrams.
Saturation by T; saturation T from P; superheated h,s from (P, T).
"""

import os
import pandas as pd
import numpy as np


def _resolve_csv(name: str) -> str:
    """Resolve path to CSV: project root, then example/."""
    base = os.path.dirname(os.path.abspath(__file__))
    for folder in (base, os.path.join(base, "example")):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return os.path.join(base, name)


class SteamTableLookup:
    def __init__(self, file_path: str | None = None):
        path = file_path or _resolve_csv("saturated_by_pressure_V1.4.csv")
        try:
            self.df = pd.read_csv(path)
            self.df.columns = self.df.columns.str.strip()
            self.df = self.df.sort_values("T (°C)").reset_index(drop=True)
        except Exception as e:
            print(f"Error loading CSV {path}: {e}")
            self.df = None

    def lookup_enthalpy(self, target_temp: float) -> tuple[float | None, float | None]:
        if self.df is None:
            return None, None
        temps = self.df["T (°C)"].values
        if target_temp <= temps[0]:
            row = self.df.iloc[0]
            return float(row["Enthalpy Liquid (kJ/kg)"]), float(row["Enthalpy of Vaporization (kJ/kg)"])
        if target_temp >= temps[-1]:
            row = self.df.iloc[-1]
            return float(row["Enthalpy Liquid (kJ/kg)"]), float(row["Enthalpy of Vaporization (kJ/kg)"])
        hf = float(np.interp(target_temp, temps, self.df["Enthalpy Liquid (kJ/kg)"].values))
        hfg = float(np.interp(target_temp, temps, self.df["Enthalpy of Vaporization (kJ/kg)"].values))
        return hf, hfg

    def lookup_entropy(self, target_temp: float) -> tuple[float | None, float | None]:
        if self.df is None:
            return None, None
        temps = self.df["T (°C)"].values
        if target_temp <= temps[0]:
            row = self.df.iloc[0]
            return float(row["Entropy Liquid [kJ/(kg K)]"]), float(row["Entropy Vapor [kJ/(kg K)]"])
        if target_temp >= temps[-1]:
            row = self.df.iloc[-1]
            return float(row["Entropy Liquid [kJ/(kg K)]"]), float(row["Entropy Vapor [kJ/(kg K)]"])
        sf = float(np.interp(target_temp, temps, self.df["Entropy Liquid [kJ/(kg K)]"].values))
        sg = float(np.interp(target_temp, temps, self.df["Entropy Vapor [kJ/(kg K)]"].values))
        return sf, sg

    def get_sat_temp(self, target_pressure: float) -> float | None:
        """Saturation temperature (°C) at given pressure (MPa)."""
        if self.df is None:
            return None
        try:
            pressures = self.df["P (MPa)"].values
            temps = self.df["T (°C)"].values
            if target_pressure <= pressures[0]:
                return float(temps[0])
            if target_pressure >= pressures[-1]:
                return float(temps[-1])
            return float(np.interp(target_pressure, pressures, temps))
        except KeyError:
            return None

    def get_sat_pressure(self, target_temp: float) -> float | None:
        """Saturation pressure (MPa) at given temperature (°C). Inverse of get_sat_temp."""
        if self.df is None:
            return None
        try:
            temps = self.df["T (°C)"].values
            pressures = self.df["P (MPa)"].values
            if target_temp <= temps[0]:
                return float(pressures[0])
            if target_temp >= temps[-1]:
                return float(pressures[-1])
            return float(np.interp(target_temp, temps, pressures))
        except KeyError:
            return None


class SuperheatedLookup:
    """
    Superheated (and compressed liquid) table: h, s at (P, T).
    """

    def __init__(self, file_path: str | None = None):
        path = file_path or _resolve_csv("compressed_liquid_and_superheated_steam_V1.3.csv")
        try:
            self.df = pd.read_csv(path)
            self.df.columns = self.df.columns.str.strip()
            numeric_cols = [
                "Pressure (MPa)",
                "Temperature (°C)",
                "Specific Volume (m^3/kg)",
                "Density (kg/m^3)",
                "Specific Internal Energy (kJ/kg)",
                "Specific Enthalpy (kJ/kg)",
                "Specific Entropy [kJ/(kg K)]",
            ]
            for col in numeric_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
            self.df = self.df.dropna(subset=[
                "Pressure (MPa)",
                "Temperature (°C)",
                "Specific Enthalpy (kJ/kg)",
                "Specific Entropy [kJ/(kg K)]",
            ]).reset_index(drop=True)
            if "Phase" in self.df.columns:
                self.df["Phase"] = (
                    self.df["Phase"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .str.replace('"', "", regex=False)
                )
            self.df = self.df.sort_values(["Pressure (MPa)", "Temperature (°C)"]).reset_index(drop=True)
            self.pressures = sorted(self.df["Pressure (MPa)"].unique())
        except Exception as e:
            print(f"Error loading superheated CSV {path}: {e}")
            self.df = None
            self.pressures = []

    def _lookup_at_pressure(self, target_pressure: float, target_temp: float) -> tuple[float | None, float | None]:
        subset = (
            self.df[self.df["Pressure (MPa)"] == target_pressure]
            .sort_values("Temperature (°C)")
        )
        if subset.empty:
            return None, None
        temps = subset["Temperature (°C)"].values
        h_vals = subset["Specific Enthalpy (kJ/kg)"].values
        s_vals = subset["Specific Entropy [kJ/(kg K)]"].values
        h = float(np.interp(target_temp, temps, h_vals))
        s = float(np.interp(target_temp, temps, s_vals))
        return h, s

    def lookup(self, target_pressure: float, target_temp: float) -> tuple[float | None, float | None]:
        """(h, s) in kJ/kg and kJ/(kg·K) at (P in MPa, T in °C)."""
        if self.df is None or len(self.pressures) == 0:
            return None, None
        pressures = np.array(self.pressures)
        if target_pressure <= pressures[0]:
            return self._lookup_at_pressure(float(pressures[0]), target_temp)
        if target_pressure >= pressures[-1]:
            return self._lookup_at_pressure(float(pressures[-1]), target_temp)
        idx = np.searchsorted(pressures, target_pressure)
        p_lo, p_hi = float(pressures[idx - 1]), float(pressures[idx])
        h_lo, s_lo = self._lookup_at_pressure(p_lo, target_temp)
        h_hi, s_hi = self._lookup_at_pressure(p_hi, target_temp)
        if None in (h_lo, s_lo, h_hi, s_hi):
            return None, None
        frac = (target_pressure - p_lo) / (p_hi - p_lo)
        return h_lo + frac * (h_hi - h_lo), s_lo + frac * (s_hi - s_lo)


# Singleton lookups (lazy) for use in th_diagram
_sat_lookup: SteamTableLookup | None = None
_sup_lookup: SuperheatedLookup | None = None


def get_sat_lookup() -> SteamTableLookup:
    global _sat_lookup
    if _sat_lookup is None:
        _sat_lookup = SteamTableLookup()
    return _sat_lookup


def get_sup_lookup() -> SuperheatedLookup:
    global _sup_lookup
    if _sup_lookup is None:
        _sup_lookup = SuperheatedLookup()
    return _sup_lookup
