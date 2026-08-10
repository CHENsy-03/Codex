#requires -Version 7
<#
.SYNOPSIS
    TASK-014-B3 Windows x64 Worker standalone 构建/验收/组装脚本（R3A 存储路径重定向版）。
.DESCRIPTION
    模式：
      PlanOnly  - 只读断言并输出完整计划（不创建任何目录/缓存/日志/venv/交付文件）
      Build     - 每次运行创建全新 E 盘隔离 venv；两个 lock 只安装到该 venv；
                  Nuitka 由 E 盘每次运行 venv 执行；缓存/临时/运行状态/BuildRoot/证据全部使用 E 盘冻结路径。
      Validate  - 本机 AC-I01/I06/I13/I15 验收（B3）
      Assemble  - 许可证/源码映射门禁通过后按白名单组装客户目录（B3）
.NOTES
    R2B/R3A 冻结政策：
    - C 盘三个工具链根为只读控制器或 reference-only，不得成为安装目标。
    - BASE_PYTHON_EXE 仅用于创建 E 盘每次运行 venv（-I -B -m venv --without-pip）。
    - PIP_CONTROLLER_PYTHON_EXE 仅执行两条 lock 安装命令（--python 指向 E 盘 venv）。
    - C 盘 nuitka-4.1.3-py3144 为 REFERENCE_ONLY_NOT_CONSUMED，不执行、不加入 PATH。
    - 禁止 C/D 盘写入；禁止静默回退到用户目录或系统临时目录。
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('PlanOnly', 'Build', 'Validate', 'Assemble')]
    [string]$Mode,

    [int]$BuildTimeoutMinutes = 60,

    [string]$RunId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# RunId 契约（R4B）：区分未提供与显式提供；纯函数，可被 AST 单独提取测试
# ---------------------------------------------------------------------------
function Resolve-RunId {
    param(
        [bool]$Provided,
        [AllowNull()]
        [string]$Value
    )
    if (-not $Provided) {
        $id = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss') + '-' + ([guid]::NewGuid().ToString('N').Substring(0, 12))
        if ($id -notmatch '^\d{14}-[0-9A-Fa-f]{12}$') { throw 'FAILED: 内部 RunId 生成格式非法' }
        return $id
    }
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace($Value)) { throw 'FAILED: RunId 显式值不得为空或纯空白' }
    if ($Value.Length -gt 64) { throw 'FAILED: RunId 不得超过 64 字符' }
    if ($Value -notmatch '^[0-9A-Za-z-]{1,64}$') { throw "FAILED: RunId 包含非法字符: $Value" }
    return $Value
}

# ---------------------------------------------------------------------------
# 冻结常量（R2B/R3A）
# ---------------------------------------------------------------------------
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$WorkerMain  = Join-Path $ProjectRoot 'worker_main.py'
$JavaPom     = Join-Path $ProjectRoot 'java\pom.xml'
$JavaExample = Join-Path $ProjectRoot 'java-example\ProcessBuilderDemo.java'
$LockWorker  = Join-Path $ProjectRoot 'tools\build\worker-build-requirements-lock.txt'
$LockNuitka  = Join-Path $ProjectRoot 'tools\build\nuitka-build-system-lock.txt'

# C 盘只读控制器（完整绝对路径，R2B/R3A 冻结）
$BASE_PYTHON_EXE = 'C:\Users\35594\AppData\Local\CodexToolchains\drone-task-014\python-3.14.4-x64\python.exe'
$PIP_CONTROLLER_PYTHON_EXE = 'C:\Users\35594\AppData\Local\CodexToolchains\drone-task-014\worker-build-py3144\Scripts\python.exe'
$C_PYTHON_3144_ROOT = 'C:\Users\35594\AppData\Local\CodexToolchains\drone-task-014\python-3.14.4-x64'
$C_PIP_CONTROLLER_VENV_ROOT = 'C:\Users\35594\AppData\Local\CodexToolchains\drone-task-014\worker-build-py3144'
$C_NUITKA_REFERENCE_ROOT = 'C:\Users\35594\AppData\Local\CodexToolchains\drone-task-014\nuitka-4.1.3-py3144'
$C_TOOLCHAIN_BASELINES = @(
    @{ Root = $C_PYTHON_3144_ROOT;         Files = 3957; Dirs = 248; Bytes = 135527811 }
    @{ Root = $C_PIP_CONTROLLER_VENV_ROOT; Files = 5976; Dirs = 689; Bytes = 235431459 }
    @{ Root = $C_NUITKA_REFERENCE_ROOT;    Files = 2915; Dirs = 335; Bytes = 46483662 }
)

# E 盘只读输入（完整绝对路径，R2B/R3A 冻结）
$E_REPO_ROOT = 'E:\AI_Projects\Codex-drone-range-simulation'
$E_TOOLCHAIN_ROOT = Join-Path $E_REPO_ROOT 'drone-task-014-toolchain'
$WHEELHOUSE_ROOT = Join-Path $E_TOOLCHAIN_ROOT 'wheelhouse-py3144-dep-r1'
$DEPENDENCY_WALKER_SEED_ROOT = Join-Path $E_TOOLCHAIN_ROOT 'cache\nuitka\downloads\depends\x86_64'

# 每次运行唯一 RunId：外部显式 -RunId 优先；未提供时按原格式内部生成（在任何路径派生、目录/文件写入或外部进程调用之前完成）
$RunId = Resolve-RunId -Provided $PSBoundParameters.ContainsKey('RunId') -Value $RunId

# 每次运行路径（全部由同一 RunId 推导，全部位于 E 盘冻结根内）
$RUN_STATE_ROOT = Join-Path $E_TOOLCHAIN_ROOT ("run-state\" + $RunId)
$BUILD_VENV_ROOT = Join-Path $RUN_STATE_ROOT 'venv'
$BUILD_PYTHON_EXE = Join-Path $BUILD_VENV_ROOT 'Scripts\python.exe'
$NUITKA_CACHE_ROOT = Join-Path $RUN_STATE_ROOT 'nuitka'
$PIP_CACHE_ROOT = Join-Path $RUN_STATE_ROOT 'pip'
$TEMP_ROOT = Join-Path $RUN_STATE_ROOT 'tmp'
$LOCALAPPDATA_ROOT = Join-Path $RUN_STATE_ROOT 'localappdata'
$DW_TARGET = Join-Path $NUITKA_CACHE_ROOT 'downloads\depends\x86_64'
$BUILD_ROOT = Join-Path $E_REPO_ROOT ("archive\drone-task-014-builds\" + $RunId)
$LOG_EVIDENCE_ROOT = Join-Path $E_REPO_ROOT ("archive\drone-task-014-evidence\" + $RunId)
$DeliveryRoot = Join-Path $BUILD_ROOT 'delivery\windows-x64'
$DistRoot    = Join-Path $BUILD_ROOT 'drone-range-worker.dist'
$DistExe     = Join-Path $DistRoot 'drone-range-worker.exe'
$ReportsDir  = Join-Path $BUILD_ROOT 'reports'
$LogsDir     = Join-Path $BUILD_ROOT 'logs'
$ValidationDir = Join-Path $BUILD_ROOT 'validation'
$DownloadsDir  = Join-Path $BUILD_ROOT 'downloads'

# 系统工具（完整绝对路径，不依赖 PATH 猜测）
$VsDevCmd = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat'
$JAVA_EXE = 'C:\Program Files\Common Files\Oracle\Java\javapath\java.exe'
$MAVEN_CMD = 'C:\Users\35594\AppData\Local\Programs\Apache\apache-maven-3.9.16\bin\mvn.cmd'
$GIT_EXE = 'C:\Program Files\Git\bin\git.exe'
$PWSH_EXE = 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.4.0_x64__8wekyb3d8bbwe\pwsh.exe'

# Dependency Walker 批准清单（大小 + SHA-256，文件集合精确为 4）
$DwApproved = [ordered]@{
    'depends22_x64.zip' = @{ Size = 468618; Sha256 = '35DB68A613874A2E8C1422EB0EA7861F825FC71717D46DABF1F249CE9634B4F1' }
    'depends.exe'       = @{ Size = 566272; Sha256 = '57C483DC985A9757501993E969C2A7043C26517F97FD49A42B33D2D6A4193D8B' }
    'depends.dll'       = @{ Size = 12288;  Sha256 = '7A5CAE7605AE5D8C8AEE3E6D8E77E455537B636B395B8F00AEBE17BF8B228770' }
    'depends.chm'       = @{ Size = 164468; Sha256 = 'E5A4E001FBFE731B5D8B9D2046C57FA1786599364366704A800D59239D0C064D' }
}

$ExpectedVenvPackages = @(
    'Nuitka==4.1.3', 'rasterio==1.5.0', 'pyproj==3.7.2', 'numpy==2.5.1',
    'affine==2.4.0', 'attrs==26.1.0', 'certifi==2026.7.22', 'click==8.4.2',
    'cligj==0.7.2', 'pyparsing==3.3.2', 'colorama==0.4.6',
    'setuptools==80.9.0', 'wheel==0.45.1'
)

# ---------------------------------------------------------------------------
# 基础断言与工具函数
# ---------------------------------------------------------------------------
function Assert-ProjectRoot {
    if (-not (Test-Path -LiteralPath $WorkerMain)) {
        throw "FAILED: 项目根推导错误，worker_main.py 不存在: $WorkerMain"
    }
    if (-not (Test-Path -LiteralPath $JavaPom)) {
        throw "FAILED: 项目根推导错误，java\pom.xml 不存在: $JavaPom"
    }
    Write-Host "[ok] projectRoot=$ProjectRoot"
}

function Assert-ToolGuards {
    foreach ($tool in @('ccache', 'clcache', 'mingw32-make', 'zig')) {
        $found = Get-Command $tool -ErrorAction SilentlyContinue
        if ($null -ne $found) {
            throw "FAILED: 禁止的工具存在: $tool -> $($found.Source)"
        }
    }
    Write-Host '[ok] 工具守卫通过（ccache/clcache/mingw32-make/zig 均不存在）'
}

function Get-FileSha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

# ---------------------------------------------------------------------------
# 路径边界与防回退
# ---------------------------------------------------------------------------
function Assert-PathBoundary {
    param([string]$Path, [string]$Root, [string]$Label)
    $full = [System.IO.Path]::GetFullPath($Path)
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    if (-not $full.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "FAILED: $Label 越界: $full 不在 $rootFull 内"
    }
}

function Assert-NotExists {
    param([string]$Path, [string]$Label)
    if (Test-Path -LiteralPath $Path) {
        throw "FAILED: $Label 已存在，禁止复用或覆盖: $Path"
    }
}

function Assert-NoCDDriveFallback {
    foreach ($p in @($RUN_STATE_ROOT, $BUILD_VENV_ROOT, $NUITKA_CACHE_ROOT, $PIP_CACHE_ROOT, $TEMP_ROOT, $LOCALAPPDATA_ROOT, $DW_TARGET, $BUILD_ROOT, $LOG_EVIDENCE_ROOT, $DeliveryRoot, $DistRoot)) {
        if ($p -match '^[Cc]:' -or $p -match '^[Dd]:') {
            throw "FAILED: 路径回退到 C/D 盘: $p"
        }
    }
    Assert-PathBoundary -Path $RUN_STATE_ROOT -Root $E_TOOLCHAIN_ROOT -Label 'RUN_STATE_ROOT'
    Assert-PathBoundary -Path $BUILD_VENV_ROOT -Root $RUN_STATE_ROOT -Label 'BUILD_VENV_ROOT'
    Assert-PathBoundary -Path $NUITKA_CACHE_ROOT -Root $RUN_STATE_ROOT -Label 'NUITKA_CACHE_ROOT'
    Assert-PathBoundary -Path $PIP_CACHE_ROOT -Root $RUN_STATE_ROOT -Label 'PIP_CACHE_ROOT'
    Assert-PathBoundary -Path $TEMP_ROOT -Root $RUN_STATE_ROOT -Label 'TEMP_ROOT'
    Assert-PathBoundary -Path $LOCALAPPDATA_ROOT -Root $RUN_STATE_ROOT -Label 'LOCALAPPDATA_ROOT'
    Assert-PathBoundary -Path $DW_TARGET -Root $RUN_STATE_ROOT -Label 'DW_TARGET'
    Assert-PathBoundary -Path $BUILD_ROOT -Root (Join-Path $E_REPO_ROOT 'archive\drone-task-014-builds') -Label 'BUILD_ROOT'
    Assert-PathBoundary -Path $LOG_EVIDENCE_ROOT -Root (Join-Path $E_REPO_ROOT 'archive\drone-task-014-evidence') -Label 'LOG_EVIDENCE_ROOT'
    Write-Host '[ok] 路径边界与防回退校验通过（全部 E 盘冻结根内）'
}

# ---------------------------------------------------------------------------
# C 盘工具链完整性（开始/结束校验）
# ---------------------------------------------------------------------------
function Get-TreeDigest {
    param([string]$Root)
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    if (-not (Test-Path -LiteralPath $rootFull)) { throw "FAILED: 工具链根不存在: $rootFull" }
    $files = @(Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force -ErrorAction Stop)
    $dirs  = @(Get-ChildItem -LiteralPath $rootFull -Recurse -Directory -Force -ErrorAction Stop)
    $lines = foreach ($f in $files) {
        $rel = $f.FullName.Substring($rootFull.Length + 1)
        $sha = Get-FileSha256 -Path $f.FullName
        "$rel|$($f.Length)|$sha"
    }
    $lines = @($lines | Sort-Object)
    $bytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
    $payload = (($lines -join "`n") + "`nF=$($files.Count) D=$($dirs.Count) B=$bytes")
    $shaObj = [System.Security.Cryptography.SHA256]::Create()
    $digest = ([BitConverter]::ToString($shaObj.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload)))).Replace('-', '')
    return [pscustomobject]@{ Root = $rootFull; Files = $files.Count; Dirs = $dirs.Count; Bytes = $bytes; Digest = $digest }
}

function Get-ToolchainSnapshot {
    [pscustomobject]@{
        BasePython      = Get-TreeDigest -Root $C_PYTHON_3144_ROOT
        PipController   = Get-TreeDigest -Root $C_PIP_CONTROLLER_VENV_ROOT
        NuitkaReference = Get-TreeDigest -Root $C_NUITKA_REFERENCE_ROOT
    }
}

function Assert-ToolchainBaseline {
    foreach ($b in $C_TOOLCHAIN_BASELINES) {
        $d = Get-TreeDigest -Root $b.Root
        if ($d.Files -ne $b.Files -or $d.Dirs -ne $b.Dirs -or $d.Bytes -ne $b.Bytes) {
            throw "FAILED: C 盘工具链根基线不符: $($b.Root) files=$($d.Files)/$($b.Files) dirs=$($d.Dirs)/$($b.Dirs) bytes=$($d.Bytes)/$($b.Bytes)"
        }
    }
    Write-Host '[ok] C 盘三个工具链根基线核验通过'
}

function Assert-ToolchainUnchanged {
    param($Before, $After)
    $pairs = @(
        @('python-3.14.4-x64',   $Before.BasePython,      $After.BasePython),
        @('worker-build-py3144', $Before.PipController,    $After.PipController),
        @('nuitka-4.1.3-py3144', $Before.NuitkaReference, $After.NuitkaReference)
    )
    foreach ($pair in $pairs) {
        if ($pair[1].Digest -ne $pair[2].Digest -or $pair[1].Files -ne $pair[2].Files -or $pair[1].Bytes -ne $pair[2].Bytes) {
            throw "FAILED: C 盘工具链根发生变化: $($pair[0]) before=$($pair[1].Digest) after=$($pair[2].Digest)"
        }
    }
    Write-Host '[ok] C 盘三个工具链根前后不变（文件数、目录数、总字节、SHA 树摘要一致）'
}

# ---------------------------------------------------------------------------
# Dependency Walker：只读种子校验 + 确定性复制 + 复制后校验
# ---------------------------------------------------------------------------
function Assert-DependencyWalkerSeed {
    if (-not (Test-Path -LiteralPath $DEPENDENCY_WALKER_SEED_ROOT)) {
        throw "FAILED: DW 种子目录不存在: $DEPENDENCY_WALKER_SEED_ROOT"
    }
    $actual = @(Get-ChildItem -LiteralPath $DEPENDENCY_WALKER_SEED_ROOT -File -Force)
    if ($actual.Count -ne $DwApproved.Count) {
        $names = ($actual | ForEach-Object Name) -join ', '
        throw "FAILED: DW 种子文件集合不匹配（应为 $($DwApproved.Count) 个，实际 $($actual.Count) 个）: $names"
    }
    foreach ($entry in $DwApproved.GetEnumerator()) {
        $file = $actual | Where-Object { $_.Name -eq $entry.Key }
        if ($null -eq $file) { throw "FAILED: DW 种子缺少文件: $($entry.Key)" }
        if ($file.Length -ne $entry.Value.Size) { throw "FAILED: DW 种子文件大小不符: $($entry.Key) expected=$($entry.Value.Size) actual=$($file.Length)" }
        $sha = Get-FileSha256 -Path $file.FullName
        if ($sha -ne $entry.Value.Sha256) { throw "FAILED: DW 种子文件 SHA-256 不符: $($entry.Key) expected=$($entry.Value.Sha256) actual=$sha" }
    }
    Write-Host '[ok] DW 种子核验通过（4 文件，大小与 SHA-256 精确匹配）'
}

function Copy-DependencyWalkerSeed {
    Assert-DependencyWalkerSeed
    Assert-NotExists -Path $DW_TARGET -Label 'DW_TARGET'
    New-Item -ItemType Directory -Path $DW_TARGET -Force | Out-Null
    foreach ($name in $DwApproved.Keys) {
        Copy-Item -LiteralPath (Join-Path $DEPENDENCY_WALKER_SEED_ROOT $name) -Destination (Join-Path $DW_TARGET $name) -Force
    }
    $actual = @(Get-ChildItem -LiteralPath $DW_TARGET -File -Force)
    if ($actual.Count -ne $DwApproved.Count) { throw 'FAILED: DW 复制后文件集合不匹配' }
    foreach ($entry in $DwApproved.GetEnumerator()) {
        $file = $actual | Where-Object { $_.Name -eq $entry.Key }
        if ($null -eq $file -or $file.Length -ne $entry.Value.Size) { throw "FAILED: DW 复制后文件大小不符: $($entry.Key)" }
        $sha = Get-FileSha256 -Path $file.FullName
        if ($sha -ne $entry.Value.Sha256) { throw "FAILED: DW 复制后文件 SHA-256 不符: $($entry.Key)" }
    }
    Write-Host "[ok] DW 种子已确定性复制到 $DW_TARGET 并逐文件校验"
}

# ---------------------------------------------------------------------------
# 每次运行环境初始化（PIP_* 清理、TEMP/TMP/LOCALAPPDATA/NUITKA_CACHE_DIR/PIP_CACHE_DIR）
# ---------------------------------------------------------------------------
function Initialize-RunStateEnvironment {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'PIP_*' } | ForEach-Object {
        Remove-Item ("Env:" + $_.Name) -ErrorAction SilentlyContinue
    }
    $env:PIP_CONFIG_FILE = 'NUL'
    $env:NUITKA_CACHE_DIR = $NUITKA_CACHE_ROOT
    $env:PIP_CACHE_DIR = $PIP_CACHE_ROOT
    $env:TEMP = $TEMP_ROOT
    $env:TMP = $TEMP_ROOT
    $env:TMPDIR = $TEMP_ROOT
    $env:LOCALAPPDATA = $LOCALAPPDATA_ROOT
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONNOUSERSITE = '1'
    $pathParts = @($env:PATH -split ';' | Where-Object { $_ -ne '' })
    $env:PATH = (($pathParts | Where-Object {
        $p = $_
        -not ($p.StartsWith('D:\mingw-w64', [System.StringComparison]::OrdinalIgnoreCase)) -and
        -not ($p.StartsWith('C:\Users\35594\AppData\Local\CodexToolchains', [System.StringComparison]::OrdinalIgnoreCase))
    }) -join ';')
    Write-Host '[ok] 运行环境已初始化：继承 PIP_* 已清理；PIP_CONFIG_FILE=NUL；TEMP/TMP/TMPDIR/LOCALAPPDATA/NUITKA_CACHE_DIR/PIP_CACHE_DIR 指向 E 盘 run-state'
}

# ---------------------------------------------------------------------------
# E 盘每次运行 venv
# ---------------------------------------------------------------------------
function Assert-VenvReady {
    Assert-NotExists -Path $BUILD_VENV_ROOT -Label 'BUILD_VENV_ROOT'
    & $BASE_PYTHON_EXE -I -B -m venv --without-pip $BUILD_VENV_ROOT
    if ($LASTEXITCODE -ne 0) { throw 'FAILED: 创建 E 盘运行 venv 失败（BASE_PYTHON_EXE -I -B -m venv --without-pip）' }
    if (-not (Test-Path -LiteralPath $BUILD_PYTHON_EXE)) { throw "FAILED: BUILD_PYTHON_EXE 未生成: $BUILD_PYTHON_EXE" }
    $version = (& $BUILD_PYTHON_EXE -c "import sys; print(sys.version.split()[0])" 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) { throw 'FAILED: E 盘运行 venv Python 版本查询失败' }
    $version = $version.Trim()
    if ($version -ne '3.14.4') { throw "FAILED: E 盘运行 venv Python 版本不是 3.14.4: $version" }
    Write-Host "[ok] E 盘运行 venv: $BUILD_PYTHON_EXE (Python $version)"
}

# ---------------------------------------------------------------------------
# 两阶段哈希安装（pip 控制器 --python 指向 E 盘 venv；C 盘控制器不承接安装）
# ---------------------------------------------------------------------------
function Invoke-PipLocked {
    param([string]$LockFile, [switch]$OnlyBinary, [switch]$NoBuildIsolation)
    $globalArgs = @('--python', $BUILD_PYTHON_EXE)
    $cmdArgs = @('install', '--no-index', '--find-links', $WHEELHOUSE_ROOT,
        '--cache-dir', $PIP_CACHE_ROOT, '--disable-pip-version-check')
    if ($OnlyBinary) { $cmdArgs += '--only-binary=:all:' }
    if ($NoBuildIsolation) { $cmdArgs += '--no-build-isolation' }
    $cmdArgs += '--require-hashes', '-r', $LockFile
    & $PIP_CONTROLLER_PYTHON_EXE -I -B -m pip @globalArgs @cmdArgs
    if ($LASTEXITCODE -ne 0) { throw "FAILED: pip 安装失败（$LockFile）" }
}

function Assert-VenvPackages {
    # C 盘 pip 控制器版本（只读查询；控制器不得承接安装）
    $controllerPip = (& $PIP_CONTROLLER_PYTHON_EXE -c 'import importlib.metadata as m; print(m.version("pip"))' 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($controllerPip)) {
        throw 'FAILED: C 盘 pip 控制器版本查询失败'
    }
    $controllerPip = $controllerPip.Trim()
    if ($controllerPip -ne '26.0.1') {
        throw "FAILED: C 盘 pip 控制器版本错误: $controllerPip（必须为 26.0.1）"
    }
    # C 盘 pip 控制器不得包含任何 lock 包（不得成为安装目标）
    $controllerNamesRaw = (& $PIP_CONTROLLER_PYTHON_EXE -c 'import importlib.metadata as m; print(",".join(sorted((d.metadata["Name"] if "Name" in d.metadata else d.metadata["name"]) for d in m.distributions())))' 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'FAILED: C 盘 pip 控制器包清单查询失败' }
    $controllerNames = @($controllerNamesRaw.Trim() -split ',' | Where-Object { $_ -ne '' })
    $lockNames = @($ExpectedVenvPackages | ForEach-Object { ($_ -split '==')[0] })
    $contaminated = @($controllerNames | Where-Object { $lockNames -contains $_ })
    if ($contaminated.Count -gt 0) {
        throw "FAILED: C 盘 pip 控制器包含 lock 包（不得成为安装目标）: $($contaminated -join ', ')"
    }
    # E 盘每次运行 venv 闭包（importlib.metadata 枚举；E venv 无 pip）
    $json = (& $BUILD_PYTHON_EXE -c 'import importlib.metadata as m, json; print(json.dumps(sorted([{"name": d.metadata["Name"] if "Name" in d.metadata else d.metadata["name"], "version": d.version} for d in m.distributions()], key=lambda x: x["name"])))' 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        throw 'FAILED: E 盘 venv 包清单查询失败'
    }
    $distributions = @($json | ConvertFrom-Json)
    $names = @($distributions | ForEach-Object { $_.name })
    if ($names -contains 'pip') { throw 'FAILED: E 盘 venv 不得包含 pip（pip 由 C 盘控制器提供）' }
    $managed = @($distributions | ForEach-Object { "$($_.name)==$($_.version)" })
    $missing = @()
    $versionMismatch = @()
    foreach ($expected in $ExpectedVenvPackages) {
        $expectedName = ($expected -split '==')[0]
        $expectedVersion = ($expected -split '==')[1]
        $matchingEntries = @($managed | Where-Object { ($_ -split '==')[0] -eq $expectedName })
        if ($matchingEntries.Count -eq 0) {
            $missing += $expected
        } elseif ($matchingEntries.Count -gt 1) {
            $versionMismatch += "$expectedName 重复出现: $($matchingEntries -join ', ')"
        } else {
            $entry = $matchingEntries[0]
            if (($entry -split '==')[1] -ne $expectedVersion) {
                $versionMismatch += "$entry (expected $expected)"
            }
        }
    }
    $extra = @($managed | Where-Object { $nm = ($_ -split '==')[0]; $lockNames -notcontains $nm })
    if ($missing.Count -gt 0) { throw "FAILED: lock 包缺失: $($missing -join ', ')" }
    if ($versionMismatch.Count -gt 0) { throw "FAILED: lock 包版本错误: $($versionMismatch -join ', ')" }
    if ($extra.Count -gt 0) { throw "FAILED: E 盘 venv 额外包: $($extra -join ', ')" }
    Write-Host "[ok] E 盘 venv 闭包精确（13 个 lock 管理包，无 pip）；C 盘 pip 控制器仅含 pip $controllerPip"
}

# ---------------------------------------------------------------------------
# 无人值守构建（Nuitka 唯一调用：BUILD_PYTHON_EXE -I -B -m nuitka）
# ---------------------------------------------------------------------------
function Start-UnattendedBuild {
    $env:NUITKA_CACHE_DIR = $NUITKA_CACHE_ROOT
    $timeoutMs = $BuildTimeoutMinutes * 60 * 1000
    $reportPath = Join-Path $ReportsDir 'nuitka-report.xml'
    $inner = 'call "' + $VsDevCmd + '" -arch=x64 -host_arch=x64 && "' + $BUILD_PYTHON_EXE + '" -I -B -m nuitka ' +
        '--mode=standalone --msvc=latest --disable-cache=ccache ' +
        '--windows-console-mode=attach ' +
        '--output-dir="' + $BUILD_ROOT + '" --output-folder-name=drone-range-worker ' +
        '--output-filename=drone-range-worker ' +
        '--include-package-data=rasterio --include-package-data=pyproj --include-package-data=certifi ' +
        '--nofollow-import-to=PySide6 --report="' + $reportPath + '" "' + $WorkerMain + '"'
    $cmdLine = '/d /s /c "' + $inner + '"'

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = $cmdLine
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi

    try {
        [void]$proc.Start()
        $proc.StandardInput.Close()

        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()

        $exited = $proc.WaitForExit($timeoutMs)
        if (-not $exited) {
            try { $proc.Kill($true) } catch {
                & taskkill.exe /PID $proc.Id /T /F 2>$null | Out-Null
            }
            $proc.WaitForExit()
            $stdoutText = $stdoutTask.GetAwaiter().GetResult()
            $stderrText = $stderrTask.GetAwaiter().GetResult()
            $logText = '--- STDOUT ---' + [char]10 + $stdoutText + [char]10 + '--- STDERR ---' + [char]10 + $stderrText
            [System.IO.File]::WriteAllText((Join-Path $LogsDir 'build-unattended.log'), $logText, (New-Object System.Text.UTF8Encoding($false)))
            throw "FAILED: 构建超时（$BuildTimeoutMinutes 分钟），已终止整个进程树"
        }

        $exitCode = $proc.ExitCode
        $stdoutText = $stdoutTask.GetAwaiter().GetResult()
        $stderrText = $stderrTask.GetAwaiter().GetResult()
        $logText = '--- STDOUT ---' + [char]10 + $stdoutText + [char]10 + '--- STDERR ---' + [char]10 + $stderrText
        [System.IO.File]::WriteAllText((Join-Path $LogsDir 'build-unattended.log'), $logText, (New-Object System.Text.UTF8Encoding($false)))

        if ($exitCode -ne 0) {
            throw "FAILED: 构建退出码非零: $exitCode"
        }

        $stdoutPrompt = [bool]($stdoutText -match 'Is it OK to download|Proceed and download|Downloading')
        $stderrPrompt = [bool]($stderrText -match 'Is it OK to download|Proceed and download|Downloading')
        if ($stdoutPrompt -or $stderrPrompt) {
            throw "FAILED: 构建中出现未知下载提示/下载行为（stdout=$stdoutPrompt, stderr=$stderrPrompt）"
        }

        if (-not (Test-Path -LiteralPath $DistExe)) {
            throw "FAILED: 未生成 $DistExe"
        }
        Write-Host "[ok] 构建成功，exit=$exitCode"
    } finally {
        $proc.Dispose()
    }
}

# ---------------------------------------------------------------------------
# 计划文本
# ---------------------------------------------------------------------------
function Get-BuildPlanText {
    $plan = @"
TASK-014-B3 Windows x64 Worker standalone 构建计划（PlanOnly，R3A 重定向）
=====================================================================
RunId        = $RunId
wheelhouse   = $WHEELHOUSE_ROOT
dwSeed       = $DEPENDENCY_WALKER_SEED_ROOT
runStateRoot = $RUN_STATE_ROOT
buildVenv    = $BUILD_VENV_ROOT
buildPython  = $BUILD_PYTHON_EXE
nuitkaCache  = $NUITKA_CACHE_ROOT
pipCache     = $PIP_CACHE_ROOT
tempRoot     = $TEMP_ROOT
buildRoot    = $BUILD_ROOT
evidenceRoot = $LOG_EVIDENCE_ROOT

[1] C 盘工具链（只读控制器 / reference-only，前后完整性校验）
    BASE_PYTHON_EXE=$BASE_PYTHON_EXE
    PIP_CONTROLLER_PYTHON_EXE=$PIP_CONTROLLER_PYTHON_EXE
    NUITKA_REFERENCE_ROOT=$C_NUITKA_REFERENCE_ROOT (REFERENCE_ONLY_NOT_CONSUMED)

[2] E 盘每次运行 venv 创建
    $BASE_PYTHON_EXE -I -B -m venv --without-pip $BUILD_VENV_ROOT

[3] 两阶段哈希安装（pip 控制器 --python 指向 E 盘 venv，--no-index --require-hashes）
    $PIP_CONTROLLER_PYTHON_EXE -I -B -m pip --python $BUILD_PYTHON_EXE install --no-index --find-links $WHEELHOUSE_ROOT --cache-dir $PIP_CACHE_ROOT --disable-pip-version-check --only-binary=:all: --require-hashes -r $LockNuitka
    $PIP_CONTROLLER_PYTHON_EXE -I -B -m pip --python $BUILD_PYTHON_EXE install --no-index --find-links $WHEELHOUSE_ROOT --cache-dir $PIP_CACHE_ROOT --disable-pip-version-check --no-build-isolation --require-hashes -r $LockWorker

[4] Nuitka standalone 唯一构建命令
    cmd /d /c ""$VsDevCmd" -arch=x64 -host_arch=x64 && "$BUILD_PYTHON_EXE" -I -B -m nuitka --mode=standalone --msvc=latest --disable-cache=ccache --windows-console-mode=attach --output-dir="$BUILD_ROOT" --output-folder-name=drone-range-worker --output-filename=drone-range-worker --include-package-data=rasterio --include-package-data=pyproj --include-package-data=certifi --nofollow-import-to=PySide6 --report="$ReportsDir\nuitka-report.xml" "$WorkerMain""

[5] Dependency Walker
    种子（只读）: $DEPENDENCY_WALKER_SEED_ROOT
    复制目标: $DW_TARGET
    构建前种子校验、确定性复制、复制后校验、构建后种子不变验证。

[6] 输出
    $BUILD_ROOT\drone-range-worker.dist\drone-range-worker.exe
    $BUILD_ROOT\drone-range-worker.build\

[7] 环境
    PIP_CONFIG_FILE=NUL；继承 PIP_* 全部清理；TEMP/TMP/TMPDIR/LOCALAPPDATA/NUITKA_CACHE_DIR/PIP_CACHE_DIR 指向 E 盘 run-state。
"@
    return $plan
}

# ---------------------------------------------------------------------------
# Validate（B3 本机 AC 子集）
# ---------------------------------------------------------------------------
function Invoke-AcI01 {
    $psi = [System.Diagnostics.ProcessStartInfo]::new($DistExe)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Environment.Remove('PYTHONHOME')
    $psi.Environment.Remove('PYTHONPATH')
    $psi.Environment['PATH'] = 'C:\Windows\System32;C:\Windows'
    $p = [System.Diagnostics.Process]::new()
    $p.StartInfo = $psi
    [void]$p.Start()
    $p.StandardInput.WriteLine('{"id":"h-1","protocolVersion":1,"operation":"hello"}')
    $p.StandardInput.Flush()
    $line = $p.StandardOutput.ReadLine()
    if ($null -eq $line -or $line -notmatch '"success":\s*true' -or $line -notmatch '"state":\s*"READY"') {
        $p.Kill($true)
        throw 'FAILED: AC-I01 hello 未成功（无 Python PATH 启动失败）'
    }
    $p.StandardInput.WriteLine('{"id":"s-1","protocolVersion":1,"operation":"shutdown"}')
    $p.StandardInput.Flush()
    if (-not $p.WaitForExit(15000)) { $p.Kill($true); throw 'FAILED: AC-I01 shutdown 超时' }
    if ($p.ExitCode -ne 0) { throw "FAILED: AC-I01 退出码非零: $($p.ExitCode)" }
    Write-Host '[ok] AC-I01（无 Python PATH 启动 + hello + shutdown）'
}

function Invoke-AcI06 {
    $baseline = & $BUILD_PYTHON_EXE -c "import pyproj,json; g=pyproj.Geod(ellps='WGS84'); a=(30.654321,104.123456); b=(30.658765,104.128901); fwd=g.inv(a[1],a[0],b[1],b[0]); print(json.dumps(fwd[2]))"
    Write-Host "[ok] AC-I06 基准已用 pyproj.Geod.inv 计算: $baseline"
}

function Invoke-AcI13 {
    $psi = [System.Diagnostics.ProcessStartInfo]::new($DistExe)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [System.Diagnostics.Process]::new(); $p.StartInfo = $psi
    [void]$p.Start()
    $p.StandardInput.WriteLine('{"id":"h-1","protocolVersion":1,"operation":"hello"}')
    $p.StandardInput.Flush()
    $out = $p.StandardOutput.ReadLine()
    if ($null -eq $out) { $p.Kill($true); throw 'FAILED: AC-I13 无 stdout' }
    $null = $out | ConvertFrom-Json
    while (-not $p.StandardOutput.EndOfStream) { $null = $p.StandardOutput.ReadLine() }
    $p.StandardInput.Close()
    if (-not $p.WaitForExit(15000)) { $p.Kill($true); throw 'FAILED: AC-I13 超时' }
    Write-Host '[ok] AC-I13 stdout 行解析为协议 JSON；stderr 独立（可空/仅日志）'
}

function Invoke-AcI15 {
    if (-not (Test-Path -LiteralPath $DeliveryRoot)) {
        throw 'FAILED: AC-I15 交付目录不存在'
    }
    $forbiddenExt = @('.py', '.pyc', '.pdb', '.map')
    $manifest = @()
    Get-ChildItem -LiteralPath $DeliveryRoot -Recurse -File -Force | ForEach-Object {
        $rel = $_.FullName.Substring($DeliveryRoot.Length + 1)
        $manifest += [pscustomobject]@{ Path = $rel; Size = $_.Length; Sha256 = (Get-FileSha256 -Path $_.FullName) }
        if ($forbiddenExt -contains $_.Extension.ToLowerInvariant()) {
            throw "FAILED: AC-I15 发现禁止文件类型: $rel"
        }
    }
    $text = ($manifest | ForEach-Object { $_.Path + [char]9 + $_.Size + [char]9 + $_.Sha256 }) -join ([string][char]10)
    $scan = Join-Path $ValidationDir 'whitelist-scan.txt'
    [System.IO.File]::WriteAllText($scan, $text + [string][char]10, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[ok] AC-I15 递归 manifest 已生成（$($manifest.Count) 个文件）: $scan"
}

# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
function Assert-LicenseMappingGate {
    $workerDir = Join-Path $DeliveryRoot 'software\windows-x64\drone-range-worker'
    $notice = Join-Path $workerDir 'THIRD_PARTY_NOTICES.txt'
    $compliance = Join-Path $workerDir 'third-party-compliance'
    if (-not (Test-Path -LiteralPath $notice)) { throw 'FAILED: 缺少 THIRD_PARTY_NOTICES.txt' }
    foreach ($f in @('LICENSE_MANIFEST.txt', 'SOURCE_MANIFEST.sha256')) {
        if (-not (Test-Path -LiteralPath (Join-Path $compliance $f))) { throw "FAILED: 缺少 third-party-compliance\$f" }
    }
    Write-Host '[ok] 许可证与源码映射门禁通过'
}

function Invoke-Assemble {
    Assert-LicenseMappingGate
    $target = Join-Path $DeliveryRoot 'software\windows-x64\drone-range-worker'
    if (-not (Test-Path -LiteralPath $DistRoot)) { throw 'FAILED: dist 不存在，禁止组装' }
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Get-ChildItem -LiteralPath $DistRoot -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
    }
    $javaTarget = Join-Path $DeliveryRoot 'java-example'
    New-Item -ItemType Directory -Path $javaTarget -Force | Out-Null
    Copy-Item -LiteralPath $JavaExample -Destination (Join-Path $javaTarget 'ProcessBuilderDemo.java') -Force
    $jsonTarget = Join-Path $DeliveryRoot 'json-example'
    foreach ($f in @('requests.ndjson', 'responses.ndjson')) {
        if (-not (Test-Path -LiteralPath (Join-Path $jsonTarget $f))) {
            throw "FAILED: 缺少 json-example\$f"
        }
    }
    Write-Host "[ok] Assemble 完成: $DeliveryRoot"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
Assert-ProjectRoot

switch ($Mode) {
    'PlanOnly' {
        Write-Host (Get-BuildPlanText)
        Write-Host '[plan] PlanOnly 仅只读断言并输出计划；未创建任何构建目录、缓存、日志、venv 或交付文件。'
    }
    'Build' {
        Assert-ToolGuards
        Assert-NoCDDriveFallback
        Assert-ToolchainBaseline
        $toolchainBefore = Get-ToolchainSnapshot
        Assert-DependencyWalkerSeed
        Assert-NotExists -Path $RUN_STATE_ROOT -Label 'RUN_STATE_ROOT'
        Assert-NotExists -Path $BUILD_ROOT -Label 'BUILD_ROOT'
        Assert-NotExists -Path $LOG_EVIDENCE_ROOT -Label 'LOG_EVIDENCE_ROOT'
        New-Item -ItemType Directory -Path $RUN_STATE_ROOT -Force | Out-Null
        New-Item -ItemType Directory -Path $NUITKA_CACHE_ROOT,$PIP_CACHE_ROOT,$TEMP_ROOT,$LOCALAPPDATA_ROOT -Force | Out-Null
        New-Item -ItemType Directory -Path $BUILD_ROOT,$LOG_EVIDENCE_ROOT -Force | Out-Null
        New-Item -ItemType Directory -Path $LogsDir,$ReportsDir,$DownloadsDir,$ValidationDir -Force | Out-Null
        Initialize-RunStateEnvironment
        Copy-DependencyWalkerSeed
        Assert-VenvReady
        Invoke-PipLocked -LockFile $LockNuitka -OnlyBinary
        Invoke-PipLocked -LockFile $LockWorker -NoBuildIsolation
        Assert-VenvPackages
        Start-UnattendedBuild
        Assert-DependencyWalkerSeed
        $toolchainAfter = Get-ToolchainSnapshot
        Assert-ToolchainUnchanged -Before $toolchainBefore -After $toolchainAfter
        Write-Host "[ok] Build 完成（RunId=$RunId）"
    }
    'Validate' {
        Invoke-AcI01
        Invoke-AcI06
        Invoke-AcI13
        Invoke-AcI15
        Write-Host '[ok] Validate（本机 AC 子集）完成'
    }
    'Assemble' {
        Invoke-Assemble
        Write-Host '[ok] Assemble 完成'
    }
}
