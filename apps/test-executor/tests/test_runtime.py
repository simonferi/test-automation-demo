from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import threading

import yaml
from typer.testing import CliRunner

from test_executor.main import app

runner = CliRunner()


def _start_test_server() -> tuple[HTTPServer, threading.Thread]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - HTTP handler requirement
            if self.path == "/fail":
                self.send_response(500)
            else:
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format: str, *args: object) -> None:  # pragma: no cover - silence logs
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    payloads = bundle / "payloads"
    payloads.mkdir(parents=True)

    (payloads / "001_step.json").write_text(json.dumps({"headers": {"X-Test": "1"}}), encoding="utf-8")
    (payloads / "002_step.json").write_text(json.dumps({}), encoding="utf-8")
    (payloads / "003_step.json").write_text(json.dumps({}), encoding="utf-8")

    scenario = {
        "scenario_id": "smoke-payments-v1",
        "service": "Payments",
        "version": "v1",
        "protocol": "openapi",
        "metadata": {
            "tags": ["smoke"],
        },
        "steps": [
            {
                "name": "step-pass",
                "protocol": "openapi",
                "request": {"method": "GET", "path": "/ok", "payload": "payloads/001_step.json"},
                "assertions": ["status == 200"],
            },
            {
                "name": "step-fail",
                "protocol": "openapi",
                "request": {"method": "GET", "path": "/fail", "payload": "payloads/002_step.json"},
                "assertions": ["status == 200"],
            },
            {
                "name": "step-pass-2",
                "protocol": "openapi",
                "request": {"method": "GET", "path": "/ok", "payload": "payloads/003_step.json"},
            },
        ],
    }
    (bundle / "scenario.yaml").write_text(yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8")
    return bundle


def test_runtime_produces_summary_and_events(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    output_dir = tmp_path / "runs"
    server, thread = _start_test_server()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    result = runner.invoke(
        app,
        [
            "--bundle",
            str(bundle),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "test-run",
        ],
        env={"SMOKE_RUNTIME_BASE_URL": base_url},
    )

    server.shutdown()
    thread.join(timeout=2)

    assert result.exit_code == 0, result.output

    summary_file = output_dir / "test-run" / "summary.json"
    events_file = output_dir / "test-run" / "events.jsonl"
    junit_file = output_dir / "test-run" / "results.junit.xml"

    assert summary_file.exists()
    assert events_file.exists()
    assert junit_file.exists()

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["total_steps"] == 3
    assert summary["passed_steps"] == 2
    assert summary["failed_steps"] == 1
    assert len(summary["failures"]) == 1
    assert summary["failures"][0]["step_name"] == "step-fail"

    events = [json.loads(line) for line in events_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(events) == 3
    assert events[1]["step_name"] == "step-fail"
    assert events[1]["status"] == "failed"
    assert events[2]["step_name"] == "step-pass-2"
    assert events[2]["status"] == "passed"
