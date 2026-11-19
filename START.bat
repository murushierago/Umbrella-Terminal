@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First launch: installing dependencies ...
  call "%~dp0INSTALL.bat"
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" "%~dp0umbrella_terminal.py"
if errorlevel 1 (
  echo.
  echo Umbrella Terminal stopped unexpectedly.
  pause
)
