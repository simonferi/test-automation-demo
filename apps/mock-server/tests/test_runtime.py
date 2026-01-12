from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path

import yaml

from mock_config_builder.models import MockConfig
from mock_server.config import load_config
from mock_server.server import MockRuntime


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _write_config(tmp_path: Path) -> Path:
    port = _find_free_port()
    payload = {
        "service": "Payments",
        "version": "v1",
        "protocol": "openapi",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_ir": "specs/payments.yaml",
        "metadata": {},
        "servers": [
            {
                "name": "payments-rest",
                "protocol": "rest",
                "host": "127.0.0.1",
                "port": port,
                "routes": [
                    {
                        "operation": "listPayments",
                        "description": "List payments",
                        "matcher": {"method": "GET", "path": "/payments"},
                        "response": {
                            "status": 200,
                            "headers": {"X-Mock": "payments"},
                            "body": {"items": []},
                            "latency_ms": 0,
                        },
                        "assertions": [],
                        "driver_stub": "drivers/rest/payments_listPayments.py",
                    }
                ],
            }
        ],
    }
    config_path = tmp_path / "payments-mock.yaml"
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


def test_runtime_serves_configured_route(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    cfg = load_config(config_path)
    runtime = MockRuntime(cfg)
    runtime.start()
    try:
        port = cfg.servers[0].port
        connection = HTTPConnection("127.0.0.1", port, timeout=2)
        connection.request("GET", "/payments")
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["items"] == []
        assert response.getheader("X-Mock") == "payments"
    finally:
        runtime.stop()
