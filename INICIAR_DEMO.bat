@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ===================================================
echo    Cafeteria Cash  -  DEMO
echo  ===================================================
echo.

set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo  [ERROR] No esta instalada la demo.
    echo          Ejecuta primero INSTALAR_DEMO.bat
    goto :error
)

if not exist "data\demo.sqlite" (
    echo  [ERROR] No existe la base de demostracion.
    echo          Ejecuta primero INSTALAR_DEMO.bat
    goto :error
)

REM ---------------------------------------------------------------
REM  La demo trabaja SIEMPRE sobre data\demo.sqlite. No depende de
REM  que nadie configure nada: se fija aqui, dentro de este proceso.
REM ---------------------------------------------------------------
set "CAFETERIA_DB=%~dp0data\demo.sqlite"

REM  Carpeta de copias de la demo. Se crea JUNTO a esta carpeta, no dentro:
REM  en la aplicacion real la copia va siempre fuera, y las pruebas comprueban
REM  que no quede ninguna copia dentro del proyecto. La aplicacion nunca crea
REM  carpetas de backup, asi que la crea el lanzador. Es ficticia y local.
for %%i in ("%~dp0..\copias-demo") do set "CAFETERIA_BACKUP_DIR=%%~fi"
if not exist "%CAFETERIA_BACKUP_DIR%" mkdir "%CAFETERIA_BACKUP_DIR%"

echo  Base de datos .... data\demo.sqlite        (datos ficticios)
echo  Copias ........... %CAFETERIA_BACKUP_DIR%
echo  Documentos PDF ... exports\
echo.
echo  La aplicacion se abrira en:  http://127.0.0.1:5000
echo  Solo es accesible desde este ordenador.
echo.
echo  Para detenerla: pulsa Ctrl+C en esta ventana, o cierrala.
echo  ---------------------------------------------------
echo.

REM  Abrir el navegador unos segundos despues, cuando el servidor
REM  ya responda. No anade ninguna dependencia: es parte de Windows.
start "" /B cmd /c "timeout /t 3 >nul & start "" http://127.0.0.1:5000"

"%PY%" run.py

echo.
echo  Aplicacion detenida.
pause
exit /b 0

:error
echo.
pause
exit /b 1
