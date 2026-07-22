"""Validate receiver white-noise PSD, RMS and a directly countable BER."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.ber import validate_gaussian_ber_by_counting
from mrm_link.config import load_config, value
from mrm_link.noise import validate_filtered_white_noise
from mrm_link.noise_plot import plot_white_noise_validation
from mrm_link.waveform import run_noiseless_waveform


def main() -> None:
    link_config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    validation_config = load_config(
        PROJECT_ROOT / "configs" / "white_noise_validation.toml"
    )
    symbol_rate_hz = float(value(link_config, "signal", "symbol_rate"))
    samples_per_ui = int(value(link_config, "signal", "samples_per_ui"))
    sample_rate_hz = symbol_rate_hz * samples_per_ui
    bandwidth_hz = float(value(link_config, "receiver", "reference_filter_bandwidth"))
    asd_v_per_sqrt_hz = float(
        value(validation_config, "white_noise", "output_voltage_noise_asd")
    )
    seed = int(validation_config["meta"]["random_seed"])

    noiseless = run_noiseless_waveform(link_config)
    noise = validate_filtered_white_noise(
        one_sided_asd_v_per_sqrt_hz=asd_v_per_sqrt_hz,
        sample_rate_hz=sample_rate_hz,
        bandwidth_hz=bandwidth_hz,
        number_of_samples=int(
            value(validation_config, "white_noise", "number_of_time_samples")
        ),
        welch_segment_samples=int(
            value(validation_config, "white_noise", "welch_segment_samples")
        ),
        seed=seed,
    )

    target_q = float(value(validation_config, "ber_stress_validation", "target_q"))
    stress_sigma_v = noiseless.sampling.eye_height / (2.0 * target_q)
    ber = validate_gaussian_ber_by_counting(
        samples_v=noiseless.sampling.samples,
        labels=noiseless.sampling.labels,
        sigma_v=stress_sigma_v,
        repeats=int(value(validation_config, "ber_stress_validation", "repeats")),
        seed=seed + 1,
    )

    summary_path = PROJECT_ROOT / "results" / "white_noise_validation_summary.json"
    plot_path = PROJECT_ROOT / "results" / "white_noise_validation.png"
    payload = {
        "model": "L2_isolated_receiver_white_noise",
        "noise_reference_plane": value(
            validation_config, "white_noise", "reference_plane"
        ),
        "psd_convention": value(validation_config, "white_noise", "psd_convention"),
        "input_asd_v_per_sqrt_hz": asd_v_per_sqrt_hz,
        "reference_filter_enbw_hz": noise.enbw_hz,
        "theoretical_output_rms_v": noise.theoretical_rms_v,
        "time_domain_output_rms_v": noise.measured_rms_v,
        "welch_integrated_output_rms_v": noise.welch_integrated_rms_v,
        "time_rms_relative_error": noise.time_rms_relative_error,
        "welch_rms_relative_error": noise.welch_rms_relative_error,
        "device_noise_value_status": "ASSUMPTION_not_project_TIA_data",
        "ber_validation_mode": "stress_only_directly_countable",
        "ber_stress_target_q": target_q,
        "ber_stress_sigma_v": stress_sigma_v,
        "ber_theoretical": ber.theoretical_ber,
        "ber_counted": ber.counted_ber,
        "ber_counted_errors": ber.counted_errors,
        "ber_counted_bits": ber.counted_bits,
        "low_ber_claim": "none",
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_white_noise_validation(noise, ber, plot_path)

    print("L2 isolated receiver white-noise validation")
    print(f"  one-sided ASD: {asd_v_per_sqrt_hz:.3e} V/sqrt(Hz) [ASSUMPTION]")
    print(f"  reference-filter ENBW: {noise.enbw_hz / 1e9:.6f} GHz")
    print(f"  theoretical RMS: {noise.theoretical_rms_v * 1e6:.6f} uV")
    print(f"  time-domain RMS: {noise.measured_rms_v * 1e6:.6f} uV")
    print(f"  Welch-integrated RMS: {noise.welch_integrated_rms_v * 1e6:.6f} uV")
    print(
        f"  BER stress validation: counted={ber.counted_ber:.6e}, "
        f"theory={ber.theoretical_ber:.6e}, errors={ber.counted_errors}"
    )
    print("  This BER is a validation stress case, not a device prediction.")


if __name__ == "__main__":
    main()

