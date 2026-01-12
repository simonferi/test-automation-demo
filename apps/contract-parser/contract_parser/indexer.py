"""JSON-based contract indexing utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .models import ContractIR


class ContractIndexer:
    """Builds a JSON-based search index for IR fragments."""

    def __init__(self, index_path: Path, dim: int = 384) -> None:
        self.index_path = index_path
        self._contracts: list[dict[str, Any]] = []

    def add_contract(self, ir: ContractIR) -> None:
        """Add every operation of the contract to the index buffer."""

        for operation in ir.operations:
            # Create searchable keywords from operation details
            keywords = self._extract_keywords(
                ir.service,
                operation.name,
                operation.method or "",
                operation.path or "",
                operation.description or "",
            )

            self._contracts.append(
                {
                    "service": ir.service,
                    "version": ir.version,
                    "protocol": ir.protocol,
                    "operation": operation.name,
                    "method": operation.method,
                    "path": operation.path,
                    "description": operation.description,
                    "keywords": keywords,
                }
            )

    def persist(self) -> None:
        """Write the JSON index to disk."""

        if not self._contracts:
            return

        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a searchable index structure
        index_data = {
            "format": "json",
            "version": "1.0",
            "total_operations": len(self._contracts),
            "contracts": self._contracts,
        }

        with self.index_path.open("w", encoding="utf-8") as fp:
            json.dump(index_data, fp, indent=2, ensure_ascii=False)

    def _extract_keywords(
        self,
        service: str,
        operation: str,
        method: str,
        path: str,
        description: str,
    ) -> list[str]:
        """Extract searchable keywords from operation details."""

        keywords = set()

        # Add service name parts
        keywords.update(service.lower().split())

        # Add operation name parts
        keywords.update(operation.lower().split())

        # Add method
        if method:
            keywords.add(method.lower())

        # Add path segments
        if path:
            # Extract path segments and parameters
            for segment in path.split("/"):
                if segment and not segment.startswith("{"):
                    keywords.add(segment.lower())

        # Add description words
        if description:
            # Extract meaningful words (skip common words)
            words = description.lower().split()
            keywords.update(w for w in words if len(w) > 3)

        return sorted(keywords)
