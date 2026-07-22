"""Run the first static MRM baseline from the command line."""

from __future__ import annotations

import argparse
from pathlib import Path

from .baseline import run_static_baseline, write_scan_csv
from .config import load_config
from .plotting import plot_static_scan


def main() -> None:
    package_root = Path(__file__).resolve().parents[2]
    default_config = package_root / "configs" / "mrm_oci_53g_nrz_v0.toml"
    default_scan = package_root / "results" / "static_mrm_q_detuning_scan.csv"
    default_plot = package_root / "results" / "static_mrm_q_detuning_scan.png"

    parser = argparse.ArgumentParser(
        description="Run the noiseless L0 static through-port MRM baseline"
    )
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--scan-output", type=Path, default=default_scan)
    parser.add_argument("--plot-output", type=Path, default=default_plot)
    args = parser.parse_args()

    config = load_config(args.config)
    result = run_static_baseline(config)
    scan_path = write_scan_csv(config, args.scan_output)
    plot_path = plot_static_scan(scan_path, args.plot_output)

    print("Noiseless static MRM baseline")
    print(f"  config: {args.config.resolve()}")
    print(f"  UI: {result.ui_s * 1e12:.6f} ps")
    print(f"  MRM FWHM: {result.fwhm_m * 1e12:.6f} pm")
    print(
        f"  state 0: V={result.voltage_0_v:.3f} V, "
        f"detuning={result.detuning_0_m * 1e12:.3f} pm, "
        f"T={result.transmission_0:.6f}, "
        f"P0={result.levels.p0_w * 1e3:.6f} mW"
    )
    print(
        f"  state 1: V={result.voltage_1_v:.3f} V, "
        f"detuning={result.detuning_1_m * 1e12:.3f} pm, "
        f"T={result.transmission_1:.6f}, "
        f"P1={result.levels.p1_w * 1e3:.6f} mW"
    )
    print(f"  OMA: {result.levels.oma_w * 1e3:.6f} mW")
    print(f"  OMA: {result.levels.oma_dbm:.6f} dBm")
    print(f"  ER: {result.levels.er_db:.6f} dB")
    print(f"  Q/detuning scan: {scan_path.resolve()}")
    print(f"  Q/detuning plot: {plot_path.resolve()}")


if __name__ == "__main__":
    main()

