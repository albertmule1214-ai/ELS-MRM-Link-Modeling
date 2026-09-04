# ELS + Microring Optical-Link System Model

Sanitized, reproducible Python models from a 2026 microring internship. All
checked-in configurations are synthetic or public examples. No customer data,
internal presentation, licensed PDK, Cadence/OA database or calibrated product
parameter is included.

## Download

- Git: `git clone https://github.com/albertmule1214-ai/ELS-MRM-Link-Modeling.git`
- Browser: select **Code -> Download ZIP** on GitHub.
- Direct ZIP: <https://github.com/albertmule1214-ai/ELS-MRM-Link-Modeling/archive/refs/heads/main.zip>

Prefer the latest tagged release for a fixed, reproducible handoff.

## Included models

```text
PRBS -> driver -> TX microring -> optical loss -> PD/TIA -> eye / PSD / BER
```

- L0 static microring transfer, Q/detuning, OMA and ER.
- L1 noiseless 53.125-Gbaud NRZ waveform and eye.
- L2 one-sided white-noise PSD, RMS and countable-BER closure.
- L3 signal-dependent shot noise and synthetic sensitivity.
- L4 explicitly band-limited RIN with PSD/RMS closure.
- L5 quasi-static temperature detuning and eye-polarity mapping.
- L6 synthetic four-lane feedback: local RX-ring tracking plus slow shared-ELS
  recentering, with delay/gain, range, outlier and sensor sweeps.

L6 is a behavioral architecture example. Its time constants, wavelength
ranges, delays and sensor errors are assumptions, not hardware limits.

## Five-minute setup

Python 3.11 or newer is required.

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
```

Run the new feedback examples:

```powershell
& .\.venv\Scripts\python.exe scripts\run_bidirectional_els_rx_feedback.py
& .\.venv\Scripts\python.exe scripts\run_bidirectional_els_rx_robustness.py
```

Other runnable stages are under `scripts/`. Generated PNG, CSV and JSON files
appear under `results/` and are ignored by Git.

## Adaptation and handoff

Start with:

- `configs/bidirectional_els_rx_feedback_synthetic.toml`
- `configs/bidirectional_els_rx_robustness_synthetic.toml`
- `docs/bidirectional_els_rx_feedback.md`
- `docs/handoff_and_data_boundary.md`

Keep private parameters in ignored `configs/local/` and private data outside
Git. The actual licensed Cadence/PDK implementation belongs in a separate
company-internal handoff.

## Scientific and legal boundary

- No result is product compliance, silicon prediction or tape-out signoff.
- Slow thermal feedback does not remove MHz-to-GHz laser noise.
- No patent, PDK or third-party data rights are conveyed.
- A formal open-source license has not been selected; obtain project-owner
  approval before external redistribution or commercial use.
