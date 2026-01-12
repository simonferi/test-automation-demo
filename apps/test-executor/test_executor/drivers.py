"""Dynamic driver loading helpers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable


class DriverRegistry:
    """Caches driver modules/functions relative to a scenario bundle."""

    def __init__(self, bundle_root: Path) -> None:
        self.bundle_root = bundle_root
        self._cache: dict[tuple[str, str], Callable] = {}
        self._modules: dict[str, ModuleType] = {}
        self._path_added = False

    def resolve(self, module_name: str, function_name: str) -> Callable:
        key = (module_name, function_name)
        if key in self._cache:
            return self._cache[key]

        self._ensure_path()
        module = self._modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
            self._modules[module_name] = module
        func = getattr(module, function_name, None)
        if func is None:
            raise AttributeError(f"Driver function {function_name} not found in {module_name}")
        self._cache[key] = func
        return func

    def _ensure_path(self) -> None:
        if self._path_added:
            return
        bundle_str = str(self.bundle_root)
        if bundle_str not in sys.path:
            sys.path.insert(0, bundle_str)
        self._path_added = True
