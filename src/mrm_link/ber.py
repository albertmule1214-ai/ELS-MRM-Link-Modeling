"""BER calculations that avoid brute-force simulation of rare tails."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import special


@dataclass(frozen=True)
class GaussianBerValidationResult:
    threshold_v: float
    sigma_v: float
    theoretical_ber: float
    counted_ber: float
    counted_errors: int
    counted_bits: int


def gaussian_ber_for_noiseless_samples(
    samples_v: np.ndarray,
    labels: np.ndarray,
    threshold_v: float,
    sigma_v: float,
) -> float:
    """Average exact Gaussian tail probabilities over deterministic ISI samples."""

    if sigma_v <= 0.0:
        raise ValueError("Noise sigma must be positive")
    samples_v = np.asarray(samples_v, dtype=float)
    labels = np.asarray(labels)
    zero_error = special.ndtr((samples_v[labels == 0] - threshold_v) / sigma_v)
    one_error = special.ndtr((threshold_v - samples_v[labels == 1]) / sigma_v)
    return float((np.sum(zero_error) + np.sum(one_error)) / len(samples_v))


def validate_gaussian_ber_by_counting(
    samples_v: np.ndarray,
    labels: np.ndarray,
    sigma_v: float,
    repeats: int,
    seed: int,
    threshold_v: float | None = None,
) -> GaussianBerValidationResult:
    """Count a deliberately measurable BER and compare it with Gaussian tails."""

    samples_v = np.asarray(samples_v, dtype=float)
    labels = np.asarray(labels, dtype=np.uint8)
    if threshold_v is None:
        threshold_v = 0.5 * (
            float(np.mean(samples_v[labels == 0]))
            + float(np.mean(samples_v[labels == 1]))
        )
    theoretical_ber = gaussian_ber_for_noiseless_samples(
        samples_v, labels, threshold_v, sigma_v
    )

    generator = np.random.default_rng(seed)
    counted_errors = 0
    for _ in range(repeats):
        noisy_samples = samples_v + generator.normal(0.0, sigma_v, len(samples_v))
        decisions = noisy_samples >= threshold_v
        counted_errors += int(np.count_nonzero(decisions != labels))
    counted_bits = int(repeats * len(samples_v))
    return GaussianBerValidationResult(
        threshold_v=float(threshold_v),
        sigma_v=float(sigma_v),
        theoretical_ber=theoretical_ber,
        counted_ber=counted_errors / counted_bits,
        counted_errors=counted_errors,
        counted_bits=counted_bits,
    )

