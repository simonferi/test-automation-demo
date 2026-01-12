"""Entry point for the cli-contract-intake application."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "contract_parser"

from .indexer import ContractIndexer
from .models import ContractIR
from .normalizers import UnsupportedSpecError, normalize_spec

app = typer.Typer(help="Normalize API specifications into IR snapshots and JSON indexes.")

DEFAULT_OUTPUT = Path("workspace/catalog")
DEFAULT_INDEX = DEFAULT_OUTPUT / "index.json"


def _load_policy(policy_path: Optional[Path]) -> dict[str, object] | None:
    if policy_path is None:
        return None
    if not policy_path.exists():
        raise typer.BadParameter(f"Policy file {policy_path} does not exist")
    text = policy_path.read_text(encoding="utf-8")
    if policy_path.suffix.lower() in {".json"}:
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise typer.BadParameter("Policy file must deserialize into a mapping")
    return payload


def _persist_ir(ir: ContractIR, output_dir: Path) -> Path:
    service_safe = ir.service.lower().replace(" ", "-")
    version_safe = ir.version.replace("/", "-")
    destination_dir = output_dir / service_safe
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_file = destination_dir / f"{version_safe}.json"
    with destination_file.open("w", encoding="utf-8") as fp:
        json.dump(ir.as_serializable(), fp, indent=2, ensure_ascii=False)
    return destination_file


@app.command()
def intake(
    spec: list[Path] = typer.Option(..., exists=True, help="Path to one or more API specifications."),
    policy: Optional[Path] = typer.Option(None, help="Optional policy YAML/JSON applied to metadata."),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT, help="Directory for normalized IR snapshots."),
    index_path: Path = typer.Option(DEFAULT_INDEX, help="Path to the JSON index file."),
    service_name: Optional[str] = typer.Option(None, help="Override service name stored in the IR."),
) -> None:
    """Normalize provided specifications into canonical IR + JSON index."""

    policy_payload = _load_policy(policy)
    indexer = ContractIndexer(index_path=index_path)

    for spec_path in spec:
        try:
            ir = normalize_spec(spec_path, policy=policy_payload, service_override=service_name)
        except UnsupportedSpecError as exc:  # pragma: no cover - user feedback
            raise typer.BadParameter(str(exc)) from exc

        snapshot_path = _persist_ir(ir, output_dir)
        typer.secho(f"Saved IR snapshot -> {snapshot_path}", fg=typer.colors.GREEN)
        indexer.add_contract(ir)

    indexer.persist()
    typer.secho(f"Index updated at {index_path}", fg=typer.colors.CYAN)


def run() -> None:
    """CLI entry point for console_scripts."""

    app()


if __name__ == "__main__":  # pragma: no cover
    run()
