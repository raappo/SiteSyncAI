<#
.SYNOPSIS
    SiteSync AI — Full Test Runner
    Runs the complete test suite and shows a summary.
.DESCRIPTION
    1. Seeds the database (in-memory for tests)
    2. Runs all pytest tests with coverage
    3. Reports pass/fail summary
#>

$ErrorActionPreference = "Continue"
$startTime = Get-Date

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  SiteSync AI — Full Test Suite" -ForegroundColor Cyan  
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check if uv is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'uv' not found. Install: pip install uv" -ForegroundColor Red
    exit 1
}

# Run tests
Write-Host "Running pytest..." -ForegroundColor Yellow
uv run pytest tests/ -v --tb=short --no-header -q 2>&1 | Tee-Object -Variable testOutput

$exitCode = $LASTEXITCODE
$duration = (Get-Date) - $startTime

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  ✅ ALL TESTS PASSED  (Duration: $($duration.TotalSeconds.ToString('F1'))s)" -ForegroundColor Green
} else {
    Write-Host "  ❌ SOME TESTS FAILED  (Duration: $($duration.TotalSeconds.ToString('F1'))s)" -ForegroundColor Red
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

exit $exitCode
