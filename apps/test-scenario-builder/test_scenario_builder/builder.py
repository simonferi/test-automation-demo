"""Scenario bundle builder."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re

import yaml

from contract_parser.models import ContractIR, Operation

from .prompts import PromptLibrary


class ScenarioBundleBuilder:
    """Constructs editable scenario bundles from ContractIR objects."""

    def __init__(
        self,
        *,
        output_dir: Path,
        prompt_library: PromptLibrary,
        tags: list[str] | None = None,
        metadata_overrides: dict[str, str] | None = None,
        scenario_prefix: str = "smoke",
    ) -> None:
        self.output_dir = output_dir
        self.prompt_library = prompt_library
        base_tags = ["smoke"] + prompt_library.tags()
        if tags:
            base_tags += tags
        self.tags = _deduplicate(base_tags)
        base_meta = prompt_library.custom_metadata()
        if metadata_overrides:
            base_meta.update(metadata_overrides)
        self.metadata_overrides = base_meta
        self.scenario_prefix = scenario_prefix

    def build(self, ir: ContractIR) -> Path:
        """Generate files for a single IR snapshot."""

        bundle_dir = self._bundle_directory(ir)
        payloads_dir = bundle_dir / "payloads"
        payloads_dir.mkdir(parents=True, exist_ok=True)

        scenario_id = self._scenario_id(ir)
        scenario_doc = {
            "scenario_id": scenario_id,
            "service": ir.service,
            "version": ir.version,
            "protocol": ir.protocol,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "tags": self.tags,
                "custom": self.metadata_overrides,
            },
            "steps": [],
        }

        for index, operation in enumerate(ir.operations, start=1):
            step = self._build_step(ir, operation, index, payloads_dir, bundle_dir)
            scenario_doc["steps"].append(step)

        _write_yaml(bundle_dir / "scenario.yaml", scenario_doc)
        return bundle_dir

    def _build_step(
        self,
        ir: ContractIR,
        operation: Operation,
        index: int,
        payloads_dir: Path,
        bundle_dir: Path,
    ) -> dict[str, Any]:
        slug = _slugify(operation.name or f"step-{index}")
        payload_file = payloads_dir / f"{index:03d}_{slug}.json"
        replacements = {
            "operation_name": operation.name,
            "method": (operation.method or "CUSTOM"),
            "path": (operation.path or f"/{slug}"),
            "protocol": ir.protocol,
            "service": ir.service,
            "version": ir.version,
        }
        payload = self.prompt_library.render_payload(ir.protocol, replacements)
        payload_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        request = self._request_block(ir.protocol, operation, payload_file.relative_to(bundle_dir))
        description = self.prompt_library.description(ir.protocol, replacements)
        assertions = self.prompt_library.assertions(ir.protocol)
        step: dict[str, Any] = {
            "name": operation.name,
            "description": description,
            "protocol": ir.protocol,
            "request": request,
            "assertions": assertions,
        }
        if operation.description:
            step["notes"] = operation.description
        return step

    def _bundle_directory(self, ir: ContractIR) -> Path:
        service_slug = _slugify(ir.service)
        version_slug = ir.version.replace("/", "-")
        bundle = self.output_dir / service_slug / version_slug
        bundle.mkdir(parents=True, exist_ok=True)
        return bundle

    def _scenario_id(self, ir: ContractIR) -> str:
        service_slug = _slugify(ir.service)
        version_slug = _slugify(ir.version)
        return f"{self.scenario_prefix}-{service_slug}-{version_slug}"

    def _request_block(self, protocol: str, operation: Operation, payload_rel: Path) -> dict[str, Any]:
        payload_ref = str(payload_rel).replace("\\", "/")
        match protocol.lower():
            case "openapi":
                return {
                    "method": (operation.method or "POST"),
                    "path": (operation.path or f"/{_slugify(operation.name)}"),
                    "payload": payload_ref,
                }
            case "wsdl":
                return {
                    "operation": operation.name,
                    "soapAction": operation.name,
                    "payload": payload_ref,
                }
            case "proto":
                return {
                    "rpc": operation.name,
                    "payload": payload_ref,
                }
            case _:
                return {
                    "operation": operation.name,
                    "payload": payload_ref,
                }

def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug.lower() or "item"


def _deduplicate(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
