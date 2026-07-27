Set-StrictMode -Version Latest

function Initialize-R1JobRuntime {
    if ('GamePrimitives.R1.JobRuntime' -as [type]) {
        return
    }

    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace GamePrimitives.R1
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

function Invoke-R1TrackedProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][string] $StandardOutputPath,
        [Parameter(Mandatory = $true)][string] $StandardErrorPath,
        [int] $TimeoutMilliseconds = 600000
    )

    foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            throw "$Step received an argument that requires unsupported quoting: $argument"
        }
    }
    Initialize-R1JobRuntime

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments -join ' '
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
    try {
        $job = [GamePrimitives.R1.JobRuntime]::CreateKillOnCloseJob()
        if (-not $process.Start()) {
            throw "$Step failed to start."
        }
        $startedPid = $process.Id
        try {
            [GamePrimitives.R1.JobRuntime]::Assign($job, $process)
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

        $activeBeforeCleanup = [GamePrimitives.R1.JobRuntime]::ActiveProcessCount(
            $job
        )
        if ($activeBeforeCleanup -gt 0) {
            [GamePrimitives.R1.JobRuntime]::Terminate($job)
        }
        $deadline = [System.Diagnostics.Stopwatch]::StartNew()
        while (
            [GamePrimitives.R1.JobRuntime]::ActiveProcessCount($job) -ne 0 -and
            $deadline.ElapsedMilliseconds -lt 10000
        ) {
            Start-Sleep -Milliseconds 25
        }
        $activeAfterCleanup = [GamePrimitives.R1.JobRuntime]::ActiveProcessCount(
            $job
        )
        if ($activeAfterCleanup -ne 0) {
            throw "$Step retained $activeAfterCleanup owned process(es) after Job Object cleanup."
        }
        if (-not $stdoutTask.Wait(10000) -or -not $stderrTask.Wait(10000)) {
            throw "$Step output pipes did not close after Job Object cleanup."
        }
        $standardOutput = $stdoutTask.GetAwaiter().GetResult()
        $standardError = $stderrTask.GetAwaiter().GetResult()
        [System.IO.File]::WriteAllText(
            $StandardOutputPath,
            $standardOutput,
            [System.Text.UTF8Encoding]::new($false)
        )
        [System.IO.File]::WriteAllText(
            $StandardErrorPath,
            $standardError,
            [System.Text.UTF8Encoding]::new($false)
        )

        if ($timedOut) {
            $exception = [System.TimeoutException]::new(
                "$Step timed out after $TimeoutMilliseconds ms; its scoped Job Object was terminated."
            )
            $exception.Data['started_pid'] = $startedPid
            $exception.Data['job_active_before_cleanup'] = $activeBeforeCleanup
            $exception.Data['job_active_after_cleanup'] = $activeAfterCleanup
            throw $exception
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
        }
    }
    finally {
        if ($job -ne [IntPtr]::Zero) {
            [GamePrimitives.R1.JobRuntime]::Close($job)
        }
        $process.Dispose()
    }
}
