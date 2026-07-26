param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$UnityPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [ValidateRange(30, 1800)]
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'

$expectedCommit = '7eaaad799bb7912625c15af9407c2c67e6305d75'
$expectedProjectVersion = 'm_EditorVersion: 2018.1.1f1'
$expectedUnityVersion = '2018.1.1.12110773'

function Invoke-Git {
    param([string[]]$Arguments)

    $output = @(& git @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
    return @($output | ForEach-Object { $_.ToString() })
}

$resolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
$resolvedUnity = (Resolve-Path -LiteralPath $UnityPath).Path
$projectVersionPath = Join-Path $resolvedSource 'ProjectSettings\ProjectVersion.txt'

if (-not (Test-Path -LiteralPath $projectVersionPath -PathType Leaf)) {
    throw "Missing Unity project version file: $projectVersionPath"
}

$head = (Invoke-Git -Arguments @('-C', $resolvedSource, 'rev-parse', 'HEAD')).Trim()
if ($head -ne $expectedCommit) {
    throw "Frozen source mismatch. Expected $expectedCommit, found $head."
}

$statusBefore = @(Invoke-Git -Arguments @('-C', $resolvedSource, 'status', '--porcelain=v1'))
if ($statusBefore.Count -ne 0) {
    throw 'Frozen source must be clean before the neutral import probe.'
}

$projectVersion = (Get-Content -LiteralPath $projectVersionPath -Raw -Encoding utf8).Trim()
if ($projectVersion -ne $expectedProjectVersion) {
    throw "Project version mismatch. Expected '$expectedProjectVersion', found '$projectVersion'."
}

$unityItem = Get-Item -LiteralPath $resolvedUnity
if ($unityItem.VersionInfo.FileVersion -ne $expectedUnityVersion) {
    throw "Unity executable mismatch. Expected $expectedUnityVersion, found $($unityItem.VersionInfo.FileVersion)."
}

if (-not (Test-Path -LiteralPath $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
}
$resolvedOutput = (Resolve-Path -LiteralPath $OutputPath).Path
$logPath = Join-Path $resolvedOutput 'unity-neutral-import.log'

$arguments = @(
    '-batchmode',
    '-nographics',
    '-quit',
    '-projectPath',
    ('"' + $resolvedSource + '"'),
    '-logFile',
    ('"' + $logPath + '"')
)

$process = Start-Process `
    -FilePath $resolvedUnity `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -PassThru

$timedOut = $false
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    $timedOut = $true
}

$remaining = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
if ($remaining) {
    if ($remaining.Path -ne $resolvedUnity) {
        throw "Refusing to stop unexpected process $($remaining.Id): $($remaining.Path)"
    }
    Stop-Process -Id $remaining.Id -Force
}

if ($timedOut) {
    throw "Unity neutral import timed out after $TimeoutSeconds seconds. PID $($process.Id) was stopped."
}

$process.Refresh()
if ($process.ExitCode -ne 0) {
    throw "Unity neutral import failed with exit code $($process.ExitCode). See $logPath."
}

$logText = Get-Content -LiteralPath $logPath -Raw -Encoding utf8
if ($logText -match 'has not been activated with a valid License') {
    throw "Unity 2018.1.1f1 is not activated. See $logPath."
}
if ($logText -match '(?i)(error\s+CS[0-9]+|scripts have compiler errors)') {
    throw "Unity reported script compilation errors. See $logPath."
}

$statusAfter = @(Invoke-Git -Arguments @('-C', $resolvedSource, 'status', '--porcelain=v1'))
if ($statusAfter.Count -ne 0) {
    throw 'Frozen tracked source changed during the neutral import probe.'
}

[pscustomobject]@{
    Commit = $head
    FormalInputExecuted = $false
    FormalResultProduced = $false
    LogPath = $logPath
    LogSHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $logPath).Hash.ToLowerInvariant()
    SourceClean = $true
    Status = 'passed'
    UnityVersion = $unityItem.VersionInfo.FileVersion
}
