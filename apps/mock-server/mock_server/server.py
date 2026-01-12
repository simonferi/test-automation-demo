"""Server runtime orchestrating mock services for REST/SOAP/RPC."""

from __future__ import annotations

import json
import socketserver
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import structlog

from mock_config_builder.models import MockConfig, MockResponse, MockRoute, MockServer

LOGGER = structlog.get_logger("cli_mock_runtime")


@dataclass
class MockRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes

    @property
    def json(self) -> dict[str, Any] | None:
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8"))
        except Exception:  # pragma: no cover - diagnostics only
            return None


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MockServerRunner:
    """Runs a single HTTP server instance based on MockServer definition."""

    def __init__(self, server_config: MockServer) -> None:
        self._config = server_config
        self._httpd: ThreadedHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._logger = LOGGER.bind(server=server_config.name, protocol=server_config.protocol)

    def start(self) -> None:
        handler_factory = self._build_handler_factory()
        self._logger.info(
            "server_starting",
            host=self._config.host,
            port=self._config.port,
        )
        httpd = ThreadedHTTPServer((self._config.host, self._config.port), handler_factory)
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()
        self._ready.set()
        self._logger = self._logger.bind(host=httpd.server_address[0], port=httpd.server_address[1])
        self._logger.info("server_started")
        for line in _server_console_summary(self._config):
            print(line)

    def stop(self) -> None:
        if not self._httpd:
            return
        self._logger.info("server_stopping")
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        finally:
            if self._thread:
                self._thread.join(timeout=2)
        self._logger.info("server_stopped")

    def wait_until_ready(self, timeout: float = 1.0) -> bool:
        return self._ready.wait(timeout=timeout)

    def _build_handler_factory(self) -> type[BaseHTTPRequestHandler]:
        server_config = self._config

        handler_logger = LOGGER.bind(server=server_config.name, protocol=server_config.protocol)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - avoid stdout
                handler_logger.debug(
                    "http_trace",
                    client_ip=self.client_address[0],
                    message=format % args,
                )

            def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler requirement)
                self._handle()

            def do_POST(self) -> None:  # noqa: N802
                self._handle()

            def do_PUT(self) -> None:  # noqa: N802
                self._handle()

            def do_DELETE(self) -> None:  # noqa: N802
                self._handle()

            def do_PATCH(self) -> None:  # noqa: N802
                self._handle()

            def do_HEAD(self) -> None:  # noqa: N802
                self._handle(head_only=True)

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._handle()

            def _handle(self, *, head_only: bool = False) -> None:
                request = MockRequest(
                    method=self.command,
                    path=self.path.split("?", 1)[0],
                    headers={key: value for key, value in self.headers.items()},
                    body=self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)),
                )
                request_logger = handler_logger.bind(
                    host=self.server.server_address[0],
                    port=self.server.server_address[1],
                )
                request_logger.info(
                    "request_received",
                    method=request.method,
                    path=request.path,
                    content_length=len(request.body),
                )
                try:
                    route = _match_route(server_config, request)
                    if not route:
                        self._respond(HTTPStatus.NOT_FOUND, {"error": "No mock route matched"}, head_only=head_only)
                        request_logger.warning(
                            "request_unmatched",
                            method=request.method,
                            path=request.path,
                        )
                        return
                    self._respond_with_route(route, request, request_logger, head_only=head_only)
                except Exception as exc:  # pragma: no cover - resilience path
                    request_logger.exception(
                        "request_failed",
                        method=request.method,
                        path=request.path,
                    )
                    self._respond(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "mock failure"}, head_only=head_only)

            def _respond_with_route(
                self,
                route: MockRoute,
                request: MockRequest,
                request_logger: Any | None = None,
                *,
                head_only: bool = False,
            ) -> None:
                logger = request_logger or handler_logger.bind(
                    host=self.server.server_address[0],
                    port=self.server.server_address[1],
                )
                request_logger = logger  # compat: allow existing bytecode referencing old name
                response = route.response
                latency = max(response.latency_ms, 0) / 1000
                if latency:
                    time.sleep(latency)
                payload = _render_body(server_config.protocol, response)
                status_code = response.status or 200
                headers = {"Content-Type": _content_type(server_config.protocol)}
                headers.update(response.headers)
                self.send_response(status_code)
                for key, value in headers.items():
                    self.send_header(key, value)
                body_bytes = payload.encode("utf-8")
                self.send_header("Content-Length", str(len(body_bytes)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(body_bytes)
                logger.info(
                    "request_served",
                    method=request.method,
                    path=request.path,
                    operation=route.operation,
                    status=status_code,
                    latency_ms=response.latency_ms,
                )

            def _respond(self, status: HTTPStatus, payload: dict[str, Any], *, head_only: bool = False) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(body)

        return Handler


def _match_route(server: MockServer, request: MockRequest) -> MockRoute | None:
    for route in server.routes:
        matcher = route.matcher
        if server.protocol == "rest":
            if matcher.path and not _rest_path_matches(matcher.path, request.path):
                continue
            if matcher.method and matcher.method.upper() != request.method.upper():
                continue
            return route
        if server.protocol == "soap":
            soap_action = request.headers.get("SOAPAction", "").strip('"')
            if matcher.soap_action and matcher.soap_action != soap_action:
                continue
            if matcher.path and matcher.path != request.path:
                continue
            return route
        if server.protocol == "rpc":
            payload = request.json or {}
            method_name = payload.get("method") if isinstance(payload, dict) else None
            if matcher.rpc_method and matcher.rpc_method != method_name:
                continue
            return route
    return None


def _render_body(protocol: str, response: MockResponse) -> str:
    body = response.body
    if isinstance(body, (dict, list)):
        if protocol == "soap":
            return json.dumps(body)
        return json.dumps(body)
    if isinstance(body, str):
        return body
    return json.dumps(body)


def _content_type(protocol: str) -> str:
    if protocol == "soap":
        return "text/xml"
    return "application/json"


def _rest_path_matches(matcher_path: str, request_path: str) -> bool:
    if matcher_path == request_path:
        return True
    if "{" not in matcher_path:
        return False
    matcher_parts = matcher_path.strip("/").split("/")
    request_parts = request_path.strip("/").split("/")
    if len(matcher_parts) != len(request_parts):
        return False
    for matcher_part, request_part in zip(matcher_parts, request_parts):
        if matcher_part.startswith("{") and matcher_part.endswith("}"):
            continue
        if matcher_part != request_part:
            return False
    return True


def _describe_route(server: MockServer, route: MockRoute) -> str:
    matcher = route.matcher
    if server.protocol == "rest":
        method = (matcher.method or "*").upper()
        path = matcher.path or "/*"
        return f"{method} {path}"
    if server.protocol == "soap":
        action = matcher.soap_action or route.operation
        return f"SOAPAction {action}"
    if server.protocol == "rpc":
        rpc_name = matcher.rpc_method or route.operation
        return f"RPC {rpc_name}"
    return route.operation


def _server_console_summary(server: MockServer) -> list[str]:
    header = f"[mock-runtime] {server.name} ({server.protocol.upper()}) listening on {server.host}:{server.port}"
    route_lines = ["    routes:"]
    described = [_describe_route(server, route) for route in server.routes]
    if described:
        route_lines.extend(f"      - {description}" for description in described)
    else:
        route_lines.append("      (no routes configured)")
    return [header, *route_lines]


class MockRuntime:
    """Starts all configured servers and manages their lifecycle."""

    def __init__(self, config: MockConfig) -> None:
        self._config = config
        self._runners: list[MockServerRunner] = []
        self._logger = LOGGER.bind(service=config.service, version=config.version)

    def start(self) -> None:
        self._logger.info("runtime_starting_servers", server_count=len(self._config.servers))
        for server in self._config.servers:
            runner = MockServerRunner(server)
            runner.start()
            runner.wait_until_ready()
            self._runners.append(runner)
        self._logger.info("runtime_running", active_servers=len(self._runners))

    def stop(self) -> None:
        self._logger.info("runtime_stopping_servers", active_servers=len(self._runners))
        for runner in self._runners:
            runner.stop()
        self._runners.clear()
        self._logger.info("runtime_stopped_servers")

    def __enter__(self) -> "MockRuntime":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - context helper
        self.stop()
