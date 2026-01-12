from pathlib import Path

import yaml
from typer.testing import CliRunner

from contract_parser.models import ContractIR, Operation
from mock_config_builder.main import app

runner = CliRunner()


def _write_ir(tmp_path: Path) -> Path:
    ir = ContractIR(
        service="Payments",
        version="v1",
        protocol="openapi",
        source_path="specs/payments.yaml",
        metadata={"team": "core"},
        operations=[
            Operation(
                name="listPayments",
                method="GET",
                path="/payments",
                description="List payments",
            )
        ],
    )
    target = tmp_path / "payments-ir.json"
    target.write_text(ir.model_dump_json(indent=2), encoding="utf-8")
    return target


def _write_prompt(tmp_path: Path) -> Path:
    data = {
        "defaults": {
            "description": "Invoke ${operation_name}",
            "default_assertions": ["status == 200"],
            "payload_template": {
                "body": {"operation": "${operation_name}"},
            },
        },
    }
    target = tmp_path / "prompts.yaml"
    target.write_text(yaml.safe_dump(data), encoding="utf-8")
    return target


def test_generate_creates_yaml_configuration(tmp_path: Path) -> None:
    ir_path = _write_ir(tmp_path)
    prompt_path = _write_prompt(tmp_path)
    output_dir = tmp_path / "artifacts" / "mocks"

    result = runner.invoke(
        app,
        [
            "--ir",
            str(ir_path),
            "--prompt-library",
            str(prompt_path),
            "--output-dir",
            str(output_dir),
            "--port",
            "rest=9105",
        ],
    )

    assert result.exit_code == 0, result.output

    config_file = output_dir / "payments" / "v1" / "mock-config.yaml"
    assert config_file.exists()
    payload = yaml.safe_load(config_file.read_text(encoding="utf-8"))

    assert payload["service"] == "Payments"
    assert payload["servers"][0]["port"] == 9105
    route = payload["servers"][0]["routes"][0]
    assert route["matcher"]["path"] == "/payments"
    assert route["response"]["body"]["body"]["operation"] == "listPayments"
    assert route["driver_stub"].endswith("listPayments.py")
