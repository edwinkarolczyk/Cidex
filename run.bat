@echo off
setlocal
cd /d "%~dp0"
title CIDEX - Monitor Excel

echo ==========================================
echo   CIDEX - Monitor Excel
echo ==========================================
echo.

python -c "import openpyxl, pandas, xlrd" >nul 2>&1
if errorlevel 1 (
  echo Instalowanie wymaganych bibliotek...
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

python cidex_entry.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Nie udalo sie uruchomic CIDEX.
echo Sprawdz komunikat bledu powyzej oraz instalacje Pythona.
pause
exit /b 1
