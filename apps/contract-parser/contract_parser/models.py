"""Pydantic models for the contract intake CLI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Operation(BaseModel):
    """Represents a single API operation extracted from an input specification."""

    name: str
    method: str | None = None
    path: str | None = None
    description: str | None = None


class ContractIR(BaseModel):
    """Normalized intermediate representation persisted as JSON."""

    service: str
    version: str
    protocol: str
    source_path: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    operations: list[Operation] = Field(default_factory=list)

    def as_serializable(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        payload = self.model_dump(mode="json")
        payload["operations"] = [op.model_dump(mode="json") for op in self.operations]
        return payload
