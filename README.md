# ELS + MRM Optical-Link System Model

Local, offline Python models for studying how transmitter, microring-modulator and receiver impairments affect a single-channel optical link.

The first target is a synthetic 53.125-Gbaud NRZ link:

```text
PRBS15 -> voltage driver -> TX microring modulator -> optical loss
       -> photodiode -> TIA -> reference receiver -> eye / PSD / BER
```

This repository is intentionally data-safe. It contains reusable code, tests and synthetic example configurations. It does **not** contain internal presentations, papers, specifications, measured device data or project-specific parameter files.

## Current milestones

- L0: static through-port MRM transfer function, Q/detuning sweep, OMA and ER.
- L1: noiseless 53.125-Gbaud NRZ waveform and receiver eye.
- L2: isolated additive white-noise validation from one-sided PSD to filtered RMS and countable BER.
- L3: signal-dependent photodiode shot noise, conditional 0/1 RMS and a synthetic receiver-sensitivity curve.
- L4: explicitly band-limited high-speed RIN with source and constant-power receiver PSD/RMS closure.
- Automated tests cover PRBS balance, reference-plane alignment, Q sweeps, PSD/RMS closure and BER counting.

Formal TDEC, calibrated sensitivity, laser RIN/linewidth conversion, thermal control, WDM crosstalk and receiver rings are future work.

## Important scientific boundary

All numerical values in `configs/mrm_oci_53g_nrz_v0.toml` are either public-spec examples or explicitly marked synthetic assumptions. They are useful for validating the software architecture, not for predicting a specific device.

The BER stress test deliberately uses a directly countable BER near `1e-3`. It validates the Gaussian-tail calculation; it does not claim an ultra-low device BER. The platform must not estimate `1e-12` BER by brute-force transmission of `1e12` bits.

## Setup

Python 3.11 or newer is required.

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the verified stages:

```powershell
& .\.venv\Scripts\python.exe scripts\run_static_baseline.py
& .\.venv\Scripts\python.exe scripts\run_noiseless_l1.py
& .\.venv\Scripts\python.exe scripts\run_white_noise_validation.py
& .\.venv\Scripts\python.exe scripts\run_shot_noise_sensitivity.py
& .\.venv\Scripts\python.exe scripts\run_rin_bandlimited_validation.py
& .\.venv\Scripts\python.exe -m pytest -q
```

Generated plots and JSON/CSV summaries appear in `results/`.

## Repository map

```text
configs/      synthetic, provenance-tagged examples
docs/         scope, roadmap and development record
scripts/      reproducible entry points
src/mrm_link/ model implementation
tests/        numerical and regression tests
data/         ignored placeholders for local data
results/      ignored generated outputs
```

Read [docs/model_scope.md](docs/model_scope.md) before interpreting results, [docs/shot_noise_and_sensitivity.md](docs/shot_noise_and_sensitivity.md) for the L3 equations, [docs/band_limited_rin.md](docs/band_limited_rin.md) for the L4 boundary, and [docs/data_boundary.md](docs/data_boundary.md) before adding data or parameters.

