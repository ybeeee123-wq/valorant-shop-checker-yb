#define AppExe "..\dist\VALSHOP\VALSHOP.exe"
#define MyAppVersion GetVersionNumbersString(AppExe)

[Setup]
AppId={{F8B2D89D-437E-4ED0-91CA-D680DF72E2E2}
AppName=VALSHOP
AppVersion={#MyAppVersion}
AppPublisher=VALSHOP
UninstallDisplayName=VALSHOP
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\VALSHOP
DefaultGroupName=VALSHOP
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=VALSHOP-Setup
SetupIconFile=..\companion\assets\valshop.ico
UninstallDisplayIcon={app}\VALSHOP.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\VALSHOP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VALSHOP"; Filename: "{app}\VALSHOP.exe"
Name: "{autodesktop}\VALSHOP"; Filename: "{app}\VALSHOP.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VALSHOP.exe"; Description: "Launch VALSHOP"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "VALSHOP Companion"; Flags: uninsdeletevalue dontcreatekey

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM VALSHOP.exe /F"; Flags: runhidden skipifdoesntexist; RunOnceId: "StopVALSHOP"
