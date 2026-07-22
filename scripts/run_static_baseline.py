"""Portable project-local launcher for the first verified model."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
runpy.run_module("mrm_link", run_name="__main__")

