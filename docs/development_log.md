# Development log

## L0 — static MRM baseline

- Added a replaceable Lorentzian through-port model.
- Separated loaded Q, notch depth, insertion loss, detuning and voltage tuning.
- Added Q/detuning sweeps and OMA/ER metrics.
- Added regression coverage for a multi-Q generator-exhaustion bug.

## L1 — noiseless time-domain baseline

- Added PRBS15, finite driver edges, static nonlinear modulation, PD/TIA conversion and reference filtering.
- Added separate TX-optical and RX-electrical sampling alignment.
- Added a regression test preventing downstream receiver delay from being reused at the upstream optical reference plane.

## L2 — isolated receiver white noise

- Defined a one-sided PSD convention.
- Verified analytic equivalent-noise-bandwidth RMS against time-domain RMS and Welch-PSD integration.
- Added conditional Gaussian-tail BER over deterministic ISI samples.
- Validated BER only in a deliberately countable stress range; no ultra-low BER claim was made.

## L3 — signal-dependent PD shot noise and synthetic sensitivity

- Added the one-sided photodiode relation `S_i = 2*q*I` at the PD-current reference plane.
- Propagated time-varying input variance through the squared receiver impulse response.
- Confirmed that bit 1 has higher shot-noise RMS than bit 0.
- Added heteroscedastic Gaussian-tail BER with an optimized decision threshold.
- Added a received-power sweep while signal scales with power, shot variance scales with power and output-referred TIA variance remains fixed.

The synthetic target crossing is a software-validation result, not a calibrated device sensitivity or standards-compliance claim.

## L4 — explicitly band-limited high-speed RIN

- Added a one-sided fractional optical-power PSD with mandatory lower and upper validity frequencies.
- Generated a real band-limited time waveform by retaining only explicitly allowed FFT bins.
- Closed source theory, time RMS and Welch-integrated RMS.
- Closed a constant-power PD/TIA/reference-receiver path against `gain^2 * RIN * |H|^2`.
- Recorded `low_frequency_apc_psd_reused = false` in configuration and results.
- Deferred data-modulated RIN BER until a conditional covariance or equivalent verified model exists.

## Next verified increment

Add quasi-static MRM temperature detuning and separate it from high-speed random noise:

```text
temperature offset -> resonance shift -> OMA/ER/eye/BER sensitivity
                   -> later thermal-control operating-point distribution
```