; Optional genuine Windows installer; compile with Inno Setup 6.
#define MyAppName "Umbrella Terminal"
#define MyAppVersion "3.0"
#define MyAppExeName "UmbrellaTerminal.exe"
[Setup]
AppId={{E9E15726-6A91-4890-B4D1-A46BCE92237C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\UmbrellaTerminal
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=Umbrella_Terminal_Setup
WizardStyle=modern
[Files]
Source: "dist\UmbrellaTerminal\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Umbrella Terminal"; Flags: nowait postinstall skipifsilent
