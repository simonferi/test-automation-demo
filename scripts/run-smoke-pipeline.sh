#!/usr/bin/env bash
# Universal Smoke Test Pipeline for Linux/macOS
# Usage: ./scripts/run-smoke-pipeline.sh --spec specs/payments.yaml [OPTIONS]

set -e

# Default values
SPEC_PATH=""
SERVICE=""
VERSION=""
REST_PORT="9101"
SCENARIO_PREFIX="smoke"
SCENARIO_TAGS=()
SMOKE_BASE_URL=""
OUTPUT_FORMAT="auto"
KEEP_MOCK_RUNTIME=false
SKIP_PARSING=false
SKIP_MOCK_CONFIG=false
SKIP_TEST_GENERATION=false
MOCK_PID=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Functions
print_usage() {
    cat << EOF
Usage: $0 --spec <path> [OPTIONS]

Required:
  --spec PATH              Path to OpenAPI specification file

Options:
  --service NAME           Service name (auto-detected if not provided)
  --version VERSION        Service version (auto-detected if not provided)
  --port PORT              REST API port for mock server (default: 9101)
  --prefix PREFIX          Scenario prefix (default: smoke)
  --tag TAG                Scenario tag (can be specified multiple times)
  --base-url URL           Base URL for smoke tests (default: http://127.0.0.1:PORT)
  --output-format FORMAT   Output format: auto, rich, plain, json (default: auto)
  --keep-mock              Keep mock server running after tests
  --skip-parsing           Skip contract parsing
  --skip-mock-config       Skip mock config generation
  --skip-test-generation   Skip test scenario generation
  -h, --help               Show this help message

Examples:
  $0 --spec specs/payments.yaml
  $0 --spec specs/commerce.yaml --port 9102 --output-format rich
  $0 --spec specs/flights.yaml --tag flights --tag integration

EOF
}

log_info() {
    echo -e "${CYAN}$1${NC}"
}

log_success() {
    echo -e "${GREEN}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}$1${NC}"
}

log_error() {
    echo -e "${RED}$1${NC}" >&2
}

log_gray() {
    echo -e "${GRAY}$1${NC}"
}

create_slug() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^0-9a-z_-]/-/g' | sed 's/^-*//;s/-*$//'
}

get_spec_info() {
    local spec_file="$1"
    local title=""
    local version=""
    
    if [[ ! -f "$spec_file" ]]; then
        log_error "Specification file not found: $spec_file"
        exit 1
    fi
    
    # Extract title and version from YAML/JSON
    if [[ "$spec_file" == *.json ]]; then
        title=$(python3 -c "import json,sys; data=json.load(open('$spec_file')); print(data.get('info',{}).get('title','UnknownService'))")
        version=$(python3 -c "import json,sys; data=json.load(open('$spec_file')); print(data.get('info',{}).get('version','1.0.0'))")
    else
        # Simple YAML parsing
        title=$(grep -m1 "title:" "$spec_file" | sed 's/.*title:[[:space:]]*//;s/["'\'']//g' | tr -d '\r')
        version=$(grep -m1 "version:" "$spec_file" | sed 's/.*version:[[:space:]]*//;s/["'\'']//g' | tr -d '\r')
    fi
    
    # Defaults if not found
    title=${title:-UnknownService}
    version=${version:-1.0.0}
    
    echo "$title|$version"
}

cleanup() {
    if [[ -n "$MOCK_PID" ]] && [[ "$KEEP_MOCK_RUNTIME" == "false" ]]; then
        log_info "\nStopping mock server (PID: $MOCK_PID)..."
        kill $MOCK_PID 2>/dev/null || true
        wait $MOCK_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --spec)
            SPEC_PATH="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --port)
            REST_PORT="$2"
            shift 2
            ;;
        --prefix)
            SCENARIO_PREFIX="$2"
            shift 2
            ;;
        --tag)
            SCENARIO_TAGS+=("$2")
            shift 2
            ;;
        --base-url)
            SMOKE_BASE_URL="$2"
            shift 2
            ;;
        --output-format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --keep-mock)
            KEEP_MOCK_RUNTIME=true
            shift
            ;;
        --skip-parsing)
            SKIP_PARSING=true
            shift
            ;;
        --skip-mock-config)
            SKIP_MOCK_CONFIG=true
            shift
            ;;
        --skip-test-generation)
            SKIP_TEST_GENERATION=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$SPEC_PATH" ]]; then
    log_error "Error: --spec is required"
    print_usage
    exit 1
fi

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Set environment variables
export CONSOLE_OUTPUT_FORMAT="$OUTPUT_FORMAT"
export PYTHONPATH="$REPO_ROOT/apps/contract-parser:$REPO_ROOT/apps/test-scenario-builder:$REPO_ROOT/apps/mock-config-builder:$REPO_ROOT/apps/mock-server:$REPO_ROOT/apps/test-executor"

# Auto-detect service info if needed
SPEC_INFO=$(get_spec_info "$SPEC_PATH")
DETECTED_SERVICE=$(echo "$SPEC_INFO" | cut -d'|' -f1)
DETECTED_VERSION=$(echo "$SPEC_INFO" | cut -d'|' -f2)

if [[ -z "$SERVICE" ]]; then
    SERVICE="$DETECTED_SERVICE"
    log_warning "Auto-detected service name: $SERVICE"
fi

if [[ -z "$VERSION" ]]; then
    VERSION="$DETECTED_VERSION"
    log_warning "Auto-detected version: $VERSION"
fi

# Auto-configure base URL
if [[ -z "$SMOKE_BASE_URL" ]]; then
    SMOKE_BASE_URL="http://127.0.0.1:$REST_PORT"
    log_warning "Using base URL: $SMOKE_BASE_URL"
fi

# Auto-configure tags
if [[ ${#SCENARIO_TAGS[@]} -eq 0 ]]; then
    SERVICE_SLUG=$(create_slug "$SERVICE")
    FIRST_WORD=$(echo "$SERVICE_SLUG" | cut -d'-' -f1)
    SCENARIO_TAGS=("$FIRST_WORD")
    log_warning "Using scenario tags: ${SCENARIO_TAGS[*]}"
fi

# Generate file paths
SERVICE_SLUG=$(create_slug "$SERVICE")
VERSION_SLUG=$(create_slug "$VERSION")
VERSION_FILE="${VERSION//\//-}"
IR_FILE="workspace/catalog/$SERVICE_SLUG/$VERSION_FILE.json"
MOCK_CONFIG_PATH="artifacts/mocks/$SERVICE_SLUG/$VERSION_SLUG/mock-config.yaml"
BUNDLE_DIR="artifacts/tests/$SERVICE_SLUG/$VERSION_FILE"

# Print header
echo ""
log_info "=== Smoke Test Pipeline ==="
echo "Service:     $SERVICE"
echo "Version:     $VERSION"
echo "Spec:        $SPEC_PATH"
echo "Port:        $REST_PORT"
echo "Output:      $OUTPUT_FORMAT"
log_info "==========================="
echo ""

# Step 1: Contract Parser
if [[ "$SKIP_PARSING" == "false" ]]; then
    log_info "[1/5] Running contract-parser"
    uv run python apps/contract-parser/contract_parser/main.py \
        --spec "$SPEC_PATH" \
        --output-dir "workspace/catalog" \
        --service-name "$SERVICE"
else
    log_gray "[1/5] Skipping contract-parser (--skip-parsing)"
    if [[ ! -f "$IR_FILE" ]]; then
        log_error "IR file not found: $IR_FILE. Cannot skip parsing."
        exit 1
    fi
fi

# Step 2: Mock Config Builder
if [[ "$SKIP_MOCK_CONFIG" == "false" ]]; then
    log_info "[2/5] Running mock-config-builder"
    uv run python apps/mock-config-builder/mock_config_builder/main.py \
        --ir "$IR_FILE" \
        --output-dir "artifacts/mocks" \
        --format "yaml" \
        --host "127.0.0.1" \
        --port "rest=$REST_PORT"
else
    log_gray "[2/5] Skipping mock-config-builder (--skip-mock-config)"
    if [[ ! -f "$MOCK_CONFIG_PATH" ]]; then
        log_error "Mock config not found: $MOCK_CONFIG_PATH. Cannot skip generation."
        exit 1
    fi
fi

# Step 3: Test Scenario Builder
if [[ "$SKIP_TEST_GENERATION" == "false" ]]; then
    log_info "[3/5] Running test-scenario-builder"
    GENERATOR_ARGS=(
        "apps/test-scenario-builder/test_scenario_builder/main.py"
        "--ir" "$IR_FILE"
        "--output-dir" "artifacts/tests"
        "--scenario-prefix" "$SCENARIO_PREFIX"
    )
    for tag in "${SCENARIO_TAGS[@]}"; do
        if [[ -n "$tag" ]]; then
            GENERATOR_ARGS+=("--tag" "$tag")
        fi
    done
    uv run python "${GENERATOR_ARGS[@]}"
else
    log_gray "[3/5] Skipping test-scenario-builder (--skip-test-generation)"
    if [[ ! -d "$BUNDLE_DIR" ]]; then
        log_error "Test bundle not found: $BUNDLE_DIR. Cannot skip generation."
        exit 1
    fi
fi

# Step 4: Start Mock Server
log_info "[4/5] Starting mock-server in background"
uv run python apps/mock-server/mock_server/main.py --config "$MOCK_CONFIG_PATH" > /tmp/mock-server-$$.log 2>&1 &
MOCK_PID=$!

# Wait for mock server to start
sleep 3

# Check if process is still running
if ! kill -0 $MOCK_PID 2>/dev/null; then
    log_error "Mock server failed to start. Log output:"
    cat /tmp/mock-server-$$.log
    exit 1
fi

# Step 5: Run Test Executor
log_info "[5/5] Running test-executor"
ORIGINAL_BASE_URL="${SMOKE_RUNTIME_BASE_URL:-}"
export SMOKE_RUNTIME_BASE_URL="$SMOKE_BASE_URL"
uv run python apps/test-executor/test_executor/main.py \
    --bundle "$BUNDLE_DIR" \
    --output-dir "runs"

# Restore original base URL
if [[ -n "$ORIGINAL_BASE_URL" ]]; then
    export SMOKE_RUNTIME_BASE_URL="$ORIGINAL_BASE_URL"
else
    unset SMOKE_RUNTIME_BASE_URL
fi

# Show results
LATEST_RUN=$(ls -td runs/*/ 2>/dev/null | head -1)
if [[ -n "$LATEST_RUN" ]]; then
    log_success "\nSmoke results saved to ${LATEST_RUN%/}"
fi

log_success "\n=== Pipeline Completed Successfully ==="

# Keep mock running if requested
if [[ "$KEEP_MOCK_RUNTIME" == "true" ]]; then
    log_warning "\nMock runtime is still running (PID: $MOCK_PID)"
    log_warning "Logs: /tmp/mock-server-$$.log"
    log_warning "Use 'kill $MOCK_PID' to stop it"
    MOCK_PID=""  # Prevent cleanup from killing it
fi
