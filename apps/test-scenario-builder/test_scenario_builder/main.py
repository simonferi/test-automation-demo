"""CLI entrypoint for cli-test-generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

if __package__ in {None, ""}:
    current_file = Path(__file__).resolve()
    package_root = current_file.parents[1]
    apps_dir = current_file.parents[2]
    extra_paths = [package_root, apps_dir, apps_dir / "cli-contract-intake"]
    for candidate in extra_paths:
        candidate_str = str(candidate)
        if candidate_str not in sys.path and candidate.exists():
            sys.path.insert(0, candidate_str)
    __package__ = "test_scenario_builder"

from contract_parser.models import ContractIR

from .builder import ScenarioBundleBuilder
from .prompts import PromptLibrary

app = typer.Typer(help="Generate editable smoke-test scenarios from IR snapshots.")

DEFAULT_IR_DIR = Path("workspace/catalog")
DEFAULT_OUTPUT_DIR = Path("artifacts/tests")


def _load_ir(path: Path) -> ContractIR:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - user error path
        raise typer.BadParameter(f"IR file {path} is not valid JSON: {exc}") from exc
    return ContractIR.model_validate(payload)


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter("Metadata overrides must be in key=value format")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter("Metadata key cannot be empty")
        result[key] = value.strip()
    return result


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
        help="Optional prompt YAML controlling description/assertions/payload templates.",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_OUTPUT_DIR,
        help="Destination directory for generated scenario bundles.",
    ),
    scenario_prefix: str = typer.Option(
        "smoke",
        help="Prefix applied to scenario_id values.",
    ),
    tag: list[str] = typer.Option(
        [],
        "--tag",
        "-t",
        help="Additional tags recorded in scenario metadata.",
    ),
    metadata: list[str] = typer.Option(
        [],
        "--meta",
        help="Custom metadata key=value pairs stored under metadata.custom.",
    ),
) -> None:
    """Generate scenario bundles (YAML + payloads)."""

    if not ir:
        raise typer.BadParameter("Provide at least one IR snapshot via --ir")

    metadata_overrides = _parse_metadata(metadata)
    prompt = PromptLibrary.from_file(prompt_library)
    builder = ScenarioBundleBuilder(
        output_dir=output_dir,
        prompt_library=prompt,
        tags=tag,
        metadata_overrides=metadata_overrides,
        scenario_prefix=scenario_prefix,
    )

    for ir_path in ir:
        contract = _load_ir(ir_path)
        bundle_dir = builder.build(contract)
        typer.secho(f"Scenario bundle created -> {bundle_dir}", fg=typer.colors.GREEN)


def run() -> None:
    """Console_scripts hook."""

    app()


if __name__ == "__main__":  # pragma: no cover
    run()
