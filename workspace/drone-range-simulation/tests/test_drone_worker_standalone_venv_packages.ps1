[CmdletBinding()]
param(
    [string]$ScriptPath = 'E:\AI_Projects\Codex-drone-range-simulation\workspace\drone-range-simulation\tools\build\drone_worker_standalone.ps1',
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$EvidenceDir
)
# R3A: 测试临时数据只允许写入 R3A 证据目录下的独立测试子目录（venv-packages）
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'
$EvidenceDir = [System.IO.Path]::GetFullPath($EvidenceDir).TrimEnd('\')
$r3aPrefix = 'E:\AI_Projects\Codex-drone-range-simulation\archive\drone-task-014-migration\'
if (-not (Test-Path -LiteralPath $EvidenceDir -PathType Container)) { throw "EVIDENCE_DIR_NOT_EXISTS: $EvidenceDir" }
if (-not $EvidenceDir.StartsWith($r3aPrefix, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'EVIDENCE_DIR_NOT_UNDER_R3A_MIGRATION' }
$leaf = Split-Path $EvidenceDir -Leaf
$parentLeaf = Split-Path (Split-Path (Split-Path $EvidenceDir -Parent) -Parent) -Leaf
if ($parentLeaf -notmatch '^task014-storage-consolidation-build-control-implementation-r3a-\d{14}$') { throw 'EVIDENCE_PARENT_NOT_R3A' }
if ($leaf -ne 'venv-packages') { throw 'EVIDENCE_LEAF_NOT_VENV_PACKAGES' }
$evItem = Get-Item -LiteralPath $EvidenceDir -Force
if ($evItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'EVIDENCE_DIR_IS_REPARSE_POINT' }
if ($evItem.LinkType) { throw 'EVIDENCE_DIR_IS_LINK' }
$results = New-Object System.Collections.Generic.List[string]
function Add-Result([string]$id, [bool]$ok, [string]$detail) {
    $results.Add(("{0}`t{1}`t{2}" -f $id, $(if ($ok) { 'PASS' } else { 'FAIL' }), $detail))
}
$ExpectedVenvPackages = @(
    'Nuitka==4.1.3','rasterio==1.5.0','pyproj==3.7.2','numpy==2.5.1',
    'affine==2.4.0','attrs==26.1.0','certifi==2026.7.22','click==8.4.2',
    'cligj==0.7.2','pyparsing==3.3.2','colorama==0.4.6',
    'setuptools==80.9.0','wheel==0.45.1'
)
# --- AST: parse script and load ONLY Assert-VenvPackages and Invoke-PipLocked (entry never executed) ---
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($ScriptPath, [ref]$tokens, [ref]$errors)
Add-Result 'PARSE_ERRORS_ZERO' ($errors.Count -eq 0) "errors=$($errors.Count)"
$fullText = Get-Content -LiteralPath $ScriptPath -Raw
$funcs = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
$avp = @($funcs | Where-Object { $_.Name -eq 'Assert-VenvPackages' })
Add-Result 'AVP_DEFINITION_COUNT_ONE' ($avp.Count -eq 1) "count=$($avp.Count)"
. ([scriptblock]::Create($avp[0].Extent.Text))
$ipl = @($funcs | Where-Object { $_.Name -eq 'Invoke-PipLocked' })
Add-Result 'IPL_DEFINITION_COUNT_ONE' ($ipl.Count -eq 1) "count=$($ipl.Count)"
$iplText = $ipl[0].Extent.Text
Add-Result 'ENTRY_NEVER_EXECUTED' $true 'only function scriptblocks created; top-level switch/Mode never ran'
# --- static pip command shape (R3A: pip controller --python -> E venv, no network index) ---
Add-Result 'PIP_GLOBAL_PYTHON' ($iplText -match '--python' -and $iplText -match '\$BUILD_PYTHON_EXE') 'pip --python BUILD_PYTHON_EXE present'
Add-Result 'PIP_NO_INDEX' ($iplText -match '--no-index') '--no-index present'
Add-Result 'PIP_FIND_LINKS' ($iplText -match '--find-links' -and $iplText -match '\$WHEELHOUSE_ROOT') '--find-links WHEELHOUSE_ROOT present'
Add-Result 'PIP_CACHE_DIR' ($iplText -match '--cache-dir' -and $iplText -match '\$PIP_CACHE_ROOT') '--cache-dir PIP_CACHE_ROOT present'
Add-Result 'PIP_REQUIRE_HASHES' ($iplText -match '--require-hashes') '--require-hashes present'
Add-Result 'PIP_ONLY_BINARY' ($iplText -match '--only-binary=:all:') 'nuitka lock: --only-binary=:all:'
Add-Result 'PIP_NO_BUILD_ISOLATION' ($iplText -match '--no-build-isolation') 'worker lock: --no-build-isolation'
Add-Result 'PIP_NO_INDEX_URL' (-not ($iplText -match '--index-url')) 'no --index-url (network index forbidden)'
Add-Result 'PIP_NO_FORBIDDEN_TARGET' (-not ($iplText -match '--user') -and -not ($iplText -match '--target') -and -not ($iplText -match '--prefix') -and -not ($iplText -match '--root')) 'no --user/--target/--prefix/--root'
Add-Result 'PIP_CONTROLLER_EXEC' ($iplText -match '\$PIP_CONTROLLER_PYTHON_EXE') 'executed by PIP_CONTROLLER_PYTHON_EXE'
Add-Result 'PIP_NO_VENVPYTHON' (-not ($iplText -match '\$VenvPython')) 'no legacy VenvPython pip execution'
# --- static script-wide policy assertions (no execution) ---
Add-Result 'STATIC_VENV_CREATE' ($fullText -match '\$BASE_PYTHON_EXE -I -B -m venv --without-pip \$BUILD_VENV_ROOT') 'venv creation via BASE_PYTHON_EXE --without-pip'
Add-Result 'STATIC_PIP_ENV' ($fullText -match 'PIP_CONFIG_FILE' -and $fullText -match 'PYTHONDONTWRITEBYTECODE' -and $fullText -match 'PYTHONNOUSERSITE') 'PIP_CONFIG_FILE + PYTHONDONTWRITEBYTECODE + PYTHONNOUSERSITE'
Add-Result 'STATIC_RUN_STATE_VARS' ($fullText -match '\$RUN_STATE_ROOT' -and $fullText -match '\$BUILD_VENV_ROOT' -and $fullText -match '\$BUILD_PYTHON_EXE' -and $fullText -match '\$NUITKA_CACHE_ROOT' -and $fullText -match '\$PIP_CACHE_ROOT' -and $fullText -match '\$TEMP_ROOT' -and $fullText -match '\$LOCALAPPDATA_ROOT' -and $fullText -match '\$DW_TARGET' -and $fullText -match '\$BUILD_ROOT' -and $fullText -match '\$LOG_EVIDENCE_ROOT') 'all R2B/R3A frozen path variables present'
Add-Result 'STATIC_RUNID_VALIDATION' ($fullText -match 'RunId' -and $fullText -match '\^\[0-9A-Za-z\\-\]\{1,64\}\$') 'RunId safe-char validation present'
Add-Result 'STATIC_NO_CD_FALLBACK' ($fullText -match 'Assert-NoCDDriveFallback' -and -not ($fullText -match '\$env:LOCALAPPDATA[^\r\n]*CodexToolchains')) 'no C/D fallback'
Add-Result 'STATIC_DW' ($fullText -match 'Assert-DependencyWalkerSeed' -and $fullText -match 'Copy-DependencyWalkerSeed' -and $fullText -match '\$DEPENDENCY_WALKER_SEED_ROOT' -and $fullText -match '\$DW_TARGET') 'DW seed validation + copy + target'
Add-Result 'STATIC_TOOLCHAIN_INTEGRITY' ($fullText -match 'Get-ToolchainSnapshot' -and $fullText -match 'Assert-ToolchainBaseline' -and $fullText -match 'Assert-ToolchainUnchanged') 'C toolchain integrity before/after'
Add-Result 'STATIC_NUITKA_E_DRIVE' ($fullText -match '-I -B -m nuitka' -and -not ($fullText -match '\$PIP_CONTROLLER_PYTHON_EXE[^\r\n]*\-m nuitka')) 'Nuitka only via BUILD_PYTHON_EXE -I -B -m nuitka'
# --- lock byte invariance (read-only hash) ---
$lockDir = Split-Path $ScriptPath -Parent
Add-Result 'LOCK_NUITKA_SHA' ((Get-FileHash -LiteralPath (Join-Path $lockDir 'nuitka-build-system-lock.txt') -Algorithm SHA256).Hash -eq '83F111E093BAD00E18D8EE645A55359E4A3B9EA26A1B2D8B91776712A0DB30FB') 'nuitka lock SHA unchanged'
Add-Result 'LOCK_WORKER_SHA' ((Get-FileHash -LiteralPath (Join-Path $lockDir 'worker-build-requirements-lock.txt') -Algorithm SHA256).Hash -eq '4E3BFE284DA2FA6732AAB238B1806AB2B64F6EFFFBFA28D74CF77FC60A6C8181') 'worker lock SHA unchanged'
# --- mock infrastructure (scratch under R3A evidence test subdir; no real python/pip executed) ---
$scratch = Join-Path $EvidenceDir 'scratch'
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$controllerMock = Join-Path $scratch 'mockcontroller.cmd'
$buildMock = Join-Path $scratch 'mockbuild.cmd'
$controllerText = "@echo off`r`nsetlocal enabledelayedexpansion`r`nset `"CMD=%*`"`r`necho %CMD% | findstr /C:`"m.version(`" >nul`r`nif !errorlevel! equ 0 (echo %MOCK_CONTROLLER_PIP% & exit /b 0)`r`necho %CMD% | findstr /C:`"m.distributions()`" >nul`r`nif !errorlevel! equ 0 (echo %MOCK_CONTROLLER_NAMES% & exit /b 0)`r`nexit /b 1`r`n"
Set-Content -LiteralPath $controllerMock -Value $controllerText -Encoding Ascii
$buildText = "@echo off`r`nsetlocal enabledelayedexpansion`r`nset `"CMD=%*`"`r`necho %CMD% | findstr /C:`"json.dumps(sorted`" >nul`r`nif !errorlevel! equ 0 (echo %MOCK_BUILD_JSON% & exit /b 0)`r`nexit /b 1`r`n"
Set-Content -LiteralPath $buildMock -Value $buildText -Encoding Ascii
function Set-Mock([string]$controllerPip, [string]$controllerNames, [string]$buildJson) {
    $env:MOCK_CONTROLLER_PIP = $controllerPip
    $env:MOCK_CONTROLLER_NAMES = $controllerNames
    $env:MOCK_BUILD_JSON = $buildJson
}
function New-PkgJson([string[]]$entries) {
    $objs = @()
    foreach ($e in $entries) {
        $p = $e -split '==', 2
        $objs += [pscustomobject]@{ name = $p[0]; version = $p[1] }
    }
    return ($objs | ConvertTo-Json -Compress)
}
$PIP_CONTROLLER_PYTHON_EXE = $controllerMock
$BUILD_PYTHON_EXE = $buildMock
function Invoke-ExpectFail([string]$id, [string]$fragment) {
    $caught = $null
    try { Assert-VenvPackages | Out-Null; $caught = 'NO_THROW' } catch { $caught = $_.Exception.Message }
    $ok = ($caught -ne 'NO_THROW') -and ($caught -match $fragment)
    Add-Result $id $ok "message=$caught"
}
function Invoke-ExpectPass([string]$id) {
    $caught = $null
    try { Assert-VenvPackages | Out-Null; $caught = 'PASS' } catch { $caught = 'THROW: ' + $_.Exception.Message }
    Add-Result $id ($caught -eq 'PASS') "result=$caught"
}
$base13 = @('Nuitka==4.1.3','rasterio==1.5.0','pyproj==3.7.2','numpy==2.5.1','affine==2.4.0','attrs==26.1.0','certifi==2026.7.22','click==8.4.2','cligj==0.7.2','colorama==0.4.6','pyparsing==3.3.2','setuptools==80.9.0','wheel==0.45.1')
try {
    # Scenario 1: controller pip 26.0.1 + controller only pip + E venv exactly 13 -> PASS
    Set-Mock '26.0.1' 'pip' (New-PkgJson $base13)
    Invoke-ExpectPass 'SCENARIO_1_E13_PASS'
    # Scenario 2: E venv missing a lock package -> FAIL
    Set-Mock '26.0.1' 'pip' (New-PkgJson ($base13 | Where-Object { $_ -ne 'numpy==2.5.1' }))
    Invoke-ExpectFail 'SCENARIO_2_MISSING_LOCK_FAIL' 'lock 包缺失'
    # Scenario 3: E venv wrong lock version -> FAIL
    $bad13 = @($base13 | ForEach-Object { if ($_ -eq 'numpy==2.5.1') { 'numpy==2.5.2' } else { $_ } })
    Set-Mock '26.0.1' 'pip' (New-PkgJson $bad13)
    Invoke-ExpectFail 'SCENARIO_3_WRONG_LOCK_VERSION_FAIL' 'lock 包版本错误'
    # Scenario 4: E venv extra package -> FAIL
    Set-Mock '26.0.1' 'pip' (New-PkgJson ($base13 + 'pytest==9.1.1'))
    Invoke-ExpectFail 'SCENARIO_4_EXTRA_PACKAGE_FAIL' 'E 盘 venv 额外包'
    # Scenario 5: E venv contains pip -> FAIL (pip only on C controller)
    Set-Mock '26.0.1' 'pip' (New-PkgJson ($base13 + 'pip==26.0.1'))
    Invoke-ExpectFail 'SCENARIO_5_E_VENV_PIP_FORBIDDEN' 'E 盘 venv 不得包含 pip'
    # Scenario 6: controller pip wrong version -> FAIL
    Set-Mock '26.0.2' 'pip' (New-PkgJson $base13)
    Invoke-ExpectFail 'SCENARIO_6_CONTROLLER_PIP_WRONG_VERSION' 'C 盘 pip 控制器版本错误'
    # Scenario 7: controller contains lock package -> FAIL (install target contamination)
    Set-Mock '26.0.1' 'pip,Nuitka' (New-PkgJson $base13)
    Invoke-ExpectFail 'SCENARIO_7_CONTROLLER_CONTAMINATED' 'C 盘 pip 控制器包含 lock 包'
    # Scenario 8: repeat pass to prove determinism
    Set-Mock '26.0.1' 'pip' (New-PkgJson $base13)
    Invoke-ExpectPass 'SCENARIO_8_REPEAT_PASS'
} finally {
    $env:MOCK_CONTROLLER_PIP = $null
    $env:MOCK_CONTROLLER_NAMES = $null
    $env:MOCK_BUILD_JSON = $null
    if (Test-Path -LiteralPath $scratch) { [System.IO.Directory]::Delete($scratch, $true) }
}
$failures = @($results | Where-Object { $_ -match "`tFAIL`t" })
$results | ForEach-Object { Write-Output $_ }
Write-Output ("TOTAL=" + $results.Count + " PASSED=" + ($results.Count - $failures.Count) + " FAILED=" + $failures.Count)
if ($failures.Count -gt 0) { exit 1 } else { exit 0 }
