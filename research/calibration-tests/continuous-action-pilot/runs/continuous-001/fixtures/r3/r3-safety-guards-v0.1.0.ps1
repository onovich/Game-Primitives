Set-StrictMode -Version Latest

function Get-R3CanonicalPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $full = [System.IO.Path]::GetFullPath(
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    )
    $volumeRoot = [System.IO.Path]::GetPathRoot($full)
    if ($full.TrimEnd('\').Equals(
            $volumeRoot.TrimEnd('\'),
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        return $volumeRoot
    }
    return $full.TrimEnd('\')
}

function Test-R3SameOrChildPath {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

    $candidateFull = (Get-R3CanonicalPath -Path $Candidate).TrimEnd('\')
    $parentFull = (Get-R3CanonicalPath -Path $Parent).TrimEnd('\')
    return $candidateFull.Equals(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or $candidateFull.StartsWith(
        $parentFull + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Test-R3PathsOverlap {
    param(
        [Parameter(Mandatory = $true)][string] $Left,
        [Parameter(Mandatory = $true)][string] $Right
    )

    return (Test-R3SameOrChildPath -Candidate $Left -Parent $Right) -or
        (Test-R3SameOrChildPath -Candidate $Right -Parent $Left)
}

function Assert-R3NoReparsePoint {
    param([Parameter(Mandatory = $true)][string] $Path)

    $cursor = Get-R3CanonicalPath -Path $Path
    while (-not [string]::IsNullOrEmpty($cursor)) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "R3 path crosses a reparse point: $cursor"
            }
        }
        $cursorKey = $cursor.TrimEnd('\')
        $volumeRoot =
            [System.IO.Path]::GetPathRoot($cursor).TrimEnd('\')
        if ($cursorKey.Equals(
                $volumeRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            break
        }
        $parent = [System.IO.Directory]::GetParent($cursor)
        if ($null -eq $parent -or
            $parent.FullName.TrimEnd('\').Equals(
                $cursorKey,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            break
        }
        $cursor = $parent.FullName
    }
}

function Assert-R3ProtectedRootSeparation {
    param(
        [Parameter(Mandatory = $true)][string] $CandidateRoot,
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [string] $SourceRoot,
        [string] $DotnetPath
    )

    $candidate = Get-R3CanonicalPath -Path $CandidateRoot
    $protected = @(
        [pscustomobject]@{
            label = 'repository'
            path = Get-R3CanonicalPath -Path $RepositoryRoot
        }
    )
    if (-not [string]::IsNullOrEmpty($SourceRoot)) {
        $protected += [pscustomobject]@{
            label = 'source'
            path = Get-R3CanonicalPath -Path $SourceRoot
        }
    }
    if (-not [string]::IsNullOrEmpty($DotnetPath)) {
        $protected += [pscustomobject]@{
            label = 'toolchain'
            path = Get-R3CanonicalPath -Path (Split-Path -Parent $DotnetPath)
        }
    }
    foreach ($entry in $protected) {
        if (Test-R3PathsOverlap -Left $candidate -Right $entry.path) {
            throw "R3 candidate root overlaps the $($entry.label) root."
        }
    }
}

function Assert-R3SafeRoot {
    param(
        [Parameter(Mandatory = $true)][string] $CandidateRoot,
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [string] $SourceRoot,
        [string] $DotnetPath,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not [System.IO.Path]::IsPathRooted($CandidateRoot)) {
        throw "$Label must be absolute."
    }
    $root = Get-R3CanonicalPath -Path $CandidateRoot
    $volumeRoot = [System.IO.Path]::GetPathRoot($root).TrimEnd('\')
    if ($root.Equals($volumeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must not be a volume root."
    }
    if ($root -match '\s') {
        throw "$Label must not contain whitespace."
    }
    if ((Test-Path -LiteralPath $root) -and
        -not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "$Label exists but is not a directory."
    }
    Assert-R3ProtectedRootSeparation `
        -CandidateRoot $root `
        -RepositoryRoot $RepositoryRoot `
        -SourceRoot $SourceRoot `
        -DotnetPath $DotnetPath
    Assert-R3NoReparsePoint -Path $root
    return $root
}

function Get-R3ConfigurationTuple {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet(
            'config.baseline',
            'config.variant',
            'config.negative-a',
            'config.negative-b'
        )]
        [string] $ConfigurationId
    )

    switch ($ConfigurationId) {
        'config.baseline' {
            return [pscustomobject]@{
                configuration_id = $ConfigurationId
                adjudication_delay_ms = 0
                hit_animations = $true
            }
        }
        'config.variant' {
            return [pscustomobject]@{
                configuration_id = $ConfigurationId
                adjudication_delay_ms = 75
                hit_animations = $true
            }
        }
        'config.negative-a' {
            return [pscustomobject]@{
                configuration_id = $ConfigurationId
                adjudication_delay_ms = 0
                hit_animations = $true
            }
        }
        'config.negative-b' {
            return [pscustomobject]@{
                configuration_id = $ConfigurationId
                adjudication_delay_ms = 0
                hit_animations = $false
            }
        }
    }
}

function Resolve-R3FormalOutputLayout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('runner', 'comparator')]
        [string] $Mode,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $FormalOutputRoot,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $RepositoryRoot,

        [string] $SourceRoot,
        [string] $DotnetPath,

        [ValidateSet(
            'config.baseline',
            'config.variant',
            'config.negative-a',
            'config.negative-b'
        )]
        [string] $ConfigurationId,

        [ValidateRange(1, 2)]
        [int] $RepetitionIndex
    )

    $requiredRoot = Get-R3CanonicalPath -Path 'D:\GamePrimitivesFormalOutputs'
    $requestedRoot = Get-R3CanonicalPath -Path $FormalOutputRoot
    if (-not $requestedRoot.Equals(
            $requiredRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw (
            'FormalOutputRoot must be exactly ' +
            "'D:\GamePrimitivesFormalOutputs'."
        )
    }

    $root = Assert-R3SafeRoot `
        -CandidateRoot $FormalOutputRoot `
        -RepositoryRoot $RepositoryRoot `
        -SourceRoot $SourceRoot `
        -DotnetPath $DotnetPath `
        -Label 'FormalOutputRoot'
    $caseRoot = Join-Path $root 'continuous-001\CA-R3'
    $comparison = Join-Path $caseRoot 'comparison\formal-comparator-output.json'

    if ($Mode -ceq 'runner') {
        if ([string]::IsNullOrEmpty($ConfigurationId) -or $RepetitionIndex -lt 1) {
            throw 'Runner output validation requires a configuration and repetition.'
        }
        $leaf = 'repetition-{0:0000}' -f $RepetitionIndex
        $trace = Join-Path $caseRoot "raw\$ConfigurationId\$leaf.trace.json"
        $log = Join-Path $caseRoot "logs\$ConfigurationId\$leaf.runner-log.json"
        foreach ($path in @(
                (Split-Path -Parent $trace),
                (Split-Path -Parent $log)
            )) {
            Assert-R3NoReparsePoint -Path $path
        }
        if ((Test-Path -LiteralPath $trace) -or (Test-Path -LiteralPath $log)) {
            throw 'R3 runner trace or log already exists.'
        }
        return [pscustomobject]@{
            formal_output_root = $root
            case_root = $caseRoot
            trace_path = Get-R3CanonicalPath -Path $trace
            runner_log_path = Get-R3CanonicalPath -Path $log
            comparison_path = Get-R3CanonicalPath -Path $comparison
        }
    }

    $traces = @()
    foreach ($configuration in @(
            'config.baseline',
            'config.variant',
            'config.negative-a',
            'config.negative-b'
        )) {
        foreach ($repetition in 1..2) {
            $leaf = 'repetition-{0:0000}' -f $repetition
            $trace = Join-Path $caseRoot "raw\$configuration\$leaf.trace.json"
            Assert-R3NoReparsePoint -Path $trace
            if (-not (Test-Path -LiteralPath $trace -PathType Leaf)) {
                throw "R3 comparator requires fixed trace: $trace"
            }
            $traces += [pscustomobject]@{
                configuration_id = $configuration
                repetition_index = $repetition
                path = Get-R3CanonicalPath -Path $trace
            }
        }
    }
    Assert-R3NoReparsePoint -Path (Split-Path -Parent $comparison)
    if (Test-Path -LiteralPath $comparison) {
        throw 'R3 comparator output already exists.'
    }
    return [pscustomobject]@{
        formal_output_root = $root
        case_root = $caseRoot
        traces = $traces
        comparison_path = Get-R3CanonicalPath -Path $comparison
    }
}

function Assert-R3EmptyBuildRoot {
    param(
        [Parameter(Mandatory = $true)][string] $CacheRoot,
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][string] $SourceRoot,
        [Parameter(Mandatory = $true)][string] $DotnetPath
    )

    $root = Assert-R3SafeRoot `
        -CandidateRoot $CacheRoot `
        -RepositoryRoot $RepositoryRoot `
        -SourceRoot $SourceRoot `
        -DotnetPath $DotnetPath `
        -Label 'CacheRoot'
    if ((Test-Path -LiteralPath $root) -and
        @(Get-ChildItem -LiteralPath $root -Force).Count -ne 0) {
        throw "CacheRoot must be new or empty: $root"
    }
    return $root
}

function Initialize-R3JobRuntime {
    if ('GamePrimitives.R3.JobRuntime' -as [type]) {
        return
    }

    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace GamePrimitives.R3
{
    public static class JobRuntime
    {
        private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
        private const int JobObjectBasicAccountingInformation = 1;
        private const int JobObjectExtendedLimitInformation = 9;

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
        {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct IO_COUNTERS
        {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
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

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
        {
            public long TotalUserTime;
            public long TotalKernelTime;
            public long ThisPeriodTotalUserTime;
            public long ThisPeriodTotalKernelTime;
            public uint TotalPageFaultCount;
            public uint TotalProcesses;
            public uint ActiveProcesses;
            public uint TotalTerminatedProcesses;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObject(
            IntPtr lpJobAttributes,
            string lpName);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(
            IntPtr hJob,
            int JobObjectInformationClass,
            IntPtr lpJobObjectInformation,
            uint cbJobObjectInformationLength);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(
            IntPtr hJob,
            IntPtr hProcess);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool QueryInformationJobObject(
            IntPtr hJob,
            int JobObjectInformationClass,
            IntPtr lpJobObjectInformation,
            uint cbJobObjectInformationLength,
            IntPtr lpReturnLength);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool TerminateJobObject(
            IntPtr hJob,
            uint uExitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr hObject);

        public static IntPtr CreateKillOnCloseJob()
        {
            IntPtr job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero)
                throw new Win32Exception(Marshal.GetLastWin32Error());

            JOBOBJECT_EXTENDED_LIMIT_INFORMATION info =
                new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags =
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            int length = Marshal.SizeOf(info);
            IntPtr pointer = Marshal.AllocHGlobal(length);
            try
            {
                Marshal.StructureToPtr(info, pointer, false);
                if (!SetInformationJobObject(
                        job,
                        JobObjectExtendedLimitInformation,
                        pointer,
                        (uint)length))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
            }
            catch
            {
                CloseHandle(job);
                throw;
            }
            finally
            {
                Marshal.FreeHGlobal(pointer);
            }
            return job;
        }

        public static void Assign(IntPtr job, Process process)
        {
            if (!AssignProcessToJobObject(job, process.Handle))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        public static uint ActiveProcessCount(IntPtr job)
        {
            JOBOBJECT_BASIC_ACCOUNTING_INFORMATION info =
                new JOBOBJECT_BASIC_ACCOUNTING_INFORMATION();
            int length = Marshal.SizeOf(info);
            IntPtr pointer = Marshal.AllocHGlobal(length);
            try
            {
                if (!QueryInformationJobObject(
                        job,
                        JobObjectBasicAccountingInformation,
                        pointer,
                        (uint)length,
                        IntPtr.Zero))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                info = (JOBOBJECT_BASIC_ACCOUNTING_INFORMATION)
                    Marshal.PtrToStructure(
                        pointer,
                        typeof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION));
                return info.ActiveProcesses;
            }
            finally
            {
                Marshal.FreeHGlobal(pointer);
            }
        }

        public static void Terminate(IntPtr job)
        {
            if (!TerminateJobObject(job, 1))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }

        public static void Close(IntPtr job)
        {
            if (job != IntPtr.Zero && !CloseHandle(job))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }
    }
}
'@
}

function ConvertTo-R3WindowsCommandLineArgument {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string] $Argument)

    if ($Argument -match "[`0`r`n]") {
        throw 'R3 process argument contains a forbidden control character.'
    }
    if ($Argument.Length -gt 0 -and $Argument -notmatch '[\s"]') {
        return $Argument
    }

    $builder = New-Object System.Text.StringBuilder
    $null = $builder.Append('"')
    $backslashes = 0
    foreach ($character in $Argument.ToCharArray()) {
        if ($character -eq '\') {
            $backslashes += 1
            continue
        }
        if ($character -eq '"') {
            $null = $builder.Append(('\' * (($backslashes * 2) + 1)))
            $null = $builder.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            $null = $builder.Append(('\' * $backslashes))
            $backslashes = 0
        }
        $null = $builder.Append($character)
    }
    if ($backslashes -gt 0) {
        $null = $builder.Append(('\' * ($backslashes * 2)))
    }
    $null = $builder.Append('"')
    return $builder.ToString()
}

function Invoke-R3ScopedProcess {
    param(
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [string] $StandardOutputPath,
        [string] $StandardErrorPath,
        [int] $TimeoutMilliseconds = 600000,
        [Parameter(Mandatory = $true)]
        [System.Text.Encoding] $OutputEncoding
    )

    Initialize-R3JobRuntime

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = @(
        $Arguments |
            ForEach-Object {
                ConvertTo-R3WindowsCommandLineArgument -Argument $_
            }
    ) -join ' '
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $job = [IntPtr]::Zero
    $startedPid = 0
    $timedOut = $false
    $activeBeforeCleanup = 0
    $stdout = ''
    $stderr = ''
    try {
        $job = [GamePrimitives.R3.JobRuntime]::CreateKillOnCloseJob()
        if (-not $process.Start()) {
            throw "$Step failed to start."
        }
        $startedPid = $process.Id
        try {
            [GamePrimitives.R3.JobRuntime]::Assign($job, $process)
        }
        catch {
            Stop-Process -Id $startedPid -Force -ErrorAction SilentlyContinue
            throw "$Step could not enter its scoped Job Object: $($_.Exception.Message)"
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $timedOut = $true
        }

        $activeBeforeCleanup = [GamePrimitives.R3.JobRuntime]::ActiveProcessCount($job)
        if ($activeBeforeCleanup -gt 0) {
            [GamePrimitives.R3.JobRuntime]::Terminate($job)
        }
        $deadline = [System.Diagnostics.Stopwatch]::StartNew()
        while ([GamePrimitives.R3.JobRuntime]::ActiveProcessCount($job) -ne 0 -and
            $deadline.ElapsedMilliseconds -lt 10000) {
            Start-Sleep -Milliseconds 25
        }
        $activeAfterCleanup = [GamePrimitives.R3.JobRuntime]::ActiveProcessCount($job)
        if ($activeAfterCleanup -ne 0) {
            throw "$Step retained $activeAfterCleanup owned process(es) after Job Object cleanup."
        }
        if (-not $stdoutTask.Wait(10000) -or -not $stderrTask.Wait(10000)) {
            throw "$Step output pipes did not close after Job Object cleanup."
        }
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()

        if (-not [string]::IsNullOrEmpty($StandardOutputPath)) {
            [System.IO.File]::WriteAllText(
                $StandardOutputPath,
                $stdout,
                $OutputEncoding)
        }
        if (-not [string]::IsNullOrEmpty($StandardErrorPath)) {
            [System.IO.File]::WriteAllText(
                $StandardErrorPath,
                $stderr,
                $OutputEncoding)
        }
        if ($timedOut) {
            throw "$Step timed out after $TimeoutMilliseconds ms; its Job Object was terminated."
        }

        return [pscustomobject]@{
            step = $Step
            pid = $startedPid
            exit_code = $process.ExitCode
            alive_after = 0
            job_active_before_cleanup = $activeBeforeCleanup
            job_active_after_cleanup = $activeAfterCleanup
            job_kill_on_close = $true
            timed_out = $false
            stdout = $stdout
            stderr = $stderr
        }
    }
    finally {
        if ($job -ne [IntPtr]::Zero) {
            [GamePrimitives.R3.JobRuntime]::Close($job)
        }
        $process.Dispose()
    }
}

function Invoke-R3BootstrapProcess {
    param(
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [int] $TimeoutMilliseconds = 60000
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Arguments = @(
        $Arguments |
            ForEach-Object {
                ConvertTo-R3WindowsCommandLineArgument -Argument $_
            }
    ) -join ' '

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) {
            throw "$Step failed to start."
        }
        $pidStarted = $process.Id
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            Stop-Process -Id $pidStarted -Force -ErrorAction SilentlyContinue
            $null = $process.WaitForExit(10000)
            throw "$Step timed out after $TimeoutMilliseconds ms."
        }
        if (-not $stdoutTask.Wait(10000) -or -not $stderrTask.Wait(10000)) {
            throw "$Step output pipes did not close."
        }
        return [pscustomobject]@{
            step = $Step
            pid = $pidStarted
            exit_code = $process.ExitCode
            alive_after = @(Get-Process -Id $pidStarted -ErrorAction SilentlyContinue).Count
            stdout = $stdoutTask.GetAwaiter().GetResult()
            stderr = $stderrTask.GetAwaiter().GetResult()
            timed_out = $false
        }
    }
    finally {
        $process.Dispose()
    }
}

function Get-R3PortableDotnetPids {
    param([Parameter(Mandatory = $true)][string] $ResolvedDotnetPath)

    return @(
        Get-Process -Name dotnet -ErrorAction SilentlyContinue |
            Where-Object {
                try {
                    [string]::Equals(
                        $_.Path,
                        $ResolvedDotnetPath,
                        [System.StringComparison]::OrdinalIgnoreCase)
                }
                catch {
                    $false
                }
            } |
            Select-Object -ExpandProperty Id
    )
}

function Remove-R3OwnedTempDirectory {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $SystemTempRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $resolved = (Get-Item -LiteralPath $Path -Force).FullName
    $temp = Get-R3CanonicalPath -Path $SystemTempRoot
    if (-not (Test-R3SameOrChildPath -Candidate $resolved -Parent $temp) -or
        (Get-R3CanonicalPath -Path $resolved).Equals(
            $temp,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a non-owned R3 temp directory: $resolved"
    }
    Assert-R3NoReparsePoint -Path $resolved
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
