"""Plots for shot-noise validation and synthetic sensitivity."""

from __future__ import annotations

from pathlib import Path
import os

_MPL_CACHE = Path(__file__).resolve().parents[2] / "results" / ".matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .sensitivity import SensitivitySweepResult
from .shot_noise import ShotNoiseValidationResult


def plot_shot_noise_and_sensitivity(
    noise: ShotNoiseValidationResult,
    sensitivity: SensitivitySweepResult,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)

    positive = noise.frequency_hz > 0.0
    axes[0].semilogy(
        noise.frequency_hz[positive] / 1.0e9,
        noise.measured_psd_v2_per_hz[positive],
        linewidth=1.0,
        alpha=0.75,
        label="Welch measurement",
    )
    axes[0].semilogy(
        noise.frequency_hz[positive] / 1.0e9,
        noise.expected_psd_v2_per_hz[positive],
        linewidth=2.0,
        label="Time-average theory",
    )
    axes[0].set_title("PD shot + TIA noise PSD")
    axes[0].set_xlabel("Frequency (GHz)")
    axes[0].set_ylabel("Output PSD (V^2/Hz)")
    axes[0].legend()

    x = np.arange(2)
    width = 0.36
    axes[1].bar(
        x - width / 2,
        [noise.theoretical_rms_0_v * 1e3, noise.theoretical_rms_1_v * 1e3],
        width,
        label="Theory",
    )
    axes[1].bar(
        x + width / 2,
        [noise.measured_rms_0_v * 1e3, noise.measured_rms_1_v * 1e3],
        width,
        label="Time waveform",
    )
    axes[1].set_xticks(x, ["bit 0", "bit 1"])
    axes[1].set_ylabel("Decision noise RMS (mV)")
    axes[1].set_title("Signal-dependent conditional RMS")
    axes[1].legend()

    axes[2].semilogy(
        sensitivity.received_average_power_dbm,
        np.maximum(sensitivity.ber, 1.0e-300),
        linewidth=2.0,
    )
    axes[2].axhline(
        sensitivity.target_ber,
        color="#d1495b",
        linestyle="--",
        label=f"target {sensitivity.target_ber:.1e}",
    )
    if sensitivity.sensitivity_dbm is not None:
        axes[2].axvline(
            sensitivity.sensitivity_dbm,
            color="#2a9d8f",
            linestyle="--",
            label=f"synthetic sensitivity {sensitivity.sensitivity_dbm:.2f} dBm",
        )
    axes[2].set_ylim(1.0e-12, 0.6)
    axes[2].set_xlabel("Average optical power at PD (dBm)")
    axes[2].set_ylabel("Analytic conditional BER")
    axes[2].set_title("Synthetic receiver sensitivity")
    axes[2].legend()

    for axis in axes:
        axis.grid(True, which="both", alpha=0.22)
    figure.suptitle("L3 signal-dependent shot noise and sensitivity validation")
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

