# Contract Parser

Parses OpenAPI specifications into normalized Intermediate Representation (IR) format with JSON-based search indexing.

## Overview

The contract parser validates and normalizes OpenAPI specifications, creating a searchable catalog of API operations. It replaces the previous FAISS/NumPy-based indexing with a lightweight JSON keyword search system.

## Features

- ✅ OpenAPI 3.0+ specification parsing
- ✅ JSON-based keyword search indexing (no NumPy/FAISS required)
- ✅ Service and version auto-detection
- ✅ Operation metadata extraction
- ✅ Normalized IR generation

## Usage

### Command Line

```powershell
# Basic usage
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml

# With custom output directory
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --output-dir workspace/catalog \
    --service-name "My API"

# Multiple specs
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --spec specs/commerce.yaml \
    --spec specs/flights.yaml
```

### Via Scripts

```powershell
# Automatic via universal pipeline
.\scripts\run-smoke-pipeline.ps1 -SpecPath specs/payments.yaml
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--spec` | Yes | - | Path to OpenAPI specification file(s) |
| `--output-dir` | No | `workspace/catalog` | Directory for IR snapshots |
| `--index-path` | No | `workspace/catalog/index.json` | Path to search index |
| `--service-name` | No | Auto-detected | Override service name |
| `--policy` | No | - | Optional policy YAML/JSON |

## Output Structure

### IR Snapshot

Location: `workspace/catalog/{service-slug}/{version}.json`

```json
{
  "service": "Payments API",
  "version": "1.0.0",
  "protocol": "openapi",
  "operations": [
    {
      "name": "GET /payments",
      "method": "GET",
      "path": "/payments",
      "description": "List payments",
      "parameters": [...],
      "responses": [...]
    }
  ]
}
```

### Search Index

Location: `workspace/catalog/index.json`

```json
{
  "format": "json",
  "version": "1.0",
  "total_operations": 8,
  "contracts": [
    {
      "service": "Payments API",
      "version": "1.0.0",
      "operation": "GET /payments",
      "keywords": ["api", "get", "list", "payments"]
    }
  ]
}
```

## Architecture

### Indexing Strategy

**Previous:** FAISS vector-based search with NumPy embeddings  
**Current:** Simple JSON keyword extraction and matching

Benefits:
- Zero dependencies (stdlib only)
- Fast parsing and indexing
- Easy to understand and debug
- Cross-platform without binary dependencies

### Keyword Extraction

```python
def _extract_keywords(service, operation, method, path, description):
    """
    Extracts searchable keywords from operation details:
    - Service name words
    - Operation name words
    - HTTP method
    - Path segments (excluding parameters)
    - Description words (>3 chars)
    """
```

## Implementation Details

### Files

- `main.py` - CLI entrypoint, argument parsing
- `indexer.py` - JSON indexing logic
- `normalizers.py` - OpenAPI normalization
- `models.py` - IR data models (Pydantic)

### Dependencies

- `pydantic>=2.10.0` - Data validation
- `pyyaml>=6.0.2` - YAML parsing
- `typer>=0.15.0` - CLI framework

## Examples

### Parse Single Spec

```powershell
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --output-dir workspace/catalog
```

**Output:**
```
Saved IR snapshot -> workspace\catalog\payments-api\1.0.0.json
Index updated at workspace\catalog\index.json
```

### Parse Multiple Specs

```powershell
uv run python apps/contract-parser/contract_parser/main.py \
    --spec specs/payments.yaml \
    --spec specs/commerce.yaml \
    --spec specs/flights.yaml
```

## Testing

```powershell
# Run tests
uv run pytest apps/contract-parser/tests/

# With coverage
uv run pytest apps/contract-parser/tests/ --cov=contract_parser
```

## See Also

- [Main README](../../README.md)
- [Test Scenario Builder](../test-scenario-builder/)
- [Mock Config Builder](../mock-config-builder/)
