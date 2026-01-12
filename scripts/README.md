# Smoke Test Pipeline Scripts

This directory contains multi-platform scripts for running end-to-end smoke test pipelines on Windows, Linux, macOS, and CI/CD environments.

## 📋 Table of Contents

- [Platform Support](#platform-support)
- [Quick Start](#quick-start)
- [Universal Pipeline Script](#universal-pipeline-script)
- [Platform-Specific Usage](#platform-specific-usage)
- [CI/CD Integration](#cicd-integration)
- [Parameters](#parameters)
- [Examples](#examples)
- [Prerequisites](#prerequisites)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## 🌍 Platform Support

The smoke test pipeline is available in three formats to support all platforms:

| Script | Platform | Best For |
|--------|----------|----------|
| `run-smoke-pipeline.ps1` | Windows PowerShell | Windows developers, Windows CI/CD |
| `run-smoke-pipeline.sh` | Bash (Linux/macOS) | Unix-based systems, Docker containers |
| `run-smoke-pipeline.py` | Python (Universal) | Cross-platform, any OS with Python 3.12+ |

**All scripts provide identical functionality and command-line options.**

---

## 🚀 Quick Start

### Windows

```powershell
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

### Linux/macOS

```bash
# Make executable (first time only)
chmod +x scripts/run-smoke-pipeline.sh

# Run
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml
```

### Universal (Python)

```bash
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml
```

---

## 🔄 Universal Pipeline Script

### Overview

A universal script that can run the complete smoke test pipeline for **any OpenAPI specification**. It automatically detects service information and orchestrates the entire workflow.

### Features

✨ **Automatic Detection**
- Service name (from `info.title`)
- Service version (from `info.version`)
- Auto-generated scenario tags
- Smart defaults for all parameters

🎯 **Full Pipeline Execution**
1. **Contract Parser** - Parses OpenAPI spec into IR (Intermediate Representation)
2. **Mock Config Builder** - Generates mock server configuration
3. **Test Scenario Builder** - Creates test scenarios from operations
4. **Mock Server** - Starts mock server in background
5. **Test Executor** - Runs smoke tests against mock server

🎨 **Output Formats**
- `auto` - Smart detection (rich for interactive, plain for CI/CD)
- `rich` - Beautiful colored output with progress bars
- `plain` - Plain text for CI/CD pipelines
- `json` - Machine-readable structured output

---

## 💻 Platform-Specific Usage

### Windows (PowerShell)

```powershell
# Basic usage
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml

# With options
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/payments.yaml `
    -RestPort 9101 `
    -OutputFormat rich `
    -KeepMockRuntime
```

### Linux/macOS (Bash)

```bash
# Make script executable (first time only)
chmod +x scripts/run-smoke-pipeline.sh

# Basic usage
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml

# With options
./scripts/run-smoke-pipeline.sh \
    --spec specs/payments.yaml \
    --port 9101 \
    --output-format rich \
    --keep-mock
```

### Universal (Python)

```bash
# Works on any platform with Python 3.12+
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml

# With options
python scripts/run-smoke-pipeline.py \
    --spec specs/payments.yaml \
    --port 9101 \
    --output-format rich \
    --keep-mock
```

---

## 🔄 CI/CD Integration

### GitHub Actions

See [`.github/workflows/smoke-tests.yml`](../.github/workflows/smoke-tests.yml) for a complete example.

```yaml
- name: Run smoke tests
  run: |
    python scripts/run-smoke-pipeline.py \
      --spec specs/payments.yaml \
      --output-format json
```

### GitLab CI/CD

See [`.gitlab-ci.yml`](../.gitlab-ci.yml) for a complete example.

```yaml
payments-smoke-test:
  script:
    - python scripts/run-smoke-pipeline.py --spec specs/payments.yaml --output-format json
```

### Jenkins

See [`Jenkinsfile`](../Jenkinsfile) for complete examples (single and parallel execution).

```groovy
sh """
    python scripts/run-smoke-pipeline.py \
        --spec ${params.SPEC_FILE} \
        --output-format json
"""
```

---

## 📋 Parameters

### PowerShell Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `-SpecPath` | `string` | ✅ Yes | Path to OpenAPI specification file |
| `-Service` | `string` | ❌ No | Service name (auto-detected from spec) |
| `-Version` | `string` | ❌ No | Service version (auto-detected from spec) |
| `-RestPort` | `string` | ❌ No | REST API port (default: 9101) |
| `-ScenarioPrefix` | `string` | ❌ No | Scenario prefix (default: smoke) |
| `-ScenarioTags` | `string[]` | ❌ No | Scenario tags (auto-detected from service name) |
| `-SmokeBaseUrl` | `string` | ❌ No | Base URL (default: http://127.0.0.1:{port}) |
| `-OutputFormat` | `string` | ❌ No | Output format: auto/rich/plain/json (default: auto) |
| `-KeepMockRuntime` | `switch` | ❌ No | Keep mock server running after tests |
| `-SkipParsing` | `switch` | ❌ No | Skip contract parsing |
| `-SkipMockConfig` | `switch` | ❌ No | Skip mock config generation |
| `-SkipTestGeneration` | `switch` | ❌ No | Skip test scenario generation |

### Bash/Python Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--spec` | `string` | ✅ Yes | Path to OpenAPI specification file |
| `--service` | `string` | ❌ No | Service name (auto-detected from spec) |
| `--version` | `string` | ❌ No | Service version (auto-detected from spec) |
| `--port` | `string` | ❌ No | REST API port (default: 9101) |
| `--prefix` | `string` | ❌ No | Scenario prefix (default: smoke) |
| `--tag` | `string` | ❌ No | Scenario tag (can be specified multiple times) |
| `--base-url` | `string` | ❌ No | Base URL (default: http://127.0.0.1:{port}) |
| `--output-format` | `string` | ❌ No | Output format: auto/rich/plain/json (default: auto) |
| `--keep-mock` | `flag` | ❌ No | Keep mock server running after tests |
| `--skip-parsing` | `flag` | ❌ No | Skip contract parsing |
| `--skip-mock-config` | `flag` | ❌ No | Skip mock config generation |
| `--skip-test-generation` | `flag` | ❌ No | Skip test scenario generation |

---

## 📚 Examples

### Basic Usage (All Platforms)

**PowerShell:**
```powershell
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml
```

**Output:**
```
Auto-detected service name: Payments API
Auto-detected version: 1.0.0
Using base URL: http://127.0.0.1:9101
Using scenario tags: payments

=== Smoke Test Pipeline ===
Service:     Payments API
Version:     1.0.0
Spec:        specs/payments.yaml
Port:        9101
Output:      auto
===========================
```

### Custom Port and Output Format

**PowerShell:**
```powershell
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/commerce.yaml `
    -RestPort 9102 `
    -OutputFormat rich
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh \
    --spec specs/commerce.yaml \
    --port 9102 \
    --output-format rich
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py \
    --spec specs/commerce.yaml \
    --port 9102 \
    --output-format rich
```

### Multiple Services Simultaneously

**PowerShell:**
```powershell
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml -RestPort 9101
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/commerce.yaml -RestPort 9102
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/flights.yaml -RestPort 9103
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --port 9101 &
./scripts/run-smoke-pipeline.sh --spec specs/commerce.yaml --port 9102 &
./scripts/run-smoke-pipeline.sh --spec specs/flights.yaml --port 9103 &
wait
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml --port 9101 &
python scripts/run-smoke-pipeline.py --spec specs/commerce.yaml --port 9102 &
python scripts/run-smoke-pipeline.py --spec specs/flights.yaml --port 9103 &
wait
```

### Development Workflow (Keep Mock Running)

**PowerShell:**
```powershell
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/payments.yaml `
    -KeepMockRuntime

# Later, stop the mock server
Get-Job | Stop-Job
Get-Job | Remove-Job
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh \
    --spec specs/payments.yaml \
    --keep-mock

# Later, stop the mock server
# (PID will be displayed at the end)
kill <PID>
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py \
    --spec specs/payments.yaml \
    --keep-mock

# Later, stop the mock server
# (PID will be displayed at the end)
kill <PID>
```

### Iterative Development (Skip Stages)

**PowerShell:**
```powershell
# First run - full pipeline
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml

# Subsequent runs - skip parsing if spec unchanged
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/payments.yaml `
    -SkipParsing

# Only regenerate tests (skip parsing and mock config)
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/payments.yaml `
    -SkipParsing `
    -SkipMockConfig
```

**Bash:**
```bash
# First run - full pipeline
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml

# Subsequent runs - skip parsing if spec unchanged
./scripts/run-smoke-pipeline.sh \
    --spec specs/payments.yaml \
    --skip-parsing

# Only regenerate tests
./scripts/run-smoke-pipeline.sh \
    --spec specs/payments.yaml \
    --skip-parsing \
    --skip-mock-config
```

**Python:**
```bash
# First run - full pipeline
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml

# Subsequent runs - skip parsing if spec unchanged
python scripts/run-smoke-pipeline.py \
    --spec specs/payments.yaml \
    --skip-parsing

# Only regenerate tests
python scripts/run-smoke-pipeline.py \
    --spec specs/payments.yaml \
    --skip-parsing \
    --skip-mock-config
```

### Override Auto-Detection

**PowerShell:**
```powershell
.\scripts\run-smoke-pipeline.ps1 `
    -SpecPath specs/my-api.yaml `
    -Service "My Custom API" `
    -Version "3.0.0" `
    -ScenarioTags @("custom", "api", "v3") `
    -RestPort 8080
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh \
    --spec specs/my-api.yaml \
    --service "My Custom API" \
    --version "3.0.0" \
    --tag custom --tag api --tag v3 \
    --port 8080
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py \
    --spec specs/my-api.yaml \
    --service "My Custom API" \
    --version "3.0.0" \
    --tag custom --tag api --tag v3 \
    --port 8080
```

---

## 🔧 Prerequisites

### Required Software

| Software | Version | Platform | Installation |
|----------|---------|----------|--------------|
| Python | 3.12+ | All | [python.org](https://python.org) |
| uv | Latest | All | `pip install uv` or [astral.sh/uv](https://astral.sh/uv) |
| PowerShell | 5.1+ | Windows | Pre-installed |
| Bash | 4.0+ | Linux/macOS | Pre-installed |

### Installation

**All Platforms:**
```bash
# Install uv (if not already installed)
pip install uv

# Install project dependencies
cd test-automation-demo
uv sync
```

**Linux/macOS (Bash script setup):**
```bash
# Make Bash script executable
chmod +x scripts/run-smoke-pipeline.sh
```

### Environment Setup

The scripts automatically configure the following environment variables:
- `PYTHONPATH` - Adds all application modules to Python path
- `CONSOLE_OUTPUT_FORMAT` - Controls output formatting
- `SMOKE_RUNTIME_BASE_URL` - Sets base URL for tests

---

## 📊 Output Formats

### Rich Format

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

### Plain Format

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

### JSON Format

```json
{
  "summary": {
    "status": "passed",
    "total_scenarios": 8,
    "passed_scenarios": 8,
    "failed_scenarios": 0,
    "duration": 0.568
  },
  "scenarios": [
    {
      "name": "smoke-get-payments",
      "status": "passed",
      "duration": 0.112,
      "endpoint": "GET /payments"
    }
  ]
}
```

### Result Artifacts

After each run, results are saved in `runs/` directory:

```
runs/
└── smoke-payments-api-1-0-0-20260112-122906/
    ├── scenario.json          # Test scenario metadata
    ├── results.json          # Test execution results
    └── execution-report.json # Detailed test report
```

---

## 🐛 Troubleshooting

### Common Issues

#### ❌ "Specification file not found"

**Problem:** The spec path is incorrect or file doesn't exist.

**Solution:**
```bash
# Use relative path from repository root
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml

# Or absolute path
./scripts/run-smoke-pipeline.sh --spec /full/path/to/spec.yaml
```

#### ❌ "Mock server failed to start"

**Problem:** Port is already in use by another process.

**Solution:**
```bash
# Check what's using the port (Linux/macOS)
lsof -i :9101

# Check what's using the port (Windows)
netstat -ano | findstr :9101

# Use a different port
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --port 9102
```

#### ❌ "IR file not found" (when using --skip-parsing)

**Problem:** You're trying to skip parsing but the IR file doesn't exist yet.

**Solution:**
```bash
# Run full pipeline first
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml

# Then subsequent runs can skip parsing
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --skip-parsing
```

#### ❌ "Permission denied" (Bash script)

**Problem:** Bash script is not executable.

**Solution:**
```bash
chmod +x scripts/run-smoke-pipeline.sh
```

#### ❌ Tests fail with connection errors

**Problem:** Mock server didn't start successfully or is running on wrong port.

**Solution:**
```bash
# Ensure port matches between mock server and tests
./scripts/run-smoke-pipeline.sh \
    --spec specs/payments.yaml \
    --port 9101 \
    --base-url "http://127.0.0.1:9101"

# Check mock server logs
cat mock-server.log  # (Python script creates this)
```

### Getting Help

**PowerShell:**
```powershell
Get-Help .\scripts\run-smoke-pipeline.ps1 -Detailed
Get-Help .\scripts\run-smoke-pipeline.ps1 -Examples
```

**Bash:**
```bash
./scripts/run-smoke-pipeline.sh --help
```

**Python:**
```bash
python scripts/run-smoke-pipeline.py --help
```

---

## 🎯 Best Practices

### 1. Use Auto-Detection for Standard Specs

Let the script detect service info from your OpenAPI spec:
```bash
./scripts/run-smoke-pipeline.sh --spec specs/my-api.yaml
```

### 2. Use Rich Format for Development

Beautiful output helps during development:
```bash
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --output-format rich
```

### 3. Use JSON Format for CI/CD

Machine-readable output for automated processing:
```bash
python scripts/run-smoke-pipeline.py --spec specs/payments.yaml --output-format json
```

### 4. Keep Mock Server Running for Debugging

```bash
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --keep-mock

# Test manually
curl http://127.0.0.1:9101/payments

# Stop when done (use PID displayed at end)
kill <PID>
```

### 5. Use Different Ports for Multiple Services

```bash
# Terminal 1
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --port 9101 --keep-mock

# Terminal 2
./scripts/run-smoke-pipeline.sh --spec specs/commerce.yaml --port 9102 --keep-mock

# Terminal 3
./scripts/run-smoke-pipeline.sh --spec specs/flights.yaml --port 9103 --keep-mock
```

### 6. Use Skip Flags for Faster Iterations

```bash
# Initial run - full pipeline
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml

# Subsequent runs - skip unchanged stages
./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml --skip-parsing --skip-mock-config
```

---

## 📊 Pipeline Stages Explained

### Stage 1: Contract Parser

**Purpose:** Parse OpenAPI specification into normalized IR format.

**Output:** `workspace/catalog/{service-slug}/{version}.json`

**What it does:**
- Validates OpenAPI spec
- Extracts operations, schemas, parameters
- Creates searchable index for operations

### Stage 2: Mock Config Builder

**Purpose:** Generate mock server configuration.

**Output:** `artifacts/mocks/{service-slug}/{version-slug}/mock-config.yaml`

**What it does:**
- Maps operations to mock endpoints
- Generates response templates
- Configures server host/port

### Stage 3: Test Scenario Builder

**Purpose:** Generate test scenarios from operations.

**Output:** `artifacts/tests/{service-slug}/{version}/`

**What it does:**
- Creates test cases for each operation
- Generates request templates
- Sets up validation rules

### Stage 4: Mock Server

**Purpose:** Start mock server to handle test requests.

**Process:** Runs as background process

**What it does:**
- Loads mock configuration
- Starts REST API server
- Returns predefined responses

### Stage 5: Test Executor

**Purpose:** Execute smoke tests against mock server.

**Output:** `runs/smoke-{service-slug}-{version}-{timestamp}/`

**What it does:**
- Runs all test scenarios
- Validates responses
- Generates test report

---

## 🔗 Related Documentation

- [Main Project README](../README.md)
- [API Documentation](../plans/api-smoke-architecture.md)
- [Contract Parser](../apps/contract-parser/README.md)
- [Mock Config Builder](../apps/mock-config-builder/README.md)
- [Test Scenario Builder](../apps/test-scenario-builder/README.md)
- [Mock Server](../apps/mock-server/README.md)
- [Test Executor](../apps/test-executor/README.md)

---

## 📝 License

This project is part of the API Smoke Platform.

---

**Last Updated:** January 12, 2026
