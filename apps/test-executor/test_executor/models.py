"""Scenario and runtime models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScenarioStep(BaseModel):
    """Single executable step inside the scenario."""

    name: str
    description: Optional[str] = None
    protocol: str
    request: dict[str, Any]
    assertions: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class Scenario(BaseModel):
    """Editable scenario emitted by the generator CLI."""

    scenario_id: str
    service: str
    version: str
    protocol: str
    generated_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[ScenarioStep] = Field(default_factory=list)


class StepResult(BaseModel):
    """Runtime result for one step."""

    step_index: int
    step_name: str
    status: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    assertions: list[str]
    error: Optional[str] = None
    traceback: Optional[str] = None


class ScenarioResult(BaseModel):
    """Aggregated runtime summary."""

    scenario_id: str
    service: str
    version: str
    protocol: str
    run_id: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    total_steps: int
    passed_steps: int
    failed_steps: int
    failures: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    events_file: str
    summary_file: str
    junit_file: str
