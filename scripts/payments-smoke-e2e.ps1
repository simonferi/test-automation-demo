param(
    [string]$SpecPath = "specs/payments.yaml",
    [string]$Service = "Payments",
    [string]$Version = "1.0.0",
    [string]$RestPort = "9101",
    [string]$ScenarioPrefix = "smoke",
    [string[]]$ScenarioTags = @("payments"),
    [string]$SmokeBaseUrl = "http://127.0.0.1:9101",
    [string]$OutputFormat = "auto",
    [switch]$KeepMockRuntime
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Push-Location $repoRoot

$env:PYTHONPATH = "$repoRoot/apps/contract-parser;$repoRoot/apps/test-scenario-builder;$repoRoot/apps/mock-config-builder;$repoRoot/apps/mock-server;$repoRoot/apps/test-executor"

# Set unified console output format via environment variable
$env:CONSOLE_OUTPUT_FORMAT = $OutputFormat

function Invoke-UvPython {
    param([string[]]$Arguments)
    & uv run python @Arguments
}

function New-Slug {
    param([string]$Value)
    $slug = ($Value.ToLower() -replace "[^0-9a-z_-]+", "-").Trim('-')
    if ([string]::IsNullOrWhiteSpace($slug)) {
        return "value"
    }
    return $slug
}

$serviceSlug = New-Slug $Service
$versionSlug = New-Slug $Version
$versionFile = $Version.Replace('/', '-')
$irFile = "workspace/catalog/$serviceSlug/$versionFile.json"
$mockConfigPath = "artifacts/mocks/$serviceSlug/$versionSlug/mock-config.yaml"
$bundleDir = "artifacts/tests/$serviceSlug/$versionFile"
$mockJob = $null

try {
    Write-Host "[1/5] Running contract-parser" -ForegroundColor Cyan
    Invoke-UvPython @(
        "apps/contract-parser/contract_parser/main.py",
        "--spec", $SpecPath,
        "--output-dir", "workspace/catalog",
        "--service-name", $Service
    )

    Write-Host "[2/5] Running mock-config-builder" -ForegroundColor Cyan
    Invoke-UvPython @(
        "apps/mock-config-builder/mock_config_builder/main.py",
        "--ir", $irFile,
        "--output-dir", "artifacts/mocks",
        "--format", "yaml",
        "--host", "127.0.0.1",
        "--port", "rest=$RestPort"
    )

    Write-Host "[3/5] Running test-scenario-builder" -ForegroundColor Cyan
    $generatorArgs = @(
        "apps/test-scenario-builder/test_scenario_builder/main.py",
        "--ir", $irFile,
        "--output-dir", "artifacts/tests",
        "--scenario-prefix", $ScenarioPrefix
    )
    foreach ($tag in $ScenarioTags) {
        if (![string]::IsNullOrWhiteSpace($tag)) {
            $generatorArgs += @("--tag", $tag)
        }
    }
    Invoke-UvPython $generatorArgs

    Write-Host "[4/5] Starting mock-server as background job" -ForegroundColor Cyan
    $mockJob = Start-Job -ScriptBlock {
        param($RepoRoot, $ConfigPath, $OutputFormat)
        Set-Location $RepoRoot
        $env:PYTHONPATH = "$RepoRoot/apps/contract-parser;$RepoRoot/apps/test-scenario-builder;$RepoRoot/apps/mock-config-builder;$RepoRoot/apps/mock-server;$RepoRoot/apps/test-executor"
        $env:CONSOLE_OUTPUT_FORMAT = $OutputFormat
        uv run python apps/mock-server/mock_server/main.py --config $ConfigPath
    } -ArgumentList $repoRoot, $mockConfigPath, $OutputFormat
    Start-Sleep -Seconds 3

    Write-Host "[5/5] Running test-executor" -ForegroundColor Cyan
    $originalBaseUrl = $env:SMOKE_RUNTIME_BASE_URL
    try {
        $env:SMOKE_RUNTIME_BASE_URL = $SmokeBaseUrl
        Invoke-UvPython @(
            "apps/test-executor/test_executor/main.py",
            "--bundle", $bundleDir,
            "--output-dir", "runs"
        )
    }
    finally {
        if ($null -ne $originalBaseUrl) {
            $env:SMOKE_RUNTIME_BASE_URL = $originalBaseUrl
        }
        else {
            Remove-Item Env:SMOKE_RUNTIME_BASE_URL -ErrorAction SilentlyContinue
        }
    }
    $latestRun = Get-ChildItem -Path "runs" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestRun) {
        Write-Host "Smoke results saved to runs/$($latestRun.Name)" -ForegroundColor Green
    }
}
finally {
    if ($mockJob) {
        if ($KeepMockRuntime) {
            Write-Host "Mock runtime is still running in job Id $($mockJob.Id). Use Receive-Job/Stop-Job manually." -ForegroundColor Yellow
        }
        else {
            Stop-Job -Id $mockJob.Id -ErrorAction SilentlyContinue | Out-Null
            Receive-Job -Id $mockJob.Id -ErrorAction SilentlyContinue | Out-Host
            Remove-Job -Id $mockJob.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Pop-Location
}
