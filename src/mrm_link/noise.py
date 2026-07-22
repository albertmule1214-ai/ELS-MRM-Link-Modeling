"""Noise generation and PSD/RMS validation utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class WhiteNoiseValidationResult:
    frequency_hz: np.ndarray
    measured_psd_v2_per_hz: np.ndarray
    expected_psd_v2_per_hz: np.ndarray
    enbw_hz: float
    theoretical_rms_v: float
    measured_rms_v: float
    welch_integrated_rms_v: float
    input_sample_rms_v: float

    @property
    def time_rms_relative_error(self) -> float:
        return self.measured_rms_v / self.theoretical_rms_v - 1.0

    @property
    def welch_rms_relative_error(self) -> float:
        return self.welch_integrated_rms_v / self.theoretical_rms_v - 1.0


def bessel_reference_sos(
    sample_rate_hz: float, bandwidth_hz: float, order: int = 4
) -> np.ndarray:
    """Return the same -3 dB-normalized Bessel filter used by the L1 receiver."""

    return signal.bessel(
        order,
        bandwidth_hz,
        btype="lowpass",
        analog=False,
        output="sos",
        norm="mag",
        fs=sample_rate_hz,
    )


def equivalent_noise_bandwidth_hz(
    sections: np.ndarray, sample_rate_hz: float, points: int = 131073
) -> float:
    """Integrate |H(f)|^2 over the positive-frequency Nyquist interval."""

    frequency_hz, response = signal.sosfreqz(
        sections, worN=points, fs=sample_rate_hz
    )
    return float(np.trapezoid(np.abs(response) ** 2, frequency_hz))


def validate_filtered_white_noise(
    one_sided_asd_v_per_sqrt_hz: float,
    sample_rate_hz: float,
    bandwidth_hz: float,
    number_of_samples: int,
    welch_segment_samples: int,
    seed: int,
) -> WhiteNoiseValidationResult:
    """Compare theory, time-domain RMS and Welch-integrated RMS."""

    if one_sided_asd_v_per_sqrt_hz <= 0.0:
        raise ValueError("White-noise ASD must be positive")
    if number_of_samples < 8 * welch_segment_samples:
        raise ValueError("Use at least eight Welch segments")

    sections = bessel_reference_sos(sample_rate_hz, bandwidth_hz)
    enbw_hz = equivalent_noise_bandwidth_hz(sections, sample_rate_hz)
    theoretical_rms_v = one_sided_asd_v_per_sqrt_hz * np.sqrt(enbw_hz)

    # For sampled real white noise, one-sided PSD = 2*sigma^2/fs.
    input_sample_rms_v = (
        one_sided_asd_v_per_sqrt_hz * np.sqrt(sample_rate_hz / 2.0)
    )
    generator = np.random.default_rng(seed)
    input_noise_v = generator.normal(0.0, input_sample_rms_v, number_of_samples)
    output_noise_v = signal.sosfilt(sections, input_noise_v)

    settling_samples = min(welch_segment_samples, number_of_samples // 8)
    settled_noise_v = output_noise_v[settling_samples:]
    measured_rms_v = float(np.std(settled_noise_v, ddof=0))
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
    expected_psd = (
        one_sided_asd_v_per_sqrt_hz**2 * np.abs(response) ** 2
    )
    welch_integrated_rms_v = float(np.sqrt(np.trapezoid(measured_psd, frequency_hz)))

    return WhiteNoiseValidationResult(
        frequency_hz=frequency_hz,
        measured_psd_v2_per_hz=measured_psd,
        expected_psd_v2_per_hz=expected_psd,
        enbw_hz=enbw_hz,
        theoretical_rms_v=float(theoretical_rms_v),
        measured_rms_v=measured_rms_v,
        welch_integrated_rms_v=welch_integrated_rms_v,
        input_sample_rms_v=float(input_sample_rms_v),
    )

