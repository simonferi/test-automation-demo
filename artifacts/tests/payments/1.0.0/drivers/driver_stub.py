"""HTTP driver that exercises the Payments mock runtime."""

from __future__ import annotations

from typing import Any
import json
import os
import re
import time
from urllib import error, request

BASE_URL = os.getenv("SMOKE_RUNTIME_BASE_URL", "http://127.0.0.1:9101").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_RUNTIME_TIMEOUT", "10"))
_PLACEHOLDER_PATTERN = re.compile(r"\{([^}]+)\}")
_PLACEHOLDER_DEFAULTS = {
    "paymentId": "111",
    "customerId": "cust-001",
    "reportId": "rep-001",
}


def execute_step(step_name: str, context: dict[str, Any]) -> None:
    """Perform the HTTP call defined in the scenario step against the mock runtime."""

    request_block = context.get("request", {})
    method = str(request_block.get("method", "GET")).upper()
    raw_path = request_block.get("path") or "/"
    url = _build_url(raw_path)

    payload = context.get("payload") or {}
    headers = {"Accept": "application/json"}
    headers.update(_normalize_headers(payload.get("headers")))
    body_bytes = _encode_body(method, payload.get("body"))

    status, _, elapsed_ms = _perform_request(method, url, headers, body_bytes)
    assertions = (context.get("step") or {}).get("assertions", [])
    _evaluate_assertions(assertions, status, elapsed_ms, step_name)


def _build_url(path: str) -> str:
    resolved_path = _PLACEHOLDER_PATTERN.sub(_substitute_placeholder, path)
    if not resolved_path.startswith("/"):
        resolved_path = f"/{resolved_path}"
    return f"{BASE_URL}{resolved_path}"


def _substitute_placeholder(match: re.Match[str]) -> str:
    key = match.group(1)
    return _PLACEHOLDER_DEFAULTS.get(key, "sample")


def _normalize_headers(raw_headers: Any) -> dict[str, str]:
    if not isinstance(raw_headers, dict):
        return {}
    return {str(key): str(value) for key, value in raw_headers.items()}


def _encode_body(method: str, body: Any) -> bytes | None:
    if body is None or method == "GET":
        return None
    if isinstance(body, (dict, list)):
        return json.dumps(body).encode("utf-8")
    if isinstance(body, str):
        return body.encode("utf-8")
    return str(body).encode("utf-8")


def _perform_request(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, str, float]:
    data = body if body is not None else None
    req = request.Request(url, data=data, headers=headers, method=method)
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=TIMEOUT) as response:
            payload = response.read().decode("utf-8", errors="replace")
            status = response.getcode()
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except error.URLError as exc:  # pragma: no cover - network failure path
        raise RuntimeError(f"HTTP request failed for {method} {url}: {exc}") from exc
    elapsed_ms = (time.perf_counter() - start) * 1000
    return status, payload, elapsed_ms


def _evaluate_assertions(assertions: list[Any], status: int, elapsed_ms: float, step_name: str) -> None:
    for clause in assertions:
        if not isinstance(clause, str):
            continue
        text = clause.strip()
        if text.startswith("status =="):
            expected = int(text.split("==", 1)[1].strip())
            if status != expected:
                raise AssertionError(
                    f"Step '{step_name}' expected status {expected} but received {status}"
                )
            continue
        if text.startswith("response_time_ms <"):
            threshold = float(text.split("<", 1)[1].strip())
            if elapsed_ms >= threshold:
                raise AssertionError(
                    f"Step '{step_name}' exceeded response time threshold {threshold}ms"
                )

