@echo off
cd /d "%~dp0"
echo Toto zmaze cars.db vratane historie cien.
choice /C AN /M "Naozaj zmazat databazu? (A=ano, N=nie)"
if errorlevel 2 exit /b 0
if exist cars.db del /q cars.db
echo Databaza zmazana. Pri dalsom scane sa vytvori nanovo.
pause
