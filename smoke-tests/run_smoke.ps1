<#
.SYNOPSIS
    Run the Azure AI Search smoke test suite.

.DESCRIPTION
    Validates environment, activates venv if present, installs deps, and runs pytest
    with JUnit XML output.  Results are written to results/{SKU}/ based on the
    SEARCH_SKU environment variable.  Use -Setup to provision all external resources
    first, or -Teardown to clean up search resources after.

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
# ── Read SKU from .env or environment ───────────────────────────────────────────
if (-not $env:SEARCH_SKU) {
    # Try to read from .env
    if (Test-Path ".env") {
        $skuLine = Get-Content ".env" | Where-Object { $_ -match "^SEARCH_SKU=" } | Select-Object -First 1
        if ($skuLine) {
            $env:SEARCH_SKU = ($skuLine -split "=", 2)[1].Trim()
        }
    }
}
if (-not $env:SEARCH_SKU) {
    Write-Error "SEARCH_SKU not set. Add it to .env (e.g. SEARCH_SKU=basic)."
    Pop-Location; exit 1
}
$sku = $env:SEARCH_SKU

# Ensure per-SKU results directory exists
$skuResultsDir = Join-Path "results" $sku
if (-not (Test-Path $skuResultsDir)) {
    New-Item -ItemType Directory -Path $skuResultsDir -Force | Out-Null
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
    "--junitxml=results/$sku/junit.xml"
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
Write-Host "`n=== Azure AI Search — Smoke Tests ==" -ForegroundColor Cyan
Write-Host "SKU:           $sku"
Write-Host "Endpoint:      $env:SEARCH_ENDPOINT"
Write-Host "API Version:   $env:SEARCH_API_VERSION"
Write-Host "Results:       results/$sku/`n"

python -m pytest @pytestArgs

$exitCode = $LASTEXITCODE

# ── Summary ─────────────────────────────────────────────────────────────────
if (Test-Path "results/$sku/failure_summary.md") {
    Write-Host "`n=== Failure Summary ($sku) ===" -ForegroundColor Yellow
    Get-Content "results/$sku/failure_summary.md" | Select-Object -First 30
    Write-Host "`nFull report: results/$sku/failure_summary.md"
    Write-Host "JSON report: results/$sku/failure_report.json"
}

Write-Host "Dashboard:   results/$sku/test_log.md"
Write-Host "JUnit XML:   results/$sku/junit.xml`n"

# ── Teardown phase ──────────────────────────────────────────────────────────
if ($Teardown) {
    Write-Host "`n=== Running Resource Teardown ===" -ForegroundColor Cyan
    $teardownArgs = @("setup_resources.py", "teardown")
    if ($DeleteSearch) { $teardownArgs += "--delete-search" }
    python @teardownArgs
}

Pop-Location
exit $exitCode
