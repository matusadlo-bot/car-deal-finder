@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [CHYBA] Virtualne prostredie .venv neexistuje.
    echo Najprv spusti setup_windows.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 14), sys.version" >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] .venv nebolo vytvorene cez Python 3.14.
    echo Spusti setup_windows.bat - stare .venv sa automaticky nahradi.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" scheduler.py
pause
