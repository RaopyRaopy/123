$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "Python virtual environment was not found at .venv\Scripts\python.exe"
  Write-Host "Please create the environment and install requirements first."
  Read-Host "Press Enter to exit"
  exit 1
}

Write-Host "Starting Smart Travel local preview..."
Write-Host "URL: http://127.0.0.1:8000/"
Write-Host ""
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Write-Host ""
Write-Host "Server stopped."
Read-Host "Press Enter to exit"
