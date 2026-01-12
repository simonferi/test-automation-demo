from pathlib import Path

import yaml
from typer.testing import CliRunner

from contract_parser.models import ContractIR, Operation
from test_scenario_builder.main import app

runner = CliRunner()


def _write_ir(tmp_path: Path) -> Path:
    ir = ContractIR(
        service="Payments",
        version="v1",
        protocol="openapi",
        source_path="specs/payments.yaml",
        metadata={"test": "data"},
        operations=[
            Operation(
                name="listPayments",
                method="GET",
                path="/payments",
                description="List payments",
            )
        ],
    )
    ir_path = tmp_path / "payments-ir.json"
    ir_path.write_text(ir.model_dump_json(indent=2), encoding="utf-8")
    return ir_path


def _write_prompt(tmp_path: Path) -> Path:
    prompt_payload = {
        "defaults": {
            "tags": ["smoke"],
            "metadata": {"environment": "local"},
            "description": "Execute ${operation_name}",
        },
        "protocols": {
            "openapi": {
                "default_assertions": ["status == 200"],
                "payload_template": {"body": {"operation": "${operation_name}"}},
            }
        },
    }
    prompt_path = tmp_path / "prompts.yaml"
    prompt_path.write_text(yaml.safe_dump(prompt_payload), encoding="utf-8")
    return prompt_path


def test_generate_creates_scenario_bundle(tmp_path: Path) -> None:
    ir_path = _write_ir(tmp_path)
    prompt_path = _write_prompt(tmp_path)
    output_dir = tmp_path / "artifacts" / "tests"

    result = runner.invoke(
        app,
        [
            "--ir",
            str(ir_path),
            "--prompt-library",
            str(prompt_path),
            "--output-dir",
            str(output_dir),
            "--meta",
            "project=PAY",
            "--tag",
            "critical",
        ],
    )

    assert result.exit_code == 0, result.output

    scenario_file = output_dir / "payments" / "v1" / "scenario.yaml"
    assert scenario_file.exists()

    scenario = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
    assert scenario["scenario_id"].startswith("smoke-payments")
    assert scenario["metadata"]["custom"]["project"] == "PAY"
    assert "critical" in scenario["metadata"]["tags"]
    assert len(scenario["steps"]) == 1
    request = scenario["steps"][0]["request"]
    payload_rel = request["payload"]
    payload_file = scenario_file.parent / payload_rel
    assert payload_file.exists()
    payload = yaml.safe_load(payload_file.read_text(encoding="utf-8"))
    assert payload["body"]["operation"] == "listPayments"