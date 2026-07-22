from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.sensitivity import sweep_receiver_sensitivity
from mrm_link.shot_noise import validate_signal_dependent_shot_noise
from mrm_link.waveform import SamplingResult


def test_constant_power_shot_noise_matches_analytic_enbw() -> None:
    samples_per_ui = 16
    bits = np.tile(np.array([0, 1], dtype=np.uint8), 2048)
    power_w = np.full(len(bits) * samples_per_ui, 1.0e-3)
    alignment = SamplingResult(
        phase_samples=8,
        integer_lag_ui=1,
        samples=np.empty(0),
        labels=np.empty(0, dtype=np.uint8),
        mean_0=0.0,
        mean_1=1.0,
    )
    result = validate_signal_dependent_shot_noise(
        optical_power_w=power_w,
        bits=bits,
        samples_per_ui=samples_per_ui,
        alignment=alignment,
        sample_rate_hz=53.125e9 * samples_per_ui,
        bandwidth_hz=26.5625e9,
        responsivity_a_per_w=0.9,
        transimpedance_ohm=1.0e3,
        electron_charge_c=1.602176634e-19,
        dark_current_a=0.0,
        tia_output_asd_v_per_sqrt_hz=0.0,
        welch_segment_samples=4096,
        impulse_response_min_samples=2048,
        seed=123,
    )
    expected = 1.0e3 * np.sqrt(
        2.0 * 1.602176634e-19 * 0.9e-3 * result.enbw_hz
    )
    assert abs(result.theoretical_total_rms_v / expected - 1.0) < 0.005
    assert abs(result.measured_total_rms_v / expected - 1.0) < 0.04
    assert abs(result.welch_integrated_rms_v / expected - 1.0) < 0.05


def test_sensitivity_ber_is_monotonic_and_crosses_target() -> None:
    labels = np.tile(np.array([0, 1], dtype=np.uint8), 1024)
    samples_v = labels.astype(float)
    shot_variance = np.where(labels == 0, 1.0e-4, 4.0e-4)
    loss_db = np.linspace(0.0, 60.0, 61)
    result = sweep_receiver_sensitivity(
        baseline_samples_v=samples_v,
        labels=labels,
        baseline_shot_variance_v2=shot_variance,
        tia_variance_v2=1.0e-4,
        baseline_average_optical_power_w=1.0e-3,
        additional_loss_db=loss_db,
        target_ber=2.4e-4,
    )
    assert np.all(np.diff(result.ber) >= -1.0e-12)
    assert result.sensitivity_dbm is not None
    assert result.received_average_power_dbm[-1] < result.sensitivity_dbm < result.received_average_power_dbm[0]
