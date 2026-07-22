"""Validate an explicit-bandwidth high-speed RIN source and receiver path."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config, value
from mrm_link.rin import (
    generate_band_limited_rin,
    validate_constant_power_rin_receiver,
)
from mrm_link.rin_plot import plot_rin_validation
from mrm_link.waveform import run_noiseless_waveform


def main() -> None:
    link_config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    rin_config = load_config(
        PROJECT_ROOT / "configs" / "rin_bandlimited_validation.toml"
    )
    symbol_rate_hz = float(value(link_config, "signal", "symbol_rate"))
    samples_per_ui = int(value(link_config, "signal", "samples_per_ui"))
    sample_rate_hz = symbol_rate_hz * samples_per_ui
    frequency_min_hz = float(value(rin_config, "rin", "valid_frequency_min"))
    frequency_max_hz = float(value(rin_config, "rin", "valid_frequency_max"))
    welch_samples = int(value(rin_config, "validation", "welch_segment_samples"))

    source = generate_band_limited_rin(
        number_of_samples=int(value(rin_config, "validation", "number_of_samples")),
        sample_rate_hz=sample_rate_hz,
        rin_db_per_hz=float(value(rin_config, "rin", "density")),
        valid_frequency_min_hz=frequency_min_hz,
        valid_frequency_max_hz=frequency_max_hz,
        welch_segment_samples=welch_samples,
        seed=int(rin_config["meta"]["random_seed"]),
    )
    noiseless = run_noiseless_waveform(link_config)
    receiver = validate_constant_power_rin_receiver(
        rin=source,
        sample_rate_hz=sample_rate_hz,
        valid_frequency_min_hz=frequency_min_hz,
        valid_frequency_max_hz=frequency_max_hz,
        optical_power_w=float(np.mean(noiseless.optical_power_w)),
        responsivity_a_per_w=float(value(link_config, "receiver", "pd_responsivity")),
        transimpedance_ohm=float(value(link_config, "receiver", "tia_transimpedance")),
        receiver_bandwidth_hz=float(
            value(link_config, "receiver", "reference_filter_bandwidth")
        ),
        welch_segment_samples=welch_samples,
    )

    summary_path = PROJECT_ROOT / "results" / "rin_bandlimited_summary.json"
    plot_path = PROJECT_ROOT / "results" / "rin_bandlimited_validation.png"
    payload = {
        "model": "L4_explicitly_band_limited_high_speed_RIN",
        "status": "synthetic_validation_not_device_prediction",
        "psd_convention": value(rin_config, "rin", "psd_convention"),
        "rin_density_db_per_hz": value(rin_config, "rin", "density"),
        "valid_frequency_min_hz": frequency_min_hz,
        "valid_frequency_max_hz": frequency_max_hz,
        "low_frequency_apc_psd_reused": rin_config["rin"]["low_frequency_apc_psd_reused"],
        "source_theoretical_fractional_rms": source.theoretical_rms,
        "source_measured_fractional_rms": source.measured_rms,
        "source_welch_fractional_rms": source.welch_integrated_rms,
        "source_rms_relative_error": source.rms_relative_error,
        "constant_power_reference_w": float(np.mean(noiseless.optical_power_w)),
        "receiver_theoretical_rms_v": receiver.theoretical_rms_v,
        "receiver_measured_rms_v": receiver.measured_rms_v,
        "receiver_welch_rms_v": receiver.welch_integrated_rms_v,
        "receiver_rms_relative_error": receiver.rms_relative_error,
        "data_modulated_ber": "not_implemented_until_conditional_model_is_validated",
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_rin_validation(source, receiver, plot_path)

    print("L4 explicitly band-limited high-speed RIN")
    print(f"  configured RIN: {value(rin_config, 'rin', 'density'):.3f} dB/Hz")
    print(f"  explicit support: {frequency_min_hz/1e6:.3f} MHz to {frequency_max_hz/1e9:.3f} GHz")
    print(f"  source fractional RMS theory/time/Welch: {source.theoretical_rms:.6e} / {source.measured_rms:.6e} / {source.welch_integrated_rms:.6e}")
    print(f"  receiver RMS theory/time/Welch: {receiver.theoretical_rms_v*1e3:.6f} / {receiver.measured_rms_v*1e3:.6f} / {receiver.welch_integrated_rms_v*1e3:.6f} mV")
    print("  low-frequency APC PSD reused: false")
    print("  data-modulated RIN BER: intentionally deferred")


if __name__ == "__main__":
    main()

