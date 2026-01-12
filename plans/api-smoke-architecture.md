# API Smoke Test Platform Architecture

**Last Updated:** January 12, 2026  
**Version:** 2.0

## 1. Overview

A lightweight, contract-driven platform for generating smoke tests and mock servers from OpenAPI specifications. The platform emphasizes simplicity, modern tooling, and intelligent environment detection.

### Key Principles

- 🎯 **Zero Configuration** - Works out of the box with smart defaults
- 🚀 **Fast & Lightweight** - No heavy dependencies (NumPy, FAISS removed)
- 🎨 **Beautiful UX** - Rich terminal UI with automatic plain text fallback
- 🔧 **Modern Stack** - Python 3.12+, Ruff formatting, structured logging
- 📦 **Universal Pipeline** - Single script works with any OpenAPI spec

## 2. System Architecture

```
┌─────────────────┐
│  OpenAPI Spec   │
│  (YAML/JSON)    │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────────────────┐
│         Contract Parser (apps/contract-parser)       │
│  • Validates OpenAPI specification                   │
│  • Extracts operations, schemas, parameters          │
│  • Creates JSON-based keyword index                  │
│  • Generates normalized IR (Intermediate Repr.)      │
└────────┬────────────────────────────────────────────┘
         │
         ├──────────────────┬─────────────────────────┐
         v                  v                         v
┌──────────────────┐ ┌─────────────────┐  ┌─────────────────┐
│ Mock Config      │ │ Test Scenario   │  │ Search Index    │
│ Builder          │ │ Builder         │  │ (JSON)          │
│                  │ │                 │  │                 │
│ • Generates      │ │ • Creates test  │  │ • Keyword-based │
│   mock configs   │ │   scenarios     │  │   operation     │
│ • Response       │ │ • Request       │  │   search        │
│   templates      │ │   templates     │  │                 │
└────────┬─────────┘ └────────┬────────┘  └─────────────────┘
         │                    │
         v                    v
┌─────────────────┐  ┌─────────────────┐
│  Mock Server    │  │  Test Executor  │
│  (FastAPI)      │  │  (Typer+Rich)   │
│                 │  │                 │
│ • Serves mock   │  │ • Runs tests    │
│   responses     │  │ • Progress UI   │
│ • Structured    │  │ • Results       │
│   logging       │  │   artifacts     │
└─────────────────┘  └─────────────────┘
```

## 3. Core Components

### Contract Parser (`apps/contract-parser`)

**Purpose:** Parse OpenAPI specifications into normalized IR format with searchable index

**Key Features:**
- OpenAPI 3.0+ validation
- JSON-based keyword search (replaces FAISS/NumPy)
- Service/version auto-detection
- Operation metadata extraction

**Input:** OpenAPI YAML/JSON specifications  
**Output:** 
- `workspace/catalog/{service}/{version}.json` - Normalized IR
- `workspace/catalog/index.json` - Searchable operation index

**CLI:**
```bash
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --output-dir workspace/catalog
```

---

### Mock Config Builder (`apps/mock-config-builder`)

**Purpose:** Generate mock server configurations from IR

**Key Features:**
- Response template generation
- Port and host configuration
- YAML output format

**Input:** IR JSON from contract parser  
**Output:** `artifacts/mocks/{service}/{version}/mock-config.yaml`

**CLI:**
```bash
uv run python apps/mock-config-builder/mock_config_builder/main.py \
    --ir workspace/catalog/payments-api/1.0.0.json \
    --output-dir artifacts/mocks \
    --port rest=9101
```

---

### Test Scenario Builder (`apps/test-scenario-builder`)

**Purpose:** Generate test scenarios from operations

**Key Features:**
- Test case generation for each operation
- Request template creation
- Validation rule setup

**Input:** IR JSON from contract parser  
**Output:** `artifacts/tests/{service}/{version}/` - Test scenario bundle

**CLI:**
```bash
uv run python apps/test-scenario-builder/test_scenario_builder/main.py \
    --ir workspace/catalog/payments-api/1.0.0.json \
    --output-dir artifacts/tests \
    --scenario-prefix smoke
```

---

### Mock Server (`apps/mock-server`)

**Purpose:** FastAPI-based mock server runtime

**Key Features:**
- FastAPI web framework
- Structured logging with `structlog`
- Multiple log formats: console (rich), plain, json
- Auto-route registration from config

**Input:** Mock configuration YAML  
**Output:** Running HTTP server + structured logs

**CLI:**
```bash
uv run python apps/mock-server/mock_server/main.py \
    --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
```

---

### Test Executor (`apps/test-executor`)

**Purpose:** Execute smoke tests with beautiful console output

**Key Features:**
- Rich terminal UI with progress bars
- Smart environment detection (interactive vs CI/CD)
- Multiple output formats
- Timestamped result artifacts

**Input:** Test scenario bundle  
**Output:** 
- Console output (rich/plain/json)
- `runs/{scenario}-{timestamp}/results.json`

**CLI:**
```bash
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```

## 4. Tooling and Environment Strategy

### Dependency Management
- **uv**: Fast Python package manager (10-100× faster than pip)
- **dependency-groups.dev**: PEP 735 standard for development dependencies
- Direct Python invocation: `uv run python apps/{component}/main.py`

### Formatters & Linters
- **Ruff 0.9.0+**: All-in-one linter and formatter (10-100× faster than Black + Flake8)
  - `ruff format .` - Code formatting
  - `ruff check .` - Linting with auto-fix

### Output Control
- **CONSOLE_OUTPUT_FORMAT**: Unified output format control
  - `rich` - Beautiful terminal UI with colors and progress bars
  - `plain` - Simple text output (CI/CD friendly)
  - `json` - Structured JSON logs
  - `auto` - Smart detection (rich for interactive, plain for CI)

### Data Layout
- `workspace/catalog/`: IR JSON files + searchable index (JSON-based keyword search)
- `artifacts/mocks/`: Mock configurations per service/version
- `artifacts/tests/`: Test scenario bundles per service/version
- `runs/{service}-{version}-{timestamp}/`: Test results with timestamps

## 5. Reference Workflow

### Universal Pipeline (Recommended)

```powershell
# Complete pipeline for any OpenAPI spec
.\scripts\run-smoke-pipeline.ps1 -SpecPath "specs/payments.yaml"

# With custom parameters
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath "specs/commerce.yaml" `
    -MockPort 9200 `
    -OutputFormat rich `
    -Verbose
```

The universal pipeline automatically:
1. Parses OpenAPI spec → IR JSON + search index
2. Generates mock configuration → `artifacts/mocks/`
3. Generates test scenarios → `artifacts/tests/`
4. Starts mock server in background
5. Executes smoke tests → `runs/{scenario}-{timestamp}/`
6. Stops mock server

### Manual Step-by-Step

**1. Parse Contract**
```bash
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --output-dir workspace/catalog
```
→ Output: `workspace/catalog/payments-api/1.0.0.json` + `workspace/catalog/index.json`

**2. Generate Mock Config**
```bash
uv run python apps/mock-config-builder/mock_config_builder/main.py \
    --ir workspace/catalog/payments-api/1.0.0.json \
    --output-dir artifacts/mocks \
    --port rest=9101
```
→ Output: `artifacts/mocks/payments-api/1-0-0/mock-config.yaml`

**3. Generate Test Scenarios**
```bash
uv run python apps/test-scenario-builder/test_scenario_builder/main.py \
    --ir workspace/catalog/payments-api/1.0.0.json \
    --output-dir artifacts/tests \
    --scenario-prefix smoke
```
→ Output: `artifacts/tests/payments-api/1.0.0/` bundle

**4. Start Mock Server**
```bash
$env:CONSOLE_OUTPUT_FORMAT = "rich"
Start-Job -ScriptBlock {
    uv run python apps/mock-server/mock_server/main.py `
        --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml
}
```

**5. Run Smoke Tests**
```bash
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```
→ Output: `runs/smoke-payments-1-0-0-{timestamp}/results.json`

## 6. Configuration & Overrides

### Environment Variables

**CONSOLE_OUTPUT_FORMAT** - Controls console output across all components
- `rich` - Beautiful terminal UI (default for interactive)
- `plain` - Simple text output (CI/CD friendly)
- `json` - Structured JSON logs
- `auto` - Smart detection based on environment

**LOG_LEVEL** - Logging verbosity
- `DEBUG` - All messages including debug info
- `INFO` - Standard operational messages (default)
- `WARNING` - Warnings and errors only
- `ERROR` - Errors only

### Mock Server Configuration

YAML configuration per service/version in `artifacts/mocks/{service}/{version}/mock-config.yaml`:

```yaml
service: payments-api
version: 1.0.0
port: 9101
host: localhost
routes:
  - path: /payments
    method: POST
    response:
      status: 200
      body:
        paymentId: "mock-12345"
        status: "completed"
```

### Test Scenario Configuration

Test bundles in `artifacts/tests/{service}/{version}/`:
- `manifest.json` - Test metadata and configuration
- `test_{operation_id}.json` - Individual test cases with:
  - Request templates
  - Expected responses
  - Validation rules

### Runtime Overrides

Components support command-line overrides:
- `--port` - Override service port
- `--host` - Override bind address
- `--output-format` - Override output format
- `--log-level` - Override logging level

## 7. Concurrency and Scaling

### Process Isolation
- Each mock server binds to a unique port (configurable via `--port`)
- Test executor runs isolated per service/version with timestamped output directories
- No shared state between concurrent runs

### Parallel Execution
Components are designed for parallel execution:
- **Contract Parser**: Parse multiple specs simultaneously
- **Mock Servers**: Run multiple mock instances on different ports
- **Test Executor**: Execute tests in parallel (future enhancement)

### Output Organization
```
runs/
  smoke-payments-1-0-0-20260112-122906/    # Timestamped run
    results.json
    summary.txt
  smoke-commerce-1-1-0-20260112-123015/
    results.json
    summary.txt
```

### Resource Management
- Mock servers run in background PowerShell jobs
- Clean shutdown via `Stop-Job` or pipeline script cleanup
- Structured logging prevents log interleaving with request IDs

---

## 8. CI/CD Integration

### GitHub Actions Example

```yaml
name: Smoke Tests

on: [push, pull_request]

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Run Payments Smoke Tests
        env:
          CONSOLE_OUTPUT_FORMAT: plain
        run: |
          ./scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
      
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-test-results
          path: runs/
```

### GitLab CI Example

```yaml
smoke-tests:
  image: python:3.12
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
  script:
    - export CONSOLE_OUTPUT_FORMAT=plain
    - pwsh scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
  artifacts:
    when: always
    paths:
      - runs/
```

### CI Best Practices
1. **Use `plain` or `json` output format**: `CONSOLE_OUTPUT_FORMAT=plain`
2. **Always upload artifacts**: Test results in `runs/` directory
3. **Cache dependencies**: Cache `.venv/` or use uv's cache
4. **Parallel execution**: Run different specs in parallel jobs

---

## 9. Quality & Observability

### Structured Logging
All components use `structlog` with consistent format:
```json
{
  "event": "request_received",
  "timestamp": "2026-01-12T12:29:06.123456Z",
  "request_id": "req-abc123",
  "method": "POST",
  "path": "/payments",
  "level": "info"
}
```

### Test Result Artifacts
```json
{
  "summary": {
    "total": 10,
    "passed": 9,
    "failed": 1,
    "duration_seconds": 2.34
  },
  "tests": [
    {
      "name": "POST /payments",
      "status": "passed",
      "duration": 0.123,
      "request": {...},
      "response": {...}
    }
  ]
}
```

### Quality Gates
- **Ruff linting**: `ruff check .` enforces code quality
- **Ruff formatting**: `ruff format --check .` verifies formatting
- **Type checking**: Static types with Pydantic models
- **Test validation**: Schema validation for all API interactions

---

## 10. Future Enhancements

### Planned Features
1. **GraphQL Support**: Extend parser to handle GraphQL schemas
2. **gRPC Mocking**: Protocol buffer support for gRPC services
3. **Performance Testing**: Load testing capabilities in test executor
4. **Contract Testing**: Consumer-driven contract testing support
5. **Web Dashboard**: Streamlit/FastAPI UI for visualizing test results

### Architecture Evolution
- **Plugin System**: Extensible architecture for custom validators
- **Database Mocking**: Support for database interaction mocking
- **Cloud Integration**: Azure/AWS service mocking capabilities
- **Advanced Scenarios**: Complex multi-step test flows with state management
