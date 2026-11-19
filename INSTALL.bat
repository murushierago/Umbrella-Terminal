@echo off
setlocal
cd /d "%~dp0"
title Umbrella Corporation - Local Installer
color 0C
echo ===============================================
echo   UMBRELLA CORPORATION // TERMINAL INSTALLER
 echo ===============================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating isolated Python environment...
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto :fail
)
if not exist ".venv\Scripts\python.exe" goto :fail
echo [2/3] Installing Pygame and OpenCV ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo [3/3] Creating Desktop shortcut ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_SHORTCUT.ps1"
if errorlevel 1 (
  echo Could not create shortcut, but the app can run via START.bat.
)
echo.
echo INSTALLATION COMPLETE. Double-click START.bat to launch.
echo.
pause
exit /b 0
:fail
echo.
echo INSTALLATION FAILED. Make sure Python 3 is installed and you have Internet.
pause
exit /b 1
