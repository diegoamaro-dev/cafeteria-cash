# Cafetería Cash — instalación desde un clon limpio (FASE 0)
#
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#
# Crea el entorno virtual .venv e instala las dependencias de requirements.txt.
# No toca datos: no crea bases de datos ni backups.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = "python"
& $python --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3 no esta disponible en PATH. Instalalo antes de continuar."
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual en .venv ..."
    & $python -m venv .venv
} else {
    Write-Host "El entorno virtual .venv ya existe."
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "Actualizando pip ..."
& $venvPython -m pip install --upgrade pip

Write-Host "Instalando dependencias de requirements.txt ..."
& $venvPython -m pip install -r requirements.txt

Write-Host ""
Write-Host "Instalacion terminada. Arranca la aplicacion con:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
