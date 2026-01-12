"""Mock configuration builder."""

from __future__ import annotations

from typing import Any

from contract_parser.models import ContractIR, Operation
from test_scenario_builder.prompts import PromptLibrary

from .models import MockConfig, MockMatcher, MockResponse, MockRoute, MockServer

PROTOCOL_KIND_MAP: dict[str, str] = {
    "openapi": "rest",
    "rest": "rest",
    "http": "rest",
    "wsdl": "soap",
    "soap": "soap",
    "grpc": "rpc",
    "proto": "rpc",
    "rpc": "rpc",
}

DEFAULT_PORTS: dict[str, int] = {
    "rest": 8500,
    "soap": 8600,
    "rpc": 8700,
}


class MockConfigBuilder:
    """Derives human-friendly mock configuration from IR + prompts."""

    def __init__(
        self,
        prompt_library: PromptLibrary,
        host: str,
        port_overrides: dict[str, int] | None = None,
    ) -> None:
        self._prompt = prompt_library
        self._host = host
        self._ports = {k.lower(): v for k, v in (port_overrides or {}).items() if v > 0}

    def build(self, ir: ContractIR) -> MockConfig:
        protocol_kind = PROTOCOL_KIND_MAP.get(ir.protocol.lower(), "rest")
        server = MockServer(
            name=f"{ir.service} {protocol_kind} mock",
            protocol=protocol_kind,
            host=self._host,
            port=self._port_for(protocol_kind),
            routes=[self._route_from_operation(ir, op, protocol_kind) for op in ir.operations],
        )

        metadata: dict[str, Any] = {
            "ir_metadata": ir.metadata,
            "protocol_kind": protocol_kind,
            "ports": {protocol_kind: server.port},
        }

        return MockConfig(
            service=ir.service,
            version=ir.version,
            protocol=ir.protocol,
            generated_at=ir.generated_at,
            source_ir=ir.source_path,
            metadata=metadata,
            servers=[server],
        )

    def _port_for(self, protocol_kind: str) -> int:
        if protocol_kind in self._ports:
            return self._ports[protocol_kind]
        return DEFAULT_PORTS.get(protocol_kind, 8500)

    def _route_from_operation(self, ir: ContractIR, op: Operation, protocol_kind: str) -> MockRoute:
        replacements = {
            "operation_name": op.name,
            "service": ir.service,
            "method": op.method or "",
            "path": op.path or "",
        }
        description = self._prompt.description(ir.protocol, replacements)
        payload = self._prompt.render_payload(ir.protocol, replacements)
        assertions = self._prompt.assertions(ir.protocol)

        matcher = MockMatcher(
            method=op.method if protocol_kind == "rest" else None,
            path=op.path if protocol_kind == "rest" else None,
            soap_action=op.name if protocol_kind == "soap" else None,
            rpc_method=op.name if protocol_kind == "rpc" else None,
        )

        response_headers = {"Content-Type": "application/json"} if protocol_kind == "rest" else {}

        response = MockResponse(
            status=200,
            headers=response_headers,
            body=payload,
            latency_ms=50,
        )

        driver_stub = f"drivers/{protocol_kind}/{ir.service.lower()}_{op.name}.py"

        return MockRoute(
            operation=op.name,
            description=description,
            matcher=matcher,
            response=response,
            assertions=assertions,
            driver_stub=driver_stub,
        )
