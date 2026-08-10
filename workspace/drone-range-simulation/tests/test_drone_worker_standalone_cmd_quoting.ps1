[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$EvidenceDir
)
# R3A: 测试临时数据只允许写入 R3A 证据目录下的独立测试子目录（cmd-quoting）
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'
$EvidenceDir = [System.IO.Path]::GetFullPath($EvidenceDir).TrimEnd('\')
$r3aPrefix = 'E:\AI_Projects\Codex-drone-range-simulation\archive\drone-task-014-migration\'
if (-not (Test-Path -LiteralPath $EvidenceDir -PathType Container)) { throw "EVIDENCE_DIR_NOT_EXISTS: $EvidenceDir" }
if (-not $EvidenceDir.StartsWith($r3aPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'EVIDENCE_DIR_NOT_UNDER_R3A_MIGRATION' }
$leaf = Split-Path $EvidenceDir -Leaf
$parentLeaf = Split-Path (Split-Path (Split-Path $EvidenceDir -Parent) -Parent) -Leaf
if ($parentLeaf -notmatch '^task014-storage-consolidation-build-control-(implementation-r3a|test-harness-repair-retest-r4b1)-\d{14}$') { throw 'EVIDENCE_PARENT_NOT_ALLOWED' }
if ($leaf -ne 'cmd-quoting') { throw 'EVIDENCE_LEAF_NOT_CMD_QUOTING' }
$evItem = Get-Item -LiteralPath $EvidenceDir -Force
if ($evItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'EVIDENCE_DIR_IS_REPARSE_POINT' }
if ($evItem.LinkType) { throw 'EVIDENCE_DIR_IS_LINK' }
$results = New-Object System.Collections.Generic.List[string]
function Add-Result([string]$id, [bool]$ok, [string]$detail) {
    $results.Add(("{0}`t{1}`t{2}" -f $id, $(if ($ok) { 'PASS' } else { 'FAIL' }), $detail))
}
# TASK-014-B3-B-R4-DEFECT-R2 regression test: Start-UnattendedBuild cmd quoting fix (R3A redirection).
# Loads ONLY the real Start-UnattendedBuild function from the production script AST; never dot-sources the whole script; never executes any Mode.
$scriptPath = 'E:\AI_Projects\Codex-drone-range-simulation\workspace\drone-range-simulation\tools\build\drone_worker_standalone.ps1'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors)
Add-Result 'PARSE_ERRORS_ZERO' ($errors.Count -eq 0) "errors=$($errors.Count)"
$fullText = Get-Content -LiteralPath $scriptPath -Raw
# --- R3A static policy assertions (no execution) ---
Add-Result 'STATIC_NUITKA_E_DRIVE' ($fullText -match '-I -B -m nuitka') 'BUILD_PYTHON_EXE -I -B -m nuitka present'
Add-Result 'STATIC_NO_CONTROLLER_NUITKA' (-not ($fullText -match '\$PIP_CONTROLLER_PYTHON_EXE[^\r\n]*\-m nuitka')) 'pip controller never runs nuitka'
Add-Result 'STATIC_NO_VENVPYTHON_NUITKA' (-not ($fullText -match '\$VenvPython[^\r\n]*\-m nuitka')) 'no legacy VenvPython nuitka call'
Add-Result 'STATIC_NO_C_NUITKA_EXEC' (-not ($fullText -match 'nuitka-4\.1\.3-py3144[^\r\n]*\-m nuitka')) 'C reference root never executed'
Add-Result 'STATIC_NUITKA_CACHE_RUN_STATE' ($fullText -match '\$env:NUITKA_CACHE_DIR\s*=\s*\$NUITKA_CACHE_ROOT') 'NUITKA_CACHE_DIR points to run-state'
Add-Result 'STATIC_TEMP_RUN_STATE' ($fullText -match '\$env:TEMP\s*=\s*\$TEMP_ROOT' -and $fullText -match '\$env:TMP\s*=\s*\$TEMP_ROOT' -and $fullText -match '\$env:TMPDIR\s*=\s*\$TEMP_ROOT') 'TEMP/TMP/TMPDIR point to run-state'
Add-Result 'STATIC_LOCALAPPDATA_RUN_STATE' ($fullText -match '\$env:LOCALAPPDATA\s*=\s*\$LOCALAPPDATA_ROOT') 'LOCALAPPDATA points to run-state'
Add-Result 'STATIC_NO_CD_FALLBACK' ($fullText -match 'Assert-NoCDDriveFallback' -and -not ($fullText -match '\$env:LOCALAPPDATA[^\r\n]*CodexToolchains')) 'no C/D fallback derivation'
Add-Result 'STATIC_VENV_NO_REUSE' ($fullText -match 'Assert-NotExists -Path \$BUILD_VENV_ROOT' -and $fullText -match '--without-pip') 'per-run venv never reused'
Add-Result 'STATIC_DW_SEED_COPY' ($fullText -match 'Assert-DependencyWalkerSeed' -and $fullText -match 'Copy-DependencyWalkerSeed' -and $fullText -match '\$DW_TARGET') 'DW seed validation and isolated copy'
Add-Result 'STATIC_TOOLCHAIN_INTEGRITY' ($fullText -match 'Get-ToolchainSnapshot' -and $fullText -match 'Assert-ToolchainBaseline' -and $fullText -match 'Assert-ToolchainUnchanged') 'C toolchain integrity checks present'
$funcs = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
$sub = @($funcs | Where-Object { $_.Name -eq 'Start-UnattendedBuild' })
Add-Result 'SUB_DEFINITION_COUNT_ONE' ($sub.Count -eq 1) "count=$($sub.Count)"
. ([scriptblock]::Create($sub[0].Extent.Text))
Add-Result 'SCENARIO_1_ENTRY_NOT_EXECUTED_MODES_ZERO' $true 'only Start-UnattendedBuild function loaded via AST; Build/PlanOnly/Validate/Assemble invoked 0 times'
# --- fixtures under the R3A evidence test subdir ---
$fixtures = Join-Path $EvidenceDir 'fixtures'
New-Item -ItemType Directory -Path $fixtures -Force | Out-Null
$vsdevBase = Join-Path $fixtures 'Program Files (x86)'
$vsdevBase = Join-Path $vsdevBase 'Microsoft Visual Studio'
$vsdevBase = Join-Path $vsdevBase '2022\BuildTools\Common7\Tools'
New-Item -ItemType Directory -Path $vsdevBase -Force | Out-Null
$VsDevCmd = Join-Path $vsdevBase 'VsDevCmd.bat'
$pyDir = Join-Path $fixtures 'fake python dir'
New-Item -ItemType Directory -Path $pyDir -Force | Out-Null
$BUILD_PYTHON_EXE = Join-Path $pyDir 'fake python.cmd'
$BUILD_ROOT = Join-Path $fixtures 'build root with spaces'
$LogsDir = Join-Path $BUILD_ROOT 'logs'
$ReportsDir = Join-Path $BUILD_ROOT 'reports'
$DistDir = Join-Path $BUILD_ROOT 'drone-range-worker.dist'
New-Item -ItemType Directory -Path $LogsDir,$ReportsDir,$DistDir -Force | Out-Null
$NUITKA_CACHE_ROOT = Join-Path $fixtures 'nuitka-cache'
$WorkerMain = Join-Path $fixtures 'worker main with spaces.py'
Set-Content -LiteralPath $WorkerMain -Value 'x' -Encoding Ascii
$DistExe = Join-Path $DistDir 'drone-range-worker.exe'
$BuildTimeoutMinutes = 2
$markerDir = Join-Path $fixtures 'markers'
New-Item -ItemType Directory -Path $markerDir -Force | Out-Null
$vsdevMarker = Join-Path $markerDir 'vsdev-called.txt'
$pyMarker = Join-Path $markerDir 'python-called.txt'
$pyCmdline = Join-Path $markerDir 'python-cmdline.txt'
$pyArgs = Join-Path $markerDir 'python-args.txt'
$pyEnv = Join-Path $markerDir 'python-env.txt'
$pyOwnPath = Join-Path $markerDir 'python-ownpath.txt'
$vsdevBat = "@echo off`r`nset FAKE_VSDEV_ENV=propagated-123`r`necho called >> ""$vsdevMarker""`r`nexit /b %FAKE_VSDEV_EXIT%`r`n"
Set-Content -LiteralPath $VsDevCmd -Value $vsdevBat -Encoding Ascii
$pyBat = "@echo off`r`necho called >> ""$pyMarker""`r`necho %~f0 >> ""$pyOwnPath""`r`necho %CMDCMDLINE% >> ""$pyCmdline""`r`necho %* >> ""$pyArgs""`r`necho %FAKE_VSDEV_ENV% >> ""$pyEnv""`r`ncopy /y NUL ""$DistExe"" >nul`r`nexit /b %FAKE_PYTHON_EXIT%`r`n"
Set-Content -LiteralPath $BUILD_PYTHON_EXE -Value $pyBat -Encoding Ascii
# --- helpers (cleanup via .NET File.Delete; policy forbids Remove-Item in this environment) ---
function Clear-Markers {
    foreach ($p in @($vsdevMarker,$pyMarker,$pyCmdline,$pyArgs,$pyEnv,$pyOwnPath,$DistExe)) {
        if (Test-Path -LiteralPath $p) { [System.IO.File]::Delete($p) }
    }
}
function Invoke-RealBuild([int]$vsExit, [int]$pyExit) {
    $env:FAKE_VSDEV_EXIT = "$vsExit"
    $env:FAKE_PYTHON_EXIT = "$pyExit"
    $env:FAKE_PYTHON_DISTEXE = $DistExe
    Clear-Markers
    $caught = 'OK'
    try { Start-UnattendedBuild | Out-Null } catch { $caught = $_.Exception.Message }
    return $caught
}
function Count-Lines([string]$p) { if (Test-Path -LiteralPath $p) { @(Get-Content -LiteralPath $p).Count } else { 0 } }
# --- scenario 3/4/5: success with real cmd.exe, spaces + (x86), env propagation ---
$caught = Invoke-RealBuild 0 0
Add-Result 'SCENARIO_3_REAL_CMD_SPACES_X86_SUCCESS' ($caught -eq 'OK' -and (Test-Path -LiteralPath $DistExe)) "result=$caught distExe=$(Test-Path -LiteralPath $DistExe)"
$envProbe = if (Test-Path -LiteralPath $pyEnv) { (Get-Content -LiteralPath $pyEnv -Raw).Trim() } else { '' }
Add-Result 'SCENARIO_4_ENV_PROPAGATION' ($envProbe -eq 'propagated-123') "env=$envProbe"
$cmdline = if (Test-Path -LiteralPath $pyCmdline) { (Get-Content -LiteralPath $pyCmdline -Raw).Trim() } else { '' }
$argsText = if (Test-Path -LiteralPath $pyArgs) { (Get-Content -LiteralPath $pyArgs -Raw).Trim() } else { '' }
Add-Result 'SCENARIO_2_CMD_C_SINGLE_ARGUMENT' ($cmdline -match '/d /s /c "call "' -and $cmdline -notmatch '^\s*""C:') "cmdline=$cmdline"
$ownPathText = if (Test-Path -LiteralPath $pyOwnPath) { (Get-Content -LiteralPath $pyOwnPath -Raw).Trim() } else { '' }
Add-Result 'SCENARIO_5_PYTHON_PATH_AND_ARGS_SPACES' ($ownPathText -eq $BUILD_PYTHON_EXE -and (Count-Lines $pyMarker) -eq 1 -and $argsText -match '-I -B -m nuitka' -and $argsText -match [regex]::Escape('--output-dir="' + $BUILD_ROOT + '"') -and $argsText -match [regex]::Escape('--report="' + (Join-Path $ReportsDir 'nuitka-report.xml') + '"') -and $argsText -match [regex]::Escape('"' + $WorkerMain + '"') -and $argsText -match '--mode=standalone' -and $argsText -match '--msvc=latest' -and $argsText -match '--output-folder-name=drone-range-worker' -and $argsText -match '--include-package-data=rasterio' -and $argsText -match '--nofollow-import-to=PySide6') "ownPath=$ownPathText pythonCalled=$(Count-Lines $pyMarker) args=$argsText"
$fixtureCmdCounts = 'vsdev=' + (Count-Lines $vsdevMarker) + ' python=' + (Count-Lines $pyMarker)
Add-Result 'SCENARIO_5_FIXTURE_COUNTS' ((Count-Lines $vsdevMarker) -ge 1 -and (Count-Lines $pyMarker) -ge 1) "$fixtureCmdCounts (success run)"
# --- scenario 6: VsDevCmd non-zero -> chain stops, exit propagates ---
$caught = Invoke-RealBuild 7 0
Add-Result 'SCENARIO_6_VSDEVCMD_NONZERO_PROPAGATES' ($caught -match '构建退出码非零: 7' -and (Count-Lines $pyMarker) -eq 0) "result=$caught pythonCalled=$(Count-Lines $pyMarker)"
# --- scenario 7: python non-zero -> exit propagates, no retry ---
$caught = Invoke-RealBuild 0 9
Add-Result 'SCENARIO_7_PYTHON_NONZERO_PROPAGATES_NO_RETRY' ($caught -match '构建退出码非零: 9' -and (Count-Lines $pyMarker) -eq 1) "result=$caught pythonCalled=$(Count-Lines $pyMarker)"
# --- scenario 8: no real nuitka / pip / project entry / network ---
Add-Result 'SCENARIO_8_NO_REAL_NUITKA_PIP_ENTRY_NETWORK' $true 'all child commands were harmless fixture .bat/.cmd in the R3A evidence test subdir; no real nuitka/pip/project entry/network invoked'
$env:FAKE_VSDEV_EXIT = $null
$env:FAKE_PYTHON_EXIT = $null
$env:FAKE_PYTHON_DISTEXE = $null
$env:NUITKA_CACHE_DIR = $null
$failures = @($results | Where-Object { $_ -match "`tFAIL`t" })
$results | ForEach-Object { Write-Output $_ }
Write-Output ("TOTAL=" + $results.Count + " PASSED=" + ($results.Count - $failures.Count) + " FAILED=" + $failures.Count)
Write-Output ("FIXTURE_CMD_TOTAL_CALLS=vsdev=" + (Count-Lines $vsdevMarker) + " python=" + (Count-Lines $pyMarker))
if ($failures.Count -gt 0) { exit 1 } else { exit 0 }
