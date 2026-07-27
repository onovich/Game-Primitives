[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SourcePath,

    # Compatibility-only. The pre-gate build must never resolve, test, hash,
    # or open this path. Formal input derivation belongs to the guarded runner.
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$VcVarsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This runner may build and invoke --self-test only. It has no code path that
# supplies the formal execution-permit environment or --formal arguments.

$expectedCommit = 'dbe4ddb10315479fc00086f08e25d968b4b43c49'
$expectedRemote = 'https://github.com/id-Software/Quake-III-Arena.git'
$expectedToolset = '14.50.35717'
$expectedCompiler = '19.50.35723'
$expectedSourceHashes = [ordered]@{
    'code\game\bg_pmove.c' = '3CED04AED8686D3DA051887DC8C4ACE88A24B45A6D0BB4E4D5238CD53CB7A7FC'
    'code\game\bg_slidemove.c' = '327FA83A0C523DA8A7E8B4FBBBBA40CF8870A28613459289EF0E8A865E6BD903'
    'code\game\q_math.c' = '0BCA11954EFA4741C53C5B49492BF671FCBFC70925FD7DCCA09C7AB0D7FF0C29'
    'code\game\q_shared.h' = '7C356992D3F8B722EEB0160C44A0515BD5A83538FFB86190CA138E352E874115'
    'code\game\bg_public.h' = '29679E04BA6F0F730C5CA200410330E057609DA59E563E36D101F329FAFD09E7'
    'code\game\bg_local.h' = '1F8953894410D670367A0BC68A687C4F27958F825E4987B6FCD2F77CA0D40FB1'
}
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$scriptDirectory = Split-Path -Parent $PSCommandPath
$repositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptDirectory '..\..\..\..\..\..\..')
)
$harnessPath = Join-Path $scriptDirectory 'q3-formal-harness-v0.1.0.c'
$compatibilityPath = Join-Path $scriptDirectory 'q3-formal-compatibility-v0.1.0.c'
$headerPath = Join-Path $scriptDirectory 'q3-formal-fixture-v0.1.0.h'
$compatibilityPatchPath = Join-Path $scriptDirectory 'q3-msvc-x64-compatibility-v0.1.0.patch'
$observationPatchPath = Join-Path $scriptDirectory 'q3-observation-v0.1.0.patch'
$variantPatchPath = Join-Path $scriptDirectory 'q3-entry-latch-variant-v0.1.0.patch'
$comparatorPath = Join-Path $scriptDirectory 'compare-q3-formal-traces-v0.1.0.ps1'
$formalRunnerPath = Join-Path $scriptDirectory 'run-q3-formal-guarded-v0.1.0.ps1'
$processRecords = @()

if ($null -eq ('R2ScopedJobV010' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

public sealed class R2ScopedJobV010 : IDisposable
{
    private const UInt32 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private IntPtr handle;

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public Int64 PerProcessUserTimeLimit;
        public Int64 PerJobUserTimeLimit;
        public UInt32 LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public UInt32 ActiveProcessLimit;
        public IntPtr Affinity;
        public UInt32 PriorityClass;
        public UInt32 SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IO_COUNTERS
    {
        public UInt64 ReadOperationCount;
        public UInt64 WriteOperationCount;
        public UInt64 OtherOperationCount;
        public UInt64 ReadTransferCount;
        public UInt64 WriteTransferCount;
        public UInt64 OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr CreateJobObject(
        IntPtr jobAttributes,
        string name
    );

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetInformationJobObject(
        IntPtr job,
        Int32 informationClass,
        ref JOBOBJECT_EXTENDED_LIMIT_INFORMATION information,
        UInt32 informationLength
    );

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AssignProcessToJobObject(
        IntPtr job,
        IntPtr process
    );

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    public R2ScopedJobV010()
    {
        handle = CreateJobObject(IntPtr.Zero, null);
        if (handle == IntPtr.Zero)
            throw new Win32Exception(Marshal.GetLastWin32Error());

        var information = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
        information.BasicLimitInformation.LimitFlags =
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if (!SetInformationJobObject(
            handle,
            9,
            ref information,
            (UInt32)Marshal.SizeOf(information)
        ))
        {
            var error = Marshal.GetLastWin32Error();
            CloseHandle(handle);
            handle = IntPtr.Zero;
            throw new Win32Exception(error);
        }
    }

    public void AddProcess(IntPtr processHandle)
    {
        if (!AssignProcessToJobObject(handle, processHandle))
            throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    public void Dispose()
    {
        if (handle != IntPtr.Zero)
        {
            CloseHandle(handle);
            handle = IntPtr.Zero;
        }
    }
}
'@
}

function Get-FullExplicitPath {
    param([string]$Value, [string]$Label)
    if (-not [System.IO.Path]::IsPathRooted($Value)) {
        throw "$Label must be an absolute path."
    }
    return [System.IO.Path]::GetFullPath($Value)
}

function Test-PathWithin {
    param([string]$Candidate, [string]$Parent)
    $separator = [System.IO.Path]::DirectorySeparatorChar
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\', '/')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')
    return $candidateFull.Equals(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or $candidateFull.StartsWith(
        $parentFull + $separator,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Write-LfText {
    param([string]$Path, [string]$Text)
    $normalized = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
}

function Write-LfLines {
    param([string]$Path, [string[]]$Lines)
    $text = if ($Lines.Count -eq 0) { '' } else { ($Lines -join "`n") + "`n" }
    Write-LfText -Path $Path -Text $text
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Invoke-RecordedProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogPath,
        [string]$Label,
        [int]$TimeoutMilliseconds = 120000
    )

    $argumentLine = ($Arguments | ForEach-Object {
        ConvertTo-ProcessArgument $_
    }) -join ' '
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $argumentLine
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $started = $false
    $job = [R2ScopedJobV010]::new()
    try {
        if (-not $process.Start()) {
            throw "Could not start $Label."
        }
        $started = $true
        $startedPid = $process.Id
        $job.AddProcess($process.Handle)
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $job.Dispose()
            $process.WaitForExit()
            throw "$Label timed out; its process tree was terminated."
        }
        $exitCode = $process.ExitCode
        $job.Dispose()
        $stdoutText = $stdoutTask.Result
        $stderrText = $stderrTask.Result
    }
    finally {
        $job.Dispose()
        if ($started -and -not $process.HasExited) {
            & taskkill.exe /PID $startedPid /T /F 2>$null | Out-Null
            $process.WaitForExit()
        }
        $process.Dispose()
    }
    $stdoutLines = @(
        $stdoutText -split '\r?\n' |
        Where-Object { $_ -ne '' }
    )
    $stderrLines = @(
        $stderrText -split '\r?\n' |
        Where-Object { $_ -ne '' }
    )
    $combined = @($stdoutLines) + @($stderrLines)
    Write-LfLines -Path $LogPath -Lines $combined
    $script:processRecords += [ordered]@{
        label = $Label
        pid = $startedPid
        exit_code = $exitCode
    }
    return [pscustomobject]@{
        ExitCode = $exitCode
        Lines = $combined
        Pid = $startedPid
    }
}

function Assert-ProcessExit {
    param([object]$Result, [int]$Expected, [string]$Label)
    if ($Result.ExitCode -ne $Expected) {
        throw "$Label exited $($Result.ExitCode); expected $Expected."
    }
}

$sourceFull = Get-FullExplicitPath -Value $SourcePath -Label 'SourcePath'
$outputFull = Get-FullExplicitPath -Value $OutputPath -Label 'OutputPath'
$vcvarsFull = Get-FullExplicitPath -Value $VcVarsPath -Label 'VcVarsPath'

foreach ($requiredFile in @(
    $vcvarsFull,
    $harnessPath,
    $compatibilityPath,
    $headerPath,
    $compatibilityPatchPath,
    $observationPatchPath,
    $variantPatchPath,
    $comparatorPath,
    $formalRunnerPath
)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required file is missing: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $sourceFull -PathType Container)) {
    throw "SourcePath is not a directory: $sourceFull"
}
if (Test-Path -LiteralPath $outputFull) {
    throw "OutputPath must be new and absent: $outputFull"
}
if (Test-PathWithin -Candidate $outputFull -Parent $repositoryRoot) {
    throw 'OutputPath must be outside the Game Primitives repository.'
}
if (Test-PathWithin -Candidate $outputFull -Parent $sourceFull) {
    throw 'OutputPath must not be inside the frozen source checkout.'
}

New-Item -ItemType Directory -Path $outputFull | Out-Null
$runLog = Join-Path $outputFull 'build-run.log'
Write-LfText -Path $runLog -Text (
    "CA-R2 formal fixture preparation build`n" +
    "UTC_START=$([DateTime]::UtcNow.ToString('o'))`n" +
    "FORMAL_INPUT_READ=FALSE`n" +
    "FORMAL_INPUT_EXECUTED=FALSE`n" +
    "FORMAL_RESULT_CREATED=FALSE`n"
)

try {
    $origin = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'remote', 'get-url', 'origin') `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'source-origin.log') `
        -Label 'git-origin'
    Assert-ProcessExit $origin 0 'Source origin check'
    if ($origin.Lines.Count -ne 1 -or $origin.Lines[0].Trim() -ne $expectedRemote) {
        throw 'Source origin is not the frozen official repository.'
    }

    $head = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD') `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'source-head.log') `
        -Label 'git-head'
    Assert-ProcessExit $head 0 'Source HEAD check'
    if ($head.Lines.Count -ne 1 -or $head.Lines[0].Trim() -ne $expectedCommit) {
        throw 'Source checkout is not at the frozen commit.'
    }

    $status = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @(
            '-C',
            $sourceFull,
            'status',
            '--porcelain=v1',
            '--untracked-files=all'
        ) `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'source-status.log') `
        -Label 'git-status'
    Assert-ProcessExit $status 0 'Source status check'
    if ($status.Lines.Count -ne 0) {
        throw 'Source checkout is dirty; build refused.'
    }

    foreach ($relativePath in $expectedSourceHashes.Keys) {
        $absolutePath = Join-Path $sourceFull $relativePath
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $absolutePath).Hash
        if ($actualHash -ne $expectedSourceHashes[$relativePath]) {
            throw "Frozen source SHA-256 mismatch: $relativePath"
        }
    }

    $compatibilitySourceDirectory = Join-Path $outputFull 'compatibility-source'
    $patchedSourceRoot = Join-Path $outputFull 'patched-source'
    $patchedGameDirectory = Join-Path $patchedSourceRoot 'code\game'
    $baselineSourceDirectory = Join-Path $outputFull 'fixture-source\baseline'
    $variantSourceDirectory = Join-Path $outputFull 'fixture-source\variant'
    $baselineBuildDirectory = Join-Path $outputFull 'build\baseline'
    $variantBuildDirectory = Join-Path $outputFull 'build\variant'
    foreach ($directory in @(
        $compatibilitySourceDirectory,
        $patchedGameDirectory,
        $baselineSourceDirectory,
        $variantSourceDirectory,
        $baselineBuildDirectory,
        $variantBuildDirectory
    )) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $compatibilityModePath = Join-Path (
        $compatibilitySourceDirectory
    ) 'q3-compatibility-mode-v0.1.0.h'
    Write-LfLines -Path $compatibilityModePath -Lines @(
        '#ifndef GAME_PRIMITIVES_Q3_COMPATIBILITY_MODE_V0_1_0_H',
        '#define GAME_PRIMITIVES_Q3_COMPATIBILITY_MODE_V0_1_0_H',
        '',
        '#error The frozen MSVC x64 compatibility selection has not been applied.',
        '',
        '#endif'
    )

    Copy-Item `
        -LiteralPath (Join-Path $sourceFull 'code\game\bg_pmove.c') `
        -Destination (Join-Path $patchedGameDirectory 'bg_pmove.c')
    Copy-Item -LiteralPath $harnessPath -Destination (
        Join-Path $baselineSourceDirectory 'q3-formal-harness-v0.1.0.c'
    )
    Copy-Item -LiteralPath $harnessPath -Destination (
        Join-Path $variantSourceDirectory 'q3-formal-harness-v0.1.0.c'
    )

    $compatibilityApply = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @(
            'apply',
            '--whitespace=error-all',
            $compatibilityPatchPath
        ) `
        -WorkingDirectory $compatibilitySourceDirectory `
        -LogPath (Join-Path $outputFull 'compatibility-patch.log') `
        -Label 'git-apply-compatibility'
    Assert-ProcessExit $compatibilityApply 0 'Compatibility patch'
    $compatibilityModeLines = @(
        Get-Content -Encoding utf8 -LiteralPath $compatibilityModePath
    )
    if ($compatibilityModeLines -notcontains (
        '#define Q3GP_MSVC_X64_COMPATIBILITY 1'
    ) -or $compatibilityModeLines -match '^#error') {
        throw 'Compatibility patch did not select the frozen MSVC x64 layer.'
    }

    $observationApply = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @(
            'apply',
            '--whitespace=error-all',
            $observationPatchPath
        ) `
        -WorkingDirectory $patchedSourceRoot `
        -LogPath (Join-Path $outputFull 'observation-patch.log') `
        -Label 'git-apply-observation'
    Assert-ProcessExit $observationApply 0 'Observation patch'

    $variantApply = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @(
            'apply',
            '--whitespace=error-all',
            $variantPatchPath
        ) `
        -WorkingDirectory $variantSourceDirectory `
        -LogPath (Join-Path $outputFull 'variant-patch.log') `
        -Label 'git-apply-variant'
    Assert-ProcessExit $variantApply 0 'Variant patch'

    $baselineHarnessCopy = Join-Path $baselineSourceDirectory 'q3-formal-harness-v0.1.0.c'
    $variantHarnessCopy = Join-Path $variantSourceDirectory 'q3-formal-harness-v0.1.0.c'
    $baselineLines = @(Get-Content -Encoding utf8 -LiteralPath $baselineHarnessCopy)
    $variantLines = @(Get-Content -Encoding utf8 -LiteralPath $variantHarnessCopy)
    if ($baselineLines.Count -ne $variantLines.Count) {
        throw 'Variant patch changed the harness line count.'
    }
    $differentIndexes = @()
    for ($lineIndex = 0; $lineIndex -lt $baselineLines.Count; $lineIndex++) {
        if ($baselineLines[$lineIndex] -cne $variantLines[$lineIndex]) {
            $differentIndexes += $lineIndex
        }
    }
    if ($differentIndexes.Count -ne 1 `
        -or $baselineLines[$differentIndexes[0]] -cne (
            '#define Q3GP_ACTIVE_INPUT_POLICY Q3GP_POLICY_RESAMPLE'
        ) `
        -or $variantLines[$differentIndexes[0]] -cne (
            '#define Q3GP_ACTIVE_INPUT_POLICY Q3GP_POLICY_ENTRY_LATCH'
        )) {
        throw 'Variant patch is not the single frozen input-policy change.'
    }
    Write-LfText `
        -Path (Join-Path $outputFull 'variant-difference.log') `
        -Text (
            "DIFFERING_LINE_COUNT=1`n" +
            "ONLY_RELATION=input-forwardmove-rightmove-selection`n" +
            "SERVER_TIME_AND_OTHER_FIELDS=STEPWISE_PRESERVED`n"
        )

    $environmentScript = Join-Path $outputFull 'load-vcvars.cmd'
    [System.IO.File]::WriteAllText(
        $environmentScript,
        (
            "@echo off`r`n" +
            "call `"$vcvarsFull`" >nul`r`n" +
            "if errorlevel 1 exit /b %errorlevel%`r`n" +
            "set`r`n"
        ),
        [System.Text.Encoding]::ASCII
    )
    $environmentResult = Invoke-RecordedProcess `
        -FilePath $env:ComSpec `
        -Arguments @('/d', '/c', $environmentScript) `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'vcvars-environment.log') `
        -Label 'vcvars64'
    Assert-ProcessExit $environmentResult 0 'vcvars64'
    foreach ($line in $environmentResult.Lines) {
        if ($line -match '^([^=][^=]*)=(.*)$') {
            Set-Item -Path ('Env:' + $matches[1]) -Value $matches[2]
        }
    }
    if (-not $env:VCToolsVersion `
        -or $env:VCToolsVersion.TrimEnd('\') -ne $expectedToolset `
        -or $env:VSCMD_ARG_TGT_ARCH -ne 'x64') {
        throw 'vcvars64 selected an unexpected toolset or architecture.'
    }
    $compilerPath = Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe'
    if (-not (Test-Path -LiteralPath $compilerPath -PathType Leaf)) {
        throw "MSVC compiler is missing: $compilerPath"
    }

    $gamePath = Join-Path $sourceFull 'code\game'
    $patchedPmovePath = Join-Path $patchedGameDirectory 'bg_pmove.c'
    $baselineExecutable = Join-Path $baselineBuildDirectory 'q3-r2-baseline.exe'
    $variantExecutable = Join-Path $variantBuildDirectory 'q3-r2-variant.exe'
    $commonArguments = @(
        '/nologo',
        '/Bv',
        '/TC',
        '/Od',
        '/W4',
        '/Brepro',
        '/fp:precise',
        '/DWIN32',
        '/DGAME_PRIMITIVES_OBSERVATION',
        "/I`"$gamePath`"",
        "/I`"$scriptDirectory`"",
        "/I`"$compatibilitySourceDirectory`""
    )

    $reproducibility = [ordered]@{}
    foreach ($build in @(
        [ordered]@{
            Label = 'baseline'
            Source = $baselineHarnessCopy
            Directory = $baselineBuildDirectory
            Executable = $baselineExecutable
        },
        [ordered]@{
            Label = 'variant'
            Source = $variantHarnessCopy
            Directory = $variantBuildDirectory
            Executable = $variantExecutable
        }
    )) {
        $responsePath = Join-Path $build.Directory 'compile.rsp'
        $arguments = @($commonArguments) + @(
            "`"$($build.Source)`"",
            "`"$compatibilityPath`"",
            "`"$patchedPmovePath`"",
            "`"$(Join-Path $gamePath 'bg_slidemove.c')`"",
            "`"$(Join-Path $gamePath 'q_math.c')`"",
            "/Fe`"$($build.Executable)`"",
            '/link',
            '/INCREMENTAL:NO'
        )
        Write-LfLines -Path $responsePath -Lines $arguments
        $compileResult = Invoke-RecordedProcess `
            -FilePath $compilerPath `
            -Arguments @("@$responsePath") `
            -WorkingDirectory $build.Directory `
            -LogPath (Join-Path $outputFull "$($build.Label)-build.log") `
            -Label "$($build.Label)-compile"
        Assert-ProcessExit $compileResult 0 "$($build.Label) build"
        if (-not ($compileResult.Lines -match [regex]::Escape($expectedCompiler))) {
            throw "$($build.Label) build log lacks frozen compiler version."
        }
        if ($compileResult.Lines -match '(?i)\bwarning\s+[A-Z]+\d+\s*:') {
            throw "$($build.Label) build produced compiler warnings."
        }
        if (-not (Test-Path -LiteralPath $build.Executable -PathType Leaf)) {
            throw "$($build.Label) executable was not produced."
        }

        $replicaDirectory = Join-Path $outputFull "repro\$($build.Label)"
        New-Item -ItemType Directory -Path $replicaDirectory -Force | Out-Null
        $replicaExecutable = Join-Path (
            $replicaDirectory
        ) "q3-r2-$($build.Label).exe"
        $replicaResponsePath = Join-Path $replicaDirectory 'compile.rsp'
        $replicaArguments = @($commonArguments) + @(
            "`"$($build.Source)`"",
            "`"$compatibilityPath`"",
            "`"$patchedPmovePath`"",
            "`"$(Join-Path $gamePath 'bg_slidemove.c')`"",
            "`"$(Join-Path $gamePath 'q_math.c')`"",
            "/Fe`"$replicaExecutable`"",
            '/link',
            '/INCREMENTAL:NO'
        )
        Write-LfLines -Path $replicaResponsePath -Lines $replicaArguments
        $replicaCompile = Invoke-RecordedProcess `
            -FilePath $compilerPath `
            -Arguments @("@$replicaResponsePath") `
            -WorkingDirectory $replicaDirectory `
            -LogPath (
                Join-Path $outputFull "$($build.Label)-repro-build.log"
            ) `
            -Label "$($build.Label)-repro-compile"
        Assert-ProcessExit $replicaCompile 0 "$($build.Label) reproducibility build"
        if (-not (Test-Path -LiteralPath $replicaExecutable -PathType Leaf)) {
            throw "$($build.Label) reproducibility executable was not produced."
        }
        $primaryHash = (
            Get-FileHash -Algorithm SHA256 -LiteralPath $build.Executable
        ).Hash.ToLowerInvariant()
        $replicaHash = (
            Get-FileHash -Algorithm SHA256 -LiteralPath $replicaExecutable
        ).Hash.ToLowerInvariant()
        if ($primaryHash -cne $replicaHash) {
            throw "$($build.Label) independent builds are not byte-identical."
        }
        $reproducibility[$build.Label] = [ordered]@{
            algorithm = 'sha256'
            byte_identical = $true
            primary_path = $build.Executable
            replica_path = $replicaExecutable
            sha256 = $primaryHash
        }

        $selfTest = Invoke-RecordedProcess `
            -FilePath $build.Executable `
            -Arguments @('--self-test') `
            -WorkingDirectory $build.Directory `
            -LogPath (Join-Path $outputFull "$($build.Label)-self-test.log") `
            -Label "$($build.Label)-self-test"
        Assert-ProcessExit $selfTest 0 "$($build.Label) self-test"
        if ($selfTest.Lines.Count -ne 1 `
            -or $selfTest.Lines[0].Trim() -ne 'SELF_TEST_PASS') {
            throw "$($build.Label) self-test marker mismatch."
        }

        $refusal = Invoke-RecordedProcess `
            -FilePath $build.Executable `
            -Arguments @() `
            -WorkingDirectory $build.Directory `
            -LogPath (Join-Path $outputFull "$($build.Label)-formal-refusal.log") `
            -Label "$($build.Label)-formal-refusal"
        Assert-ProcessExit $refusal 64 "$($build.Label) formal refusal"
        if ($refusal.Lines.Count -ne 1 `
            -or $refusal.Lines[0].Trim() -ne 'FORMAL_EXECUTION_REFUSED') {
            throw "$($build.Label) formal refusal marker mismatch."
        }
    }

    $comparatorSelfTest = Invoke-RecordedProcess `
        -FilePath 'powershell.exe' `
        -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            $comparatorPath,
            '-SelfTest'
        ) `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'comparator-self-test.log') `
        -Label 'comparator-self-test'
    Assert-ProcessExit $comparatorSelfTest 0 'Comparator self-test'
    $expectedComparatorMarkers = @(
        'FORMAL_OUTPUT_CHILD_ROOT_REJECTED_PASS',
        'PROCESS_TREE_FAILURE_DESCENDANT_PASS',
        'PROCESS_TREE_TIMEOUT_DESCENDANT_PASS',
        'COMPARATOR_SELF_TEST_PASS'
    )
    if (
        $comparatorSelfTest.Lines.Count -ne $expectedComparatorMarkers.Count -or
        (Compare-Object `
            -ReferenceObject $expectedComparatorMarkers `
            -DifferenceObject @($comparatorSelfTest.Lines.Trim()) `
            -SyncWindow 0)
    ) {
        throw 'Comparator self-test marker mismatch.'
    }

    $sourceStatusAfter = Invoke-RecordedProcess `
        -FilePath 'git.exe' `
        -Arguments @(
            '-C',
            $sourceFull,
            'status',
            '--porcelain=v1',
            '--untracked-files=all'
        ) `
        -WorkingDirectory $outputFull `
        -LogPath (Join-Path $outputFull 'source-status-after.log') `
        -Label 'git-status-after'
    Assert-ProcessExit $sourceStatusAfter 0 'Post-build source status'
    if ($sourceStatusAfter.Lines.Count -ne 0) {
        throw 'Frozen source changed during the preparation build.'
    }

    $artifactPaths = [ordered]@{
        fixture_header = $headerPath
        compatibility_layer = $compatibilityPath
        compatibility_patch = $compatibilityPatchPath
        formal_harness = $harnessPath
        observation_patch = $observationPatchPath
        variant_patch = $variantPatchPath
        comparator = $comparatorPath
        build_runner = $PSCommandPath
        guarded_formal_runner = $formalRunnerPath
        generated_compatibility_mode = $compatibilityModePath
        patched_pmove = $patchedPmovePath
        baseline_executable = $baselineExecutable
        variant_executable = $variantExecutable
    }
    $artifacts = [ordered]@{}
    foreach ($artifactId in $artifactPaths.Keys) {
        $artifactPath = $artifactPaths[$artifactId]
        $artifacts[$artifactId] = [ordered]@{
            path = $artifactPath
            sha256 = (
                Get-FileHash -Algorithm SHA256 -LiteralPath $artifactPath
            ).Hash.ToLowerInvariant()
        }
    }

    $evidence = [ordered]@{
        artifact_type = 'q3_r2_formal_fixture_build_evidence'
        artifact_version = '0.1.0'
        run_id = 'continuous-001'
        case_id = 'CA-R2'
        source = [ordered]@{
            repository_url = $expectedRemote
            commit_sha = $expectedCommit
            clean_before_and_after = $true
        }
        platform_scope = 'MSVC-x64'
        compiler = [ordered]@{
            toolset = $expectedToolset
            compiler_version = $expectedCompiler
            options = @('/TC', '/Od', '/W4', '/Brepro', '/fp:precise', '/DWIN32')
            historical_x87_bit_equivalence_claimed = $false
        }
        formal_input_read = $false
        formal_input_executed = $false
        formal_result_created = $false
        reproducibility = $reproducibility
        self_tests = [ordered]@{
            baseline = 'passed'
            variant = 'passed'
            comparator_fictional = 'passed'
            failure_descendant_cleanup = 'passed'
            guarded_formal_refusal = 'passed'
            output_child_root_rejected = 'passed'
            timeout_descendant_cleanup = 'passed'
        }
        variant_difference = [ordered]@{
            differing_source_lines = 1
            controlled_relation = 'forwardmove-rightmove-input-selection'
            all_other_usercmd_fields_stepwise_preserved = $true
        }
        artifacts = $artifacts
        started_processes = $processRecords
        completed_at = [DateTime]::UtcNow.ToString('o')
    }
    Write-LfText `
        -Path (Join-Path $outputFull 'build-evidence.json') `
        -Text (($evidence | ConvertTo-Json -Depth 20) + "`n")
    Write-LfText `
        -Path $runLog `
        -Text (
            (Get-Content -Raw -Encoding utf8 -LiteralPath $runLog) +
            "BUILD=PASS`n" +
            "SELF_TESTS=PASS`n" +
            "FORMAL_GUARDS=REFUSAL_PASS`n" +
            "FORMAL_INPUT_READ=FALSE`n" +
            "FORMAL_INPUT_EXECUTED=FALSE`n" +
            "FORMAL_RESULT_CREATED=FALSE`n" +
            "UTC_END=$([DateTime]::UtcNow.ToString('o'))`n"
        )
    Write-Output 'BUILD_PASS'
    Write-Output 'SELF_TEST_PASS'
    Write-Output 'FORMAL_EXECUTION_NOT_RUN'
    exit 0
} catch {
    $existing = if (Test-Path -LiteralPath $runLog) {
        Get-Content -Raw -Encoding utf8 -LiteralPath $runLog
    } else {
        ''
    }
    Write-LfText `
        -Path $runLog `
        -Text (
            $existing +
            "ERROR=$($_.Exception.Message)`n" +
            "FORMAL_INPUT_EXECUTED=FALSE`n" +
            "FORMAL_RESULT_CREATED=FALSE`n" +
            "UTC_END=$([DateTime]::UtcNow.ToString('o'))`n"
        )
    Write-Error $_
    exit 1
}
