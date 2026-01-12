param(
    [Parameter(Mandatory=$true, HelpMessage="Path to the OpenAPI specification file (e.g., specs/payments.yaml)")]
    [string]$SpecPath,
    
    [Parameter(HelpMessage="Service name (auto-detected from spec if not provided)")]
    [string]$Service = "",
    
    [Parameter(HelpMessage="Service version (auto-detected from spec if not provided)")]
    [string]$Version = "",
    
    [Parameter(HelpMessage="REST API port for mock server")]
    [string]$RestPort = "9101",
    
    [Parameter(HelpMessage="Scenario prefix for test naming")]
    [string]$ScenarioPrefix = "smoke",
    
    [Parameter(HelpMessage="Tags to apply to test scenarios")]
    [string[]]$ScenarioTags = @(),
    
    [Parameter(HelpMessage="Base URL for smoke tests")]
    [string]$SmokeBaseUrl = "",
    
    [Parameter(HelpMessage="Console output format: auto, rich, plain, json")]
    [ValidateSet("auto", "rich", "plain", "json")]
    [string]$OutputFormat = "auto",
    
    [Parameter(HelpMessage="Keep mock server running after tests complete")]
    [switch]$KeepMockRuntime,
    
    [Parameter(HelpMessage="Skip contract parsing if IR already exists")]
    [switch]$SkipParsing,
    
    [Parameter(HelpMessage="Skip mock config generation")]
    [switch]$SkipMockConfig,
    
    [Parameter(HelpMessage="Skip test scenario generation")]
    [switch]$SkipTestGeneration
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Push-Location $repoRoot

# Set unified console output format via environment variable
$env:CONSOLE_OUTPUT_FORMAT = $OutputFormat

# Configure Python path
$env:PYTHONPATH = "$repoRoot/apps/contract-parser;$repoRoot/apps/test-scenario-builder;$repoRoot/apps/mock-config-builder;$repoRoot/apps/mock-server;$repoRoot/apps/test-executor"

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

function Get-SpecInfo {
    param([string]$SpecFilePath)
    
    if (-not (Test-Path $SpecFilePath)) {
        throw "Specification file not found: $SpecFilePath"
    }
    
    $content = Get-Content $SpecFilePath -Raw
    $yaml = $null
    
    # Try to parse YAML/JSON to extract service info
    try {
        if ($SpecFilePath -match '\.(json)$') {
            $yaml = $content | ConvertFrom-Json
        } else {
            # Simple YAML parsing for title and version
            if ($content -match 'title:\s*(.+)') {
                $title = $matches[1].Trim().Trim('"').Trim("'")
            }
            if ($content -match "version:\s*[`"`']?([^`"`'\r\n]+)[`"`']?") {
                $ver = $matches[1].Trim().Trim('"').Trim("'")
            }
            
            $yaml = @{
                info = @{
                    title = $title
                    version = $ver
                }
            }
        }
        
        return @{
            Title = $yaml.info.title
            Version = $yaml.info.version
        }
    } catch {
        Write-Warning "Could not auto-detect service info from spec: $_"
        return @{
            Title = "UnknownService"
            Version = "1.0.0"
        }
    }
}

# Validate spec file exists
if (-not (Test-Path $SpecPath)) {
    Write-Error "Specification file not found: $SpecPath"
    Pop-Location
    exit 1
}

# Auto-detect service name and version if not provided
$specInfo = Get-SpecInfo -SpecFilePath $SpecPath

if ([string]::IsNullOrWhiteSpace($Service)) {
    $Service = $specInfo.Title
    Write-Host "Auto-detected service name: $Service" -ForegroundColor Yellow
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = $specInfo.Version
    Write-Host "Auto-detected version: $Version" -ForegroundColor Yellow
}

# Auto-configure base URL if not provided
if ([string]::IsNullOrWhiteSpace($SmokeBaseUrl)) {
    $SmokeBaseUrl = "http://127.0.0.1:$RestPort"
    Write-Host "Using base URL: $SmokeBaseUrl" -ForegroundColor Yellow
}

# Auto-configure scenario tags if empty
if ($ScenarioTags.Count -eq 0) {
    $serviceSlug = New-Slug $Service
    $ScenarioTags = @($serviceSlug.Split('-')[0])
    Write-Host "Using scenario tags: $($ScenarioTags -join ', ')" -ForegroundColor Yellow
}

# Generate file paths
$serviceSlug = New-Slug $Service
$versionSlug = New-Slug $Version
$versionFile = $Version.Replace('/', '-')
$irFile = "workspace/catalog/$serviceSlug/$versionFile.json"
$mockConfigPath = "artifacts/mocks/$serviceSlug/$versionSlug/mock-config.yaml"
$bundleDir = "artifacts/tests/$serviceSlug/$versionFile"
$mockJob = $null

Write-Host "`n=== Smoke Test Pipeline ===" -ForegroundColor Cyan
Write-Host "Service:     $Service" -ForegroundColor White
Write-Host "Version:     $Version" -ForegroundColor White
Write-Host "Spec:        $SpecPath" -ForegroundColor White
Write-Host "Port:        $RestPort" -ForegroundColor White
Write-Host "Output:      $OutputFormat" -ForegroundColor White
Write-Host "===========================`n" -ForegroundColor Cyan

try {
    # Step 1: Contract Parser
    if (-not $SkipParsing) {
        Write-Host "[1/5] Running contract-parser" -ForegroundColor Cyan
        Invoke-UvPython @(
            "apps/contract-parser/contract_parser/main.py",
            "--spec", $SpecPath,
            "--output-dir", "workspace/catalog",
            "--service-name", $Service
        )
    } else {
        Write-Host "[1/5] Skipping contract-parser (--SkipParsing)" -ForegroundColor DarkGray
        if (-not (Test-Path $irFile)) {
            Write-Error "IR file not found: $irFile. Cannot skip parsing."
            exit 1
        }
    }

    # Step 2: Mock Config Builder
    if (-not $SkipMockConfig) {
        Write-Host "[2/5] Running mock-config-builder" -ForegroundColor Cyan
        Invoke-UvPython @(
            "apps/mock-config-builder/mock_config_builder/main.py",
            "--ir", $irFile,
            "--output-dir", "artifacts/mocks",
            "--format", "yaml",
            "--host", "127.0.0.1",
            "--port", "rest=$RestPort"
        )
    } else {
        Write-Host "[2/5] Skipping mock-config-builder (--SkipMockConfig)" -ForegroundColor DarkGray
        if (-not (Test-Path $mockConfigPath)) {
            Write-Error "Mock config not found: $mockConfigPath. Cannot skip generation."
            exit 1
        }
    }

    # Step 3: Test Scenario Builder
    if (-not $SkipTestGeneration) {
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
    } else {
        Write-Host "[3/5] Skipping test-scenario-builder (--SkipTestGeneration)" -ForegroundColor DarkGray
        if (-not (Test-Path $bundleDir)) {
            Write-Error "Test bundle not found: $bundleDir. Cannot skip generation."
            exit 1
        }
    }

    # Step 4: Start Mock Server
    Write-Host "[4/5] Starting mock-server as background job" -ForegroundColor Cyan
    $mockJob = Start-Job -ScriptBlock {
        param($RepoRoot, $ConfigPath, $OutputFormat)
        Set-Location $RepoRoot
        $env:PYTHONPATH = "$RepoRoot/apps/contract-parser;$RepoRoot/apps/test-scenario-builder;$RepoRoot/apps/mock-config-builder;$RepoRoot/apps/mock-server;$RepoRoot/apps/test-executor"
        $env:CONSOLE_OUTPUT_FORMAT = $OutputFormat
        uv run python apps/mock-server/mock_server/main.py --config $ConfigPath
    } -ArgumentList $repoRoot, $mockConfigPath, $OutputFormat
    
    Start-Sleep -Seconds 3
    
    # Check if mock server started successfully
    $jobState = (Get-Job -Id $mockJob.Id).State
    if ($jobState -eq "Failed") {
        $jobOutput = Receive-Job -Id $mockJob.Id -ErrorAction SilentlyContinue
        Write-Error "Mock server failed to start:`n$jobOutput"
        exit 1
    }

    # Step 5: Run Test Executor
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
    
    # Show results location
    $latestRun = Get-ChildItem -Path "runs" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestRun) {
        Write-Host "`nSmoke results saved to runs/$($latestRun.Name)" -ForegroundColor Green
    }
    
    Write-Host "`n=== Pipeline Completed Successfully ===" -ForegroundColor Green
}
catch {
    Write-Host "`n=== Pipeline Failed ===" -ForegroundColor Red
    Write-Error $_.Exception.Message
    exit 1
}
finally {
    # Cleanup mock server
    if ($mockJob) {
        if ($KeepMockRuntime) {
            Write-Host "`nMock runtime is still running in job Id $($mockJob.Id)." -ForegroundColor Yellow
            Write-Host "Use 'Receive-Job -Id $($mockJob.Id)' to see output or 'Stop-Job -Id $($mockJob.Id)' to stop it." -ForegroundColor Yellow
        }
        else {
            Stop-Job -Id $mockJob.Id -ErrorAction SilentlyContinue | Out-Null
            $mockOutput = Receive-Job -Id $mockJob.Id -ErrorAction SilentlyContinue
            if ($mockOutput -and $OutputFormat -ne "plain") {
                Write-Host "`nMock server output:" -ForegroundColor DarkGray
                $mockOutput | Out-Host
            }
            Remove-Job -Id $mockJob.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Pop-Location
}
