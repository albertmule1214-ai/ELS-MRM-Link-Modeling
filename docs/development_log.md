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

## Next verified increment

Add band-limited laser RIN only over an explicitly configured validity range:

```text
configured RIN support -> optical-power PSD -> generated waveform
                       -> measured PSD/RMS -> conditional BER penalty
```

