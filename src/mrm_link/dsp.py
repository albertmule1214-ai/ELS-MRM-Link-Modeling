"""Small deterministic filters used by the L1 baseline."""

from __future__ import annotations

from math import exp, log

import numpy as np
from scipy import signal


def first_order_from_20_80(
    waveform: np.ndarray, sample_interval_s: float, transition_time_20_80_s: float
) -> np.ndarray:
    """Apply a first-order response calibrated by its 20%-80% transition time."""

    if sample_interval_s <= 0.0:
        raise ValueError("sample interval must be positive")
    if transition_time_20_80_s <= 0.0:
        return np.asarray(waveform, dtype=float).copy()

    time_constant_s = transition_time_20_80_s / log(4.0)
    alpha = 1.0 - exp(-sample_interval_s / time_constant_s)
    source = np.asarray(waveform, dtype=float)
    initial_state = np.array([(1.0 - alpha) * source[0]])
    filtered, _ = signal.lfilter(
        [alpha], [1.0, -(1.0 - alpha)], source, zi=initial_state
    )
    return filtered


def bessel_thomson_lowpass(
    waveform: np.ndarray,
    sample_rate_hz: float,
    bandwidth_hz: float,
    order: int = 4,
) -> np.ndarray:
    """Apply a digital Bessel low-pass with -3 dB magnitude normalization."""

    if sample_rate_hz <= 0.0 or bandwidth_hz <= 0.0:
        raise ValueError("sample rate and bandwidth must be positive")
    if bandwidth_hz >= sample_rate_hz / 2.0:
        raise ValueError("bandwidth must be below Nyquist")
    sections = signal.bessel(
        order,
        bandwidth_hz,
        btype="lowpass",
        analog=False,
        output="sos",
        norm="mag",
        fs=sample_rate_hz,
    )
    return signal.sosfilt(sections, np.asarray(waveform, dtype=float))

