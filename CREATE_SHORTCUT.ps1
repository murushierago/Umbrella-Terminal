$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { throw "Install dependencies first." }
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Umbrella Terminal.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = ('"' + (Join-Path $root 'umbrella_terminal.py') + '"')
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Umbrella Corporation - secure terminal demo"
$shortcut.Save()
Write-Host "Desktop shortcut created: $shortcutPath"
