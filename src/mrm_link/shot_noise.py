"""Signal-dependent photodiode shot-noise validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from .noise import bessel_reference_sos, equivalent_noise_bandwidth_hz
from .waveform import SamplingResult


@dataclass(frozen=True)
class ShotNoiseValidationResult:
    frequency_hz: np.ndarray
    measured_psd_v2_per_hz: np.ndarray
    expected_psd_v2_per_hz: np.ndarray
    output_noise_v: np.ndarray
    theoretical_variance_v2: np.ndarray
    decision_indices: np.ndarray
    decision_labels: np.ndarray
    decision_noise_v: np.ndarray
    decision_shot_variance_v2: np.ndarray
    tia_variance_v2: float
    enbw_hz: float
    average_photocurrent_a: float
    theoretical_total_rms_v: float
    measured_total_rms_v: float
    welch_integrated_rms_v: float
    theoretical_rms_0_v: float
    theoretical_rms_1_v: float
    measured_rms_0_v: float
    measured_rms_1_v: float

    @property
    def total_rms_relative_error(self) -> float:
        return self.measured_total_rms_v / self.theoretical_total_rms_v - 1.0

    @property
    def welch_rms_relative_error(self) -> float:
        return self.welch_integrated_rms_v / self.theoretical_total_rms_v - 1.0


def fixed_decision_indices(
    waveform_length: int,
    bits: np.ndarray,
    samples_per_ui: int,
    alignment: SamplingResult,
    guard_bits: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Reapply a previously chosen phase/lag without optimizing on noisy data."""

    indices = np.arange(
        alignment.phase_samples,
        waveform_length,
        samples_per_ui,
        dtype=np.int64,
    )[: len(bits)]
    if alignment.integer_lag_ui >= 0:
        indices = indices[alignment.integer_lag_ui :]
        labels = bits[: len(indices)]
    else:
        indices = indices[: alignment.integer_lag_ui]
        start = -alignment.integer_lag_ui
        labels = bits[start : start + len(indices)]
    return (
        indices[guard_bits:-guard_bits],
        labels[guard_bits:-guard_bits],
    )


def _reference_impulse_response(
    sections: np.ndarray,
    sample_rate_hz: float,
    bandwidth_hz: float,
    minimum_samples: int,
) -> np.ndarray:
    length = max(minimum_samples, int(np.ceil(64.0 * sample_rate_hz / bandwidth_hz)))
    impulse = np.zeros(length, dtype=float)
    impulse[0] = 1.0
    response = signal.sosfilt(sections, impulse)
    tail_energy_fraction = float(
        np.sum(response[-64:] ** 2) / np.sum(response**2)
    )
    if tail_energy_fraction > 1.0e-12:
        raise ValueError("Reference-filter impulse response is too short")
    return response


def validate_signal_dependent_shot_noise(
    optical_power_w: np.ndarray,
    bits: np.ndarray,
    samples_per_ui: int,
    alignment: SamplingResult,
    sample_rate_hz: float,
    bandwidth_hz: float,
    responsivity_a_per_w: float,
    transimpedance_ohm: float,
    electron_charge_c: float,
    dark_current_a: float,
    tia_output_asd_v_per_sqrt_hz: float,
    welch_segment_samples: int,
    impulse_response_min_samples: int,
    seed: int,
) -> ShotNoiseValidationResult:
    """Close analytic variance, generated waveform and PSD for PD+TIA noise."""

    optical_power_w = np.asarray(optical_power_w, dtype=float)
    if np.any(optical_power_w < 0.0):
        raise ValueError("Optical power cannot be negative")
    if responsivity_a_per_w <= 0.0 or transimpedance_ohm <= 0.0:
        raise ValueError("Responsivity and transimpedance must be positive")
    if electron_charge_c <= 0.0 or dark_current_a < 0.0:
        raise ValueError("Invalid electron charge or dark current")
    if tia_output_asd_v_per_sqrt_hz < 0.0:
        raise ValueError("TIA ASD cannot be negative")

    photocurrent_a = responsivity_a_per_w * optical_power_w + dark_current_a
    sections = bessel_reference_sos(sample_rate_hz, bandwidth_hz)
    enbw_hz = equivalent_noise_bandwidth_hz(sections, sample_rate_hz)
    impulse_response = _reference_impulse_response(
        sections,
        sample_rate_hz,
        bandwidth_hz,
        impulse_response_min_samples,
    )

    # One-sided shot PSD is 2*q*I. A real sampled sequence therefore has
    # pre-filter variance (2*q*I)*fs/2 = q*I*fs.
    shot_input_variance_a2 = electron_charge_c * photocurrent_a * sample_rate_hz
    squared_voltage_impulse = (transimpedance_ohm * impulse_response) ** 2
    shot_output_variance_v2 = signal.fftconvolve(
        shot_input_variance_a2,
        squared_voltage_impulse,
        mode="full",
    )[: len(optical_power_w)]
    tia_variance_v2 = tia_output_asd_v_per_sqrt_hz**2 * enbw_hz
    theoretical_variance_v2 = shot_output_variance_v2 + tia_variance_v2

    generator = np.random.default_rng(seed)
    shot_current_noise_a = generator.normal(size=len(optical_power_w)) * np.sqrt(
        shot_input_variance_a2
    )
    tia_input_rms_v = tia_output_asd_v_per_sqrt_hz * np.sqrt(sample_rate_hz / 2.0)
    tia_voltage_noise_v = generator.normal(
        0.0, tia_input_rms_v, len(optical_power_w)
    )
    output_noise_v = signal.sosfilt(
        sections,
        transimpedance_ohm * shot_current_noise_a + tia_voltage_noise_v,
    )

    settling_samples = min(welch_segment_samples, len(output_noise_v) // 8)
    settled_noise_v = output_noise_v[settling_samples:]
    settled_variance_v2 = theoretical_variance_v2[settling_samples:]
    theoretical_total_rms_v = float(np.sqrt(np.mean(settled_variance_v2)))
    measured_total_rms_v = float(np.sqrt(np.mean(settled_noise_v**2)))
    frequency_hz, measured_psd = signal.welch(
        settled_noise_v,
        fs=sample_rate_hz,
        window="hann",
        nperseg=welch_segment_samples,
        detrend=False,
        scaling="density",
        return_onesided=True,
    )
    _, response = signal.sosfreqz(
        sections, worN=frequency_hz, fs=sample_rate_hz
    )
    average_photocurrent_a = float(np.mean(photocurrent_a[settling_samples:]))
    expected_input_psd_v2_per_hz = (
        2.0
        * electron_charge_c
        * average_photocurrent_a
        * transimpedance_ohm**2
        + tia_output_asd_v_per_sqrt_hz**2
    )
    expected_psd = expected_input_psd_v2_per_hz * np.abs(response) ** 2
    welch_integrated_rms_v = float(np.sqrt(np.trapezoid(measured_psd, frequency_hz)))

    decision_indices, decision_labels = fixed_decision_indices(
        len(output_noise_v), bits, samples_per_ui, alignment
    )
    decision_noise_v = output_noise_v[decision_indices]
    decision_shot_variance_v2 = shot_output_variance_v2[decision_indices]
    decision_total_variance_v2 = decision_shot_variance_v2 + tia_variance_v2

    zero = decision_labels == 0
    one = decision_labels == 1
    theoretical_rms_0_v = float(np.sqrt(np.mean(decision_total_variance_v2[zero])))
    theoretical_rms_1_v = float(np.sqrt(np.mean(decision_total_variance_v2[one])))
    measured_rms_0_v = float(np.sqrt(np.mean(decision_noise_v[zero] ** 2)))
    measured_rms_1_v = float(np.sqrt(np.mean(decision_noise_v[one] ** 2)))

    return ShotNoiseValidationResult(
        frequency_hz=frequency_hz,
        measured_psd_v2_per_hz=measured_psd,
        expected_psd_v2_per_hz=expected_psd,
        output_noise_v=output_noise_v,
        theoretical_variance_v2=theoretical_variance_v2,
        decision_indices=decision_indices,
        decision_labels=decision_labels,
        decision_noise_v=decision_noise_v,
        decision_shot_variance_v2=decision_shot_variance_v2,
        tia_variance_v2=float(tia_variance_v2),
        enbw_hz=enbw_hz,
        average_photocurrent_a=average_photocurrent_a,
        theoretical_total_rms_v=theoretical_total_rms_v,
        measured_total_rms_v=measured_total_rms_v,
        welch_integrated_rms_v=welch_integrated_rms_v,
        theoretical_rms_0_v=theoretical_rms_0_v,
        theoretical_rms_1_v=theoretical_rms_1_v,
        measured_rms_0_v=measured_rms_0_v,
        measured_rms_1_v=measured_rms_1_v,
    )

