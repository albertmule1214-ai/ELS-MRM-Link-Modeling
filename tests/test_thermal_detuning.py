from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.config import load_config
from mrm_link.thermal import sweep_quasi_static_temperature


def test_temperature_shift_sign_and_scale() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    result = sweep_quasi_static_temperature(
        config,
        np.array([-1.0, 0.0, 1.0]),
        number_of_bits=1024,
        samples_per_ui=8,
    )
    assert np.allclose(result.resonance_shift_pm, [-74.0, 0.0, 74.0])
    assert np.allclose(np.diff(result.detuning_0_pm), [-74.0, -74.0])
    assert result.signed_oma_mw[1] > 0.0


def test_temperature_sweep_detects_polarity_inversion() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml")
    result = sweep_quasi_static_temperature(
        config,
        np.linspace(-4.0, 4.0, 33),
        number_of_bits=1024,
        samples_per_ui=8,
    )
    assert np.min(result.signed_oma_mw) < 0.0 < np.max(result.signed_oma_mw)
    correlation = np.corrcoef(
        result.signed_oma_mw, result.signed_eye_height_v
    )[0, 1]
    assert correlation > 0.98
