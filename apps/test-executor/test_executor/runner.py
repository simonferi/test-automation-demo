"""Scenario execution engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import json
import time
import traceback
import xml.etree.ElementTree as ET

from .console_reporter import ConsoleReporter
from .http_executor import ExecutionResult, HttpStepExecutor
from .output_config import OutputFormat
from .loader import load_scenario
from .models import Scenario, ScenarioResult, ScenarioStep, StepResult


@dataclass
class RunArtifacts:
    run_dir: Path
    events_file: Path
    summary_file: Path
    junit_file: Path


class ScenarioRunner:
    """Executes a generated scenario bundle and records artifacts."""

    def __init__(
        self,
        *,
        bundle: Path,
        output_root: Path,
        run_id: str,
        output_format: OutputFormat = OutputFormat.AUTO,
    ) -> None:
        self.bundle = bundle
        self.output_root = output_root
        self.run_id = run_id
        self.scenario_file = bundle if bundle.is_file() else bundle / "scenario.yaml"
        if not self.scenario_file.exists():
            raise FileNotFoundError(f"Scenario file not found: {self.scenario_file}")
        self._http_executor = HttpStepExecutor()
        self._reporter = ConsoleReporter(output_format=output_format)

    def run(self) -> ScenarioResult:
        scenario = load_scenario(self.scenario_file)
        artifacts = self._prepare_artifacts()
        events_handle = artifacts.events_file.open("w", encoding="utf-8")

        scenario_start = datetime.now(timezone.utc)
        step_results: list[StepResult] = []
        
        # Start test suite display
        self._reporter.start_test_suite(
            total_steps=len(scenario.steps),
            scenario_name=scenario.scenario_id
        )

        try:
            for index, step in enumerate(scenario.steps, start=1):
                # Report step start
                self._reporter.report_step_start(
                    step_num=index,
                    endpoint=step.request.get("path", "/"),
                    method=step.request.get("method", "GET")
                )
                
                result = self._execute_step(
                    scenario=scenario,
                    step=step,
                    step_index=index,
                )
                step_results.append(result)
                events_handle.write(json.dumps(_serialize_step_result(result)) + "\n")
                
                # Report step result
                self._reporter.report_step_result(
                    step_num=index,
                    endpoint=step.request.get("path", "/"),
                    method=step.request.get("method", "GET"),
                    passed=result.status == "passed",
                    duration_ms=result.duration_ms,
                    error_msg=result.error
                )
        finally:
            events_handle.close()

        scenario_end = datetime.now(timezone.utc)
        summary = self._build_summary(
            scenario=scenario,
            scenario_start=scenario_start,
            scenario_end=scenario_end,
            step_results=step_results,
            artifacts=artifacts,
        )
        artifacts.summary_file.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        self._write_junit(step_results, scenario, artifacts.junit_file)
        
        # Display final summary
        self._reporter.finish_test_suite(
            total=summary.total_steps,
            passed=summary.passed_steps,
            failed=summary.failed_steps,
            duration_ms=summary.duration_ms
        )
        
        return summary

    def _execute_step(
        self,
        *,
        scenario: Scenario,
        step: ScenarioStep,
        step_index: int,
    ) -> StepResult:
        payload, payload_path = _load_payload(self.bundle, step.request.get("payload"))
        context = {
            "scenario": scenario.model_dump(mode="json"),
            "step": step.model_dump(mode="json"),
            "payload": payload,
            "payload_path": str(payload_path) if payload_path else None,
            "request": step.request,
        }

        started_at = datetime.now(timezone.utc)
        timer = time.perf_counter()
        error_text: str | None = None
        tb_text: str | None = None
        status = "passed"

        try:
            execution = self._execute_with_protocol(scenario, step, payload, context)
            self._validate_assertions(step, execution)
        except Exception as exc:  # pragma: no cover - exercised in tests
            status = "failed"
            error_text = str(exc)
            tb_text = traceback.format_exc()
        duration_ms = (time.perf_counter() - timer) * 1000
        finished_at = datetime.now(timezone.utc)

        return StepResult(
            step_index=step_index,
            step_name=step.name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(duration_ms, 3),
            assertions=step.assertions,
            error=error_text,
            traceback=tb_text,
        )

    def _execute_with_protocol(
        self,
        scenario: Scenario,
        step: ScenarioStep,
        payload: Any,
        context: dict[str, Any],
    ) -> ExecutionResult:
        protocol = (step.protocol or scenario.protocol or "").lower()
        if protocol in {"openapi", "rest", "http"}:
            return self._http_executor.execute(step, payload, context)
        raise NotImplementedError(f"Protocol '{step.protocol}' is not supported")

    @staticmethod
    def _validate_assertions(step: ScenarioStep, execution: ExecutionResult) -> None:
        for clause in step.assertions:
            if not isinstance(clause, str):
                continue
            text = clause.strip()
            if text.startswith("status =="):
                expected = int(text.split("==", 1)[1].strip())
                if execution.status_code != expected:
                    raise AssertionError(
                        f"Step '{step.name}' expected status {expected} but received {execution.status_code}"
                    )
                continue
            if text.startswith("response_time_ms <"):
                threshold = float(text.split("<", 1)[1].strip())
                if execution.elapsed_ms >= threshold:
                    raise AssertionError(
                        f"Step '{step.name}' exceeded response time threshold {threshold}ms"
                    )

    def _prepare_artifacts(self) -> RunArtifacts:
        run_dir = self.output_root / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return RunArtifacts(
            run_dir=run_dir,
            events_file=run_dir / "events.jsonl",
            summary_file=run_dir / "summary.json",
            junit_file=run_dir / "results.junit.xml",
        )

    def _build_summary(
        self,
        *,
        scenario: Scenario,
        scenario_start: datetime,
        scenario_end: datetime,
        step_results: list[StepResult],
        artifacts: RunArtifacts,
    ) -> ScenarioResult:
        failed = [result for result in step_results if result.status != "passed"]
        failures_payload = [
            {
                "step_name": result.step_name,
                "error": result.error,
                "traceback": result.traceback,
            }
            for result in failed
        ]
        duration_ms = (scenario_end - scenario_start).total_seconds() * 1000
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            service=scenario.service,
            version=scenario.version,
            protocol=scenario.protocol,
            run_id=self.run_id,
            started_at=scenario_start,
            finished_at=scenario_end,
            duration_ms=round(duration_ms, 3),
            total_steps=len(step_results),
            passed_steps=len(step_results) - len(failed),
            failed_steps=len(failed),
            failures=failures_payload,
            metadata=scenario.metadata,
            events_file=str(artifacts.events_file),
            summary_file=str(artifacts.summary_file),
            junit_file=str(artifacts.junit_file),
        )

    def _write_junit(self, step_results: list[StepResult], scenario: Scenario, junit_file: Path) -> None:
        suite = ET.Element(
            "testsuite",
            attrib=
            {
                "name": scenario.scenario_id,
                "tests": str(len(step_results)),
                "failures": str(len([r for r in step_results if r.status != "passed"])),
            },
        )
        for result in step_results:
            case = ET.SubElement(
                suite,
                "testcase",
                attrib={
                    "classname": scenario.service,
                    "name": result.step_name,
                    "time": str(result.duration_ms / 1000),
                },
            )
            if result.status != "passed":
                failure = ET.SubElement(
                    case,
                    "failure",
                    attrib={"message": result.error or "Step failed"},
                )
                failure.text = result.traceback or result.error or ""
        tree = ET.ElementTree(suite)
        tree.write(junit_file, encoding="utf-8", xml_declaration=True)


def _load_payload(bundle: Path, payload_ref: Any) -> tuple[Any, Path | None]:
    if not payload_ref:
        return None, None
    base_dir = bundle if bundle.is_dir() else bundle.parent
    payload_path = (base_dir / payload_ref).resolve()
    if not payload_path.exists():
        raise FileNotFoundError(f"Payload file not found: {payload_path}")
    text = payload_path.read_text(encoding="utf-8")
    if payload_path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        return yaml.safe_load(text), payload_path
    try:
        return json.loads(text), payload_path
    except json.JSONDecodeError:
        return text, payload_path


def _serialize_step_result(result: StepResult) -> dict[str, Any]:
    return {
        "step_index": result.step_index,
        "step_name": result.step_name,
        "status": result.status,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "duration_ms": result.duration_ms,
        "assertions": result.assertions,
        "error": result.error,
        "traceback": result.traceback,
    }
