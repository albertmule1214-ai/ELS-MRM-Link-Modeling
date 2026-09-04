"""Behavioral multi-lane RX-ring and external-laser feedback model.

Each local loop aligns one RX drop ring to a shared laser wavelength.  A
low-rate backward channel reports a robust common correction to a slower
external-laser actuator.  The model is intentionally synthetic: it explores
control structure and failure boundaries rather than predicting hardware.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DualActuatorFeedbackConfig:
    lane_count: int
    time_step_s: float
    duration_s: float
    rx_actuator_time_constant_s: float
    els_actuator_time_constant_s: float
    rx_kp: float
    rx_ki_per_s: float
    els_recenter_ki_per_s: float
    rx_actuator_limit_pm: float
    els_actuator_limit_pm: float
    backward_update_period_s: float
    backward_delay_s: float
    sensor_quantization_pm: float
    sensor_noise_rms_pm: float
    random_seed: int
    common_mode_estimator: str = "median"

    def __post_init__(self) -> None:
        positive = (
            self.time_step_s,
            self.duration_s,
            self.rx_actuator_time_constant_s,
            self.els_actuator_time_constant_s,
            self.rx_actuator_limit_pm,
            self.els_actuator_limit_pm,
            self.backward_update_period_s,
        )
        if self.lane_count <= 0:
            raise ValueError("lane_count must be positive")
        if any(item <= 0.0 for item in positive):
            raise ValueError("Time constants, limits and time steps must be positive")
        if self.duration_s <= self.time_step_s:
            raise ValueError("duration must exceed one time step")
        if self.backward_delay_s < 0.0:
            raise ValueError("backward delay cannot be negative")
        if self.rx_kp < 0.0 or self.rx_ki_per_s < 0.0:
            raise ValueError("RX gains cannot be negative")
        if self.els_recenter_ki_per_s < 0.0:
            raise ValueError("ELS recenter gain cannot be negative")
        if self.sensor_quantization_pm < 0.0 or self.sensor_noise_rms_pm < 0.0:
            raise ValueError("Sensor quantization and noise cannot be negative")
        if self.common_mode_estimator not in {"mean", "median"}:
            raise ValueError("common_mode_estimator must be mean or median")


@dataclass(frozen=True)
class FeedbackDisturbance:
    laser_wavelength_pm: np.ndarray
    rx_resonance_pm: np.ndarray

    def __post_init__(self) -> None:
        laser = np.asarray(self.laser_wavelength_pm, dtype=float)
        ring = np.asarray(self.rx_resonance_pm, dtype=float)
        if laser.ndim != 1 or ring.ndim != 2:
            raise ValueError("Laser disturbance must be 1-D and RX disturbance 2-D")
        if ring.shape[0] != len(laser):
            raise ValueError("Laser and RX disturbances must share the time axis")
        if np.any(~np.isfinite(laser)) or np.any(~np.isfinite(ring)):
            raise ValueError("Disturbances must be finite")


@dataclass(frozen=True)
class FeedbackSimulationResult:
    strategy: str
    time_s: np.ndarray
    laser_disturbance_pm: np.ndarray
    rx_disturbance_pm: np.ndarray
    measured_detuning_pm: np.ndarray
    residual_detuning_pm: np.ndarray
    rx_command_pm: np.ndarray
    rx_actuator_pm: np.ndarray
    els_command_pm: np.ndarray
    els_actuator_pm: np.ndarray


def _quantize(values: np.ndarray, step_pm: float) -> np.ndarray:
    if step_pm == 0.0:
        return values
    return np.round(values / step_pm) * step_pm


def build_reference_disturbance(
    config: DualActuatorFeedbackConfig,
    *,
    common_laser_step_pm: float,
    laser_step_time_s: float,
    local_rx_step_pm: np.ndarray,
    rx_step_time_s: float,
    final_laser_ramp_pm: float,
    ramp_start_time_s: float,
) -> tuple[np.ndarray, FeedbackDisturbance]:
    """Build a deterministic scenario that separates common and local drift."""

    time_s = np.arange(
        0.0,
        config.duration_s + 0.5 * config.time_step_s,
        config.time_step_s,
    )
    local_step = np.asarray(local_rx_step_pm, dtype=float)
    if local_step.shape != (config.lane_count,):
        raise ValueError("local_rx_step_pm must contain one value per lane")
    laser = np.zeros_like(time_s)
    laser[time_s >= laser_step_time_s] += common_laser_step_pm
    ramp_duration = max(config.duration_s - ramp_start_time_s, config.time_step_s)
    ramp_fraction = np.clip((time_s - ramp_start_time_s) / ramp_duration, 0.0, 1.0)
    laser += final_laser_ramp_pm * ramp_fraction
    ring = np.zeros((len(time_s), config.lane_count), dtype=float)
    ring[time_s >= rx_step_time_s, :] = local_step
    return time_s, FeedbackDisturbance(
        laser_wavelength_pm=laser,
        rx_resonance_pm=ring,
    )


def simulate_dual_actuator_feedback(
    config: DualActuatorFeedbackConfig,
    disturbance: FeedbackDisturbance,
    *,
    strategy: str,
) -> FeedbackSimulationResult:
    """Simulate ``no_control``, ``rx_only`` or ``joint_els_rx``.

    The sign convention is ``detuning = laser wavelength - RX resonance``.
    Positive RX actuation shifts an RX resonance to a longer wavelength.  The
    shared ELS integral acts against persistent common RX correction so the
    slow and fast actuators do not fight each other.
    """

    allowed = {"no_control", "rx_only", "joint_els_rx"}
    if strategy not in allowed:
        raise ValueError(f"strategy must be one of {sorted(allowed)}")
    laser_disturbance = np.asarray(disturbance.laser_wavelength_pm, dtype=float)
    ring_disturbance = np.asarray(disturbance.rx_resonance_pm, dtype=float)
    number_of_samples = len(laser_disturbance)
    if ring_disturbance.shape != (number_of_samples, config.lane_count):
        raise ValueError("RX disturbance shape does not match config")

    time_s = np.arange(number_of_samples, dtype=float) * config.time_step_s
    residual = np.zeros_like(ring_disturbance)
    measured = np.zeros_like(ring_disturbance)
    rx_command = np.zeros_like(ring_disturbance)
    rx_actuator = np.zeros_like(ring_disturbance)
    els_command = np.zeros(number_of_samples, dtype=float)
    els_actuator = np.zeros(number_of_samples, dtype=float)
    rx_integrator = np.zeros(config.lane_count, dtype=float)
    els_integrator = 0.0
    rng = np.random.default_rng(config.random_seed)

    update_steps = max(
        1,
        int(round(config.backward_update_period_s / config.time_step_s)),
    )
    delay_steps = max(0, int(round(config.backward_delay_s / config.time_step_s)))
    common_history = np.zeros(number_of_samples, dtype=float)

    for index in range(number_of_samples):
        if index > 0:
            rx_command[index] = rx_command[index - 1]
            els_command[index] = els_command[index - 1]

        residual[index] = (
            laser_disturbance[index]
            + els_actuator[index]
            - ring_disturbance[index]
            - rx_actuator[index]
        )
        sensor_noise = rng.normal(
            0.0,
            config.sensor_noise_rms_pm,
            config.lane_count,
        )
        measured[index] = _quantize(
            residual[index] + sensor_noise,
            config.sensor_quantization_pm,
        )

        if strategy != "no_control":
            rx_integrator += config.rx_ki_per_s * measured[index] * config.time_step_s
            unclipped_rx = config.rx_kp * measured[index] + rx_integrator
            clipped_rx = np.clip(
                unclipped_rx,
                -config.rx_actuator_limit_pm,
                config.rx_actuator_limit_pm,
            )
            rx_integrator += clipped_rx - unclipped_rx
            rx_command[index] = clipped_rx

        if config.common_mode_estimator == "median":
            common_history[index] = float(np.median(rx_actuator[index]))
        else:
            common_history[index] = float(np.mean(rx_actuator[index]))

        if strategy == "joint_els_rx" and index % update_steps == 0:
            source_index = max(0, index - delay_steps)
            els_integrator -= (
                config.els_recenter_ki_per_s
                * common_history[source_index]
                * config.backward_update_period_s
            )
            els_integrator = float(
                np.clip(
                    els_integrator,
                    -config.els_actuator_limit_pm,
                    config.els_actuator_limit_pm,
                )
            )
            els_command[index] = els_integrator

        if index + 1 < number_of_samples:
            rx_actuator[index + 1] = rx_actuator[index] + (
                config.time_step_s / config.rx_actuator_time_constant_s
            ) * (rx_command[index] - rx_actuator[index])
            els_actuator[index + 1] = els_actuator[index] + (
                config.time_step_s / config.els_actuator_time_constant_s
            ) * (els_command[index] - els_actuator[index])

    return FeedbackSimulationResult(
        strategy=strategy,
        time_s=time_s,
        laser_disturbance_pm=laser_disturbance,
        rx_disturbance_pm=ring_disturbance,
        measured_detuning_pm=measured,
        residual_detuning_pm=residual,
        rx_command_pm=rx_command,
        rx_actuator_pm=rx_actuator,
        els_command_pm=els_command,
        els_actuator_pm=els_actuator,
    )
