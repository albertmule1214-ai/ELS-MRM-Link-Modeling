"""Plots for the noiseless L1 waveform."""

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

from .waveform import NoiselessWaveformResult


def plot_noiseless_eye(
    result: NoiselessWaveformResult, output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sps = result.samples_per_ui

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    start_ui = 64
    shown_ui = 16
    start = start_ui * sps
    stop = (start_ui + shown_ui) * sps
    time_ui = np.arange(stop - start) / sps

    axes[0].plot(time_ui, result.ideal_driver_v[start:stop], alpha=0.45, label="ideal")
    axes[0].plot(time_ui, result.driver_v[start:stop], linewidth=1.6, label="10 ps edge")
    axes[0].set_title("MRM driver waveform")
    axes[0].set_xlabel("Time (UI)")
    axes[0].set_ylabel("Voltage (V)")
    axes[0].legend()

    axes[1].plot(time_ui, result.optical_power_w[start:stop] * 1.0e3)
    axes[1].set_title("TX MRM optical output")
    axes[1].set_xlabel("Time (UI)")
    axes[1].set_ylabel("Optical power (mW)")

    centers = (
        result.sampling.phase_samples
        + np.arange(64, len(result.bits) - 64) * sps
    )
    centers = centers[(centers >= sps) & (centers + sps < len(result.rx_voltage_v))]
    count = min(500, len(centers))
    selected = centers[np.linspace(0, len(centers) - 1, count, dtype=int)]
    eye_time_ui = np.arange(-sps, sps + 1) / sps
    for center in selected:
        trace = result.rx_voltage_v[center - sps : center + sps + 1]
        axes[2].plot(eye_time_ui, trace, color="#0068a8", alpha=0.035)
    axes[2].axvline(0.0, color="#d1495b", linewidth=1.2, label="chosen sample")
    axes[2].axhline(result.sampling.mean_0, color="black", linewidth=0.8, alpha=0.6)
    axes[2].axhline(result.sampling.mean_1, color="black", linewidth=0.8, alpha=0.6)
    axes[2].set_title("Noiseless receiver eye")
    axes[2].set_xlabel("Time relative to sample (UI)")
    axes[2].set_ylabel("TIA output (V)")
    axes[2].legend()

    for axis in axes:
        axis.grid(True, alpha=0.22)
    figure.suptitle(
        "53.125-Gbaud NRZ L1 baseline — all random noise disabled",
        fontsize=13,
    )
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

