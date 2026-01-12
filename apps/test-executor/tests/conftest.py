"""Test bootstrap for cli-smoke-runtime."""

from __future__ import annotations

import sys
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parents[2]
for package in ["cli-smoke-runtime", "cli-test-generator", "cli-contract-intake"]:
    package_root = APPS_DIR / package
    path_str = str(package_root)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
