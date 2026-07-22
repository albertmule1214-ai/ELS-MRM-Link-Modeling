"""Quasi-static MRM temperature-detuning sweeps."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Mapping

import numpy as np

from .baseline import build_static_mrm
from .config import value
from .dsp import bessel_thomson_lowpass
from .shot_noise import fixed_decision_indices
from .waveform import run_noiseless_waveform


@dataclass(frozen=True)
class ThermalSweepResult:
    temperature_offset_c: np.ndarray
    resonance_shift_pm: np.ndarray
    detuning_0_pm: np.ndarray
    detuning_1_pm: np.ndarray
    p0_mw: np.ndarray
    p1_mw: np.ndarray
    signed_oma_mw: np.ndarray
    signed_er_db: np.ndarray
    signed_eye_height_v: np.ndarray
    nominal_index: int
    thermal_tuning_pm_per_c: float
    fwhm_pm: float


def _transmission_array(model: Any, voltage_v: np.ndarray) -> np.ndarray:
    resonance_m = model.resonance_wavelength_m(voltage_v)
    detuning_m = model.laser_wavelength_m - resonance_m
    normalized = 2.0 * detuning_m / model.fwhm_m
    depth_fraction = 1.0 - (
        model.on_resonance_transmission / model.off_resonance_transmission
    )
    transmission = model.off_resonance_transmission * (
        1.0 - depth_fraction / (1.0 + normalized**2)
    )
    return np.clip(transmission, 0.0, model.off_resonance_transmission)


def sweep_quasi_static_temperature(
    link_config: Mapping[str, Any],
    temperature_offset_c: np.ndarray,
    number_of_bits: int,
    samples_per_ui: int,
) -> ThermalSweepResult:
    """Hold each temperature fixed while evaluating the deterministic link."""

    temperatures = np.asarray(temperature_offset_c, dtype=float)
    if temperatures.ndim != 1 or len(temperatures) == 0:
        raise ValueError("Temperature sweep must be a non-empty 1D array")
    config = deepcopy(link_config)
    config["signal"]["number_of_bits"]["value"] = int(number_of_bits)
    config["signal"]["samples_per_ui"]["value"] = int(samples_per_ui)
    nominal = run_noiseless_waveform(config)

    symbol_rate_hz = float(value(config, "signal", "symbol_rate"))
    sample_rate_hz = symbol_rate_hz * samples_per_ui
    receiver_bandwidth_hz = float(
        value(config, "receiver", "reference_filter_bandwidth")
    )
    input_power_w = float(value(config, "els", "apc_setpoint"))
    channel_scale = 10.0 ** (
        -float(value(config, "optical_channel", "loss")) / 10.0
    )
    responsivity = float(value(config, "receiver", "pd_responsivity"))
    transimpedance = float(value(config, "receiver", "tia_transimpedance"))
    thermal_tuning_m_per_c = float(
        value(config, "mrm", "temperature_tuning_efficiency")
    )
    base_model = build_static_mrm(config)

    optical_indices, optical_labels = fixed_decision_indices(
        len(nominal.optical_power_w),
        nominal.bits,
        samples_per_ui,
        nominal.optical_sampling,
    )
    receiver_indices, receiver_labels = fixed_decision_indices(
        len(nominal.rx_voltage_v),
        nominal.bits,
        samples_per_ui,
        nominal.sampling,
    )
    optical_zero = optical_labels == 0
    optical_one = optical_labels == 1
    receiver_zero = receiver_labels == 0
    receiver_one = receiver_labels == 1

    p0_mw = np.empty(len(temperatures))
    p1_mw = np.empty(len(temperatures))
    signed_eye_height_v = np.empty(len(temperatures))
    detuning_0_pm = np.empty(len(temperatures))
    detuning_1_pm = np.empty(len(temperatures))
    voltage_0 = float(value(config, "driver", "voltage_low"))
    voltage_1 = float(value(config, "driver", "voltage_high"))

    for index, temperature_c in enumerate(temperatures):
        # Positive temperature red-shifts the resonance. Since detuning is
        # laser wavelength minus resonance wavelength, its sign decreases.
        reference_detuning_m = (
            base_model.reference_detuning_m
            - thermal_tuning_m_per_c * temperature_c
        )
        model = replace(base_model, reference_detuning_m=reference_detuning_m)
        transmission = _transmission_array(model, nominal.driver_v)
        optical_power_w = input_power_w * channel_scale * transmission
        optical_samples_w = optical_power_w[optical_indices]
        p0_mw[index] = float(np.mean(optical_samples_w[optical_zero]) * 1.0e3)
        p1_mw[index] = float(np.mean(optical_samples_w[optical_one]) * 1.0e3)

        tia_voltage_v = optical_power_w * responsivity * transimpedance
        rx_voltage_v = bessel_thomson_lowpass(
            tia_voltage_v,
            sample_rate_hz,
            receiver_bandwidth_hz,
            order=4,
        )
        rx_samples_v = rx_voltage_v[receiver_indices]
        signed_eye_height_v[index] = float(
            np.mean(rx_samples_v[receiver_one])
            - np.mean(rx_samples_v[receiver_zero])
        )
        detuning_0_pm[index] = model.detuning_m(voltage_0) * 1.0e12
        detuning_1_pm[index] = model.detuning_m(voltage_1) * 1.0e12

    signed_oma_mw = p1_mw - p0_mw
    signed_er_db = 10.0 * np.log10(p1_mw / p0_mw)
    nominal_index = int(np.argmin(np.abs(temperatures)))
    return ThermalSweepResult(
        temperature_offset_c=temperatures,
        resonance_shift_pm=thermal_tuning_m_per_c * temperatures * 1.0e12,
        detuning_0_pm=detuning_0_pm,
        detuning_1_pm=detuning_1_pm,
        p0_mw=p0_mw,
        p1_mw=p1_mw,
        signed_oma_mw=signed_oma_mw,
        signed_er_db=signed_er_db,
        signed_eye_height_v=signed_eye_height_v,
        nominal_index=nominal_index,
        thermal_tuning_pm_per_c=thermal_tuning_m_per_c * 1.0e12,
        fwhm_pm=base_model.fwhm_m * 1.0e12,
    )

