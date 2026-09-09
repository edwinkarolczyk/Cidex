@echo off
setlocal
cd /d "%~dp0"
title CIDEX - UI-DEMO 1

echo ==========================================
echo   CIDEX - UI-DEMO 1
echo ==========================================
echo.

python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
  echo Pierwsze uruchomienie - instalowanie wymaganych bibliotek...
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

python main.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Nie udalo sie uruchomic CIDEX.
echo Sprawdz, czy Python jest zainstalowany i dostepny w PATH.
echo.
pause
exit /b 1
