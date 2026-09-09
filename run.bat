@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo Nie udalo sie uruchomic CIDEX.
  echo Sprawdz, czy Python jest zainstalowany i dostepny w PATH.
  pause
)
