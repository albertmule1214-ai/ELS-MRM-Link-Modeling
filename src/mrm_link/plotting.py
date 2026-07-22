"""Plot helpers for the verified static MRM scan."""

from __future__ import annotations

from pathlib import Path
import os

_MPL_CACHE = Path(__file__).resolve().parents[2] / "results" / ".matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_static_scan(csv_path: str | Path, output_path: str | Path) -> Path:
    data = pd.read_csv(csv_path)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    q_values = sorted(data["q"].unique())

    selected_q = min(q_values, key=lambda item: abs(item - 7500.0))
    selected = data[data["q"] == selected_q]
    axes[0].plot(
        selected["normalized_reference_detuning"],
        selected["t0"],
        label="NRZ state 0",
        linewidth=2.0,
    )
    axes[0].plot(
        selected["normalized_reference_detuning"],
        selected["t1"],
        label="NRZ state 1",
        linewidth=2.0,
    )
    axes[0].set_title(f"Through-port levels (Q={selected_q:.0f})")
    axes[0].set_ylabel("Power transmission")
    axes[0].legend()

    for loaded_q in q_values:
        group = data[data["q"] == loaded_q]
        label = f"Q={loaded_q:.0f}"
        axes[1].plot(
            group["normalized_reference_detuning"],
            group["oma_mw_signed"],
            label=label,
        )
        axes[2].plot(
            group["normalized_reference_detuning"],
            group["er_db_signed"],
            label=label,
        )

    axes[1].set_title("Signed OMA vs. working point")
    axes[1].set_ylabel("Signed OMA (mW)")
    axes[2].set_title("Signed ER vs. working point")
    axes[2].set_ylabel("Signed ER (dB)")
    axes[2].legend()

    for axis in axes:
        axis.axhline(0.0, color="black", linewidth=0.7, alpha=0.5)
        axis.axvline(0.0, color="black", linewidth=0.7, alpha=0.5)
        axis.set_xlabel("Reference detuning / FWHM")
        axis.grid(True, alpha=0.25)

    figure.suptitle(
        "Noiseless static MRM baseline — illustrative paper/assumption parameters",
        fontsize=13,
    )
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path

