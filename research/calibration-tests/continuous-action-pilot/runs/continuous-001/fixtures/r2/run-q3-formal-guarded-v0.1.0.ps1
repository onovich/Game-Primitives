[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BuildEvidencePath,

    [Parameter(Mandatory = $true)]
    [ValidateSet('config.baseline', 'config.variant')]
    [string]$ConfigurationId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2)]
    [int]$RepetitionIndex,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExecutionPermitPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$FormalOutputRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ToolchainRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$allowedOutputBase = 'D:\GamePrimitivesFormalOutputs'
$expectedPythonPath = 'C:\Python314\python.exe'
$expectedPythonSha256 = 'cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b'
$expectedPythonBytes = 106328
$schemaSha256 = '43457e02c83b9f387319d2eb9213d39f8b4dfcf6ab103ff472367a93e6e792d6'
$requiredCommandFields = @(
    'cmd.server-time',
    'cmd.angle-0',
    'cmd.angle-1',
    'cmd.angle-2',
    'cmd.buttons',
    'cmd.weapon',
    'cmd.forwardmove',
    'cmd.rightmove',
    'cmd.upmove'
)
$processRecords = New-Object System.Collections.Generic.List[object]

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

function Write-LfText {
    param([string]$Path, [string]$Text)
    $normalized = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
}

function Resolve-FixedPythonRuntime {
    param([Parameter(Mandatory = $true)][string]$RequestedPath)

    if (-not [System.IO.Path]::IsPathRooted($RequestedPath)) {
        throw 'PythonPath must be absolute.'
    }
    $resolved = [System.IO.Path]::GetFullPath($RequestedPath)
    if (-not [string]::Equals(
            $resolved,
            $expectedPythonPath,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'PythonPath must resolve to the frozen Python 3.14.3 runtime.'
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw 'The frozen Python runtime is missing.'
    }
    if ((Get-Item -LiteralPath $resolved).Length -ne $expectedPythonBytes) {
        throw 'The frozen Python runtime byte count differs.'
    }
    $actual = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $resolved
    ).Hash.ToLowerInvariant()
    if ($actual -cne $expectedPythonSha256) {
        throw 'The frozen Python runtime SHA-256 differs.'
    }
    return (Resolve-Path -LiteralPath $resolved -ErrorAction Stop).ProviderPath
}

function Find-RepositoryRoot {
    $candidate = [System.IO.DirectoryInfo]::new($PSScriptRoot)
    while ($null -ne $candidate) {
        $tool = Join-Path $candidate.FullName (
            'research/calibration-tests/continuous-action-pilot/' +
            'tools/verify-formal-execution-permit.py'
        )
        if (Test-Path -LiteralPath $tool -PathType Leaf) {
            return $candidate.FullName
        }
        $candidate = $candidate.Parent
    }
    throw 'Could not locate the repository root or execution-permit verifier.'
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + (
        $Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1'
    ) + '"'
}

function Stop-ScopedProcessTree {
    param([int]$ProcessId)
    & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
}

function Invoke-BoundedProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$Label,
        [int]$TimeoutMilliseconds = 120000
    )
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = (
        $Arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }
    ) -join ' '
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $started = $false
    $job = [R2ScopedJobV010]::new()
    try {
        if (-not $process.Start()) {
            throw "Could not start $Label."
        }
        $started = $true
        $pidStarted = $process.Id
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
        $stdout = $stdoutTask.Result
        $stderr = $stderrTask.Result
        $record = [ordered]@{
            exit_code = $exitCode
            label = $Label
            pid = $pidStarted
            timed_out = $false
        }
        $processRecords.Add($record)
        return [pscustomobject]@{
            ExitCode = $exitCode
            StandardError = $stderr
            StandardOutput = $stdout
        }
    }
    finally {
        $job.Dispose()
        if ($started -and -not $process.HasExited) {
            Stop-ScopedProcessTree -ProcessId $process.Id
            $process.WaitForExit()
        }
        $process.Dispose()
    }
}

function Invoke-ExecutionPermitVerifier {
    param(
        [string]$RepositoryRoot,
        [string]$PermitPath,
        [string]$PythonExecutablePath
    )
    $verifier = Join-Path $RepositoryRoot (
        'research/calibration-tests/continuous-action-pilot/' +
        'tools/verify-formal-execution-permit.py'
    )
    $result = Invoke-BoundedProcess `
        -FilePath $PythonExecutablePath `
        -Arguments @(
            '-B',
            $verifier,
            'verify',
            '--repo-root',
            $RepositoryRoot,
            '--permit-path',
            $PermitPath,
            '--case-id',
            'CA-R2'
        ) `
        -WorkingDirectory $RepositoryRoot `
        -Label 'execution-permit-verifier'
    if ($result.ExitCode -ne 0) {
        throw "Execution-permit verification failed: $($result.StandardError.Trim())"
    }
    $lines = @($result.StandardOutput -split '\r?\n' | Where-Object { $_ })
    if ($lines.Count -ne 1) {
        throw 'Execution-permit verifier returned an unexpected response.'
    }
    $value = $lines[0] | ConvertFrom-Json
    if (
        $value.status -cne 'formal_execution_permit_verified' -or
        $value.run_id -cne 'continuous-001' -or
        $value.case_id -cne 'CA-R2' -or
        [string]$value.execution_permit_sha256 -cnotmatch (
            '^(?!0{64})[0-9a-f]{64}$'
        ) -or
        [string]$value.prediction_set_digest -cnotmatch (
            '^(?!0{64})[0-9a-f]{64}$'
        )
    ) {
        throw 'Execution-permit verifier returned the wrong CA-R2 context.'
    }
    if (
        [string]$value.python_runtime.runtime.executable_path -cne
            'C:/Python314/python.exe' -or
        [long]$value.python_runtime.runtime.bytes -ne $expectedPythonBytes -or
        [string]$value.python_runtime.runtime.sha256 -cne
            $expectedPythonSha256
    ) {
        throw 'Execution permit selected the wrong Python runtime.'
    }
    return $value
}

function Resolve-BoundArtifact {
    param(
        [string]$RepositoryRoot,
        [object]$Reference,
        [string]$ExpectedRelativePath,
        [string]$Label,
        [AllowNull()][string]$InvokedPath
    )
    if (
        $null -eq $Reference -or
        [string]$Reference.path -cne $ExpectedRelativePath -or
        [string]$Reference.sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$'
    ) {
        throw "$Label execution-target reference is invalid."
    }
    $full = [System.IO.Path]::GetFullPath(
        (Join-Path $RepositoryRoot $ExpectedRelativePath.Replace('/', '\'))
    )
    $rootPrefix = [System.IO.Path]::GetFullPath(
        $RepositoryRoot
    ).TrimEnd('\') + '\'
    if (
        -not $full.StartsWith(
            $rootPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        -not (Test-Path -LiteralPath $full -PathType Leaf)
    ) {
        throw "$Label path is absent or escapes the repository."
    }
    if (
        -not [string]::IsNullOrEmpty($InvokedPath) -and
        -not $full.Equals(
            [System.IO.Path]::GetFullPath($InvokedPath),
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "$Label path does not select the invoked artifact."
    }
    $actual = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $full
    ).Hash.ToLowerInvariant()
    if ($actual -cne [string]$Reference.sha256) {
        throw "$Label execution-target SHA-256 mismatch."
    }
    return $full
}

function Test-SameOrChild {
    param([string]$Candidate, [string]$Parent)
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\')
    return $candidateFull.Equals(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or $candidateFull.StartsWith(
        $parentFull + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Assert-NoReparseAncestor {
    param([string]$Path)
    $cursor = [System.IO.Path]::GetFullPath($Path)
    while (-not (Test-Path -LiteralPath $cursor)) {
        $parent = Split-Path -Parent $cursor
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $cursor) {
            throw "Cannot resolve an existing ancestor for $Path."
        }
        $cursor = $parent
    }
    while (-not [string]::IsNullOrEmpty($cursor)) {
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse-point path is forbidden: $cursor"
        }
        $parent = Split-Path -Parent $cursor
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $cursor) {
            break
        }
        $cursor = $parent
    }
}

function Resolve-FixedFormalOutputRoot {
    param([string]$RequestedRoot)
    if (
        [string]::IsNullOrWhiteSpace($RequestedRoot) -or
        -not [System.IO.Path]::IsPathRooted($RequestedRoot)
    ) {
        throw 'FormalOutputRoot must be an absolute path.'
    }
    $root = [System.IO.Path]::GetFullPath($RequestedRoot).TrimEnd('\', '/')
    $fixed = [System.IO.Path]::GetFullPath($allowedOutputBase).TrimEnd('\', '/')
    if (-not $root.Equals(
        $fixed,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "FormalOutputRoot must exactly equal $allowedOutputBase."
    }
    return $root
}

function Resolve-SafeOutputLayout {
    param(
        [string]$RepositoryRoot,
        [string]$RequestedRoot,
        [string]$Source,
        [string]$Toolchain,
        [string]$Configuration,
        [int]$Repetition
    )
    foreach ($value in @($Source, $Toolchain)) {
        if (-not [System.IO.Path]::IsPathRooted($value)) {
            throw 'Source and toolchain roots must be absolute.'
        }
    }
    $root = Resolve-FixedFormalOutputRoot -RequestedRoot $RequestedRoot
    $sourceFull = (
        Resolve-Path -LiteralPath $Source -ErrorAction Stop
    ).ProviderPath.TrimEnd('\')
    $toolchainFull = (
        Resolve-Path -LiteralPath $Toolchain -ErrorAction Stop
    ).ProviderPath.TrimEnd('\')
    if ($root -match '\s') {
        throw 'FormalOutputRoot must not contain whitespace.'
    }
    foreach ($forbidden in @($RepositoryRoot, $sourceFull, $toolchainFull)) {
        if (
            (Test-SameOrChild -Candidate $root -Parent $forbidden) -or
            (Test-SameOrChild -Candidate $forbidden -Parent $root)
        ) {
            throw 'Formal output overlaps repository, source, or toolchain.'
        }
    }
    Assert-NoReparseAncestor -Path $root
    $configurationSlug = $Configuration.Substring('config.'.Length)
    $caseRoot = Join-Path $root 'continuous-001\CA-R2'
    $stem = "rep-$Repetition"
    $layout = [ordered]@{
        case_root = $caseRoot
        command = Join-Path $caseRoot (
            "derived\$configurationSlug\$stem.commands.tsv"
        )
        invocation = Join-Path $caseRoot (
            "invocations\$configurationSlug\$stem.json"
        )
        stderr = Join-Path $caseRoot "logs\$configurationSlug\$stem.stderr.log"
        stdout = Join-Path $caseRoot "logs\$configurationSlug\$stem.stdout.log"
        trace = Join-Path $caseRoot "raw\$configurationSlug\$stem.jsonl"
    }
    foreach ($path in $layout.Values) {
        Assert-NoReparseAncestor -Path $path
    }
    foreach ($path in @(
        $layout.command,
        $layout.invocation,
        $layout.stderr,
        $layout.stdout,
        $layout.trace
    )) {
        if (Test-Path -LiteralPath $path) {
            throw "Refusing to overwrite fixed CA-R2 output: $path"
        }
    }
    return $layout
}

function Get-IntegerFieldMap {
    param([object]$Event)
    $map = @{}
    foreach ($field in $Event.fields) {
        if ($map.ContainsKey($field.field_id)) {
            throw "Duplicate command field: $($field.field_id)"
        }
        if ($field.value.value_type -cne 'integer') {
            throw "Command field is not integer: $($field.field_id)"
        }
        $parsed = 0
        if (-not [int]::TryParse(
            $field.value.serialized_value,
            [System.Globalization.NumberStyles]::Integer,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [ref]$parsed
        )) {
            throw "Command field is not canonical integer: $($field.field_id)"
        }
        $map[$field.field_id] = $parsed
    }
    if ($map.Count -ne $requiredCommandFields.Count) {
        throw 'Formal input command field count mismatch.'
    }
    foreach ($fieldId in $requiredCommandFields) {
        if (-not $map.ContainsKey($fieldId)) {
            throw "Formal input command field missing: $fieldId"
        }
    }
    return $map
}

function Convert-FormalInputToCommandLines {
    param([string]$FormalInputPath)
    $formalInput = Get-Content -Raw -Encoding utf8 -LiteralPath $FormalInputPath |
        ConvertFrom-Json
    if (
        $formalInput.artifact_type -cne 'formal_input_trace' -or
        $formalInput.artifact_version -cne '0.1.0' -or
        $formalInput.run_id -cne 'continuous-001' -or
        $formalInput.case_id -cne 'CA-R2' -or
        $formalInput.formal_input_id -cne 'o.b.0002' -or
        $formalInput.stop_boundary_id -cne 'o.b.0030' -or
        $formalInput.time_base.time_base_id -cne 'o.b.0015' -or
        $formalInput.input_events.Count -ne 25
    ) {
        throw 'Formal input does not match the frozen CA-R2 identity.'
    }
    $lines = New-Object System.Collections.Generic.List[string]
    for ($index = 0; $index -lt 25; $index++) {
        $event = $formalInput.input_events[$index]
        $fields = Get-IntegerFieldMap -Event $event
        $expectedTime = ($index + 1) * 8
        if (
            $event.sequence_index -ne $index -or
            $event.event_id -cne ('input.r2.step-{0:D2}' -f $index) -or
            $event.at.serialized_value -cne $expectedTime.ToString() -or
            $fields['cmd.server-time'] -ne $expectedTime -or
            $fields['cmd.angle-0'] -ne 0 -or
            $fields['cmd.angle-1'] -ne 0 -or
            $fields['cmd.angle-2'] -ne 0 -or
            $fields['cmd.buttons'] -ne 0 -or
            $fields['cmd.weapon'] -ne 0 -or
            $fields['cmd.upmove'] -ne 0
        ) {
            throw "Formal input sequence mismatch at step $index."
        }
        $expectedForward = if ($index -lt 5) { 127 } else { 0 }
        $expectedRight = if ($index -lt 5) { 0 } else { 127 }
        if (
            $fields['cmd.forwardmove'] -ne $expectedForward -or
            $fields['cmd.rightmove'] -ne $expectedRight
        ) {
            throw "Formal input direction mismatch at step $index."
        }
        $values = @(
            $fields['cmd.server-time'],
            $fields['cmd.angle-0'],
            $fields['cmd.angle-1'],
            $fields['cmd.angle-2'],
            $fields['cmd.buttons'],
            $fields['cmd.weapon'],
            $fields['cmd.forwardmove'],
            $fields['cmd.rightmove'],
            $fields['cmd.upmove']
        )
        $lines.Add(($values -join "`t"))
    }
    return @($lines)
}

# The permit verifier is the sole authorization boundary and must succeed
# before evidence, formal input, output paths, or traces are opened.
$resolvedPythonPath = Resolve-FixedPythonRuntime -RequestedPath $PythonPath
if (-not [System.IO.Path]::IsPathRooted($ExecutionPermitPath)) {
    throw 'ExecutionPermitPath must be absolute.'
}
$repositoryRoot = Find-RepositoryRoot
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$permit = Invoke-ExecutionPermitVerifier `
    -RepositoryRoot $repositoryRoot `
    -PermitPath $executionPermitFull `
    -PythonExecutablePath $resolvedPythonPath
$target = $permit.execution_target
$base = (
    'research/calibration-tests/continuous-action-pilot/' +
    'runs/continuous-001/fixtures/r2'
)
$runnerPath = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.formal_runner `
    -ExpectedRelativePath "$base/run-q3-formal-guarded-v0.1.0.ps1" `
    -Label 'Formal runner' `
    -InvokedPath $PSCommandPath
$formalInputPath = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.formal_input `
    -ExpectedRelativePath "$base/r2-formal-input-v0.1.0.json" `
    -Label 'Formal input' `
    -InvokedPath $null
$evidencePath = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.support_artifacts.build_readiness_evidence `
    -ExpectedRelativePath "$base/r2-build-readiness-evidence-v0.1.0.json" `
    -Label 'Build readiness evidence' `
    -InvokedPath $BuildEvidencePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.test_body `
    -ExpectedRelativePath "$base/q3-formal-harness-v0.1.0.c" `
    -Label 'Formal harness' `
    -InvokedPath $null
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.raw_trace_schema `
    -ExpectedRelativePath (
        'research/calibration-tests/continuous-action-pilot/' +
        'schema/ca-r2-raw-trace-0.1.0.schema.json'
    ) `
    -Label 'Raw trace schema' `
    -InvokedPath $null

$validatorPath = Resolve-BoundArtifact `
    -RepositoryRoot $repositoryRoot `
    -Reference $target.support_artifacts.build_readiness_verifier `
    -ExpectedRelativePath "$base/verify-r2-build-readiness-v0.1.0.py" `
    -Label 'R2 evidence validator' `
    -InvokedPath $null
$schemaPath = Join-Path $repositoryRoot (
    'research/calibration-tests/continuous-action-pilot/' +
    'schema/r2-build-readiness-evidence-0.1.0.schema.json'
)
foreach ($binding in @(
    @($schemaPath, $schemaSha256, 'R2 evidence schema')
)) {
    if (-not (Test-Path -LiteralPath $binding[0] -PathType Leaf)) {
        throw "$($binding[2]) is missing."
    }
    $actual = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $binding[0]
    ).Hash.ToLowerInvariant()
    if ($actual -cne $binding[1]) {
        throw "$($binding[2]) SHA-256 mismatch."
    }
}
$evidenceVerification = Invoke-BoundedProcess `
    -FilePath $resolvedPythonPath `
    -Arguments @(
        '-B',
        $validatorPath,
        'verify',
        '--repo-root',
        $repositoryRoot,
        '--evidence-path',
        $evidencePath
    ) `
    -WorkingDirectory $repositoryRoot `
    -Label 'r2-build-readiness-verifier'
if ($evidenceVerification.ExitCode -ne 0) {
    throw "R2 build readiness failed: $($evidenceVerification.StandardError.Trim())"
}
$evidenceResult = $evidenceVerification.StandardOutput | ConvertFrom-Json
if (
    $evidenceResult.status -cne 'r2_build_readiness_verified' -or
    $evidenceResult.evidence_sha256 -cne (
        [string]$target.support_artifacts.build_readiness_evidence.sha256
    ) -or
    $evidenceResult.formal_input_read -ne $false
) {
    throw 'R2 build readiness verifier returned the wrong binding.'
}
$selected = $evidenceResult.outputs.PSObject.Properties[
    $ConfigurationId
].Value
$expectedOutputId = if ($ConfigurationId -ceq 'config.baseline') {
    'output.ca-r2.baseline-executable'
} else {
    'output.ca-r2.variant-executable'
}
if (
    $selected.output_id -cne $expectedOutputId -or
    [string]$selected.sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$'
) {
    throw 'R2 selected executable binding is invalid.'
}
$executable = [System.IO.Path]::GetFullPath(
    ([string]$selected.external_path).Replace('/', '\')
)
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw 'R2 selected executable is missing.'
}
if (
    (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash.ToLowerInvariant() `
        -cne [string]$selected.sha256
) {
    throw 'R2 selected executable differs from permit-bound readiness.'
}

$layout = Resolve-SafeOutputLayout `
    -RepositoryRoot $repositoryRoot `
    -RequestedRoot $FormalOutputRoot `
    -Source $SourceRoot `
    -Toolchain $ToolchainRoot `
    -Configuration $ConfigurationId `
    -Repetition $RepetitionIndex

# This is the first formal-input content derivation. Permit verification
# already performed the authorization-bound hash read; parsing still waits
# until evidence, binary, and fail-before-create output preflight succeed.
$formalInputSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $formalInputPath
).Hash.ToLowerInvariant()
if ($formalInputSha256 -cne [string]$target.formal_input.sha256) {
    throw 'Formal input changed after permit verification.'
}
$commandLines = Convert-FormalInputToCommandLines -FormalInputPath $formalInputPath
if (
    (Get-FileHash -Algorithm SHA256 -LiteralPath $formalInputPath).Hash.ToLowerInvariant() `
        -cne $formalInputSha256
) {
    throw 'Formal input changed while deriving commands.'
}

foreach ($directory in @(
    (Split-Path -Parent $layout.command),
    (Split-Path -Parent $layout.invocation),
    (Split-Path -Parent $layout.stderr),
    (Split-Path -Parent $layout.trace)
)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
Write-LfText -Path $layout.command -Text (($commandLines -join "`n") + "`n")

$environmentNames = @(
    'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
    'GAME_PRIMITIVES_FORMAL_INPUT_SHA256',
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
    'GAME_PRIMITIVES_RUN_ID',
    'GAME_PRIMITIVES_CASE_ID'
)
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable(
        $name,
        'Process'
    )
}
try {
    $env:GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256 = (
        [string]$permit.execution_permit_sha256
    )
    $env:GAME_PRIMITIVES_FORMAL_INPUT_SHA256 = $formalInputSha256
    $env:GAME_PRIMITIVES_PREDICTION_SET_DIGEST = (
        [string]$permit.prediction_set_digest
    )
    $env:GAME_PRIMITIVES_RUN_ID = 'continuous-001'
    $env:GAME_PRIMITIVES_CASE_ID = 'CA-R2'

    if (
        (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash.ToLowerInvariant() `
            -cne [string]$selected.sha256
    ) {
        throw 'R2 executable changed immediately before launch.'
    }
    $run = Invoke-BoundedProcess `
        -FilePath $executable `
        -Arguments @(
            '--formal',
            '--input',
            $layout.command,
            '--output',
            $layout.trace
        ) `
        -WorkingDirectory $layout.case_root `
        -Label "execute-$ConfigurationId-repetition-$RepetitionIndex"
    Write-LfText -Path $layout.stdout -Text $run.StandardOutput
    Write-LfText -Path $layout.stderr -Text $run.StandardError
    if (
        $run.ExitCode -ne 0 -or
        $run.StandardOutput.Trim() -cne 'FORMAL_EXECUTION_COMPLETE' -or
        -not [string]::IsNullOrEmpty($run.StandardError) -or
        -not (Test-Path -LiteralPath $layout.trace -PathType Leaf)
    ) {
        throw 'R2 formal executable did not produce its fixed trace.'
    }
}
finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable(
            $name,
            $savedEnvironment[$name],
            'Process'
        )
    }
}

$rawVerifier = Join-Path $repositoryRoot (
    'research/calibration-tests/continuous-action-pilot/' +
    'tools/verify-formal-raw-trace.py'
)
$traceVerificationProcess = Invoke-BoundedProcess `
    -FilePath $resolvedPythonPath `
    -Arguments @(
        '-B',
        $rawVerifier,
        'verify',
        '--repo-root',
        $repositoryRoot,
        '--permit-path',
        $executionPermitFull,
        '--case-id',
        'CA-R2',
        '--trace-path',
        $layout.trace,
        '--configuration-id',
        $ConfigurationId
    ) `
    -WorkingDirectory $repositoryRoot `
    -Label 'r2-raw-trace-verifier'
if ($traceVerificationProcess.ExitCode -ne 0) {
    throw "R2 raw trace verification failed: $(
        $traceVerificationProcess.StandardError.Trim()
    )"
}
$traceVerification = $traceVerificationProcess.StandardOutput | ConvertFrom-Json
$traceSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $layout.trace
).Hash.ToLowerInvariant()
if (
    $traceVerification.status -cne 'formal_raw_trace_verified' -or
    $traceVerification.configuration_id -cne $ConfigurationId -or
    $traceVerification.formal_trace_sha256 -cne $traceSha256
) {
    throw 'R2 strict raw-trace verification returned the wrong binding.'
}

$invocation = [ordered]@{
    artifact_type = 'q3_r2_formal_invocation'
    artifact_version = '0.2.0'
    run_id = 'continuous-001'
    case_id = 'CA-R2'
    configuration_id = $ConfigurationId
    repetition_index = $RepetitionIndex
    execution_permit_sha256 = [string]$permit.execution_permit_sha256
    prediction_set_digest = [string]$permit.prediction_set_digest
    formal_input_sha256 = $formalInputSha256
    formal_input_read = $true
    build_evidence_sha256 = [string]$evidenceResult.evidence_sha256
    executable = [ordered]@{
        output_id = [string]$selected.output_id
        path = $executable.Replace('\', '/')
        sha256 = [string]$selected.sha256
    }
    trace = [ordered]@{
        path = $layout.trace.Replace('\', '/')
        sha256 = $traceSha256
    }
    raw_trace_verification = $traceVerification
    processes = @($processRecords)
    completed_at = [DateTime]::UtcNow.ToString('o')
}
Write-LfText `
    -Path $layout.invocation `
    -Text (($invocation | ConvertTo-Json -Depth 24) + "`n")
$invocation | ConvertTo-Json -Depth 24
