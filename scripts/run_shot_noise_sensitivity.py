"""Run signal-dependent shot-noise validation and a synthetic sensitivity sweep."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config, value
from mrm_link.sensitivity import sweep_receiver_sensitivity
from mrm_link.shot_noise import validate_signal_dependent_shot_noise
from mrm_link.shot_plot import plot_shot_noise_and_sensitivity
from mrm_link.waveform import run_noiseless_waveform


def main() -> None:
    link_config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    validation_config = load_config(
        PROJECT_ROOT / "configs" / "shot_noise_sensitivity.toml"
    )
    symbol_rate_hz = float(value(link_config, "signal", "symbol_rate"))
    samples_per_ui = int(value(link_config, "signal", "samples_per_ui"))
    sample_rate_hz = symbol_rate_hz * samples_per_ui
    bandwidth_hz = float(value(link_config, "receiver", "reference_filter_bandwidth"))
    seed = int(validation_config["meta"]["random_seed"])

    noiseless = run_noiseless_waveform(link_config)
    noise = validate_signal_dependent_shot_noise(
        optical_power_w=noiseless.optical_power_w,
        bits=noiseless.bits,
        samples_per_ui=samples_per_ui,
        alignment=noiseless.sampling,
        sample_rate_hz=sample_rate_hz,
        bandwidth_hz=bandwidth_hz,
        responsivity_a_per_w=float(value(link_config, "receiver", "pd_responsivity")),
        transimpedance_ohm=float(value(link_config, "receiver", "tia_transimpedance")),
        electron_charge_c=float(
            value(validation_config, "shot_noise", "electron_charge")
        ),
        dark_current_a=float(value(validation_config, "shot_noise", "dark_current")),
        tia_output_asd_v_per_sqrt_hz=float(
            value(validation_config, "tia_noise", "output_voltage_noise_asd")
        ),
        welch_segment_samples=int(
            value(validation_config, "validation", "welch_segment_samples")
        ),
        impulse_response_min_samples=int(
            value(validation_config, "validation", "impulse_response_min_samples")
        ),
        seed=seed,
    )

    loss_db = np.linspace(
        float(value(validation_config, "sensitivity", "additional_loss_min")),
        float(value(validation_config, "sensitivity", "additional_loss_max")),
        int(value(validation_config, "sensitivity", "points")),
    )
    sensitivity = sweep_receiver_sensitivity(
        baseline_samples_v=noiseless.sampling.samples,
        labels=noise.decision_labels,
        baseline_shot_variance_v2=noise.decision_shot_variance_v2,
        tia_variance_v2=noise.tia_variance_v2,
        baseline_average_optical_power_w=float(np.mean(noiseless.optical_power_w)),
        additional_loss_db=loss_db,
        target_ber=float(value(validation_config, "sensitivity", "target_ber")),
    )

    summary_path = PROJECT_ROOT / "results" / "shot_noise_sensitivity_summary.json"
    csv_path = PROJECT_ROOT / "results" / "shot_noise_sensitivity.csv"
    plot_path = PROJECT_ROOT / "results" / "shot_noise_sensitivity.png"
    summary = {
        "model": "L3_signal_dependent_PD_shot_noise_plus_TIA_noise",
        "status": "synthetic_validation_not_device_prediction",
        "shot_noise_reference_plane": value(
            validation_config, "shot_noise", "reference_plane"
        ),
        "tia_noise_reference_plane": value(
            validation_config, "tia_noise", "reference_plane"
        ),
        "reference_filter_enbw_hz": noise.enbw_hz,
        "average_photocurrent_a": noise.average_photocurrent_a,
        "theoretical_total_rms_v": noise.theoretical_total_rms_v,
        "measured_total_rms_v": noise.measured_total_rms_v,
        "welch_integrated_rms_v": noise.welch_integrated_rms_v,
        "total_rms_relative_error": noise.total_rms_relative_error,
        "welch_rms_relative_error": noise.welch_rms_relative_error,
        "theoretical_rms_0_v": noise.theoretical_rms_0_v,
        "theoretical_rms_1_v": noise.theoretical_rms_1_v,
        "measured_rms_0_v": noise.measured_rms_0_v,
        "measured_rms_1_v": noise.measured_rms_1_v,
        "target_ber": sensitivity.target_ber,
        "synthetic_sensitivity_dbm": sensitivity.sensitivity_dbm,
        "formal_compliance_claim": "none",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "additional_loss_db",
                "received_average_power_dbm",
                "ber",
                "decision_threshold_v",
                "rms_0_v",
                "rms_1_v",
            ]
        )
        writer.writerows(
            zip(
                sensitivity.additional_loss_db,
                sensitivity.received_average_power_dbm,
                sensitivity.ber,
                sensitivity.decision_threshold_v,
                sensitivity.rms_0_v,
                sensitivity.rms_1_v,
                strict=True,
            )
        )
    plot_shot_noise_and_sensitivity(noise, sensitivity, plot_path)

    print("L3 signal-dependent PD shot noise + TIA noise")
    print(f"  ENBW: {noise.enbw_hz / 1e9:.6f} GHz")
    print(f"  average photocurrent: {noise.average_photocurrent_a * 1e3:.6f} mA")
    print(f"  total RMS theory/time/Welch: {noise.theoretical_total_rms_v*1e3:.6f} / {noise.measured_total_rms_v*1e3:.6f} / {noise.welch_integrated_rms_v*1e3:.6f} mV")
    print(f"  conditional RMS bit 0 theory/time: {noise.theoretical_rms_0_v*1e3:.6f} / {noise.measured_rms_0_v*1e3:.6f} mV")
    print(f"  conditional RMS bit 1 theory/time: {noise.theoretical_rms_1_v*1e3:.6f} / {noise.measured_rms_1_v*1e3:.6f} mV")
    print(f"  target BER: {sensitivity.target_ber:.3e}")
    print(f"  synthetic sensitivity: {sensitivity.sensitivity_dbm:.6f} dBm")
    print("  Formal compliance/device prediction: none")


if __name__ == "__main__":
    main()

