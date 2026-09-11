; ===========================================================================
;  VisManager - Windows installer script (Inno Setup 6)
;
;  Produces a proper Setup.exe with Start Menu entry, optional desktop icon,
;  file associations, and a clean uninstaller.
;
;  HOW TO USE
;    1. Build the exe first:      build_windows.bat
;       (this script packages dist\VisManager.exe - it does not compile it)
;    2. Install Inno Setup:       https://jrsoftware.org/isdl.php
;    3. Right-click this file  -> "Compile"
;       or:  iscc installer.iss
;    4. Output lands in:          installer_output\VisManager-Setup-1.0.0.exe
; ===========================================================================

#define MyAppName        "VisManager"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "VisManager"
#define MyAppExeName     "VisManager.exe"

[Setup]
AppId={{8F3C2A91-5D74-4E2B-9A16-7C4E8B1D0F23}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=assets\vismanager.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user install needs no admin rights. Change to "admin" for all-users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"
Name: "assoctga";    Description: "Open .tga files with {#MyAppName}"; \
    GroupDescription: "File associations:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md";            DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "BUILDING.md";          DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Registry]
; Optional .tga association (only if the user ticks the task)
Root: HKA; Subkey: "Software\Classes\.tga\OpenWithProgids"; \
    ValueType: string; ValueName: "VisManager.tga"; ValueData: ""; \
    Flags: uninsdeletevalue; Tasks: assoctga
Root: HKA; Subkey: "Software\Classes\VisManager.tga"; \
    ValueType: string; ValueName: ""; ValueData: "Targa Image"; \
    Flags: uninsdeletekey; Tasks: assoctga
Root: HKA; Subkey: "Software\Classes\VisManager.tga\DefaultIcon"; \
    ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; \
    Tasks: assoctga
Root: HKA; Subkey: "Software\Classes\VisManager.tga\shell\open\command"; \
    ValueType: string; ValueName: ""; \
    ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: assoctga

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the saved keybindings / settings written to the user profile
Type: files; Name: "{userprofile}\.vismanager.json"
Type: files; Name: "{userprofile}\.tga_reviewer_keys.json"
