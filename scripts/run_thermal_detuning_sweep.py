"""Run the quasi-static MRM temperature-detuning sweep."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config, value
from mrm_link.thermal import sweep_quasi_static_temperature
from mrm_link.thermal_plot import plot_thermal_sweep


def _zero_crossing(x: np.ndarray, y: np.ndarray) -> float | None:
    crossings = np.flatnonzero(np.signbit(y[:-1]) != np.signbit(y[1:]))
    if len(crossings) == 0:
        return None
    index = int(crossings[0])
    return float(np.interp(0.0, y[index : index + 2], x[index : index + 2]))


def main() -> None:
    link_config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    sweep_config = load_config(PROJECT_ROOT / "configs" / "thermal_detuning_sweep.toml")
    temperature_c = np.linspace(
        float(value(sweep_config, "sweep", "temperature_min")),
        float(value(sweep_config, "sweep", "temperature_max")),
        int(value(sweep_config, "sweep", "points")),
    )
    result = sweep_quasi_static_temperature(
        link_config,
        temperature_c,
        number_of_bits=int(value(sweep_config, "sweep", "number_of_bits")),
        samples_per_ui=int(value(sweep_config, "sweep", "samples_per_ui")),
    )
    polarity_crossing_c = _zero_crossing(
        result.temperature_offset_c, result.signed_oma_mw
    )

    csv_path = PROJECT_ROOT / "results" / "thermal_detuning_sweep.csv"
    summary_path = PROJECT_ROOT / "results" / "thermal_detuning_summary.json"
    plot_path = PROJECT_ROOT / "results" / "thermal_detuning_sweep.png"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "temperature_offset_c",
                "resonance_shift_pm",
                "detuning_0_pm",
                "detuning_1_pm",
                "p0_mw",
                "p1_mw",
                "signed_oma_mw",
                "signed_er_db",
                "signed_eye_height_v",
            ]
        )
        writer.writerows(
            zip(
                result.temperature_offset_c,
                result.resonance_shift_pm,
                result.detuning_0_pm,
                result.detuning_1_pm,
                result.p0_mw,
                result.p1_mw,
                result.signed_oma_mw,
                result.signed_er_db,
                result.signed_eye_height_v,
                strict=True,
            )
        )
    nominal = result.nominal_index
    payload = {
        "model": "L5_quasi_static_MRM_temperature_detuning",
        "status": "synthetic_validation_not_thermal_control_prediction",
        "thermal_tuning_pm_per_c": result.thermal_tuning_pm_per_c,
        "mrm_fwhm_pm": result.fwhm_pm,
        "temperature_for_one_fwhm_c": result.fwhm_pm / result.thermal_tuning_pm_per_c,
        "nominal_temperature_offset_c": result.temperature_offset_c[nominal],
        "nominal_signed_oma_mw": result.signed_oma_mw[nominal],
        "nominal_signed_er_db": result.signed_er_db[nominal],
        "nominal_signed_eye_height_v": result.signed_eye_height_v[nominal],
        "first_polarity_crossing_c": polarity_crossing_c,
        "thermal_dynamics": sweep_config["interpretation"]["thermal_dynamics"],
        "heater_model": sweep_config["interpretation"]["heater_model"],
        "control_loop": sweep_config["interpretation"]["control_loop"],
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_thermal_sweep(result, plot_path)

    print("L5 quasi-static MRM temperature-detuning sweep")
    print(f"  thermal tuning: {result.thermal_tuning_pm_per_c:.6f} pm/degC [literature example]")
    print(f"  one FWHM temperature shift: {result.fwhm_pm/result.thermal_tuning_pm_per_c:.6f} degC")
    print(f"  nominal signed OMA: {result.signed_oma_mw[nominal]:.6f} mW")
    print(f"  nominal signed eye height: {result.signed_eye_height_v[nominal]:.6f} V")
    print(f"  first polarity crossing: {polarity_crossing_c:.6f} degC")
    print("  thermal dynamics/heater/control loop: not implemented")


if __name__ == "__main__":
    main()

