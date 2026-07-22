"""Static, normalized through-port microring model.

This is the L0 system model.  It is intentionally replaceable by measured
spectra or a temporal coupled-mode model later.  Q sets the linewidth, while
resonance depth and off-resonance insertion loss are independent parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class StaticThroughMicroring:
    laser_wavelength_m: float
    loaded_q: float
    reference_detuning_m: float
    resonance_depth_db: float
    off_resonance_insertion_loss_db: float
    voltage_tuning_efficiency_m_per_v: float
    reference_voltage_v: float

    def __post_init__(self) -> None:
        scalar_values = (
            self.laser_wavelength_m,
            self.loaded_q,
            self.reference_detuning_m,
            self.resonance_depth_db,
            self.off_resonance_insertion_loss_db,
            self.voltage_tuning_efficiency_m_per_v,
            self.reference_voltage_v,
        )
        if not all(isfinite(number) for number in scalar_values):
            raise ValueError("All microring parameters must be finite")
        if self.laser_wavelength_m <= 0.0:
            raise ValueError("Laser wavelength must be positive")
        if self.loaded_q <= 0.0:
            raise ValueError("Loaded Q must be positive")
        if self.resonance_depth_db < 0.0:
            raise ValueError("Resonance depth cannot be negative")
        if self.off_resonance_insertion_loss_db < 0.0:
            raise ValueError("Insertion loss cannot be negative")

    @property
    def fwhm_m(self) -> float:
        """Loaded resonance FWHM using the L0 definition lambda/Q."""

        return self.laser_wavelength_m / self.loaded_q

    @property
    def off_resonance_transmission(self) -> float:
        return 10.0 ** (-self.off_resonance_insertion_loss_db / 10.0)

    @property
    def on_resonance_transmission(self) -> float:
        return self.off_resonance_transmission * 10.0 ** (
            -self.resonance_depth_db / 10.0
        )

    def resonance_wavelength_m(self, voltage_v: float) -> float:
        reference_resonance_m = (
            self.laser_wavelength_m - self.reference_detuning_m
        )
        return reference_resonance_m + self.voltage_tuning_efficiency_m_per_v * (
            voltage_v - self.reference_voltage_v
        )

    def detuning_m(self, voltage_v: float) -> float:
        """Return laser wavelength minus voltage-dependent resonance."""

        return self.laser_wavelength_m - self.resonance_wavelength_m(voltage_v)

    def transmission(self, voltage_v: float) -> float:
        """Return normalized optical power transmission.

        A Lorentzian notch is used:

            T = T_off * (1 - depth_fraction / (1 + x^2))
            x = 2 * detuning / FWHM

        This guarantees T(0)=T_on and T(infinity)=T_off.
        """

        normalized_detuning = 2.0 * self.detuning_m(voltage_v) / self.fwhm_m
        depth_fraction = 1.0 - (
            self.on_resonance_transmission / self.off_resonance_transmission
        )
        transmission = self.off_resonance_transmission * (
            1.0 - depth_fraction / (1.0 + normalized_detuning**2)
        )
        return min(self.off_resonance_transmission, max(0.0, transmission))

    def with_q_and_detuning(
        self, *, loaded_q: float, reference_detuning_m: float
    ) -> "StaticThroughMicroring":
        return replace(
            self,
            loaded_q=loaded_q,
            reference_detuning_m=reference_detuning_m,
        )

