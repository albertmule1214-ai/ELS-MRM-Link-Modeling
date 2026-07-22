from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.rin import (
    generate_band_limited_rin,
    validate_constant_power_rin_receiver,
)


def test_band_limited_rin_source_psd_and_rms() -> None:
    source = generate_band_limited_rin(
        number_of_samples=262144,
        sample_rate_hz=53.125e9 * 16,
        rin_db_per_hz=-144.0,
        valid_frequency_min_hz=10.0e6,
        valid_frequency_max_hz=40.0e9,
        welch_segment_samples=8192,
        seed=987,
    )
    assert abs(source.rms_relative_error) < 0.03
    assert abs(source.welch_integrated_rms / source.theoretical_rms - 1.0) < 0.04
    assert 0.0 < source.theoretical_rms < 0.02


def test_constant_power_rin_receiver_matches_psd_integral() -> None:
    sample_rate_hz = 53.125e9 * 16
    source = generate_band_limited_rin(
        number_of_samples=262144,
        sample_rate_hz=sample_rate_hz,
        rin_db_per_hz=-144.0,
        valid_frequency_min_hz=10.0e6,
        valid_frequency_max_hz=40.0e9,
        welch_segment_samples=8192,
        seed=654,
    )
    receiver = validate_constant_power_rin_receiver(
        rin=source,
        sample_rate_hz=sample_rate_hz,
        valid_frequency_min_hz=10.0e6,
        valid_frequency_max_hz=40.0e9,
        optical_power_w=1.0e-3,
        responsivity_a_per_w=0.9,
        transimpedance_ohm=1.0e3,
        receiver_bandwidth_hz=26.5625e9,
        welch_segment_samples=8192,
    )
    assert abs(receiver.rms_relative_error) < 0.05
    assert abs(receiver.welch_integrated_rms_v / receiver.theoretical_rms_v - 1.0) < 0.05
