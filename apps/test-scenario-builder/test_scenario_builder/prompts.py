"""Prompt library utilities for cli-test-generator."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from string import Template
from typing import Any

import yaml

DEFAULT_LIBRARY: dict[str, Any] = {
    "defaults": {
        "tags": ["smoke", "generated"],
        "description": "Execute ${operation_name}",
        "payload_template": {
            "note": "Add sample payload for ${operation_name}",
        },
        "default_assertions": ["status == 200"],
        "metadata": {
            "test_type": "smoke",
        },
    },
    "protocols": {
        "openapi": {
            "description": "Call ${method} ${path}",
            "default_assertions": [
                "status == 200",
                "response_time_ms < 2000",
            ],
            "payload_template": {
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "example": "${operation_name} payload",
                },
            },
        },
        "wsdl": {
            "description": "Invoke SOAP operation ${operation_name}",
            "default_assertions": ["soap_fault is None"],
            "payload_template": {
                "soapAction": "${operation_name}",
                "body": {
                    "element": "${operation_name}Request",
                },
            },
        },
        "proto": {
            "description": "Invoke gRPC RPC ${operation_name}",
            "default_assertions": ["status == OK"],
            "payload_template": {
                "metadata": {"deadline_ms": 2000},
                "body": {
                    "message": "${operation_name} request",
                },
            },
        },
    },
}


class PromptLibrary:
    """Tiny helper that resolves prompt metadata per protocol."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        payload = deepcopy(data) if data else deepcopy(DEFAULT_LIBRARY)
        if not isinstance(payload, dict):
            raise ValueError("Prompt library root must be a mapping")
        self._defaults: dict[str, Any] = payload.get("defaults", {}) or {}
        self._protocols: dict[str, Any] = payload.get("protocols", {}) or {}

    @classmethod
    def from_file(cls, path: Path | None) -> "PromptLibrary":
        if path is None:
            return cls()
        if not path.exists():
            raise FileNotFoundError(f"Prompt library {path} not found")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(raw or {})

    def tags(self) -> list[str]:
        return list(self._defaults.get("tags", []))

    def custom_metadata(self) -> dict[str, Any]:
        metadata = self._defaults.get("metadata", {})
        return metadata.copy() if isinstance(metadata, dict) else {}

    def protocol_block(self, protocol: str) -> dict[str, Any]:
        return self._protocols.get(protocol.lower(), {}) or {}

    def description(self, protocol: str, replacements: dict[str, str]) -> str:
        block = self.protocol_block(protocol)
        template = block.get("description") or self._defaults.get("description") or "Execute step"
        return _render_value(template, replacements)

    def assertions(self, protocol: str) -> list[str]:
        block = self.protocol_block(protocol)
        assertions = block.get("default_assertions") or self._defaults.get("default_assertions")
        if isinstance(assertions, list):
            return [str(item) for item in assertions]
        return ["status == 200"]

    def payload_template(self, protocol: str) -> Any:
        block = self.protocol_block(protocol)
        template = block.get("payload_template") or self._defaults.get("payload_template")
        if template is None:
            template = {"note": "Provide payload"}
        return deepcopy(template)

    def render_payload(self, protocol: str, replacements: dict[str, str]) -> Any:
        template = self.payload_template(protocol)
        return _render_value(template, replacements)


def _render_value(value: Any, replacements: dict[str, str]) -> Any:
    """Recursively substitute placeholders in nested structures."""

    if isinstance(value, str):
        return Template(value).safe_substitute(replacements)
    if isinstance(value, list):
        return [_render_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(val, replacements) for key, val in value.items()}
    return value
