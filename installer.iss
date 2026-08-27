; Inno Setup Script for IO Tester
; This script creates a professional Windows installer for the IO Tester application
; Prerequisites: 
;   1. Build the executable first using build_exe.bat
;   2. Install Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "IO Tester"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company Name"
#define MyAppURL "https://www.yourcompany.com/"
#define MyAppExeName "IOTester.exe"
#define MyAppDescription "Hardware I/O Testing Framework for Controllino Mega"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{IO-TESTER-HARDWARE-FRAMEWORK}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=IOTester_Setup_v{#MyAppVersion}
; Uncomment the line below and add icon.ico file to use custom icon
; SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable and all files from PyInstaller onedir build
Source: "dist\IOTester\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include documentation if available
Source: "docs\*.txt"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; AfterInstall: CreateReadme
; Include license file if you have one
; Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Documentation"; Filename: "{app}\docs"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CreateReadme;
var
  ReadmeFile: String;
begin
  ReadmeFile := ExpandConstant('{app}\README.txt');
  if not FileExists(ReadmeFile) then
  begin
    SaveStringToFile(ReadmeFile, 
      '{#MyAppName} v{#MyAppVersion}' + #13#10 +
      '================================' + #13#10 + #13#10 +
      'Hardware I/O Testing Framework for Controllino Mega' + #13#10 + #13#10 +
      'Installation Directory: ' + ExpandConstant('{app}') + #13#10 +
      'Configuration Files: ' + ExpandConstant('{app}\config') + #13#10 + #13#10 +
      'For support, please contact: {#MyAppPublisher}' + #13#10 +
      'Website: {#MyAppURL}' + #13#10,
      False);
  end;
end;
