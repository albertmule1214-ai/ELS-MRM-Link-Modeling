"""Optical modulation metrics in the linear power domain."""

from __future__ import annotations

from dataclasses import dataclass
from math import log10


def watts_to_dbm(power_w: float) -> float:
    if power_w <= 0.0:
        return float("-inf")
    return 10.0 * log10(power_w / 1.0e-3)


@dataclass(frozen=True)
class OpticalLevels:
    p0_w: float
    p1_w: float

    def __post_init__(self) -> None:
        if self.p0_w < 0.0 or self.p1_w < 0.0:
            raise ValueError("Optical powers cannot be negative")
        if self.p1_w < self.p0_w:
            raise ValueError(
                "The NRZ convention requires p1 >= p0; check voltage polarity"
            )

    @property
    def oma_w(self) -> float:
        return self.p1_w - self.p0_w

    @property
    def oma_dbm(self) -> float:
        return watts_to_dbm(self.oma_w)

    @property
    def er_db(self) -> float:
        if self.p0_w == 0.0:
            return float("inf")
        return 10.0 * log10(self.p1_w / self.p0_w)

    @property
    def average_power_w(self) -> float:
        return 0.5 * (self.p1_w + self.p0_w)

