@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ===================================================
echo    Cafeteria Cash  -  reiniciar los datos de la DEMO
echo  ===================================================
echo.

set "PY=%~dp0.venv\Scripts\python.exe"
set "DEMO=%~dp0data\demo.sqlite"
set "REAL=%~dp0data\cafeteria.sqlite"

if not exist "%PY%" (
    echo  [ERROR] No esta instalada la demo.
    echo          Ejecuta primero INSTALAR_DEMO.bat
    goto :error
)

REM ---------------------------------------------------------------
REM  Comprobaciones defensivas ANTES de borrar nada.
REM  Este script solo puede tocar data\demo.sqlite. Si la ruta no es
REM  exactamente esa, se cancela sin borrar.
REM ---------------------------------------------------------------
if /i not "%DEMO:~-16%"=="data\demo.sqlite" (
    echo  [ERROR] Comprobacion de seguridad: la ruta a borrar no termina
    echo          en data\demo.sqlite. Cancelado, no se ha borrado nada.
    goto :error
)

if /i "%DEMO%"=="%REAL%" (
    echo  [ERROR] Comprobacion de seguridad: la ruta coincide con la base
    echo          real. Cancelado, no se ha borrado nada.
    goto :error
)

echo  Se va a borrar UNICAMENTE este archivo:
echo.
echo      %DEMO%
echo.
echo  Y se volveran a crear los datos ficticios de partida:
echo  10 productos, dos dias ya cerrados y el dia de hoy abierto.
echo.
echo  NO se toca ningun otro archivo. Las copias de copias-demo\
echo  y los PDF de exports\ se quedan como estan.
echo.

set "RESP="
set /p "RESP=Escribe SI y pulsa Enter para continuar: "
if /i not "%RESP%"=="SI" (
    echo.
    echo  Cancelado. No se ha borrado nada.
    echo.
    pause
    exit /b 0
)

echo.
if exist "%DEMO%" (
    del /f /q "%DEMO%"
    if exist "%DEMO%" (
        echo  [ERROR] No se ha podido borrar la base de demostracion.
        echo          Puede que la aplicacion siga abierta: cierrala e
        echo          intentalo otra vez.
        goto :error
    )
    echo  [OK]    Base de demostracion anterior borrada.
) else (
    echo  [OK]    No habia base de demostracion previa.
)

echo  [...]   Creando los datos ficticios de partida ...
"%PY%" scripts\seed_demo.py > "%TEMP%\cafeteria-demo-seed.log" 2>&1
if errorlevel 1 (
    type "%TEMP%\cafeteria-demo-seed.log"
    echo  [ERROR] No se han podido crear los datos de demostracion.
    goto :error
)
echo  [OK]    Datos de demostracion restaurados.

if exist "%REAL%" (
    echo.
    echo  [AVISO] Existe el archivo data\cafeteria.sqlite. Este script NO
    echo          lo ha tocado: solo actua sobre data\demo.sqlite.
)

echo.
echo  ===================================================
echo    Demo reiniciada. Ya puedes ejecutar INICIAR_DEMO.bat
echo  ===================================================
echo.
pause
exit /b 0

:error
echo.
pause
exit /b 1
