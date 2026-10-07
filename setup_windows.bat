@echo off
setlocal EnableExtensions

REM ============================================================
REM Car Deal Finder - Windows setup for Python 3.14
REM Robustly finds the project folder even after unusual ZIP extraction.
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR="

REM 1) Normal case: requirements.txt is next to this BAT file.
if exist "%SCRIPT_DIR%requirements.txt" set "PROJECT_DIR=%SCRIPT_DIR%"

REM 2) Recovery case: extractor created one extra nested folder.
if not defined PROJECT_DIR (
    for /r "%SCRIPT_DIR%" %%F in (requirements.txt) do (
        if not defined PROJECT_DIR set "PROJECT_DIR=%%~dpF"
    )
)

if not defined PROJECT_DIR (
    echo ========================================
    echo [CHYBA] requirements.txt sa nenasiel.
    echo ========================================
    echo.
    echo Tento ZIP pravdepodobne nebol rozbaleny cely.
    echo Rozbal CELy obsah ZIPu do jedneho priecinka a potom spusti setup_windows.bat.
    echo.
    echo Hladal som od:
    echo %SCRIPT_DIR%
    echo.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

echo ========================================
echo   Car Deal Finder 0.4.1 - Python 3.14
echo ========================================
echo Projekt:
echo %CD%
echo.
echo requirements.txt:
echo %CD%\requirements.txt
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] Python Launcher "py" sa nenasiel.
    echo Nainstaluj Python 3.14 z python.org a nechaj zapnuty Python Launcher.
    pause
    exit /b 1
)

py -3.14 --version >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] Python 3.14 sa cez prikaz "py -3.14" nenasiel.
    echo.
    echo Nainstalovane verzie Pythonu:
    py -0p
    echo.
    pause
    exit /b 1
)

echo Pouzije sa:
py -3.14 --version
for /f "delims=" %%i in ('py -3.14 -c "import sys; print(sys.executable)"') do echo %%i
echo.

if exist ".venv" (
    echo Odstranujem stare virtualne prostredie .venv ...
    rmdir /s /q ".venv"
    if exist ".venv" (
        echo [CHYBA] Nepodarilo sa odstranit .venv.
        echo Zavri dashboard/CMD okna pouzivajuce projekt a spusti setup znova.
        pause
        exit /b 1
    )
)

echo Vytvaram nove .venv cez Python 3.14 ...
py -3.14 -m venv .venv
if errorlevel 1 goto :fail

echo.
echo Overujem Python vo virtualnom prostredi ...
".venv\Scripts\python.exe" --version
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 14), sys.version; print('OK - virtualne prostredie pouziva Python 3.14')"
if errorlevel 1 goto :fail

echo.
echo Aktualizujem pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

echo.
echo Instalujem baliky projektu ...
if not exist "requirements.txt" (
    echo [CHYBA] requirements.txt zmizol po zmene priecinka: %CD%
    goto :fail
)
".venv\Scripts\python.exe" -m pip install -r "%CD%\requirements.txt"
if errorlevel 1 goto :fail

if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

echo.
echo Overujem Streamlit ...
".venv\Scripts\python.exe" -c "import streamlit; print('Streamlit', streamlit.__version__, '- OK')"
if errorlevel 1 goto :fail

echo.
echo ========================================
echo HOTOVO - projekt pouziva Python 3.14.
echo Teraz spusti run_dashboard.bat
echo ========================================
pause
exit /b 0

:fail
echo.
echo ========================================
echo [CHYBA] Instalacia sa nepodarila.
echo Projektovy priecinok: %CD%
echo ========================================
echo Skopiruj posledne riadky z tohto okna a posli mi ich.
pause
exit /b 1
