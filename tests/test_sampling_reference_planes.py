from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config
from mrm_link.waveform import run_noiseless_waveform


def test_tx_optical_levels_use_tx_reference_plane() -> None:
    """RX filter delay must not be reused when measuring the upstream TX OMA."""

    config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    config = deepcopy(config)
    config["signal"]["number_of_bits"]["value"] = 2048
    config["signal"]["samples_per_ui"]["value"] = 16
    result = run_noiseless_waveform(config)

    available_optical_swing = float(np.ptp(result.optical_power_w))
    assert result.optical_levels.oma_w > 0.8 * available_optical_swing
    assert result.optical_sampling.integer_lag_ui == 0
    assert result.sampling.integer_lag_ui >= result.optical_sampling.integer_lag_ui
