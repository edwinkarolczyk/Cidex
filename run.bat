@echo off
setlocal
cd /d "%~dp0"
title CIDEX - Planista

echo ==========================================
echo   CIDEX - Planista
if not exist requirements.txt goto :error
echo ==========================================
echo.

python -c "import customtkinter, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo Instalowanie wymaganych bibliotek...
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

python main.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Nie udalo sie uruchomic CIDEX.
echo Sprawdz komunikat bledu powyzej oraz instalacje Pythona.
pause
exit /b 1
