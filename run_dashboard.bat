@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR="

if exist "%SCRIPT_DIR%dashboard.py" set "PROJECT_DIR=%SCRIPT_DIR%"
if not defined PROJECT_DIR (
    for /r "%SCRIPT_DIR%" %%F in (dashboard.py) do (
        if not defined PROJECT_DIR set "PROJECT_DIR=%%~dpF"
    )
)

if not defined PROJECT_DIR (
    echo [CHYBA] dashboard.py sa nenasiel. Rozbal cely ZIP.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

if not exist ".venv\Scripts\python.exe" (
    echo [CHYBA] Virtualne prostredie .venv neexistuje.
    echo Najprv spusti setup_windows.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 14), sys.version" >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] .venv nebolo vytvorene cez Python 3.14.
    echo Spusti setup_windows.bat.
    pause
    exit /b 1
)

echo Spustam Car Deal Finder z:
echo %CD%
".venv\Scripts\python.exe" --version
echo.
".venv\Scripts\python.exe" -m streamlit run "%CD%\dashboard.py"

if errorlevel 1 (
    echo.
    echo [CHYBA] Dashboard sa ukoncil s chybou.
)
pause
