# Legacy API-First Smoke & Mock Plan (Historical Reference)

> This document captures the pre-Hatch approach so we can explain why the workspace moved to a pure Python toolchain. The information is meant for forensic reference only and should not be replicated.

## 1. Historical Goals

- Convert REST/SOAP/gRPC contracts into executable smoke suites and configurable mocks.
- Share normalized contract metadata, payload fixtures, and telemetry between multiple Python CLIs.
- Allow DevOps teams to invoke the same commands on Windows, Linux, and ephemeral CI workers.

## 2. Main Components (Legacy)

| Component | Purpose | Notes |
|-----------|---------|-------|
| `contract-parser` | Parsed OpenAPI/WSDL/Proto sources into an intermediate representation and JSON index. | Relied on shared libs under `libs/contract_ir` and `workspace/catalog/`. |
| `mock-config-builder` | Produced deterministic payload templates and scenario manifests. | Could attach prompts for AI-assisted fixture generation. |
| `mock-server` | Hosted REST/SOAP/gRPC mocks with HEAD/OPTIONS support and latency injection. | Exposed telemetry for every endpoint hit. |
| `test-executor` | Orchestrated regression/smoke suites, persisted junit + events. | Supported multi-scenario matrices. |
| `test-scenario-builder` | Created pytest features & Postman collections from catalog metadata. | Ensured parity between manual and automated runs. |

## 3. Tooling Stack (Legacy)

- A JavaScript-based orchestrator managed Python projects, cached virtual environments, and wired CLI commands into CI targets.
- Deterministic environments were achieved by wrapping each command with `uv run` or `hatch run`, but execution still depended on Node tooling being present.
- Project configuration files declared targets for lint (`ruff`, `black`), typing (`mypy --strict`), unit tests (`pytest`), and runtime CLIs. Parallelism, caching, and matrix definitions were driven by the orchestrator.

## 4. Limitations Observed

1. **Mandatory Node toolchain**: every contributor had to install Node.js plus the orchestration CLI before running any smoke workflow.
2. **Split mental model**: CLIs themselves were pure Python, yet developers had to remember both Node-based target names and Hatch equivalents.
3. **Caching friction**: cached `.venv` directories were nested under tooling-specific folders, which complicated CI storage policies.
4. **Documentation drift**: commands were documented twice—once for the orchestrator and once for Python—leading to skewed instructions.
5. **Cold-start cost**: Windows agents did extra work to bootstrap Node, download packages, and restore caches before running a single Python command.

## 5. Decommissioning Notes

- The workspace now uses Hatch exclusively; `pyproject.toml` scripts map one-to-one with every CLI and quality gate.
- Hatch environments live under `.hatch/`, making cache sharing simple across developers and CI.
- Removing the Node dependency reduced onboarding time and eliminated duplicated documentation.
- Legacy configuration files were archived/removed, but the historical behavior remains reproducible by following current Hatch scripts.

Consult [../api-smoke-architecture.md](../api-smoke-architecture.md) for the canonical, Hatch-only plan.




