"""Run synthetic delay, capture, outlier and sensor robustness sweeps."""

from __future__ import annotations

import csv
from dataclasses import replace
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from mrm_link.config import load_config, value
from mrm_link.dual_actuator_feedback import (
    FeedbackDisturbance,
    build_reference_disturbance,
    simulate_dual_actuator_feedback,
)
from run_bidirectional_els_rx_feedback import feedback_config


def final_metrics(result, window: int) -> dict[str, float]:
    residual = result.residual_detuning_pm[-window:]
    rx = result.rx_actuator_pm[-window:]
    return {
        "final_residual_rms_pm": float(np.sqrt(np.mean(residual**2))),
        "final_peak_abs_residual_pm": float(np.max(np.abs(residual))),
        "final_common_rx_actuator_pm": float(np.mean(rx)),
        "final_els_actuator_pm": float(np.mean(result.els_actuator_pm[-window:])),
        "maximum_rx_actuator_abs_pm": float(np.max(np.abs(result.rx_actuator_pm))),
        "maximum_els_actuator_abs_pm": float(
            np.max(np.abs(result.els_actuator_pm))
        ),
    }


def step_disturbance(config, *, laser_step_pm=0.0, lane_1_step_pm=0.0):
    samples = int(round(config.duration_s / config.time_step_s)) + 1
    laser = np.zeros(samples)
    rings = np.zeros((samples, config.lane_count))
    event = int(round(0.5e-3 / config.time_step_s))
    laser[event:] = laser_step_pm
    rings[event:, 0] = lane_1_step_pm
    return FeedbackDisturbance(laser_wavelength_pm=laser, rx_resonance_pm=rings)


def main() -> None:
    feedback = load_config(
        PROJECT_ROOT / "configs" / "bidirectional_els_rx_feedback_synthetic.toml"
    )
    sweep = load_config(
        PROJECT_ROOT / "configs" / "bidirectional_els_rx_robustness_synthetic.toml"
    )
    base = feedback_config(feedback)
    window = max(1, int(round(200.0e-6 / base.time_step_s)))
    _, reference = build_reference_disturbance(
        base,
        common_laser_step_pm=float(value(feedback, "disturbance", "common_laser_step")),
        laser_step_time_s=float(value(feedback, "disturbance", "laser_step_time")),
        local_rx_step_pm=np.asarray(
            value(feedback, "disturbance", "local_rx_steps"), dtype=float
        ),
        rx_step_time_s=float(value(feedback, "disturbance", "rx_step_time")),
        final_laser_ramp_pm=float(value(feedback, "disturbance", "final_laser_ramp")),
        ramp_start_time_s=float(value(feedback, "disturbance", "ramp_start_time")),
    )
    delays = np.asarray(value(sweep, "delay_gain_sweep", "backward_delay_us"))
    gains = np.asarray(value(sweep, "delay_gain_sweep", "els_recenter_ki_per_s"))
    pass_rms = float(value(sweep, "delay_gain_sweep", "pass_residual_rms_pm"))
    pass_common = float(value(sweep, "delay_gain_sweep", "pass_common_rx_pm"))
    residual_map = np.empty((len(gains), len(delays)))
    common_map = np.empty_like(residual_map)
    pass_map = np.zeros_like(residual_map, dtype=bool)
    rows: list[dict[str, object]] = []

    for gain_index, gain in enumerate(gains):
        for delay_index, delay in enumerate(delays):
            config = replace(
                base,
                els_recenter_ki_per_s=float(gain),
                backward_delay_s=float(delay) * 1.0e-6,
            )
            result = simulate_dual_actuator_feedback(
                config, reference, strategy="joint_els_rx"
            )
            metrics = final_metrics(result, window)
            residual_map[gain_index, delay_index] = metrics["final_residual_rms_pm"]
            common_map[gain_index, delay_index] = abs(
                metrics["final_common_rx_actuator_pm"]
            )
            passed = (
                residual_map[gain_index, delay_index] <= pass_rms
                and common_map[gain_index, delay_index] <= pass_common
            )
            pass_map[gain_index, delay_index] = passed
            rows.append(
                {
                    "experiment": "delay_gain",
                    "delay_us": delay,
                    "els_ki_per_s": gain,
                    "passed": passed,
                    **metrics,
                }
            )

    capture_steps = np.asarray(value(sweep, "capture_sweep", "common_laser_step_pm"))
    capture: dict[str, list[dict[str, float]]] = {"rx_only": [], "joint_els_rx": []}
    for strategy in capture:
        for step in capture_steps:
            result = simulate_dual_actuator_feedback(
                base,
                step_disturbance(base, laser_step_pm=float(step)),
                strategy=strategy,
            )
            metrics = final_metrics(result, window)
            capture[strategy].append(metrics)
            rows.append(
                {
                    "experiment": "capture",
                    "strategy": strategy,
                    "common_laser_step_pm": step,
                    **metrics,
                }
            )

    outlier_steps = np.asarray(
        value(sweep, "outlier_sweep", "single_lane_rx_step_pm")
    )
    estimators = tuple(value(sweep, "outlier_sweep", "estimators"))
    outlier: dict[str, list[dict[str, float]]] = {name: [] for name in estimators}
    for estimator in estimators:
        config = replace(base, common_mode_estimator=str(estimator))
        for step in outlier_steps:
            result = simulate_dual_actuator_feedback(
                config,
                step_disturbance(config, lane_1_step_pm=float(step)),
                strategy="joint_els_rx",
            )
            metrics = final_metrics(result, window)
            outlier[str(estimator)].append(metrics)
            rows.append(
                {
                    "experiment": "single_lane_outlier",
                    "estimator": estimator,
                    "single_lane_step_pm": step,
                    **metrics,
                }
            )

    noise_steps = np.asarray(value(sweep, "sensor_sweep", "noise_rms_pm"))
    quant_steps = np.asarray(value(sweep, "sensor_sweep", "quantization_pm"))
    sensor_map = np.empty((len(noise_steps), len(quant_steps)))
    sensor_pass = np.zeros_like(sensor_map, dtype=bool)
    for noise_index, noise in enumerate(noise_steps):
        for quant_index, quant in enumerate(quant_steps):
            config = replace(
                base,
                sensor_noise_rms_pm=float(noise),
                sensor_quantization_pm=float(quant),
            )
            result = simulate_dual_actuator_feedback(
                config, reference, strategy="joint_els_rx"
            )
            metrics = final_metrics(result, window)
            sensor_map[noise_index, quant_index] = metrics["final_residual_rms_pm"]
            passed = (
                metrics["final_residual_rms_pm"] <= pass_rms
                and abs(metrics["final_common_rx_actuator_pm"]) <= pass_common
            )
            sensor_pass[noise_index, quant_index] = passed
            rows.append(
                {
                    "experiment": "sensor",
                    "sensor_noise_rms_pm": noise,
                    "sensor_quantization_pm": quant,
                    "passed": passed,
                    **metrics,
                }
            )

    max_alignment = None
    max_recentered = None
    for index, step in enumerate(capture_steps):
        item = capture["joint_els_rx"][index]
        unsaturated = (
            item["maximum_rx_actuator_abs_pm"] < base.rx_actuator_limit_pm
            and item["maximum_els_actuator_abs_pm"] < base.els_actuator_limit_pm
        )
        if item["final_residual_rms_pm"] <= pass_rms and unsaturated:
            max_alignment = float(step)
            if abs(item["final_common_rx_actuator_pm"]) <= pass_common:
                max_recentered = float(step)

    summary = {
        "model": "synthetic_bidirectional_els_rx_robustness",
        "status": sweep["meta"]["status"],
        "delay_gain_pass": f"{int(np.count_nonzero(pass_map))}/{pass_map.size}",
        "maximum_alignment_capture_pm": max_alignment,
        "maximum_fully_recentered_pm": max_recentered,
        "one_lane_120pm_false_els_motion_pm": {
            "mean": abs(outlier["mean"][-1]["final_els_actuator_pm"]),
            "median": abs(outlier["median"][-1]["final_els_actuator_pm"]),
        },
        "sensor_pass": f"{int(np.count_nonzero(sensor_pass))}/{sensor_pass.size}",
        "claim_boundary": "Synthetic parameter sweep; no hardware limit is claimed.",
    }
    result_dir = PROJECT_ROOT / "results" / "bidirectional_els_rx_robustness"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    with (result_dir / "sweeps.csv").open("w", newline="", encoding="utf-8") as stream:
        fieldnames = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8), constrained_layout=True)
    image0 = axes[0, 0].pcolormesh(delays, gains, residual_map, shading="nearest")
    axes[0, 0].contour(delays, gains, pass_map.astype(float), levels=[0.5], colors="white")
    fig.colorbar(image0, ax=axes[0, 0], label="Residual RMS (pm)")
    image1 = axes[0, 1].pcolormesh(delays, gains, common_map, shading="nearest", cmap="magma")
    axes[0, 1].contour(delays, gains, pass_map.astype(float), levels=[0.5], colors="cyan")
    fig.colorbar(image1, ax=axes[0, 1], label="Common RX use (pm)")
    for strategy, style in (("rx_only", "--o"), ("joint_els_rx", "-o")):
        axes[1, 0].plot(
            capture_steps,
            [item["final_residual_rms_pm"] for item in capture[strategy]],
            style,
            label=strategy,
        )
    for estimator, style in (("mean", "--o"), ("median", "-o")):
        axes[1, 1].plot(
            outlier_steps,
            [abs(item["final_els_actuator_pm"]) for item in outlier[estimator]],
            style,
            label=estimator,
        )
    axes[0, 0].set(title="Delay/gain residual", xlabel="Delay (us)", ylabel="ELS Ki (1/s)")
    axes[0, 1].set(title="Delay/gain recentering", xlabel="Delay (us)", ylabel="ELS Ki (1/s)")
    axes[1, 0].set(title="Common-drift capture", xlabel="Step (pm)", ylabel="Residual RMS (pm)")
    axes[1, 1].set(title="Single-lane outlier", xlabel="Lane-1 step (pm)", ylabel="False ELS motion (pm)")
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
        if axis in axes[1, :]:
            axis.legend()
    fig.suptitle("Synthetic feedback robustness — white/cyan contour marks provisional pass")
    fig.savefig(result_dir / "robustness.png", dpi=180)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
