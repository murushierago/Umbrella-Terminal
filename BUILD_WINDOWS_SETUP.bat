@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call "INSTALL.bat"
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name "UmbrellaTerminal" umbrella_terminal.py
if errorlevel 1 goto :fail
xcopy "assets" "dist\UmbrellaTerminal\assets\" /e /i /y >nul
xcopy "secret_files" "dist\UmbrellaTerminal\secret_files\" /e /i /y >nul
copy /y "settings.json" "dist\UmbrellaTerminal\settings.json" >nul
where ISCC.exe >nul 2>&1
if errorlevel 1 (
  echo PyInstaller EXE ready in dist\UmbrellaTerminal.
  echo Install Inno Setup 6, then compile UmbrellaInstaller.iss.
  pause
  exit /b 0
)
ISCC.exe "UmbrellaInstaller.iss"
if errorlevel 1 goto :fail
echo Full Windows installer ready in installer_output.
pause
exit /b 0
:fail
echo Build failed. Read errors above.
pause
exit /b 1
