#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
Push-Location -LiteralPath (Join-Path $PSScriptRoot "..")
try {
    Write-Host "Starting WimPyAmp using venv\Scripts\python..."
    $env:PYTHONPATH = '.'
    .\venv\Scripts\python run_wimpyamp.py
} finally {
    Pop-Location
}
