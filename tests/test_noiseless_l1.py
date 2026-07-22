from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config
from mrm_link.prbs import prbs15
from mrm_link.waveform import run_noiseless_waveform


def test_prbs15_full_period_balance() -> None:
    bits = prbs15((1 << 15) - 1)
    assert int(np.sum(bits == 1)) == 1 << 14
    assert int(np.sum(bits == 0)) == (1 << 14) - 1


def test_noiseless_l1_has_valid_eye_and_levels() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    config = deepcopy(config)
    config["signal"]["number_of_bits"]["value"] = 1024
    config["signal"]["samples_per_ui"]["value"] = 16
    result = run_noiseless_waveform(config)

    assert result.sampling.eye_height > 0.0
    assert result.optical_levels.p1_w > result.optical_levels.p0_w
    assert 0 <= result.sampling.phase_samples < result.samples_per_ui
    assert np.all(np.isfinite(result.rx_voltage_v))
    assert np.min(result.optical_power_w) >= 0.0

