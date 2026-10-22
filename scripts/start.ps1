# Cafetería Cash — arranque de la aplicación (FASE 0)
#
#   powershell -ExecutionPolicy Bypass -File scripts\start.ps1
#
# Arranca Flask en http://127.0.0.1:5000 (solo localhost).
# Detener con Ctrl+C.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "No existe el entorno virtual. Ejecuta primero: powershell -ExecutionPolicy Bypass -File scripts\install.ps1"
    exit 1
}

Write-Host "Cafeteria Cash -> http://127.0.0.1:5000  (Ctrl+C para detener)"
& $venvPython run.py
