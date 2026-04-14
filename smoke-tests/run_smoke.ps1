<#
.SYNOPSIS
    Run the Serverless bug-bash smoke test suite.

.DESCRIPTION
    Validates environment, activates venv if present, installs deps, and runs pytest
    with JUnit XML output.  Use -Setup to provision all external resources first,
    or -Teardown to destroy them after.

.PARAMETER TestFile
    Optional: run only a specific test file (e.g. "tests/test_07_queries.py").

.PARAMETER Markers
    Optional: pytest marker expression (e.g. "queries" or "not networking").

.PARAMETER Setup
    Run setup_resources.py setup before the test run.

.PARAMETER Teardown
    Run setup_resources.py teardown after the test run (keeps search service).

.PARAMETER DeleteSearch
    When used with -Teardown, also delete the search service.

.EXAMPLE
    .\run_smoke.ps1 -Setup
    .\run_smoke.ps1
    .\run_smoke.ps1 -Teardown
    .\run_smoke.ps1 -Teardown -DeleteSearch
    .\run_smoke.ps1 -Setup -Teardown          # full lifecycle, keeps search
    .\run_smoke.ps1 -Markers "auth or indexes"
#>

param(
    [string]$TestFile = "",
    [string]$Markers = "",
    [switch]$Setup,
    [switch]$Teardown,
    [switch]$DeleteSearch
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

# ── Activate venv if present ────────────────────────────────────────────────
$venvActivate = Join-Path "." ".venv" "Scripts" "Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

# ── Install dependencies ────────────────────────────────────────────────────
pip install -q -r requirements.txt
if ($Setup -or $Teardown) {
    pip install -q -r requirements-setup.txt
}

# ── Setup phase ─────────────────────────────────────────────────────────────
if ($Setup) {
    Write-Host "`n=== Running Resource Setup ===" -ForegroundColor Cyan
    python setup_resources.py setup
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Setup failed."; Pop-Location; exit 1
    }
}

# ── Check .env ──────────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Error "No .env file found. Run with -Setup or copy .env.template to .env."
    Pop-Location; exit 1
}

# ── Build pytest args ───────────────────────────────────────────────────────
$pytestArgs = @(
    "-v",
    "--tb=short",
    "--junitxml=results/junit.xml"
)

if ($Markers) {
    $pytestArgs += @("-m", $Markers)
}

if ($TestFile) {
    $pytestArgs += $TestFile
} else {
    $pytestArgs += "tests/"
}

# ── Run ─────────────────────────────────────────────────────────────────────
Write-Host "`n=== Serverless Bug Bash — Smoke Tests ===" -ForegroundColor Cyan
Write-Host "Endpoint: $env:SEARCH_ENDPOINT"
Write-Host "API Version: $env:SEARCH_API_VERSION"
Write-Host "Mgmt API Version: $env:SEARCH_MGMT_API_VERSION"
Write-Host "Session output: results/`n"

python -m pytest @pytestArgs

$exitCode = $LASTEXITCODE

# ── Summary ─────────────────────────────────────────────────────────────────
if (Test-Path "results/failure_summary.md") {
    Write-Host "`n=== Failure Summary ===" -ForegroundColor Yellow
    Get-Content "results/failure_summary.md" | Select-Object -First 30
    Write-Host "`nFull report: results/failure_summary.md"
    Write-Host "JSON report: results/failure_report.json"
}

Write-Host "JUnit XML:   results/junit.xml`n"

# ── Teardown phase ──────────────────────────────────────────────────────────
if ($Teardown) {
    Write-Host "`n=== Running Resource Teardown ===" -ForegroundColor Cyan
    $teardownArgs = @("setup_resources.py", "teardown")
    if ($DeleteSearch) { $teardownArgs += "--delete-search" }
    python @teardownArgs
}

Pop-Location
exit $exitCode
