@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title CIDEX Mobile API

echo ==========================================
echo   CIDEX - serwer dla Cidex Mobile
echo ==========================================
echo.

python -c "import flask, waitress" >nul 2>&1
if errorlevel 1 (
  echo Instalowanie wymaganych bibliotek...
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

echo.
echo Windows moze zapytac o dostep przez Zapory.
echo Zezwol tylko dla sieci prywatnych / firmowych.
echo.
python api_server.py --host 0.0.0.0
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo [BLAD] Nie udalo sie uruchomic CIDEX Mobile API.
echo Najpierw uruchom Cidex i ustaw poprawny WM_ROOT.
echo.
pause
exit /b 1
