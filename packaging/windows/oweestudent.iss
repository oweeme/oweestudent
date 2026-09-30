; Instalador POR USUARIO (no pide administrador): se instala en %LOCALAPPDATA%\Programs\OweeStudent
#define MiVersion GetEnv("OWEE_VERSION")
[Setup]
AppName=OweeStudent
AppVersion={#MiVersion}
AppPublisher=OweeStudent
DefaultDirName={localappdata}\Programs\OweeStudent
DefaultGroupName=OweeStudent
PrivilegesRequired=lowest
OutputDir=..\..\salida
OutputBaseFilename=OweeStudent-{#MiVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayName=OweeStudent

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\..\dist\OweeStudent\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\OweeStudent"; Filename: "{app}\OweeStudent.exe"
Name: "{autodesktop}\OweeStudent"; Filename: "{app}\OweeStudent.exe"; Tasks: icono

[Tasks]
Name: "icono"; Description: "Crear icono en el escritorio"

[Run]
Filename: "{app}\OweeStudent.exe"; Description: "Abrir OweeStudent"; Flags: nowait postinstall skipifsilent
