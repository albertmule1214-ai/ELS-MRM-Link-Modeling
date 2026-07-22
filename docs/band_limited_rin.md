# Explicitly band-limited high-speed RIN

## Why the frequency support is mandatory

RIN is a relative optical-power PSD. A density value without a measurement or validity band is incomplete because integrated variance grows with bandwidth.

This model requires both `valid_frequency_min` and `valid_frequency_max`. The synthetic example uses 10 MHz to 40 GHz. These limits are assumptions and must be replaced by approved source data.

Low-frequency APC or supply-noise PSD is not reused. The configuration and result summary both record:

```text
low_frequency_apc_psd_reused = false
```

## PSD and RMS

For one-sided RIN density `RIN_linear` in `1/Hz`, fractional optical-power variance is

```text
sigma_relative^2 = integral RIN_linear(f) df.
```

The generator starts with correctly normalized real white noise, removes every FFT bin outside the configured support, and transforms back to a real time waveform. The expected RMS uses the actual retained discrete-bin bandwidth rather than silently assuming an infinite continuum.

With `-144 dB/Hz` and the synthetic 10 MHz–40 GHz support:

| Quantity | Result |
|---|---:|
| Analytic/discrete-bin fractional RMS | 1.261752% |
| Time-waveform fractional RMS | 1.267100% |
| Welch-integrated fractional RMS | 1.266908% |

## Constant-power receiver validation

Before multiplying RIN by a data-modulated optical envelope, the model validates a constant optical-power reference path:

```text
fractional RIN -> optical power -> responsivity -> transimpedance
               -> fourth-order Bessel-Thomson filter
```

For constant optical power `P`, the pre-filter voltage-noise PSD is

```text
S_v(f) = (P*R*Z)^2 * RIN_linear(f).
```

The reference filter then contributes `|H(f)|^2`. The synthetic validation gives 31.2066 mV theoretical RMS, 31.3608 mV time-domain RMS and 31.3520 mV Welch-integrated RMS.

## Why data-modulated BER is deferred

For a data waveform, receiver noise is proportional to

```text
P_data(t) * r_RIN(t).
```

The RIN waveform is band-limited and therefore temporally correlated. Multiplication by the deterministic data envelope makes the output noise cyclostationary and pattern dependent. Replacing it immediately with one average Gaussian sigma would discard this structure.

The current L4 milestone therefore validates the source and constant-power receiver path only. Data-modulated RIN BER will be added after its conditional covariance or an equivalent verified method is implemented. The result field is explicitly `not_implemented_until_conditional_model_is_validated`.
