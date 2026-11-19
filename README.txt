UMBRELLA CORPORATION // TERMINAL 3.0
=====================================
FAN PROJECT. The interface, calls and authorization are fictional simulations.
The OPTIONAL Windows shutdown function is real.

QUICK START (WINDOWS)
1. Unzip the whole folder to somewhere writable, e.g. Documents.
2. Double-click INSTALL.bat (installs Pygame + OpenCV into a local .venv).
   It also creates a Desktop shortcut. Python 3 and Internet required once.
3. Launch via START.bat or the desktop shortcut.

MAIN LOGIN PIN: 9876
No background music plays before login. Music starts only after login,
when you place your own audio at assets/ambience.mp3.

WRONG PIN / SHUTDOWN SAFETY
By default, REAL SHUTDOWN IS OFF. A wrong PIN triggers a 10-second demo
alarm with no in-app cancel. It then terminates only the fictional session.
To actually schedule a Windows shutdown:
  1. Login with 9876.
  2. Open SECURITY (tab 4).
  3. Click ENABLE (OPT-IN), then CONFIRM ENABLE.
This persists real_shutdown_enabled=true in settings.json.
An incorrect MAIN LOGIN PIN will then schedule a REAL Windows shutdown
via shutdown.exe /s /t 10 and trigger the 10-second siren.
There is deliberately NO CANCEL BUTTON in the application.

HOW TO ABORT A SCHEDULED WINDOWS SHUTDOWN (BEFORE 10 SEC EXPIRES)
Press Win+R, type:  shutdown /a  then Enter.
OR double-click CANCEL_SHUTDOWN.bat (within the 10-second window).
If the timer has already reached zero, shutdown may be underway.
Closing the app, pressing Esc, or killing Pygame DOES NOT abort an OS shutdown.
SAVE YOUR OPEN WORK BEFORE TESTING. Windows may close unsaved applications.
To disable real shutdown for future attempts, use SECURITY -> DISABLE,
or manually set "real_shutdown_enabled": false in settings.json.
Do not use the real setting on a shared PC without everyone's consent.
This does not prevent the normal Windows emergency cancellation command.

SECRET FILES (TAB 6)
Access requires FIVE sequential clearance codes, by default:
  LEVEL 1: 1998
  LEVEL 2: RACCOON
  LEVEL 3: T-VIRUS
  LEVEL 4: ALPHA
  LEVEL 5: REDQUEEN
The codes are editable in settings.json, under "vault_codes" (five strings).
Wrong vault code resets you to level 1 (NO shutdown).
Once unlocked, the vault shows a classified file explorer.
Folders are created in secret_files/ at first launch:
  Ada Wong
  Jill Valentine
  Claire Redfield
  Rebecca Chambers
  Lady Dimitrescu
You can add your own folders and any files inside them. Images (PNG, JPG,
JPEG, WEBP, BMP, GIF) are previewed directly. Other safe common formats
(PDF, TXT, MD, MP4, AVI, MKV, MP3, WAV) can be opened with Windows.
Switching away from SECRET FILES locks it again.
NOTE: The five codes only lock the Pygame UI. They DO NOT encrypt or hide files
from Windows Explorer. Do not store genuinely sensitive documents this way.

CALLS (TAB 5)
Choose Mamut Rahal or Albert Wesker to start a SIMULATED video call.
The remote participant shows a local portrait; the local camera preview
uses your real webcam, if available and you allow it. No recording or upload.
END CALL releases the webcam. C toggles your webcam during a call.

AUDIO
  assets/ambience.mp3 = your custom music (starts AFTER correct main PIN)
  assets/siren.mp3 = your siren for wrong MAIN PIN
Also supports .ogg and .wav. A synthetic fallback siren is provided.

CONTROLS
  1-6 : sections (except while entering vault codes)
  M   : toggle music after login
  C   : toggle local webcam in simulated call
  Esc : exit terminal (except during alarm, when in-app cancellation is disabled)

ADVANCED: FULL .EXE INSTALLER
Run BUILD_WINDOWS_SETUP.bat on Windows. It bundles the app with PyInstaller.
If Inno Setup 6 is on PATH, it also creates an installable .exe in
installer_output. This build step cannot be done natively on Linux.

TIP: Commit source/assets (not your private images or .venv) to Git.
