"""Pydantic models describing mock server configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MockMatcher(BaseModel):
    """Criteria used by runtime mock servers to match an incoming request."""

    method: str | None = None
    path: str | None = None
    soap_action: str | None = None
    rpc_method: str | None = None


class MockResponse(BaseModel):
    """Static response payload returned by the mock server."""

    status: int = 200
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = Field(default_factory=dict)
    latency_ms: int = 0


class MockRoute(BaseModel):
    """Single mocked operation (REST endpoint, SOAP operation or RPC method)."""

    operation: str
    description: str
    matcher: MockMatcher
    response: MockResponse
    assertions: list[str] = Field(default_factory=list)
    driver_stub: str | None = None


class MockServer(BaseModel):
    """Server instance definition with protocol, bind host and port."""

    name: str
    protocol: str
    host: str
    port: int
    routes: list[MockRoute] = Field(default_factory=list)


class MockConfig(BaseModel):
    """Top-level configuration consumed by a mock runtime."""

    service: str
    version: str
    protocol: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ir: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    servers: list[MockServer] = Field(default_factory=list)

    def as_serializable(self) -> dict[str, Any]:
        """Return a JSON/YAML friendly payload."""

        return self.model_dump(mode="json")
