# Quasi-static MRM temperature detuning

## Model boundary

Temperature is held fixed during each high-speed waveform evaluation. This is an operating-point sweep, not a thermal transient, heater or feedback-control model.

The resonance shift is

```text
delta_lambda_resonance = thermal_tuning_coefficient * delta_temperature.
```

The model defines detuning as laser wavelength minus resonance wavelength. A positive temperature coefficient therefore makes detuning more negative when temperature increases.

## Why signed metrics are required

Across a wide detuning sweep, P1 can become smaller than P0. The sweep therefore reports signed OMA, signed ER and signed eye height instead of silently taking an absolute value. A zero crossing means the optical modulation disappears; beyond it, logical optical polarity is inverted.

## Synthetic result

The current example uses a 74 pm/degC literature coefficient and a 174.704 pm loaded linewidth. One linewidth corresponds to approximately 2.36 degC.

The first P0=P1 crossing occurs near -0.674 degC for the current voltage bias and detuning convention. This is a useful architecture warning, not a target-device tolerance: the coefficient, static spectrum and bias are synthetic or cross-device examples.

## Deferred thermal functions

- Thermal capacitance and time constant.
- Heater efficiency and electrical limits.
- Sensor noise and quantization.
- Search/acquisition and lock state machines.
- Closed-loop residual detuning distribution.
- Interaction with WDM channels and receiver rings.

Those functions should be built only after the quasi-static optical operating-point map is calibrated against approved spectra or a PDK model.
