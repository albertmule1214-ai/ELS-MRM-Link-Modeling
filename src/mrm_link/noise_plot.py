"""Plots for the first isolated white-noise validation."""

from __future__ import annotations

from pathlib import Path
import os

_MPL_CACHE = Path(__file__).resolve().parents[2] / "results" / ".matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .ber import GaussianBerValidationResult
from .noise import WhiteNoiseValidationResult


def plot_white_noise_validation(
    noise: WhiteNoiseValidationResult,
    ber: GaussianBerValidationResult,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(12.2, 4.5), constrained_layout=True)

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
        label="ASD^2 x |H(f)|^2",
    )
    axes[0].set_xlabel("Frequency (GHz)")
    axes[0].set_ylabel("Output noise PSD (V^2/Hz)")
    axes[0].set_title("Filtered white-noise PSD")
    axes[0].legend()
    axes[0].grid(True, which="both", alpha=0.22)

    labels = ["Theory", "Time RMS", "Welch integral"]
    values_uv = [
        noise.theoretical_rms_v * 1.0e6,
        noise.measured_rms_v * 1.0e6,
        noise.welch_integrated_rms_v * 1.0e6,
    ]
    axes[1].bar(labels, values_uv, color=["#5b8ff9", "#61d9a5", "#f6bd16"])
    axes[1].set_ylabel("RMS noise (uV)")
    axes[1].set_title(
        f"RMS closure; BER stress check: {ber.counted_ber:.3e} vs {ber.theoretical_ber:.3e}"
    )
    axes[1].grid(True, axis="y", alpha=0.22)

    figure.suptitle("L2 isolated receiver white-noise validation")
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

