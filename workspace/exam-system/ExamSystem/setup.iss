; 考试系统安装脚本
#define AppName "考试系统"
#define AppVersion "1.0.0"
#define AppExeName "考试系统.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=.
OutputBaseFilename=考试系统安装程序
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Files]
Source: "release\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\backend\ExamSystem.exe"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "release\config\config.yaml"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "release\data\questions\default.json"; DestDir: "{app}\data\questions"; Flags: ignoreversion

[Dirs]
Name: "{app}\data\sessions"
Name: "{app}\logs"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "运行考试系统"; Flags: postinstall nowait skipifsilent shellexec
