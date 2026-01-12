"""Test bootstrap for cli-test-generator."""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = APP_ROOT.parent
DEPENDENCY_ROOT = APPS_DIR / "cli-contract-intake"

for path in (APP_ROOT, DEPENDENCY_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
