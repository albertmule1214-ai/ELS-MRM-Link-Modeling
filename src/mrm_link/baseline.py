"""Noiseless L0 static MRM baseline and parameter scan."""

from __future__ import annotations

from csv import DictWriter
from dataclasses import dataclass
from math import inf, log10
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import value
from .metrics import OpticalLevels
from .mrm import StaticThroughMicroring


@dataclass(frozen=True)
class StaticBaselineResult:
    ui_s: float
    fwhm_m: float
    voltage_0_v: float
    voltage_1_v: float
    detuning_0_m: float
    detuning_1_m: float
    transmission_0: float
    transmission_1: float
    levels: OpticalLevels


def build_static_mrm(config: Mapping[str, Any]) -> StaticThroughMicroring:
    voltage_0_v = float(value(config, "driver", "voltage_low"))
    return StaticThroughMicroring(
        laser_wavelength_m=float(value(config, "els", "wavelength")),
        loaded_q=float(value(config, "mrm", "loaded_q")),
        reference_detuning_m=float(value(config, "mrm", "detuning")),
        resonance_depth_db=float(value(config, "mrm", "resonance_depth")),
        off_resonance_insertion_loss_db=float(
            value(config, "mrm", "off_resonance_insertion_loss")
        ),
        voltage_tuning_efficiency_m_per_v=float(
            value(config, "mrm", "voltage_tuning_efficiency")
        ),
        # L0 convention: detuning is specified at the NRZ-low voltage.
        reference_voltage_v=float(value(config, "mrm", "reference_voltage")),
    )


def run_static_baseline(config: Mapping[str, Any]) -> StaticBaselineResult:
    model = build_static_mrm(config)
    voltage_0_v = float(value(config, "driver", "voltage_low"))
    voltage_1_v = float(value(config, "driver", "voltage_high"))
    input_power_w = float(value(config, "els", "apc_setpoint"))
    channel_loss_db = float(value(config, "optical_channel", "loss"))
    channel_transmission = 10.0 ** (-channel_loss_db / 10.0)

    transmission_0 = model.transmission(voltage_0_v)
    transmission_1 = model.transmission(voltage_1_v)
    p0_w = input_power_w * transmission_0 * channel_transmission
    p1_w = input_power_w * transmission_1 * channel_transmission
    levels = OpticalLevels(p0_w=p0_w, p1_w=p1_w)

    return StaticBaselineResult(
        ui_s=1.0 / float(value(config, "signal", "symbol_rate")),
        fwhm_m=model.fwhm_m,
        voltage_0_v=voltage_0_v,
        voltage_1_v=voltage_1_v,
        detuning_0_m=model.detuning_m(voltage_0_v),
        detuning_1_m=model.detuning_m(voltage_1_v),
        transmission_0=transmission_0,
        transmission_1=transmission_1,
        levels=levels,
    )


def scan_rows(
    config: Mapping[str, Any], normalized_detunings: Iterable[float]
) -> Iterable[dict[str, float]]:
    base_model = build_static_mrm(config)
    voltage_0_v = float(value(config, "driver", "voltage_low"))
    voltage_1_v = float(value(config, "driver", "voltage_high"))
    input_power_w = float(value(config, "els", "apc_setpoint"))
    q_values = [
        float(number) for number in value(config, "mrm", "loaded_q_sweep")
    ]
    # The caller may provide a one-shot generator. Materialize it so every Q
    # value is evaluated over the same detuning grid.
    detuning_values = tuple(normalized_detunings)

    for loaded_q in q_values:
        fwhm_m = base_model.laser_wavelength_m / loaded_q
        for normalized_detuning in detuning_values:
            reference_detuning_m = normalized_detuning * fwhm_m
            model = base_model.with_q_and_detuning(
                loaded_q=loaded_q,
                reference_detuning_m=reference_detuning_m,
            )
            t0 = model.transmission(voltage_0_v)
            t1 = model.transmission(voltage_1_v)
            p0_w = input_power_w * t0
            p1_w = input_power_w * t1
            if p1_w >= p0_w:
                levels = OpticalLevels(p0_w=p0_w, p1_w=p1_w)
                oma_w = levels.oma_w
                er_db = levels.er_db
            else:
                # Preserve polarity information in the raw scan.
                oma_w = p1_w - p0_w
                er_db = -inf if p1_w <= 0.0 else 10.0 * log10(
                    p1_w / p0_w
                )
            yield {
                "q": loaded_q,
                "normalized_reference_detuning": normalized_detuning,
                "reference_detuning_pm": reference_detuning_m * 1.0e12,
                "fwhm_pm": fwhm_m * 1.0e12,
                "t0": t0,
                "t1": t1,
                "p0_mw": p0_w * 1.0e3,
                "p1_mw": p1_w * 1.0e3,
                "oma_mw_signed": oma_w * 1.0e3,
                "er_db_signed": er_db,
            }


def write_scan_csv(config: Mapping[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_detunings = (index / 50.0 for index in range(-100, 101))
    rows = scan_rows(config, normalized_detunings)
    first = next(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = DictWriter(stream, fieldnames=list(first))
        writer.writeheader()
        writer.writerow(first)
        writer.writerows(rows)
    return path



