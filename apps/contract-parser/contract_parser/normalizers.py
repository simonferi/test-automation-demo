"""Helpers for turning API specifications into ContractIR objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import xml.etree.ElementTree as ET

import yaml

from .models import ContractIR, Operation


class UnsupportedSpecError(RuntimeError):
    """Raised when the CLI cannot determine how to parse a spec."""


def normalize_spec(
    spec_path: Path,
    *,
    policy: dict[str, Any] | None = None,
    service_override: str | None = None,
) -> ContractIR:
    """Normalize a supported contract file into a ContractIR object."""

    suffix = spec_path.suffix.lower()
    raw_text = spec_path.read_text(encoding="utf-8")

    if suffix in {".json", ".yaml", ".yml"}:
        parsed = yaml.safe_load(raw_text)
        if not isinstance(parsed, dict):
            raise UnsupportedSpecError("Expected OpenAPI/Swagger document to be an object")
        if "openapi" in parsed or "swagger" in parsed:
            return _normalize_openapi(parsed, spec_path, policy, service_override)
        raise UnsupportedSpecError("YAML/JSON file is not an OpenAPI/Swagger document")

    if suffix in {".wsdl", ".xml"}:
        return _normalize_wsdl(raw_text, spec_path, policy, service_override)

    if suffix == ".proto":
        return _normalize_proto(raw_text, spec_path, policy, service_override)

    raise UnsupportedSpecError(f"Unsupported specification format: {suffix}")


def _normalize_openapi(
    data: dict[str, Any],
    spec_path: Path,
    policy: dict[str, Any] | None,
    service_override: str | None,
) -> ContractIR:
    info = data.get("info", {})
    service = service_override or info.get("title") or spec_path.stem
    version = str(info.get("version", "0"))
    operations: list[Operation] = []

    for raw_path, path_item in (data.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, entry in path_item.items():
            if not isinstance(entry, dict):
                continue
            summary = entry.get("summary") or entry.get("description")
            operation_id = entry.get("operationId")
            name = operation_id or f"{method.upper()} {raw_path}"
            operations.append(
                Operation(
                    name=name,
                    method=method.upper(),
                    path=raw_path,
                    description=summary,
                )
            )

    metadata = {
        "raw_version": data.get("openapi") or data.get("swagger"),
        "policy": policy or {},
    }
    return ContractIR(
        service=service,
        version=version,
        protocol="openapi",
        source_path=str(spec_path),
        metadata=metadata,
        operations=operations,
    )


def _normalize_wsdl(
    text: str,
    spec_path: Path,
    policy: dict[str, Any] | None,
    service_override: str | None,
) -> ContractIR:
    tree = ET.fromstring(text)
    ns = {
        "wsdl": "http://schemas.xmlsoap.org/wsdl/",
        "soap": "http://schemas.xmlsoap.org/wsdl/soap/",
    }
    service = service_override or tree.attrib.get("name") or spec_path.stem
    operations: list[Operation] = []

    for op_elem in tree.findall(".//wsdl:operation", ns):
        name = op_elem.attrib.get("name", "operation")
        doc_elem = op_elem.find("wsdl:documentation", ns)
        description = doc_elem.text.strip() if doc_elem is not None and doc_elem.text else None
        operations.append(
            Operation(
                name=name,
                method="SOAP",
                description=description,
            )
        )

    metadata = {"policy": policy or {}, "namespaces": ns}
    return ContractIR(
        service=service,
        version="1.0",
        protocol="wsdl",
        source_path=str(spec_path),
        metadata=metadata,
        operations=operations,
    )


def _normalize_proto(
    text: str,
    spec_path: Path,
    policy: dict[str, Any] | None,
    service_override: str | None,
) -> ContractIR:
    service_match = re.search(r"service\s+(?P<name>\w+)", text)
    service = service_override or (service_match.group("name") if service_match else spec_path.stem)
    rpc_pattern = re.compile(r"rpc\s+(?P<name>\w+)\s*\(")
    operations: list[Operation] = []
    for match in rpc_pattern.finditer(text):
        operations.append(Operation(name=match.group("name"), method="gRPC"))

    metadata = {
        "policy": policy or {},
    }
    return ContractIR(
        service=service,
        version="1.0",
        protocol="proto",
        source_path=str(spec_path),
        metadata=metadata,
        operations=operations,
    )
