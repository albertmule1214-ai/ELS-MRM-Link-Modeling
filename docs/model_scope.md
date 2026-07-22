# Model scope and interpretation

## Current signal path

```text
PRBS15
  -> NRZ voltage levels
  -> first-order finite-edge driver
  -> static Lorentzian through-port MRM
  -> optical loss
  -> ideal responsivity and transimpedance
  -> fourth-order Bessel-Thomson reference filter
  -> fixed-reference-plane sampling
```

L0 verifies static resonance width, detuning, OMA and ER. L1 adds time-domain signaling, deterministic ISI and eye generation. L2 validates one isolated additive white-noise source. L3 adds signal-dependent photodiode shot noise and a synthetic power-sensitivity sweep. L4 adds an explicitly band-limited high-speed RIN source and constant-power receiver validation. L5 maps quasi-static MRM temperature detuning to signed optical and eye metrics.

## Implemented outputs

- Static MRM transmission and Q/detuning sweep.
- Optical P0, P1, OMA and ER.
- Driver, optical and receiver waveforms.
- Noiseless receiver eye.
- One-sided white-noise PSD, equivalent noise bandwidth and RMS closure.
- Gaussian conditional-tail BER with a directly countable stress validation.
- Signal-dependent shot-noise variance using the squared reference-filter impulse response.
- Conditional bit-0/bit-1 RMS and a synthetic BER-versus-received-power curve.
- Band-limited fractional RIN PSD/RMS and constant-power receiver propagation.
- Quasi-static temperature-to-resonance shift with polarity-aware OMA, ER and eye height.

## Explicitly not implemented

- Calibrated device prediction.
- Formal standards-compliant TDEC.
- Brute-force ultra-low BER claims.
- Dynamic cavity response.
- Laser RIN and linewidth conversion through the ring slope.
- Signal-dependent shot noise and measured TIA spectra.
- Thermal feedback, WDM channels, crosstalk and receiver rings.

The current results are software-validation artifacts. They become engineering predictions only after approved device parameters, reference planes and measurement bandwidths are supplied and validated.

