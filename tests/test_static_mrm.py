from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrm_link.baseline import build_static_mrm, run_static_baseline, scan_rows
from mrm_link.config import load_config
from mrm_link.metrics import OpticalLevels


class StaticMicroringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(
            PROJECT_ROOT / "configs" / "mrm_oci_53g_nrz_v0.toml"
        )
        cls.model = build_static_mrm(cls.config)

    def test_ui_matches_oci_symbol_rate(self) -> None:
        result = run_static_baseline(self.config)
        self.assertAlmostEqual(result.ui_s * 1e12, 18.8235294118, places=8)

    def test_fwhm_is_wavelength_over_q(self) -> None:
        expected = self.model.laser_wavelength_m / self.model.loaded_q
        self.assertAlmostEqual(self.model.fwhm_m, expected, places=24)

    def test_transmission_bounds_and_on_resonance_depth(self) -> None:
        t_on = self.model.transmission(self.model.reference_voltage_v)
        self.assertAlmostEqual(t_on, self.model.on_resonance_transmission, places=12)
        self.assertGreaterEqual(t_on, 0.0)
        self.assertLessEqual(t_on, self.model.off_resonance_transmission)

    def test_optical_metric_definitions(self) -> None:
        levels = OpticalLevels(p0_w=1.0e-3, p1_w=2.0e-3)
        self.assertAlmostEqual(levels.oma_w, 1.0e-3)
        self.assertAlmostEqual(levels.oma_dbm, 0.0)
        self.assertAlmostEqual(levels.er_db, 10.0 * math.log10(2.0))

    def test_default_polarity_produces_p1_above_p0(self) -> None:
        result = run_static_baseline(self.config)
        self.assertGreater(result.levels.p1_w, result.levels.p0_w)

    def test_q_scan_has_expected_linewidth_order(self) -> None:
        rows = list(scan_rows(self.config, (item for item in [0.0])))
        self.assertEqual(len(rows), 3)
        fwhm = [row["fwhm_pm"] for row in rows]
        self.assertGreater(fwhm[0], fwhm[1])
        self.assertGreater(fwhm[1], fwhm[2])


if __name__ == "__main__":
    unittest.main()


