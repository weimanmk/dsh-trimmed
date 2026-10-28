; DSH Trimmed installer (Inno Setup 6).
;
; Built by the package-windows.yml workflow: ISCC.exe is invoked with
;   /DStageDir=<staged installer tree> /DAppVersion=<cli package version>
; The staged tree holds node.exe, dsh-trimmed.cmd, README-INSTALL.txt,
; STAGE-INFO.txt and the materialized app/ tree (no symlinks).
; Per-user install, no elevation, unsigned (SmartScreen will warn).
; Inno Setup 6 handles the long pnpm-store paths inside app/.

#ifndef StageDir
  #define StageDir "installer-stage"
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=DSH Trimmed
AppVersion={#AppVersion}
AppPublisher=DeepSeek Harness (trimmed build)
AppPublisherURL=https://github.com/weimanmk/dsh-trimmed
DefaultDirName={localappdata}\Programs\dsh-trimmed
DefaultGroupName=DSH Trimmed
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
OutputBaseFilename=dsh-trimmed-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=DSH Trimmed
DisableDirPage=no

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DSH Trimmed"; Filename: "{cmd}"; Parameters: "/k ""{app}\dsh-trimmed.cmd"" --help"; WorkingDir: "{app}"
Name: "{group}\Uninstall DSH Trimmed"; Filename: "{uninstallexe}"

; app/ is created by setup-tree.cjs at install time, not by [Files], so the
; uninstaller does not know about it; without this the install dir survives
; uninstall (run #15: uninstall exited 0 but the dir remained). Section
; comments use semicolons, not braces (braces are only comments in [Code]).
[UninstallDelete]
Type: filesandordirs; Name: "{app}\app"
Type: dirifempty; Name: "{app}\app"
Type: files; Name: "{app}\setup-tree-error.log"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
const
  { Prefixed: Inno Setup 6.7+ predefines HWND_BROADCAST, so an
    unprefixed declaration is a duplicate identifier (run #11). }
  DSH_HWND_BROADCAST = $FFFF;
  DSH_WM_SETTINGCHANGE = $001A;
  DSH_SMTO_ABORTIFHUNG = $0002;

function SendMessageTimeout(hWnd: Longint; Msg: Cardinal; wParam: Longint; lParam: String; fuFlags: Cardinal; uTimeout: Cardinal; var lpdwResult: Cardinal): Longint;
  external 'SendMessageTimeoutA@user32.dll stdcall';

procedure BroadcastEnvironmentChange();
var
  Res: Cardinal;
begin
  SendMessageTimeout(DSH_HWND_BROADCAST, DSH_WM_SETTINGCHANGE, 0, 'Environment', DSH_SMTO_ABORTIFHUNG, 5000, Res);
end;

function NeedsAddPath(Param: String): Boolean;
var
  OrigPath: String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    Result := True
  else
    Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure RemovePath(PathToRemove: String);
var
  OrigPath, NewPath, Rest, Token: String;
  P: Integer;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    Exit;
  NewPath := '';
  Rest := OrigPath;
  while Rest <> '' do
  begin
    P := Pos(';', Rest);
    if P = 0 then
    begin
      Token := Rest;
      Rest := '';
    end
    else
    begin
      Token := Copy(Rest, 1, P - 1);
      Rest := Copy(Rest, P + 1, Length(Rest));
    end;
    if CompareText(Token, PathToRemove) <> 0 then
    begin
      if NewPath <> '' then
        NewPath := NewPath + ';';
      NewPath := NewPath + Token;
    end;
  end;
  RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    BroadcastEnvironmentChange();
    { Rebuild the runtime tree from store/ + app-manifest.json. This must
      fail the install loudly: a silent setup failure would leave a
      broken CLI that looks installed. }
    Log('setup-tree: launching ' + ExpandConstant('{app}\node.exe') + ' ' + ExpandConstant('{app}\setup-tree.cjs'));
    if not Exec(ExpandConstant('{app}\node.exe'),
      '"' + ExpandConstant('{app}\setup-tree.cjs') + '" "' + ExpandConstant('{app}') + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Could not run setup-tree.cjs (Exec failed).');
    Log('setup-tree: exit code ' + IntToStr(ResultCode));
    if ResultCode <> 0 then
      RaiseException('setup-tree.cjs failed with exit code ' + IntToStr(ResultCode) + '.');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemovePath(ExpandConstant('{app}'));
    BroadcastEnvironmentChange();
  end;
end;
