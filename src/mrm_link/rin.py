"""Explicitly band-limited high-speed relative-intensity-noise validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from .noise import bessel_reference_sos


@dataclass(frozen=True)
class BandLimitedRinResult:
    fractional_noise: np.ndarray
    frequency_hz: np.ndarray
    measured_psd_per_hz: np.ndarray
    expected_psd_per_hz: np.ndarray
    rin_linear_per_hz: float
    configured_bandwidth_hz: float
    discrete_effective_bandwidth_hz: float
    theoretical_rms: float
    measured_rms: float
    welch_integrated_rms: float

    @property
    def rms_relative_error(self) -> float:
        return self.measured_rms / self.theoretical_rms - 1.0


@dataclass(frozen=True)
class ConstantPowerRinReceiverResult:
    output_noise_v: np.ndarray
    frequency_hz: np.ndarray
    measured_psd_v2_per_hz: np.ndarray
    expected_psd_v2_per_hz: np.ndarray
    optical_to_voltage_gain_v: float
    theoretical_rms_v: float
    measured_rms_v: float
    welch_integrated_rms_v: float

    @property
    def rms_relative_error(self) -> float:
        return self.measured_rms_v / self.theoretical_rms_v - 1.0


def rin_db_per_hz_to_linear(rin_db_per_hz: float) -> float:
    return 10.0 ** (rin_db_per_hz / 10.0)


def generate_band_limited_rin(
    number_of_samples: int,
    sample_rate_hz: float,
    rin_db_per_hz: float,
    valid_frequency_min_hz: float,
    valid_frequency_max_hz: float,
    welch_segment_samples: int,
    seed: int,
) -> BandLimitedRinResult:
    """Generate real fractional-power noise with a rectangular one-sided PSD."""

    nyquist_hz = sample_rate_hz / 2.0
    if number_of_samples <= 0 or sample_rate_hz <= 0.0:
        raise ValueError("Sample count and sample rate must be positive")
    if not 0.0 <= valid_frequency_min_hz < valid_frequency_max_hz < nyquist_hz:
        raise ValueError("RIN support must lie inside the positive Nyquist interval")
    if number_of_samples < 8 * welch_segment_samples:
        raise ValueError("Use at least eight Welch segments")

    rin_linear = rin_db_per_hz_to_linear(rin_db_per_hz)
    input_sample_rms = np.sqrt(rin_linear * sample_rate_hz / 2.0)
    generator = np.random.default_rng(seed)
    white = generator.normal(0.0, input_sample_rms, number_of_samples)
    frequency_bins_hz = np.fft.rfftfreq(number_of_samples, 1.0 / sample_rate_hz)
    passband = (
        (frequency_bins_hz >= valid_frequency_min_hz)
        & (frequency_bins_hz <= valid_frequency_max_hz)
    )
    spectrum = np.fft.rfft(white)
    spectrum[~passband] = 0.0
    fractional_noise = np.fft.irfft(spectrum, n=number_of_samples)

    expected_on_bins = np.where(passband, rin_linear, 0.0)
    discrete_effective_bandwidth_hz = float(
        np.trapezoid(expected_on_bins / rin_linear, frequency_bins_hz)
    )
    theoretical_rms = float(np.sqrt(rin_linear * discrete_effective_bandwidth_hz))
    measured_rms = float(np.sqrt(np.mean(fractional_noise**2)))
    frequency_hz, measured_psd = signal.welch(
        fractional_noise,
        fs=sample_rate_hz,
        window="hann",
        nperseg=welch_segment_samples,
        detrend=False,
        scaling="density",
        return_onesided=True,
    )
    expected_psd = np.where(
        (frequency_hz >= valid_frequency_min_hz)
        & (frequency_hz <= valid_frequency_max_hz),
        rin_linear,
        0.0,
    )
    welch_integrated_rms = float(np.sqrt(np.trapezoid(measured_psd, frequency_hz)))

    return BandLimitedRinResult(
        fractional_noise=fractional_noise,
        frequency_hz=frequency_hz,
        measured_psd_per_hz=measured_psd,
        expected_psd_per_hz=expected_psd,
        rin_linear_per_hz=rin_linear,
        configured_bandwidth_hz=float(
            valid_frequency_max_hz - valid_frequency_min_hz
        ),
        discrete_effective_bandwidth_hz=discrete_effective_bandwidth_hz,
        theoretical_rms=theoretical_rms,
        measured_rms=measured_rms,
        welch_integrated_rms=welch_integrated_rms,
    )


def validate_constant_power_rin_receiver(
    rin: BandLimitedRinResult,
    sample_rate_hz: float,
    valid_frequency_min_hz: float,
    valid_frequency_max_hz: float,
    optical_power_w: float,
    responsivity_a_per_w: float,
    transimpedance_ohm: float,
    receiver_bandwidth_hz: float,
    welch_segment_samples: int,
) -> ConstantPowerRinReceiverResult:
    """Validate RIN through a constant-power PD/TIA/reference-receiver path."""

    if optical_power_w <= 0.0:
        raise ValueError("Reference optical power must be positive")
    optical_to_voltage_gain_v = (
        optical_power_w * responsivity_a_per_w * transimpedance_ohm
    )
    sections = bessel_reference_sos(sample_rate_hz, receiver_bandwidth_hz)
    output_noise_v = signal.sosfilt(
        sections, optical_to_voltage_gain_v * rin.fractional_noise
    )
    settling_samples = min(welch_segment_samples, len(output_noise_v) // 8)
    settled_noise_v = output_noise_v[settling_samples:]
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
    passband = (
        (frequency_hz >= valid_frequency_min_hz)
        & (frequency_hz <= valid_frequency_max_hz)
    )
    expected_psd = np.where(
        passband,
        optical_to_voltage_gain_v**2
        * rin.rin_linear_per_hz
        * np.abs(response) ** 2,
        0.0,
    )
    theoretical_rms_v = float(np.sqrt(np.trapezoid(expected_psd, frequency_hz)))
    measured_rms_v = float(np.sqrt(np.mean(settled_noise_v**2)))
    welch_integrated_rms_v = float(
        np.sqrt(np.trapezoid(measured_psd, frequency_hz))
    )
    return ConstantPowerRinReceiverResult(
        output_noise_v=output_noise_v,
        frequency_hz=frequency_hz,
        measured_psd_v2_per_hz=measured_psd,
        expected_psd_v2_per_hz=expected_psd,
        optical_to_voltage_gain_v=float(optical_to_voltage_gain_v),
        theoretical_rms_v=theoretical_rms_v,
        measured_rms_v=measured_rms_v,
        welch_integrated_rms_v=welch_integrated_rms_v,
    )

