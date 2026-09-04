from dataclasses import replace

import numpy as np

from mrm_link.dual_actuator_feedback import (
    DualActuatorFeedbackConfig,
    FeedbackDisturbance,
    simulate_dual_actuator_feedback,
)


def config() -> DualActuatorFeedbackConfig:
    return DualActuatorFeedbackConfig(
        lane_count=4,
        time_step_s=1.0e-6,
        duration_s=4.0e-3,
        rx_actuator_time_constant_s=30.0e-6,
        els_actuator_time_constant_s=250.0e-6,
        rx_kp=0.8,
        rx_ki_per_s=4.0e3,
        els_recenter_ki_per_s=1.2e3,
        rx_actuator_limit_pm=120.0,
        els_actuator_limit_pm=150.0,
        backward_update_period_s=10.0e-6,
        backward_delay_s=20.0e-6,
        sensor_quantization_pm=0.0,
        sensor_noise_rms_pm=0.0,
        random_seed=1,
    )


def disturbance(base: DualActuatorFeedbackConfig) -> FeedbackDisturbance:
    samples = int(round(base.duration_s / base.time_step_s)) + 1
    laser = np.zeros(samples)
    laser[samples // 4 :] = 50.0
    rings = np.zeros((samples, base.lane_count))
    return FeedbackDisturbance(laser_wavelength_pm=laser, rx_resonance_pm=rings)


def test_rx_only_reduces_residual_but_uses_local_range() -> None:
    base = config()
    result = simulate_dual_actuator_feedback(
        base, disturbance(base), strategy="rx_only"
    )
    assert float(np.sqrt(np.mean(result.residual_detuning_pm[-100:] ** 2))) < 1.0
    assert float(np.mean(result.rx_actuator_pm[-100:])) > 45.0


def test_joint_control_recenters_common_rx_actuator() -> None:
    base = config()
    source = disturbance(base)
    rx_only = simulate_dual_actuator_feedback(base, source, strategy="rx_only")
    joint = simulate_dual_actuator_feedback(base, source, strategy="joint_els_rx")
    assert abs(float(np.mean(joint.rx_actuator_pm[-100:]))) < 0.5 * abs(
        float(np.mean(rx_only.rx_actuator_pm[-100:]))
    )
    assert float(np.sqrt(np.mean(joint.residual_detuning_pm[-100:] ** 2))) < 2.0


def test_median_rejects_one_local_lane_outlier() -> None:
    base = config()
    samples = int(round(base.duration_s / base.time_step_s)) + 1
    laser = np.zeros(samples)
    rings = np.zeros((samples, base.lane_count))
    rings[samples // 4 :, 0] = 80.0
    source = FeedbackDisturbance(laser_wavelength_pm=laser, rx_resonance_pm=rings)
    mean_result = simulate_dual_actuator_feedback(
        replace(base, common_mode_estimator="mean"),
        source,
        strategy="joint_els_rx",
    )
    median_result = simulate_dual_actuator_feedback(
        replace(base, common_mode_estimator="median"),
        source,
        strategy="joint_els_rx",
    )
    assert abs(float(np.mean(median_result.els_actuator_pm[-100:]))) < 0.25 * abs(
        float(np.mean(mean_result.els_actuator_pm[-100:]))
    )
