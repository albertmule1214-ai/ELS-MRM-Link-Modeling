"""Synthetic receiver-sensitivity sweeps with heteroscedastic Gaussian noise."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize, special

from .metrics import watts_to_dbm


@dataclass(frozen=True)
class SensitivitySweepResult:
    additional_loss_db: np.ndarray
    received_average_power_dbm: np.ndarray
    ber: np.ndarray
    decision_threshold_v: np.ndarray
    rms_0_v: np.ndarray
    rms_1_v: np.ndarray
    target_ber: float
    sensitivity_dbm: float | None


def heteroscedastic_gaussian_ber(
    noiseless_samples_v: np.ndarray,
    labels: np.ndarray,
    sigma_v: np.ndarray,
    threshold_v: float,
) -> float:
    """Average Gaussian decision tails with one sigma for every sample."""

    samples = np.asarray(noiseless_samples_v, dtype=float)
    labels = np.asarray(labels, dtype=np.uint8)
    sigma = np.asarray(sigma_v, dtype=float)
    if len(samples) != len(labels) or len(samples) != len(sigma):
        raise ValueError("Samples, labels and sigma arrays must have equal length")
    if np.any(sigma <= 0.0):
        raise ValueError("All Gaussian sigmas must be positive")
    zeros = labels == 0
    ones = labels == 1
    zero_error = special.ndtr((samples[zeros] - threshold_v) / sigma[zeros])
    one_error = special.ndtr((threshold_v - samples[ones]) / sigma[ones])
    return float((np.sum(zero_error) + np.sum(one_error)) / len(samples))


def _optimum_threshold(
    samples_v: np.ndarray,
    labels: np.ndarray,
    sigma_v: np.ndarray,
) -> tuple[float, float]:
    zeros = labels == 0
    ones = labels == 1
    lower = float(np.mean(samples_v[zeros]))
    upper = float(np.mean(samples_v[ones]))
    if upper <= lower:
        raise ValueError("Mean one level must exceed mean zero level")
    result = optimize.minimize_scalar(
        lambda threshold: heteroscedastic_gaussian_ber(
            samples_v, labels, sigma_v, float(threshold)
        ),
        bounds=(lower, upper),
        method="bounded",
        options={"xatol": max((upper - lower) * 1.0e-8, 1.0e-15)},
    )
    return float(result.x), float(result.fun)


def sweep_receiver_sensitivity(
    baseline_samples_v: np.ndarray,
    labels: np.ndarray,
    baseline_shot_variance_v2: np.ndarray,
    tia_variance_v2: float,
    baseline_average_optical_power_w: float,
    additional_loss_db: np.ndarray,
    target_ber: float,
) -> SensitivitySweepResult:
    """Scale signal and shot variance consistently while TIA noise stays fixed."""

    baseline_samples_v = np.asarray(baseline_samples_v, dtype=float)
    labels = np.asarray(labels, dtype=np.uint8)
    baseline_shot_variance_v2 = np.asarray(
        baseline_shot_variance_v2, dtype=float
    )
    loss_db = np.asarray(additional_loss_db, dtype=float)
    if tia_variance_v2 <= 0.0:
        raise ValueError("A positive fixed TIA variance is required for sensitivity")
    if baseline_average_optical_power_w <= 0.0:
        raise ValueError("Baseline average optical power must be positive")
    if not 0.0 < target_ber < 0.5:
        raise ValueError("Target BER must lie between zero and 0.5")

    ber = np.empty_like(loss_db)
    threshold_v = np.empty_like(loss_db)
    rms_0_v = np.empty_like(loss_db)
    rms_1_v = np.empty_like(loss_db)
    zeros = labels == 0
    ones = labels == 1

    for index, loss in enumerate(loss_db):
        scale = 10.0 ** (-loss / 10.0)
        samples = baseline_samples_v * scale
        variance = baseline_shot_variance_v2 * scale + tia_variance_v2
        sigma = np.sqrt(variance)
        threshold_v[index], ber[index] = _optimum_threshold(samples, labels, sigma)
        rms_0_v[index] = float(np.sqrt(np.mean(variance[zeros])))
        rms_1_v[index] = float(np.sqrt(np.mean(variance[ones])))

    received_power_dbm = np.array(
        [watts_to_dbm(baseline_average_optical_power_w * 10.0 ** (-x / 10.0)) for x in loss_db]
    )
    crossing = np.flatnonzero(ber >= target_ber)
    sensitivity_dbm: float | None = None
    if len(crossing) > 0:
        current = int(crossing[0])
        if current == 0:
            sensitivity_dbm = float(received_power_dbm[0])
        else:
            previous = current - 1
            log_target = np.log10(target_ber)
            log_ber = np.log10(np.maximum(ber[[previous, current]], 1.0e-300))
            sensitivity_dbm = float(
                np.interp(
                    log_target,
                    log_ber,
                    received_power_dbm[[previous, current]],
                )
            )

    return SensitivitySweepResult(
        additional_loss_db=loss_db,
        received_average_power_dbm=received_power_dbm,
        ber=ber,
        decision_threshold_v=threshold_v,
        rms_0_v=rms_0_v,
        rms_1_v=rms_1_v,
        target_ber=float(target_ber),
        sensitivity_dbm=sensitivity_dbm,
    )

