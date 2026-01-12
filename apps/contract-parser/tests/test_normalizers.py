from pathlib import Path

import yaml

from contract_parser.normalizers import normalize_spec


def test_normalize_openapi(tmp_path: Path) -> None:
    spec = {
        "openapi": "3.0.1",
        "info": {"title": "Payments", "version": "v1"},
        "paths": {
            "/payments": {
                "get": {
                    "summary": "List payments",
                    "operationId": "listPayments",
                }
            }
        },
    }
    spec_path = tmp_path / "payments.yaml"
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")

    ir = normalize_spec(spec_path)

    assert ir.service == "Payments"
    assert ir.version == "v1"
    assert ir.protocol == "openapi"
    assert len(ir.operations) == 1
    assert ir.operations[0].name == "listPayments"
