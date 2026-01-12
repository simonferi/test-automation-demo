# API Smoke Test Platform

Contract-driven platform for generating smoke tests and mock servers from OpenAPI specifications with intelligent environment detection and beautiful console output.

## ✨ Key Features

- 🎯 **Universal Pipeline** - Single script works with any OpenAPI spec
- 🤖 **Auto-Detection** - Automatically extracts service info from specs
- 🎨 **Beautiful Output** - Rich terminal UI with progress bars and tables
- 🚀 **Fast & Lightweight** - No NumPy/FAISS, pure Python with JSON indexing
- 🔧 **Modern Stack** - Python 3.12+, Ruff formatting, structured logging
- 📦 **Zero Config** - Smart defaults, works out of the box

## 🚀 Quickstart

```powershell
# Install dependencies
uv sync

# Run complete pipeline for any OpenAPI spec (auto-detects everything!)
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml

# Or with rich colored output
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/commerce.yaml -OutputFormat rich

# Multiple services on different ports
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -RestPort 9101
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/flights.yaml -RestPort 9103
```

**Results:** Check `runs/` directory for timestamped test results with summary reports.

## Architecture

See [`plans/api-smoke-architecture.md`](plans/api-smoke-architecture.md) for detailed design.

## 📁 Project Structure

```
test-automation-demo/
├── apps/                              # Application modules
│   ├── contract-parser/               # OpenAPI spec parser → JSON IR
│   │   └── contract_parser/
│   │       ├── main.py                # CLI entrypoint
│   │       ├── indexer.py             # JSON-based search indexer
│   │       ├── normalizers.py         # OpenAPI normalization
│   │       └── models.py              # IR data models
│   ├── test-scenario-builder/         # Test scenario generator
│   │   └── test_scenario_builder/
│   │       ├── main.py                # CLI entrypoint
│   │       └── generator.py           # Scenario generation logic
│   ├── mock-config-builder/           # Mock configuration generator
│   │   └── mock_config_builder/
│   │       ├── main.py                # CLI entrypoint
│   │       └── builder.py             # Config generation
│   ├── test-executor/                 # Smoke test executor
│   │   └── test_executor/
│   │       ├── main.py                # CLI entrypoint
│   │       ├── runner.py              # Test execution engine
│   │       ├── console_reporter.py    # Rich terminal output
│   │       └── output_config.py       # Output format configuration
│   └── mock-server/                   # Mock server runtime
│       └── mock_server/
│           ├── main.py                # CLI entrypoint
│           ├── server.py              # FastAPI server
│           ├── logging_utils.py       # Structured logging
│           └── output_config.py       # Output format configuration
├── specs/                             # OpenAPI specifications
│   ├── payments.yaml                  # Payments API 1.0.0
│   ├── commerce.yaml                  # Commerce Operations API 1.1.0
│   └── flights.yaml                   # Flight Booking API 2.3.0
├── workspace/                         # Generated artifacts (parsed contracts)
│   └── catalog/                       # JSON IR snapshots + search index
│       ├── index.json                 # Searchable operations index
│       └── {service-slug}/
│           └── {version}.json         # Normalized IR
├── artifacts/                         # Generated test/mock assets
│   ├── tests/{service}/{version}/     # Test scenario bundles
│   └── mocks/{service}/{version}/     # Mock configurations
├── runs/                              # Test execution results (timestamped)
│   └── smoke-{service}-{version}-{timestamp}/
│       ├── scenario.json              # Executed scenario
│       └── results.json               # Test results
├── scripts/                           # Automation scripts
│   ├── run-smoke-pipeline.ps1         # 🚀 Universal pipeline script
│   ├── payments-smoke-e2e.ps1         # Legacy payments-specific script
│   └── README.md                      # Scripts documentation
├── plans/                             # Architecture & design docs
└── pyproject.toml                     # Python dependencies & configuration
```

## 🛠️ Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.12+ | Core platform language |
| **Package Manager** | uv | latest | Fast Python package management |
| **Dependency Groups** | PEP 735 | - | Modern dependency management |
| **Code Formatter** | Ruff | 0.9.0+ | 10-100× faster than Black |
| **Linter** | Ruff | 0.9.0+ | Comprehensive linting |
| **Type Checker** | mypy | 1.14.0+ | Strict type checking |
| **Testing** | pytest | 8.4.0+ | Unit & integration tests |
| **CLI Framework** | Typer | 0.15.0+ | Beautiful command-line interfaces |
| **Data Validation** | Pydantic | 2.10.0+ | Runtime type validation |
| **Config Format** | YAML | 6.0.2+ | Human-readable configuration |
| **Logging** | structlog | 24.4.0+ | Structured logging with context |
| **Terminal UI** | Rich | 13.9.0+ | Progress bars, tables, colors |
| **Web Framework** | FastAPI | - | Mock server runtime |

### Key Design Decisions

✅ **No NumPy/FAISS** - Replaced vector-based indexing with simple JSON keyword search  
✅ **No Black** - Using `ruff format` which is 10-100× faster and compatible  
✅ **Python 3.12+** - Modern features and improved performance  
✅ **Unified Output Control** - `CONSOLE_OUTPUT_FORMAT` environment variable  
✅ **Smart Environment Detection** - Auto-detects terminal capabilities and CI/CD

## 🎯 Getting Started

### Prerequisites

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **uv** package manager ([Install](https://docs.astral.sh/uv/getting-started/installation/))
- **PowerShell 5.1+** (Windows) or **PowerShell Core 7+** (cross-platform)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd test-automation-demo

# Install dependencies (creates virtual environment automatically)
uv sync
```

### Quick Start

#### 1. Run Universal Pipeline (Recommended)

```powershell
# Auto-detect service info from any OpenAPI spec
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml

# With custom port and rich output
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/commerce.yaml `
    -RestPort 9102 `
    -OutputFormat rich
```

**See [scripts/README.md](scripts/README.md) for complete documentation.**

#### 2. Manual Step-by-Step

```powershell
# Step 1: Parse OpenAPI spec
uv run python apps/contract-parser/contract_parser/main.py `
    --spec specs/payments.yaml `
    --output-dir workspace/catalog

# Step 2: Generate mock configuration
uv run python apps/mock-config-builder/mock_config_builder/main.py `
    --ir workspace/catalog/payments-api/1.0.0.json `
    --output-dir artifacts/mocks `
    --format yaml `
    --port rest=9101

# Step 3: Generate test scenarios
uv run python apps/test-scenario-builder/test_scenario_builder/main.py `
    --ir workspace/catalog/payments-api/1.0.0.json `
    --output-dir artifacts/tests `
    --scenario-prefix smoke `
    --tag payments

# Step 4: Start mock server (in separate terminal)
uv run python apps/mock-server/mock_server/main.py `
    --config artifacts/mocks/payments-api/1-0-0/mock-config.yaml

# Step 5: Run smoke tests
$env:SMOKE_RUNTIME_BASE_URL = "http://127.0.0.1:9101"
uv run python apps/test-executor/test_executor/main.py `
    --bundle artifacts/tests/payments-api/1.0.0 `
    --output-dir runs
```

## 🎨 Output Formats

The platform supports multiple output formats controlled via the `CONSOLE_OUTPUT_FORMAT` environment variable:

| Format | Description | Use Case |
|--------|-------------|----------|
| `auto` | Smart detection (rich for interactive, plain for CI/CD) | **Default** - works everywhere |
| `rich` | Colored output with progress bars and tables | Development, manual testing |
| `plain` | Plain text without colors | CI/CD pipelines, logs |
| `json` | Structured JSON output | Machine parsing, automation |

### Examples

```powershell
# Rich format (beautiful UI)
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat rich

# Plain format (CI/CD)
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat plain

# Or via environment variable
$env:CONSOLE_OUTPUT_FORMAT = "rich"
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

### Rich Format Output

```
  Running smoke-payments-api-1-0-0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Step         ┃ Endpoint                                 ┃ Status     ┃     Duration ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Step 1       │ GET /payments                            │ ✓ PASS     │        112ms │
│ Step 2       │ POST /payments                           │ ✓ PASS     │         78ms │
└──────────────┴──────────────────────────────────────────┴────────────┴──────────────┘

╭──────────────────────────────────────────────── ✓ ALL TESTS PASSED ─────────────────────────────────────────────────╮
│ Total: 8  Passed: 8  Failed: 0  Duration: 568ms                                                                     │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Plain Format Output

```
Running test scenario: smoke-payments-api-1-0-0
Total steps: 8
--------------------------------------------------------------------------------
[1] GET /payments ... ✓ PASS (112ms)
[2] POST /payments ... ✓ PASS (78ms)
--------------------------------------------------------------------------------
Total: 8 | Passed: 8 | Failed: 0 | Duration: 568ms
✓ ALL TESTS PASSED
```

## 📊 Sample Specifications & Results

| Service | Version | Spec | Operations | Latest Results |
|---------|---------|------|------------|----------------|
| **Payments API** | 1.0.0 | [payments.yaml](specs/payments.yaml) | 8 | ✅ All passed |
| **Commerce Operations API** | 1.1.0 | [commerce.yaml](specs/commerce.yaml) | 24 | ✅ All passed |
| **Flight Booking API** | 2.3.0 | [flights.yaml](specs/flights.yaml) | 16 | ✅ All passed |

### Test Coverage by Service

- **Payments**: GET/POST payments, refunds, payouts, reports
- **Commerce**: Orders, shipments, inventory, returns (with OPTIONS/HEAD/PUT/DELETE)
- **Flights**: Search, offers, reservations, passengers, tickets, check-in

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONSOLE_OUTPUT_FORMAT` | Output format: `auto`, `rich`, `plain`, `json` | `auto` |
| `SMOKE_RUNTIME_BASE_URL` | Base URL for test execution | `http://127.0.0.1:9101` |
| `SMOKE_RUNTIME_TIMEOUT` | Request timeout in seconds | `10` |
| `PYTHONPATH` | Python module search path | Auto-configured by scripts |

## 📚 Documentation

- **[Scripts README](scripts/README.md)** - Complete guide to pipeline scripts
- **[Architecture](plans/api-smoke-architecture.md)** - System design and architecture
- **Contract Parser** - See [apps/contract-parser/](apps/contract-parser/)
- **Test Executor** - See [apps/test-executor/](apps/test-executor/)
- **Mock Server** - See [apps/mock-server/](apps/mock-server/)

## 🧪 Development

### Running Tests

```powershell
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=apps --cov-report=html

# Run specific test file
uv run pytest apps/contract-parser/tests/test_indexer.py
```

### Code Quality

```powershell
# Format code
uv run ruff format apps/

# Lint code
uv run ruff check apps/

# Type check
uv run mypy apps/contract-parser apps/test-executor apps/mock-server
```

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Smoke Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv sync
      - run: .\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat plain
```

### GitLab CI Example

```yaml
smoke-tests:
  image: python:3.12
  script:
    - pip install uv
    - uv sync
    - pwsh scripts/run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat plain
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`uv run pytest && uv run ruff check apps/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

MIT

---

**Last Updated:** January 12, 2026  
**Python Version:** 3.12+  
**Platform:** Cross-platform (Windows, macOS, Linux)
- `SMOKE_RUNTIME_LOG_LEVEL`  optional verbosity override for `test-executor`.

These variables work across Windows PowerShell, Bash, CI pipelines, and the orchestration script above.

## Documentation Map

- [API architecture](plans/api-smoke-architecture.md)
- [Local workflow (Hatch + distributable CLIs)](plans/api-smoke-local.md)
- [Payments reference scenario](plans/payments-smoke-runtime-scenario.md)
- [Mock-only quickstart](plans/api-first-rest-mock-workflow-example.md)
- [Smoke runtime environment overview](plans/smoke-runtime-environment.md)
