[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

. (Join-Path $PSScriptRoot 'r1-process-boundary-v0.1.0.ps1')

$systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$scratch = [System.IO.Path]::GetFullPath(
    (Join-Path $systemTemp (
        'game-primitives-r1-process-boundary-' + [Guid]::NewGuid().ToString('N')
    ))
)
if (-not $scratch.StartsWith(
        $systemTemp,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'Process-boundary self-test escaped the system temp directory.'
}

try {
    New-Item -ItemType Directory -Path $scratch | Out-Null
    $powershellPath = (
        Get-Command powershell.exe -CommandType Application -ErrorAction Stop |
            Select-Object -First 1
    ).Source

    $failureChildPidPath = Join-Path $scratch 'failure-child.pid'
    $failureProbePath = Join-Path $scratch 'failure-tree-probe.ps1'
    $failureProbeSource = @'
param([string] $ChildPidPath)
$child = Start-Process powershell.exe `
    -ArgumentList @('-NoProfile', '-Command', 'Start-Sleep -Seconds 30') `
    -WindowStyle Hidden `
    -PassThru
[System.IO.File]::WriteAllText($ChildPidPath, [string]$child.Id)
exit 7
'@
    [System.IO.File]::WriteAllText(
        $failureProbePath,
        $failureProbeSource,
        [System.Text.UTF8Encoding]::new($false)
    )
    $failureRecord = Invoke-R1TrackedProcess `
        -Step 'synthetic-failure' `
        -FilePath $powershellPath `
        -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            $failureProbePath,
            '-ChildPidPath',
            $failureChildPidPath
        ) `
        -WorkingDirectory $scratch `
        -StandardOutputPath (Join-Path $scratch 'failure.stdout') `
        -StandardErrorPath (Join-Path $scratch 'failure.stderr') `
        -TimeoutMilliseconds 10000
    if (
        $failureRecord.exit_code -ne 7 -or
        $failureRecord.alive_after -ne 0 -or
        $failureRecord.job_active_before_cleanup -lt 1 -or
        $failureRecord.job_active_after_cleanup -ne 0
    ) {
        throw 'Synthetic failure process was not recorded and reaped.'
    }
    if (-not (Test-Path -LiteralPath $failureChildPidPath -PathType Leaf)) {
        throw 'Synthetic failure probe did not report its child PID.'
    }
    $failureChildPid = [int](
        Get-Content -Raw -LiteralPath $failureChildPidPath
    )
    if (@(Get-Process -Id $failureChildPid -ErrorAction SilentlyContinue).Count -ne 0) {
        throw 'Nonzero-exit process left its synthetic child alive.'
    }

    $childPidPath = Join-Path $scratch 'child.pid'
    $probePath = Join-Path $scratch 'tree-probe.ps1'
    $probeSource = @'
param([string] $ChildPidPath)
$child = Start-Process powershell.exe `
    -ArgumentList @('-NoProfile', '-Command', 'Start-Sleep -Seconds 30') `
    -WindowStyle Hidden `
    -PassThru
[System.IO.File]::WriteAllText($ChildPidPath, [string]$child.Id)
Start-Sleep -Seconds 30
'@
    [System.IO.File]::WriteAllText(
        $probePath,
        $probeSource,
        [System.Text.UTF8Encoding]::new($false)
    )

    $timeoutHeld = $false
    $treeRootPid = $null
    try {
        Invoke-R1TrackedProcess `
            -Step 'synthetic-timeout-tree' `
            -FilePath $powershellPath `
            -Arguments @(
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                $probePath,
                '-ChildPidPath',
                $childPidPath
            ) `
            -WorkingDirectory $scratch `
            -StandardOutputPath (Join-Path $scratch 'timeout.stdout') `
            -StandardErrorPath (Join-Path $scratch 'timeout.stderr') `
            -TimeoutMilliseconds 1500
    }
    catch [System.TimeoutException] {
        $timeoutHeld = $true
        $treeRootPid = [int]$_.Exception.Data['started_pid']
        if ([int]$_.Exception.Data['job_active_after_cleanup'] -ne 0) {
            throw 'Timed-out tree root remained alive.'
        }
    }
    if (-not $timeoutHeld) {
        throw 'Synthetic timeout did not trigger.'
    }
    if (-not (Test-Path -LiteralPath $childPidPath -PathType Leaf)) {
        throw 'Synthetic timeout probe did not report its child PID.'
    }
    $childPid = [int](Get-Content -Raw -LiteralPath $childPidPath)
    $remaining = @(
        Get-Process -Id $treeRootPid, $childPid -ErrorAction SilentlyContinue
    )
    if ($remaining.Count -ne 0) {
        throw 'Scoped process-tree cleanup left a synthetic process alive.'
    }

    [ordered]@{
        artifact_type = 'continuous_action_r1_process_boundary_self_test'
        artifact_version = '0.1.0'
        run_id = 'continuous-001'
        case_id = 'CA-R1'
        status = 'passed'
        synthetic_failure_exit_code = 7
        synthetic_failure_reaped = $true
        synthetic_failure_tree_reaped = $true
        synthetic_timeout_tree_reaped = $true
        formal_input_read = $false
        formal_input_executed = $false
        formal_runner_executed = $false
        comparator_executed = $false
    } | ConvertTo-Json -Compress
}
finally {
    if (Test-Path -LiteralPath $scratch) {
        $resolved = (Get-Item -LiteralPath $scratch -Force).FullName
        if (-not $resolved.StartsWith(
                $systemTemp,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            throw 'Refusing to remove process self-test outside system temp.'
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
