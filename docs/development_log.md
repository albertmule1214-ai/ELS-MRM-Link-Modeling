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

## Next verified increment

Add signal-dependent photodiode shot noise and close the same loop:

```text
analytic PSD -> analytic RMS -> generated time waveform -> measured PSD/RMS
             -> conditional BER -> countable stress cross-check
```

