"""Deterministic PRBS sources for link simulation."""

from __future__ import annotations

import numpy as np


def prbs15(number_of_bits: int, seed: int = (1 << 15) - 1) -> np.ndarray:
    """Generate PRBS15 using x^15 + x^14 + 1.

    The all-zero seed is forbidden.  The default all-one seed makes every run
    reproducible and produces a full 32767-bit period.
    """

    if number_of_bits <= 0:
        raise ValueError("number_of_bits must be positive")
    mask = (1 << 15) - 1
    state = seed & mask
    if state == 0:
        raise ValueError("PRBS state cannot be all zero")

    output = np.empty(number_of_bits, dtype=np.uint8)
    for index in range(number_of_bits):
        output[index] = (state >> 14) & 1
        feedback = ((state >> 14) ^ (state >> 13)) & 1
        state = ((state << 1) & mask) | feedback
    return output

