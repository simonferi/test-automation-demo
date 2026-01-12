# Test Executor

Executes smoke test scenarios with beautiful console output and intelligent environment detection.

## Overview

The test executor runs generated test scenarios against REST APIs, providing real-time progress feedback with rich terminal UI or plain text output suitable for CI/CD environments.

## Features

- ✅ Rich terminal UI with progress bars and tables
- ✅ Smart environment detection (interactive vs CI/CD)
- ✅ Multiple output formats: auto, rich, plain, json
- ✅ HTTP request execution with validation
- ✅ Timestamped result artifacts
- ✅ Summary reports with pass/fail statistics

## Usage

### Command Line

```powershell
# Basic usage
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs

# With output format control
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs

# Override base URL
$env:SMOKE_RUNTIME_BASE_URL = "http://localhost:8080"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```

### Via Scripts

```powershell
# Automatic via universal pipeline
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -OutputFormat rich
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--bundle` | Yes | - | Path to test scenario bundle directory |
| `--output-dir` | No | `runs` | Directory for test results |
| `--output-format` | No | `auto` | Output format: `auto`, `rich`, `plain`, `json` |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONSOLE_OUTPUT_FORMAT` | Controls output format globally | `auto` |
| `SMOKE_RUNTIME_BASE_URL` | Base URL for API requests | `http://127.0.0.1:9101` |
| `SMOKE_RUNTIME_TIMEOUT` | Request timeout in seconds | `10` |

## Output Formats

### Auto (Default)

Smart detection:
- **Interactive terminal**: Uses `rich` format with colors and progress bars
- **CI/CD environment**: Uses `plain` format without colors

Detection checks:
- `sys.stdout.isatty()` - Is stdout a terminal?
- CI environment variables: `CI`, `JENKINS_HOME`, `GITLAB_CI`, `GITHUB_ACTIONS`, `TRAVIS`

### Rich Format

Beautiful colored output with progress indicators:

```
  Running smoke-payments-api-1-0-0 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Step         ┃ Endpoint                                 ┃ Status     ┃     Duration ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Step 1       │ GET /payments                            │ ✓ PASS     │        112ms │
│ Step 2       │ POST /payments                           │ ✓ PASS     │         78ms │
└──────────────┴──────────────────────────────────────────┴────────────┴──────────────┘

╭────────────────────────────────────────────── ✓ ALL TESTS PASSED ───────────────────────────────────────────────────╮
│ Total: 8  Passed: 8  Failed: 0  Duration: 568ms                                                                     │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Plain Format

Simple text output for CI/CD:

```
Running test scenario: smoke-payments-api-1-0-0
Total steps: 8
--------------------------------------------------------------------------------
[1] GET /payments ... ✓ PASS (112ms)
[2] POST /payments ... ✓ PASS (78ms)
[3] GET /payments/{paymentId} ... ✓ PASS (76ms)
[4] PATCH /payments/{paymentId} ... ✓ PASS (53ms)
[5] POST /payments/{paymentId}/refunds ... ✓ PASS (69ms)
[6] GET /customers/{customerId}/payments ... ✓ PASS (53ms)
[7] POST /payouts ... ✓ PASS (52ms)
[8] GET /reports/daily ... ✓ PASS (63ms)
--------------------------------------------------------------------------------
Total: 8 | Passed: 8 | Failed: 0 | Duration: 568ms
✓ ALL TESTS PASSED
```

### JSON Format

Structured output for automation:

```json
{
  "scenario_id": "smoke-payments-api-1-0-0",
  "total": 8,
  "passed": 8,
  "failed": 0,
  "duration_ms": 568,
  "steps": [
    {
      "step": 1,
      "endpoint": "GET /payments",
      "status": "PASS",
      "duration_ms": 112
    }
  ]
}
```

## Output Artifacts

### Directory Structure

```
runs/
└── smoke-payments-api-1-0-0-20260112-122906/
    ├── scenario.json       # Test scenario metadata
    └── results.json        # Execution results
```

### Results Format

```json
{
  "scenario_name": "smoke-payments-api-1-0-0",
  "timestamp": "2026-01-12T12:29:06.123456",
  "total_steps": 8,
  "passed": 8,
  "failed": 0,
  "duration_ms": 568,
  "base_url": "http://127.0.0.1:9101",
  "steps": [
    {
      "step_number": 1,
      "method": "GET",
      "path": "/payments",
      "status_code": 200,
      "duration_ms": 112,
      "result": "PASS"
    }
  ]
}
```

## Architecture

### Key Components

1. **ConsoleReporter** (`console_reporter.py`)
   - Environment detection
   - Rich terminal UI rendering
   - Progress tracking
   - Result formatting

2. **ScenarioRunner** (`runner.py`)
   - Test execution engine
   - HTTP request handling
   - Result aggregation
   - Reporter integration

3. **OutputConfig** (`output_config.py`)
   - Format configuration
   - Priority handling (CLI > ENV > default)
   - Shared across applications

### Implementation Details

```python
class ConsoleReporter:
    def __init__(self, output_format: OutputFormat):
        self.format = output_format
        self._detect_environment()  # Auto-detect if format is 'auto'
    
    def start_test_suite(self, scenario_name, total_steps):
        if self.format == OutputFormat.RICH:
            # Create progress bar and table
        else:
            # Simple text output
    
    def report_step_result(self, step_num, endpoint, status, duration_ms):
        if self.format == OutputFormat.RICH:
            # Update table row
        else:
            # Print line
```

### Environment Detection

```python
def _detect_environment(self) -> bool:
    """Returns True if interactive terminal"""
    # Check if stdout is a terminal
    if not sys.stdout.isatty():
        return False
    
    # Check for CI environment
    ci_indicators = ['CI', 'JENKINS_HOME', 'GITLAB_CI', 'GITHUB_ACTIONS', 'TRAVIS']
    if any(os.getenv(var) for var in ci_indicators):
        return False
    
    return True
```

## Examples

### Development (Rich Output)

```powershell
$env:CONSOLE_OUTPUT_FORMAT = "rich"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```

### CI/CD (Plain Output)

```powershell
$env:CONSOLE_OUTPUT_FORMAT = "plain"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```

### Custom Base URL

```powershell
$env:SMOKE_RUNTIME_BASE_URL = "https://api.staging.example.com"
$env:CONSOLE_OUTPUT_FORMAT = "plain"
uv run python apps/test-executor/test_executor/main.py \
    --bundle artifacts/tests/payments-api/1.0.0 \
    --output-dir runs
```

## Testing

```powershell
# Run tests
uv run pytest apps/test-executor/tests/

# With coverage
uv run pytest apps/test-executor/tests/ --cov=test_executor
```

## Dependencies

- `typer>=0.15.0` - CLI framework
- `rich>=13.9.0` - Terminal UI
- `pydantic>=2.10.0` - Data validation
- `structlog>=24.4.0` - Structured logging

## See Also

- [Main README](../../README.md)
- [Scripts Documentation](../../scripts/README.md)
- [Mock Server](../mock-server/)
- [Test Scenario Builder](../test-scenario-builder/)
