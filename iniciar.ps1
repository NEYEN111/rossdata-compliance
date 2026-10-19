$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    Write-Host 'Primero instala el entorno siguiendo README.md.'
    exit 1
}
& '.\.venv\Scripts\python.exe' 'run.py'
