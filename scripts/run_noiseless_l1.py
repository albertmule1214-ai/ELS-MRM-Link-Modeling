"""Run and plot the first time-domain link baseline."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config
from mrm_link.eye_plot import plot_noiseless_eye
from mrm_link.waveform import run_noiseless_waveform, write_noiseless_summary


def main() -> None:
    config_path = PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml"
    summary_path = PROJECT_ROOT / "results" / "noiseless_l1_summary.json"
    plot_path = PROJECT_ROOT / "results" / "noiseless_l1_eye.png"
    config = load_config(config_path)
    result = run_noiseless_waveform(config)
    write_noiseless_summary(result, config, summary_path)
    plot_noiseless_eye(result, plot_path)

    print("Noiseless 53.125-Gbaud NRZ L1")
    print(f"  UI: {result.ui_s * 1e12:.6f} ps")
    print(
        f"  sample phase: {result.sampling.phase_samples}/"
        f"{result.samples_per_ui} UI; lag={result.sampling.integer_lag_ui} UI"
    )
    print(f"  receiver eye height: {result.sampling.eye_height:.6f} V")
    print(
        f"  optical sample phase: {result.optical_sampling.phase_samples}/"
        f"{result.samples_per_ui} UI; lag={result.optical_sampling.integer_lag_ui} UI"
    )
    print(f"  sampled optical P0: {result.optical_levels.p0_w * 1e3:.6f} mW")
    print(f"  sampled optical P1: {result.optical_levels.p1_w * 1e3:.6f} mW")
    print(f"  sampled OMA: {result.optical_levels.oma_w * 1e3:.6f} mW")
    print(f"  sampled ER: {result.optical_levels.er_db:.6f} dB")
    print(f"  summary: {summary_path.resolve()}")
    print(f"  eye plot: {plot_path.resolve()}")


if __name__ == "__main__":
    main()

