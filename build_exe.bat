@echo off
setlocal
cd /d "%~dp0"
title CIDEX - build EXE

echo ==========================================
echo   CIDEX - budowanie plikow EXE
echo ==========================================
echo.

python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo [1/2] Cidex.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Cidex main.py
if errorlevel 1 goto :fail

echo [2/2] Cidex_Api.exe...
python -m PyInstaller --noconfirm --clean --onefile --console --name Cidex_Api api_server.py
if errorlevel 1 goto :fail

if not exist "dist\Cidex.exe" goto :fail
if not exist "dist\Cidex_Api.exe" goto :fail
copy /Y "dist\Cidex.exe" "%~dp0Cidex.exe" >nul
copy /Y "dist\Cidex_Api.exe" "%~dp0Cidex_Api.exe" >nul

echo.
echo GOTOWE:
echo   %~dp0Cidex.exe
echo   %~dp0Cidex_Api.exe
echo.
echo Cidex_Api.exe uruchamiaj dopiero po ustawieniu WM_ROOT w Cidex.exe.
pause
exit /b 0

:fail
echo.
echo [BLAD] Nie udalo sie zbudowac plikow CIDEX.
pause
exit /b 1
