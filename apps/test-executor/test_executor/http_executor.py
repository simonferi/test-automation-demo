"""Built-in executors for scenario steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import os
import re
import time
from urllib import error, request

DEFAULT_BASE_URL = "http://127.0.0.1:9101"
DEFAULT_TIMEOUT = 10.0
_PLACEHOLDER_PATTERN = re.compile(r"\{([^}]+)\}")
_PLACEHOLDER_DEFAULTS = {
    "paymentId": "111",
    "customerId": "cust-001",
    "reportId": "rep-001",
}


@dataclass
class ExecutionResult:
    """Details about a performed step request."""

    status_code: int
    elapsed_ms: float
    response_body: str | None = None


class HttpStepExecutor:
    """Executes OpenAPI/REST steps directly via HTTP requests."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        env_base = os.getenv("SMOKE_RUNTIME_BASE_URL", DEFAULT_BASE_URL)
        self._base_url = (base_url or env_base).rstrip("/")
        env_timeout = os.getenv("SMOKE_RUNTIME_TIMEOUT", str(DEFAULT_TIMEOUT))
        self._timeout = timeout or float(env_timeout)

    def execute(self, step: Any, payload: Any, context: dict[str, Any]) -> ExecutionResult:
        request_block = step.request or {}
        method = str(request_block.get("method", "GET")).upper()
        raw_path = request_block.get("path") or "/"
        url = self._build_url(raw_path)

        headers = {"Accept": "application/json"}
        headers.update(self._extract_headers(payload))
        body_bytes = self._encode_body(method, payload)

        status, response_body, elapsed_ms = self._perform_request(method, url, headers, body_bytes)
        return ExecutionResult(status_code=status, elapsed_ms=elapsed_ms, response_body=response_body)

    def _build_url(self, path: str) -> str:
        resolved_path = _PLACEHOLDER_PATTERN.sub(self._substitute_placeholder, path)
        if not resolved_path.startswith("/"):
            resolved_path = f"/{resolved_path}"
        return f"{self._base_url}{resolved_path}"

    @staticmethod
    def _substitute_placeholder(match: re.Match[str]) -> str:
        key = match.group(1)
        return _PLACEHOLDER_DEFAULTS.get(key, "sample")

    @staticmethod
    def _extract_headers(payload: Any) -> dict[str, str]:
        if isinstance(payload, dict) and isinstance(payload.get("headers"), dict):
            return {str(key): str(value) for key, value in payload["headers"].items()}
        return {}

    @staticmethod
    def _encode_body(method: str, payload: Any) -> bytes | None:
        if method == "GET":
            return None
        if not isinstance(payload, dict):
            return None
        body = payload.get("body")
        if body is None:
            return None
        if isinstance(body, (dict, list)):
            return json.dumps(body).encode("utf-8")
        if isinstance(body, str):
            return body.encode("utf-8")
        return str(body).encode("utf-8")

    def _perform_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, str | None, float]:
        data = body if body is not None else None
        req = request.Request(url, data=data, headers=headers, method=method)
        start = time.perf_counter()
        try:
            with request.urlopen(req, timeout=self._timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
                status = response.getcode()
        except error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        except error.URLError as exc:  # pragma: no cover - network failure path
            raise RuntimeError(f"HTTP request failed for {method} {url}: {exc}") from exc
        elapsed_ms = (time.perf_counter() - start) * 1000
        return status, payload, elapsed_ms
