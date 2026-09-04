"""Run the synthetic hierarchical RX-ring to ELS feedback example."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config, value
from mrm_link.dual_actuator_feedback import (
    DualActuatorFeedbackConfig,
    build_reference_disturbance,
    simulate_dual_actuator_feedback,
)


STRATEGIES = ("no_control", "rx_only", "joint_els_rx")
LABELS = {
    "no_control": "No control",
    "rx_only": "RX tracking only",
    "joint_els_rx": "Joint ELS + RX",
}


def feedback_config(config: dict) -> DualActuatorFeedbackConfig:
    return DualActuatorFeedbackConfig(
        lane_count=int(value(config, "simulation", "lane_count")),
        time_step_s=float(value(config, "simulation", "time_step")),
        duration_s=float(value(config, "simulation", "duration")),
        rx_actuator_time_constant_s=float(
            value(config, "rx_control", "actuator_time_constant")
        ),
        els_actuator_time_constant_s=float(
            value(config, "els_control", "actuator_time_constant")
        ),
        rx_kp=float(value(config, "rx_control", "kp")),
        rx_ki_per_s=float(value(config, "rx_control", "ki")),
        els_recenter_ki_per_s=float(value(config, "els_control", "recenter_ki")),
        rx_actuator_limit_pm=float(value(config, "rx_control", "actuator_limit")),
        els_actuator_limit_pm=float(value(config, "els_control", "actuator_limit")),
        backward_update_period_s=float(
            value(config, "backward_channel", "update_period")
        ),
        backward_delay_s=float(value(config, "backward_channel", "delay")),
        sensor_quantization_pm=float(
            value(config, "backward_channel", "sensor_quantization")
        ),
        sensor_noise_rms_pm=float(
            value(config, "backward_channel", "sensor_noise_rms")
        ),
        random_seed=int(value(config, "simulation", "random_seed")),
        common_mode_estimator=str(
            value(config, "backward_channel", "common_mode_estimator")
        ),
    )


def main() -> None:
    source = load_config(
        PROJECT_ROOT / "configs" / "bidirectional_els_rx_feedback_synthetic.toml"
    )
    config = feedback_config(source)
    _, disturbance = build_reference_disturbance(
        config,
        common_laser_step_pm=float(value(source, "disturbance", "common_laser_step")),
        laser_step_time_s=float(value(source, "disturbance", "laser_step_time")),
        local_rx_step_pm=np.asarray(
            value(source, "disturbance", "local_rx_steps"), dtype=float
        ),
        rx_step_time_s=float(value(source, "disturbance", "rx_step_time")),
        final_laser_ramp_pm=float(value(source, "disturbance", "final_laser_ramp")),
        ramp_start_time_s=float(value(source, "disturbance", "ramp_start_time")),
    )
    results = {
        strategy: simulate_dual_actuator_feedback(
            config,
            disturbance,
            strategy=strategy,
        )
        for strategy in STRATEGIES
    }

    result_dir = PROJECT_ROOT / "results" / "bidirectional_els_rx_feedback"
    result_dir.mkdir(parents=True, exist_ok=True)
    final_window = max(1, int(round(200.0e-6 / config.time_step_s)))
    summaries: dict[str, dict[str, float]] = {}
    for strategy, result in results.items():
        residual = result.residual_detuning_pm[-final_window:]
        rx_correction = result.rx_actuator_pm[-final_window:]
        summaries[strategy] = {
            "final_residual_rms_pm": float(np.sqrt(np.mean(residual**2))),
            "final_residual_peak_abs_pm": float(np.max(np.abs(residual))),
            "final_common_rx_actuator_pm": float(np.mean(rx_correction)),
            "final_els_actuator_pm": float(
                np.mean(result.els_actuator_pm[-final_window:])
            ),
            "maximum_rx_actuator_abs_pm": float(
                np.max(np.abs(result.rx_actuator_pm))
            ),
        }

    summary = {
        "model": "synthetic_four_lane_hierarchical_els_rx_feedback",
        "status": source["meta"]["status"],
        "strategies": summaries,
        "claim_boundary": (
            "Behavioral comparison only. Replace all actuator, sensor and "
            "disturbance parameters before hardware interpretation."
        ),
    }
    (result_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    csv_path = result_dir / "timeseries.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = [
            "strategy",
            "time_us",
            "lane",
            "laser_disturbance_pm",
            "rx_disturbance_pm",
            "residual_detuning_pm",
            "rx_actuator_pm",
            "els_actuator_pm",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        stride = max(1, int(round(10.0e-6 / config.time_step_s)))
        for strategy, result in results.items():
            for index in range(0, len(result.time_s), stride):
                for lane in range(config.lane_count):
                    writer.writerow(
                        {
                            "strategy": strategy,
                            "time_us": result.time_s[index] * 1.0e6,
                            "lane": lane + 1,
                            "laser_disturbance_pm": result.laser_disturbance_pm[index],
                            "rx_disturbance_pm": result.rx_disturbance_pm[index, lane],
                            "residual_detuning_pm": result.residual_detuning_pm[
                                index, lane
                            ],
                            "rx_actuator_pm": result.rx_actuator_pm[index, lane],
                            "els_actuator_pm": result.els_actuator_pm[index],
                        }
                    )

    colors = {
        "no_control": "tab:red",
        "rx_only": "tab:orange",
        "joint_els_rx": "tab:blue",
    }
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), constrained_layout=True)
    for strategy, result in results.items():
        time_ms = result.time_s * 1.0e3
        axes[0, 0].plot(
            time_ms,
            result.residual_detuning_pm[:, 0],
            color=colors[strategy],
            label=LABELS[strategy],
        )
        axes[0, 1].plot(
            time_ms,
            np.sqrt(np.mean(result.residual_detuning_pm**2, axis=1)),
            color=colors[strategy],
            label=LABELS[strategy],
        )
    joint = results["joint_els_rx"]
    axes[1, 0].plot(
        joint.time_s * 1.0e3,
        joint.els_actuator_pm,
        color="tab:purple",
        label="ELS correction",
    )
    for lane in range(config.lane_count):
        axes[1, 0].plot(
            joint.time_s * 1.0e3,
            joint.rx_actuator_pm[:, lane],
            linewidth=1.0,
            label=f"RX{lane + 1} correction",
        )
    names = [LABELS[item] for item in STRATEGIES]
    residuals = [summaries[item]["final_residual_rms_pm"] for item in STRATEGIES]
    rx_range = [abs(summaries[item]["final_common_rx_actuator_pm"]) for item in STRATEGIES]
    x = np.arange(len(names))
    axes[1, 1].bar(x - 0.18, residuals, width=0.36, label="Residual RMS (pm)")
    axes[1, 1].bar(x + 0.18, rx_range, width=0.36, label="Common RX use (pm)")
    axes[1, 1].set_xticks(x, names)
    axes[0, 0].set(title="Lane 1 detuning", xlabel="Time (ms)", ylabel="pm")
    axes[0, 1].set(title="Four-lane detuning RMS", xlabel="Time (ms)", ylabel="pm")
    axes[1, 0].set(title="Joint actuator sharing", xlabel="Time (ms)", ylabel="pm")
    axes[1, 1].set(title="Final comparison", ylabel="pm")
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    fig.suptitle(
        "Synthetic bidirectional ELS/RX feedback — not a hardware prediction"
    )
    fig.savefig(result_dir / "feedback_comparison.png", dpi=180)
    plt.close(fig)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
