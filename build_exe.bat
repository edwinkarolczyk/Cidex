@echo off
setlocal
cd /d "%~dp0"
title CIDEX - build EXE

echo ==========================================
echo   CIDEX - budowanie Cidex.exe
echo ==========================================
echo.

python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

python -m PyInstaller --noconfirm --clean --onefile --windowed --name Cidex main.py
if errorlevel 1 goto :fail

if not exist "dist\Cidex.exe" goto :fail
copy /Y "dist\Cidex.exe" "%~dp0Cidex.exe" >nul

echo.
echo GOTOWE:
echo   %~dp0Cidex.exe
pause
exit /b 0

:fail
echo.
echo [BLAD] Nie udalo sie zbudowac Cidex.exe
pause
exit /b 1
