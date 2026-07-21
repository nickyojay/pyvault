; Inno Setup script for PyVault — builds a Windows installer wizard.
;
; Prerequisite: the PyInstaller build has produced dist\PyVault.exe
;   pyinstaller pyvault.spec --clean --noconfirm
; Then compile:
;   iscc packaging\pyvault.iss
; Output: packaging\dist_installer\PyVault-Setup.exe

#define MyAppName "PyVault"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Nick Johnson"
#define MyAppURL "https://github.com/nickyojay/pyvault"
#define MyAppExeName "PyVault.exe"

[Setup]
; A stable, unique AppId so upgrades/uninstalls are tracked correctly.
AppId={{7B3C1E2A-9D44-4F0B-8E21-2C6A0F5B9A10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user install so no administrator rights are required.
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=PyVault-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller produces a single-file exe at the repo root's dist\ folder.
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
