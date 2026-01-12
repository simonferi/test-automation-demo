"""Test bootstrap for cli-mock-generator."""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = APP_ROOT.parent
DEPENDENCIES = [APP_ROOT, APPS_DIR / "cli-contract-intake", APPS_DIR / "cli-test-generator"]

for path in DEPENDENCIES:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
