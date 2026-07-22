# Signal-dependent shot noise and synthetic sensitivity

## Reference planes

Photodiode shot noise is defined as an input-current noise before the ideal transimpedance stage. The placeholder TIA noise is defined as an output-referred voltage noise before the reference receiver filter.

Keeping these reference planes separate prevents accidental multiplication or division by transimpedance twice.

## From photocurrent to sampled shot noise

For instantaneous photocurrent `I(t)`, the one-sided shot-noise PSD is

```text
S_i(f,t) = 2*q*I(t)  [A^2/Hz].
```

For a real sequence sampled at `fs`, the corresponding pre-filter sample variance is

```text
variance_i[n] = q*I[n]*fs.
```

The noise is multiplied by transimpedance and passed through the same fourth-order Bessel-Thomson reference filter as the signal.

Because `I[n]` changes with the data waveform, output variance cannot be obtained from one average current when conditional bit statistics are required. If `h[k]` is the discrete filter impulse response, the output shot variance is

```text
variance_v[n] = sum_k (Z*h[k])^2 * q*I[n-k]*fs.
```

The squared impulse response is essential: independent noise variances add, while signal amplitudes use the ordinary impulse response.

## Validation result

With the synthetic example configuration:

| Quantity | Result |
|---|---:|
| Reference-filter ENBW | 27.771051 GHz |
| Total RMS, analytic variance | 5.490148 mV |
| Total RMS, generated waveform | 5.491860 mV |
| Total RMS, Welch integration | 5.485834 mV |
| Bit-0 conditional RMS, theory/time | 3.516275 / 3.516470 mV |
| Bit-1 conditional RMS, theory/time | 6.937432 / 6.937712 mV |

The higher bit-1 RMS is expected because its optical power and photocurrent are higher.

## Sensitivity sweep

For every additional-loss point:

- deterministic receiver samples scale with optical power;
- shot-noise variance scales with optical power;
- output-referred TIA variance remains fixed;
- the decision threshold is numerically optimized;
- Gaussian tail probabilities are averaged over every deterministic PRBS sample, preserving pattern-dependent ISI.

The configured illustrative target BER is `2.4e-4`. The synthetic crossing is approximately `-19.18 dBm` average power at the photodiode.

This number must not be reported as device sensitivity. It depends on synthetic MRM, responsivity, transimpedance and TIA-noise assumptions, and it is not a formal TDEC or compliance measurement.

## Low-BER policy

The curve uses analytic conditional Gaussian tails. Direct error counting remains limited to stress cases where enough errors can actually be observed. No claim at `1e-12` is made by brute-force bit counting.
