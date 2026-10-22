; Script Inno Setup pour VinaStudio
; Genere un installeur .exe classique (installation, raccourcis, desinstalleur)

#define MyAppName "VINA Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VINA Studio"
#define MyAppExeName "VinaStudio.exe"

[Setup]
AppId={{8B2F6C1A-4E2D-4A9B-9C3E-VINASTUDIO001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=VinaStudio-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
SetupIconFile=src\vinastudio_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer une icone sur le Bureau"; GroupDescription: "Icones supplementaires:"

[Files]
Source: "dist\VinaStudio.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent
