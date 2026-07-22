"""Plots for quasi-static MRM temperature detuning."""

from __future__ import annotations

from pathlib import Path
import os

_MPL_CACHE = Path(__file__).resolve().parents[2] / "results" / ".matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .thermal import ThermalSweepResult


def plot_thermal_sweep(
    result: ThermalSweepResult, output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(15.2, 4.6), constrained_layout=True)
    temperature = result.temperature_offset_c

    axes[0].plot(temperature, result.detuning_0_pm, label="bit 0 detuning")
    axes[0].plot(temperature, result.detuning_1_pm, label="bit 1 detuning")
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_xlabel("Temperature offset (degC)")
    axes[0].set_ylabel("Laser minus resonance (pm)")
    axes[0].set_title(f"Resonance shift ({result.thermal_tuning_pm_per_c:.1f} pm/degC)")
    axes[0].legend()

    axes[1].plot(temperature, result.p0_mw, label="P0")
    axes[1].plot(temperature, result.p1_mw, label="P1")
    axes[1].plot(temperature, result.signed_oma_mw, label="signed OMA")
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_xlabel("Temperature offset (degC)")
    axes[1].set_ylabel("Optical power (mW)")
    axes[1].set_title("Optical levels and polarity")
    axes[1].legend()

    axes[2].plot(temperature, result.signed_eye_height_v, label="signed eye height")
    axes[2].plot(temperature, result.signed_er_db, label="signed ER (dB)")
    axes[2].axhline(0.0, color="black", linewidth=0.8)
    axes[2].set_xlabel("Temperature offset (degC)")
    axes[2].set_ylabel("Signed metric")
    axes[2].set_title("Eye closure and polarity inversion")
    axes[2].legend()

    for axis in axes:
        axis.axvline(0.0, color="#d1495b", linestyle="--", linewidth=1.0)
        axis.grid(True, alpha=0.22)
    figure.suptitle("L5 quasi-static MRM temperature-detuning sweep")
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

