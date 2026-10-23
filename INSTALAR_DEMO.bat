@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ===================================================
echo    Cafeteria Cash  -  instalacion de la DEMO
echo  ===================================================
echo.
echo  Esta demo usa SIEMPRE datos ficticios.
echo  Nunca toca ninguna base de datos real.
echo.

REM ---------------------------------------------------------------
REM  1. Comprobar que hay Python 3 disponible
REM ---------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] No se encuentra Python en el PATH.
    echo.
    echo          Instala Python 3.12 desde https://www.python.org/downloads/
    echo          y marca la casilla "Add python.exe to PATH" al instalar.
    echo          Despues vuelve a ejecutar este archivo.
    goto :error
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set "PYMAJ=%%a" & set "PYMIN=%%b"

if not "%PYMAJ%"=="3" (
    echo  [ERROR] Se necesita Python 3 y se ha encontrado la version %PYVER%.
    goto :error
)

echo  [OK]    Python %PYVER% encontrado.
if not "%PYMIN%"=="12" (
    echo  [AVISO] El proyecto se ha validado con Python 3.12. Tienes %PYVER%.
    echo          Probablemente funcione, pero no esta comprobado.
)

REM ---------------------------------------------------------------
REM  2. Entorno virtual
REM ---------------------------------------------------------------
if exist ".venv\Scripts\python.exe" (
    echo  [OK]    El entorno virtual .venv ya existe.
) else (
    echo  [...]   Creando el entorno virtual .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] No se ha podido crear el entorno virtual.
        goto :error
    )
    echo  [OK]    Entorno virtual creado.
)

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo  [ERROR] El entorno virtual no contiene python.exe.
    goto :error
)

REM ---------------------------------------------------------------
REM  3. Dependencias
REM ---------------------------------------------------------------
echo  [...]   Instalando dependencias ...
"%PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo  [ERROR] No se ha podido actualizar pip.
    goto :error
)
"%PY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] No se han podido instalar las dependencias.
    echo          Comprueba que tienes conexion a internet.
    goto :error
)
echo  [OK]    Dependencias instaladas.

REM ---------------------------------------------------------------
REM  4. Base de datos de demostracion
REM ---------------------------------------------------------------
if exist "data\demo.sqlite" (
    echo  [OK]    La base de demostracion ya existe.
    echo          Para empezar de cero, usa REINICIAR_DEMO.bat
) else (
    echo  [...]   Creando la base de demostracion con datos ficticios ...
    REM  La salida va a un registro: el script imprime instrucciones para el
    REM  repositorio completo, que no aplican a este paquete. Si algo falla,
    REM  se muestra entera.
    "%PY%" scripts\seed_demo.py > "%TEMP%\cafeteria-demo-seed.log" 2>&1
    if errorlevel 1 (
        type "%TEMP%\cafeteria-demo-seed.log"
        echo  [ERROR] No se ha podido crear la base de demostracion.
        goto :error
    )
    echo  [OK]    Base de demostracion creada en data\demo.sqlite
    echo          10 productos, dos dias ya cerrados y el dia de hoy abierto.
)

REM ---------------------------------------------------------------
REM  5. Comprobacion final: la base real no debe existir
REM ---------------------------------------------------------------
if exist "data\cafeteria.sqlite" (
    echo.
    echo  [AVISO] Existe el archivo data\cafeteria.sqlite.
    echo          La demo NO lo usa ni lo modifica: trabaja solo con
    echo          data\demo.sqlite. Se deja tal cual esta.
) else (
    echo  [OK]    No existe ninguna base real. Solo datos de demostracion.
)

echo.
echo  ===================================================
echo    Instalacion terminada.
echo.
echo    Ahora ejecuta:  INICIAR_DEMO.bat
echo  ===================================================
echo.
pause
exit /b 0

:error
echo.
echo  ===================================================
echo    La instalacion NO se ha completado.
echo  ===================================================
echo.
pause
exit /b 1
