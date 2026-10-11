$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host ""
    Write-Host "ERROR: Python virtual environment was not found:"
    Write-Host $python
    Write-Host ""
    exit 1
}

$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

# Scheduler checks every 30 seconds by default.
# Override this value here if needed.
$env:NAMMAWEB_SCHEDULER_INTERVAL_SECONDS = "30"

Write-Host ""
Write-Host "============================================================"
Write-Host "NAMMAWEB CAMPAIGN SCHEDULER"
Write-Host "============================================================"
Write-Host "Project: $PSScriptRoot"
Write-Host "Python:  $python"
Write-Host "Mode:    TEST / FAKE PROVIDERS ONLY"
Write-Host "Real email/WhatsApp sending: DISABLED"
Write-Host "Interval: $env:NAMMAWEB_SCHEDULER_INTERVAL_SECONDS seconds"
Write-Host ""
Write-Host "Press Ctrl+C to stop the scheduler."
Write-Host "============================================================"
Write-Host ""

& $python -m reach.campaigns.campaign_scheduler

Write-Host ""
Write-Host "Scheduler process exited."
