"""Noiseless L1 time-domain link simulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json

import numpy as np

from .baseline import build_static_mrm
from .config import value
from .dsp import bessel_thomson_lowpass, first_order_from_20_80
from .metrics import OpticalLevels
from .prbs import prbs15


@dataclass(frozen=True)
class SamplingResult:
    phase_samples: int
    integer_lag_ui: int
    samples: np.ndarray
    labels: np.ndarray
    mean_0: float
    mean_1: float

    @property
    def eye_height(self) -> float:
        return self.mean_1 - self.mean_0


@dataclass(frozen=True)
class NoiselessWaveformResult:
    bits: np.ndarray
    samples_per_ui: int
    sample_interval_s: float
    ideal_driver_v: np.ndarray
    driver_v: np.ndarray
    optical_power_w: np.ndarray
    rx_voltage_v: np.ndarray
    sampling: SamplingResult
    optical_sampling: SamplingResult
    optical_levels: OpticalLevels

    @property
    def ui_s(self) -> float:
        return self.samples_per_ui * self.sample_interval_s


def _transmission_array(model: Any, voltage_v: np.ndarray) -> np.ndarray:
    reference_resonance_m = (
        model.laser_wavelength_m - model.reference_detuning_m
    )
    resonance_m = reference_resonance_m + model.voltage_tuning_efficiency_m_per_v * (
        voltage_v - model.reference_voltage_v
    )
    detuning_m = model.laser_wavelength_m - resonance_m
    normalized = 2.0 * detuning_m / model.fwhm_m
    depth_fraction = 1.0 - (
        model.on_resonance_transmission / model.off_resonance_transmission
    )
    transmission = model.off_resonance_transmission * (
        1.0 - depth_fraction / (1.0 + normalized**2)
    )
    return np.clip(transmission, 0.0, model.off_resonance_transmission)


def _align_samples(
    waveform: np.ndarray,
    bits: np.ndarray,
    samples_per_ui: int,
    guard_bits: int = 64,
    maximum_lag_ui: int = 4,
) -> SamplingResult:
    """Find the phase and whole-UI delay that maximize level separation."""

    best: tuple[float, int, int] | None = None

    for phase in range(samples_per_ui):
        waveform_samples = waveform[phase::samples_per_ui][: len(bits)]
        for lag in range(-maximum_lag_ui, maximum_lag_ui + 1):
            if lag >= 0:
                samples = waveform_samples[lag:]
                labels = bits[: len(samples)]
            else:
                samples = waveform_samples[:lag]
                labels = bits[-lag : -lag + len(samples)]
            if len(samples) <= 2 * guard_bits:
                continue
            samples = samples[guard_bits:-guard_bits]
            labels = labels[guard_bits:-guard_bits]
            zeros = samples[labels == 0]
            ones = samples[labels == 1]
            if len(zeros) == 0 or len(ones) == 0:
                continue
            score = float(np.mean(ones) - np.mean(zeros))
            if best is None or score > best[0]:
                best = (score, phase, lag)

    if best is None:
        raise RuntimeError("Unable to align waveform samples to the PRBS labels")

    _, phase, lag = best
    waveform_samples = waveform[phase::samples_per_ui][: len(bits)]
    if lag >= 0:
        waveform_samples = waveform_samples[lag:]
        labels = bits[: len(waveform_samples)]
    else:
        waveform_samples = waveform_samples[:lag]
        labels = bits[-lag : -lag + len(waveform_samples)]

    waveform_samples = waveform_samples[guard_bits:-guard_bits]
    labels = labels[guard_bits:-guard_bits]
    mean_0 = float(np.mean(waveform_samples[labels == 0]))
    mean_1 = float(np.mean(waveform_samples[labels == 1]))
    return SamplingResult(
        phase_samples=phase,
        integer_lag_ui=lag,
        samples=waveform_samples,
        labels=labels,
        mean_0=mean_0,
        mean_1=mean_1,
    )


def run_noiseless_waveform(config: Mapping[str, Any]) -> NoiselessWaveformResult:
    symbol_rate_hz = float(value(config, "signal", "symbol_rate"))
    samples_per_ui = int(value(config, "signal", "samples_per_ui"))
    number_of_bits = int(value(config, "signal", "number_of_bits"))
    sample_rate_hz = symbol_rate_hz * samples_per_ui
    sample_interval_s = 1.0 / sample_rate_hz

    bits = prbs15(number_of_bits)
    voltage_0_v = float(value(config, "driver", "voltage_low"))
    voltage_1_v = float(value(config, "driver", "voltage_high"))
    ideal_driver_v = np.repeat(
        np.where(bits == 0, voltage_0_v, voltage_1_v), samples_per_ui
    )
    driver_v = first_order_from_20_80(
        ideal_driver_v,
        sample_interval_s,
        float(value(config, "driver", "transition_time_20_80")),
    )

    model = build_static_mrm(config)
    transmission = _transmission_array(model, driver_v)
    input_power_w = float(value(config, "els", "apc_setpoint"))
    channel_loss_db = float(value(config, "optical_channel", "loss"))
    optical_power_w = (
        input_power_w * transmission * 10.0 ** (-channel_loss_db / 10.0)
    )

    pd_current_a = optical_power_w * float(
        value(config, "receiver", "pd_responsivity")
    )
    tia_voltage_v = pd_current_a * float(
        value(config, "receiver", "tia_transimpedance")
    )
    rx_voltage_v = bessel_thomson_lowpass(
        tia_voltage_v,
        sample_rate_hz,
        float(value(config, "receiver", "reference_filter_bandwidth")),
        order=4,
    )

    sampling = _align_samples(rx_voltage_v, bits, samples_per_ui)
    optical_sampling = _align_samples(optical_power_w, bits, samples_per_ui)
    levels = OpticalLevels(
        p0_w=optical_sampling.mean_0,
        p1_w=optical_sampling.mean_1,
    )
    return NoiselessWaveformResult(
        bits=bits,
        samples_per_ui=samples_per_ui,
        sample_interval_s=sample_interval_s,
        ideal_driver_v=ideal_driver_v,
        driver_v=driver_v,
        optical_power_w=optical_power_w,
        rx_voltage_v=rx_voltage_v,
        sampling=sampling,
        optical_sampling=optical_sampling,
        optical_levels=levels,
    )


def write_noiseless_summary(
    result: NoiselessWaveformResult,
    config: Mapping[str, Any],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": "L1_noiseless_static_MRM",
        "config": config.get("_config_path", "in_memory"),
        "ui_ps": result.ui_s * 1.0e12,
        "samples_per_ui": result.samples_per_ui,
        "sampling_phase_samples": result.sampling.phase_samples,
        "sampling_phase_ui": result.sampling.phase_samples / result.samples_per_ui,
        "integer_lag_ui": result.sampling.integer_lag_ui,
        "rx_mean_0_v": result.sampling.mean_0,
        "rx_mean_1_v": result.sampling.mean_1,
        "rx_eye_height_v": result.sampling.eye_height,
        "optical_sampling_phase_samples": result.optical_sampling.phase_samples,
        "optical_sampling_phase_ui": (
            result.optical_sampling.phase_samples / result.samples_per_ui
        ),
        "optical_integer_lag_ui": result.optical_sampling.integer_lag_ui,
        "optical_p0_mw": result.optical_levels.p0_w * 1.0e3,
        "optical_p1_mw": result.optical_levels.p1_w * 1.0e3,
        "optical_oma_mw": result.optical_levels.oma_w * 1.0e3,
        "optical_oma_dbm": result.optical_levels.oma_dbm,
        "optical_er_db": result.optical_levels.er_db,
        "random_noise": "disabled",
        "tdec": "not_implemented",
        "ber": "not_implemented",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
