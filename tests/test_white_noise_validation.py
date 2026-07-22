from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.ber import validate_gaussian_ber_by_counting
from mrm_link.noise import validate_filtered_white_noise


def test_white_noise_psd_and_rms_close_theory() -> None:
    result = validate_filtered_white_noise(
        one_sided_asd_v_per_sqrt_hz=10.0e-9,
        sample_rate_hz=53.125e9 * 16,
        bandwidth_hz=26.5625e9,
        number_of_samples=262144,
        welch_segment_samples=8192,
        seed=1234,
    )
    assert abs(result.time_rms_relative_error) < 0.03
    assert abs(result.welch_rms_relative_error) < 0.04


def test_countable_gaussian_ber_matches_tail_probability() -> None:
    samples = [-1.0, -1.0, 1.0, 1.0] * 1024
    labels = [0, 0, 1, 1] * 1024
    result = validate_gaussian_ber_by_counting(
        samples_v=samples,
        labels=labels,
        sigma_v=1.0 / 3.0,
        repeats=64,
        seed=4321,
        threshold_v=0.0,
    )
    assert result.counted_errors > 100
    assert abs(result.counted_ber / result.theoretical_ber - 1.0) < 0.15
