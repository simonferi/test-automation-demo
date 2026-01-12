"""CLI entrypoint for mock configuration generation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

if __package__ in {None, ""}:
    current_file = Path(__file__).resolve()
    package_root = current_file.parents[1]
    apps_dir = current_file.parents[2]
    for candidate in (package_root, apps_dir / "cli-contract-intake", apps_dir / "cli-test-generator"):
        candidate_str = str(candidate)
        if candidate_str not in sys.path and candidate.exists():
            sys.path.insert(0, candidate_str)
    __package__ = "mock_config_builder"

from contract_parser.models import ContractIR
from test_scenario_builder.prompts import PromptLibrary

from .generator import MockConfigBuilder
from .models import MockConfig

app = typer.Typer(help="Generate editable mock server configurations from IR snapshots.")

DEFAULT_OUTPUT_DIR = Path("artifacts/mocks")
SUPPORTED_FORMATS = {"yaml", "json"}


def _load_ir(path: Path) -> ContractIR:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - user error path
        raise typer.BadParameter(f"IR file {path} is not valid JSON: {exc}") from exc
    return ContractIR.model_validate(payload)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-") or "service"


def _parse_ports(pairs: list[str]) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter("Port overrides must use protocol=port format")
        protocol, raw_port = item.split("=", 1)
        protocol = protocol.strip().lower()
        if not protocol:
            raise typer.BadParameter("Protocol name cannot be empty")
        try:
            port = int(raw_port.strip())
        except ValueError as exc:  # pragma: no cover - validated by typer
            raise typer.BadParameter(f"Port for protocol {protocol} must be an integer") from exc
        if port <= 0 or port > 65535:
            raise typer.BadParameter("Port must be between 1 and 65535")
        overrides[protocol] = port
    return overrides


def _write_config(config: MockConfig, output_dir: Path, fmt: str) -> Path:
    fmt = fmt.lower()
    service_dir = output_dir / _slug(config.service) / _slug(config.version)
    service_dir.mkdir(parents=True, exist_ok=True)
    filename = "mock-config.json" if fmt == "json" else "mock-config.yaml"
    destination = service_dir / filename

    payload = config.as_serializable()
    if fmt == "json":
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return destination


@app.command()
def generate(
    ir: list[Path] = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path(s) to Contract IR JSON files produced by cli-contract-intake.",
    ),
    prompt_library: Optional[Path] = typer.Option(
        None,
        help="Optional prompt YAML describing response templates and defaults.",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_OUTPUT_DIR,
        help="Destination root directory for mock configuration files.",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        help="Bind host recorded in configuration files.",
    ),
    port: list[str] = typer.Option(
        [],
        "--port",
        "-p",
        help="Override default protocol ports via protocol=port (e.g. rest=9100).",
    ),
    format: str = typer.Option(
        "yaml",
        "--format",
        "-f",
        help="Output format: yaml (default) or json.",
    ),
) -> None:
    """Generate mock configuration artifacts for REST/SOAP/RPC mock runtimes."""

    if not ir:
        raise typer.BadParameter("Provide at least one IR snapshot via --ir")

    fmt = format.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise typer.BadParameter("Format must be 'yaml' or 'json'")

    prompt = PromptLibrary.from_file(prompt_library)
    port_overrides = _parse_ports(port)
    builder = MockConfigBuilder(prompt, host=host, port_overrides=port_overrides)

    for ir_path in ir:
        contract = _load_ir(ir_path)
        config = builder.build(contract)
        destination = _write_config(config, output_dir=output_dir, fmt=fmt)
        typer.secho(f"Mock config created -> {destination}", fg=typer.colors.GREEN)


def run() -> None:
    """Console_scripts hook."""

    app()


if __name__ == "__main__":  # pragma: no cover
    run()
