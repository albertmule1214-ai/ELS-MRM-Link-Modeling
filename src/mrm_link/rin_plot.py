"""Diagnostic plot for explicit-bandwidth RIN validation."""

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

from .rin import BandLimitedRinResult, ConstantPowerRinReceiverResult


def plot_rin_validation(
    source: BandLimitedRinResult,
    receiver: ConstantPowerRinReceiverResult,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), constrained_layout=True)

    positive = source.frequency_hz > 0.0
    axes[0].semilogy(
        source.frequency_hz[positive] / 1.0e9,
        source.measured_psd_per_hz[positive],
        linewidth=1.0,
        label="Welch measurement",
    )
    axes[0].semilogy(
        source.frequency_hz[positive] / 1.0e9,
        np.maximum(source.expected_psd_per_hz[positive], 1.0e-30),
        linewidth=2.0,
        label="Configured support",
    )
    axes[0].set_xlim(0.0, 80.0)
    axes[0].set_title("Fractional source RIN PSD")
    axes[0].set_xlabel("Frequency (GHz)")
    axes[0].set_ylabel("Relative-power PSD (1/Hz)")
    axes[0].legend()

    receiver_positive = receiver.frequency_hz > 0.0
    axes[1].semilogy(
        receiver.frequency_hz[receiver_positive] / 1.0e9,
        receiver.measured_psd_v2_per_hz[receiver_positive],
        linewidth=1.0,
        label="Welch measurement",
    )
    axes[1].semilogy(
        receiver.frequency_hz[receiver_positive] / 1.0e9,
        np.maximum(receiver.expected_psd_v2_per_hz[receiver_positive], 1.0e-30),
        linewidth=2.0,
        label="RIN x gain^2 x |H|^2",
    )
    axes[1].set_xlim(0.0, 80.0)
    axes[1].set_title("Constant-power receiver PSD")
    axes[1].set_xlabel("Frequency (GHz)")
    axes[1].set_ylabel("Output PSD (V^2/Hz)")
    axes[1].legend()

    labels = ["Theory", "Time RMS", "Welch integral"]
    source_values = [
        source.theoretical_rms * 100.0,
        source.measured_rms * 100.0,
        source.welch_integrated_rms * 100.0,
    ]
    axes[2].bar(labels, source_values, color=["#5b8ff9", "#61d9a5", "#f6bd16"])
    axes[2].set_ylabel("Fractional optical-power RMS (%)")
    axes[2].set_title("Source RIN RMS closure")

    for axis in axes:
        axis.grid(True, which="both", alpha=0.22)
    figure.suptitle("L4 explicitly band-limited high-speed RIN validation")
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

