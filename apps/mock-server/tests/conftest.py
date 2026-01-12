"""Test bootstrap for cli-mock-runtime."""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = APP_ROOT.parent
EXTRA_PATHS = [
    APP_ROOT,
    APPS_DIR / "cli-mock-generator",
]

for path in EXTRA_PATHS:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
