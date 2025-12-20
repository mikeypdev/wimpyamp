#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
Write-Host "Creating virtual environment 'venv' and installing dependencies..."
python -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
Write-Host "Setup complete."
