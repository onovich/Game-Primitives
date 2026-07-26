[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourcePath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $DotnetPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $CacheRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$frozenCommit = '5da71008b082d1a77e4bb301dc98886f1f24b895'
$expectedSdkVersion = '8.0.100'
$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$expectedListedTestCount = 5407
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-UnresolvedFullPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    return [System.IO.Path]::GetFullPath(
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    )
}

function Test-IsSameOrChildPath {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

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

function Assert-NoExistingReparsePointInPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $current = [System.IO.Path]::GetPathRoot($fullPath)
    $remaining = $fullPath.Substring($current.Length)
    foreach ($segment in @($remaining -split '[\\/]')) {
        if ([string]::IsNullOrWhiteSpace($segment)) {
            continue
        }

        $current = Join-Path $current $segment
        if (-not (Test-Path -LiteralPath $current)) {
            break
        }

        $item = Get-Item -LiteralPath $current -Force
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "CacheRoot path traverses a reparse point: $current"
        }
    }
}

function Get-SourceBuildOutputDirectories {
    param([Parameter(Mandatory = $true)][string] $Root)

    return @(Get-ChildItem -LiteralPath $Root -Directory -Recurse -Force | Where-Object {
        $_.Name -in @('bin', 'obj')
    })
}

function Write-LfLines {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [AllowEmptyCollection()][string[]] $Lines
    )

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $text = $Lines -join "`n"
    if ($text.Length -gt 0) {
        $text += "`n"
    }

    [System.IO.File]::WriteAllText($Path, $text, $utf8NoBom)
}

function Format-DisplayArgument {
    param([Parameter(Mandatory = $true)][string] $Argument)

    if ($Argument -notmatch "[\s;'`"]") {
        return $Argument
    }

    return "'" + $Argument.Replace("'", "''") + "'"
}

function Format-DisplayCommand {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [AllowEmptyCollection()][string[]] $Arguments
    )

    $parts = @((Format-DisplayArgument -Argument $FilePath))
    $parts += @($Arguments | ForEach-Object {
        Format-DisplayArgument -Argument ([string] $_)
    })
    return $parts -join ' '
}

function Invoke-NativeCapture {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [AllowEmptyCollection()][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory
    )

    Push-Location -LiteralPath $WorkingDirectory
    try {
        $captured = @(& $FilePath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $lines = @($captured | ForEach-Object { [string] $_ })
    return [pscustomobject]@{
        Command = Format-DisplayCommand -FilePath $FilePath -Arguments $Arguments
        ExitCode = [int] $exitCode
        Lines = $lines
        WorkingDirectory = $WorkingDirectory
    }
}

function Write-StepLog {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)] $Result,
        [AllowEmptyCollection()][string[]] $Evidence
    )

    $lines = @(
        'artifact=osu-neutral-replay-step'
        'artifact_version=0.1.0'
        "step=$Step"
        "command=$($Result.Command)"
        "working_directory=$($Result.WorkingDirectory)"
        "exit_code=$($Result.ExitCode)"
    )
    $lines += @($Evidence)
    $lines += @('output_begin')
    $lines += @($Result.Lines)
    $lines += @('output_end')
    Write-LfLines -Path $Path -Lines $lines
}

function Get-PortableDotnetProcesses {
    param([Parameter(Mandatory = $true)][string] $ResolvedDotnetPath)

    return @(Get-Process -Name dotnet -ErrorAction SilentlyContinue | Where-Object {
        try {
            [string]::Equals(
                $_.Path,
                $ResolvedDotnetPath,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        }
        catch {
            $false
        }
    })
}

$sourceFull = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$cacheRootFull = (Get-UnresolvedFullPath -Path $CacheRoot).TrimEnd('\')

if (-not (Test-Path -LiteralPath $sourceFull -PathType Container)) {
    throw "SourcePath is not a directory: $sourceFull"
}
if (-not (Test-Path -LiteralPath $dotnetFull -PathType Leaf)) {
    throw "DotnetPath is not a file: $dotnetFull"
}
$resolvedDotnetSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $dotnetFull
).Hash.ToLowerInvariant()
if ($resolvedDotnetSha256 -cne $expectedDotnetSha256) {
    throw "DotnetPath SHA-256 mismatch: expected $expectedDotnetSha256, got $resolvedDotnetSha256"
}

$gitCommand = Get-Command git.exe -ErrorAction Stop | Select-Object -First 1
$gitPath = $gitCommand.Source

$repoRootResult = Invoke-NativeCapture `
    -FilePath $gitPath `
    -Arguments @('-C', $PSScriptRoot, 'rev-parse', '--show-toplevel') `
    -WorkingDirectory $PSScriptRoot
if ($repoRootResult.ExitCode -ne 0 -or $repoRootResult.Lines.Count -ne 1) {
    throw 'Unable to resolve the Game Primitives repository root.'
}
$repoRoot = $repoRootResult.Lines[0].Trim()

if (Test-IsSameOrChildPath -Candidate $cacheRootFull -Parent $repoRoot) {
    throw "CacheRoot must be outside the Game Primitives repository: $cacheRootFull"
}
if ((Test-IsSameOrChildPath -Candidate $cacheRootFull -Parent $sourceFull) -or
    (Test-IsSameOrChildPath -Candidate $sourceFull -Parent $cacheRootFull)) {
    throw 'CacheRoot and SourcePath must not overlap.'
}
Assert-NoExistingReparsePointInPath -Path $cacheRootFull
if (Test-Path -LiteralPath $cacheRootFull) {
    $existingEntries = @(Get-ChildItem -LiteralPath $cacheRootFull -Force)
    if ($existingEntries.Count -ne 0) {
        throw "CacheRoot must be new or empty: $cacheRootFull"
    }
}

$headResult = Invoke-NativeCapture `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD^{commit}') `
    -WorkingDirectory $sourceFull
if ($headResult.ExitCode -ne 0 -or $headResult.Lines.Count -ne 1) {
    throw 'SourcePath is not a readable Git worktree.'
}
$resolvedCommit = $headResult.Lines[0].Trim()
if ($resolvedCommit -cne $frozenCommit) {
    throw "Frozen commit mismatch: expected $frozenCommit, got $resolvedCommit"
}

$originResult = Invoke-NativeCapture `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'remote', 'get-url', 'origin') `
    -WorkingDirectory $sourceFull
if ($originResult.ExitCode -ne 0 -or $originResult.Lines.Count -ne 1) {
    throw 'SourcePath has no readable origin remote.'
}
$origin = $originResult.Lines[0].Trim()
if ($origin -notmatch '^https://github\.com/ppy/osu(?:\.git)?/?$') {
    throw "Source origin is not the official ppy/osu HTTPS remote: $origin"
}

$statusResult = Invoke-NativeCapture `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'status', '--porcelain=v1', '--untracked-files=all') `
    -WorkingDirectory $sourceFull
if ($statusResult.ExitCode -ne 0) {
    throw 'Unable to inspect source worktree status.'
}
if ($statusResult.Lines.Count -ne 0) {
    throw "Source worktree is dirty:`n$($statusResult.Lines -join "`n")"
}
$initialSourceBuildOutputs = @(Get-SourceBuildOutputDirectories -Root $sourceFull)
if ($initialSourceBuildOutputs.Count -ne 0) {
    throw "SourcePath already contains bin/obj directories: $($initialSourceBuildOutputs.FullName -join ',')"
}

$projectPath = Join-Path $sourceFull 'osu.Game.Tests\osu.Game.Tests.csproj'
if (-not (Test-Path -LiteralPath $projectPath -PathType Leaf)) {
    throw "Expected test project is missing: $projectPath"
}

$trackedFilesResult = Invoke-NativeCapture `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'ls-files') `
    -WorkingDirectory $sourceFull
if ($trackedFilesResult.ExitCode -ne 0) {
    throw 'Unable to inspect tracked lock files.'
}
$trackedPackageLocks = @($trackedFilesResult.Lines | Where-Object {
    ([System.IO.Path]::GetFileName($_)) -ieq 'packages.lock.json'
})
if ($trackedPackageLocks.Count -ne 0) {
    throw 'Frozen source unexpectedly contains packages.lock.json.'
}

New-Item -ItemType Directory -Path $cacheRootFull -Force | Out-Null
Assert-NoExistingReparsePointInPath -Path $cacheRootFull
$dotnetHome = Join-Path $cacheRootFull 'dotnet-home'
$nugetPackages = Join-Path $cacheRootFull 'nuget-packages'
$tempPath = Join-Path $cacheRootFull 'temp'
$artifactsPath = Join-Path $cacheRootFull 'artifacts'
$logsPath = Join-Path $cacheRootFull 'logs'
@($dotnetHome, $nugetPackages, $tempPath, $artifactsPath, $logsPath) |
    ForEach-Object { New-Item -ItemType Directory -Path $_ -Force | Out-Null }

$environmentNames = @(
    'DOTNET_CLI_HOME'
    'NUGET_PACKAGES'
    'TEMP'
    'TMP'
    'DOTNET_SKIP_FIRST_TIME_EXPERIENCE'
    'DOTNET_CLI_TELEMETRY_OPTOUT'
    'DOTNET_NOLOGO'
    'DOTNET_CLI_UI_LANGUAGE'
    'VSLANG'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable(
        $name,
        [System.EnvironmentVariableTarget]::Process
    )
}

[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_HOME', $dotnetHome, 'Process')
[System.Environment]::SetEnvironmentVariable('NUGET_PACKAGES', $nugetPackages, 'Process')
[System.Environment]::SetEnvironmentVariable('TEMP', $tempPath, 'Process')
[System.Environment]::SetEnvironmentVariable('TMP', $tempPath, 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_SKIP_FIRST_TIME_EXPERIENCE', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_TELEMETRY_OPTOUT', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_NOLOGO', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_UI_LANGUAGE', 'en-US', 'Process')
[System.Environment]::SetEnvironmentVariable('VSLANG', '1033', 'Process')

$failureMessages = New-Object System.Collections.Generic.List[string]
$restoreResult = $null
$buildResult = $null
$listResult = $null
$shutdownResult = $null
$listedTestCount = 0
$assetEvidence = @()
$buildEvidence = @()
$dotnetWorkStarted = $false
$startedAt = Get-Date

try {
    $sdkResult = Invoke-NativeCapture `
        -FilePath $dotnetFull `
        -Arguments @('--version') `
        -WorkingDirectory $sourceFull
    if ($sdkResult.ExitCode -ne 0 -or $sdkResult.Lines.Count -ne 1) {
        throw 'Unable to resolve the isolated .NET SDK version.'
    }
    $resolvedSdkVersion = $sdkResult.Lines[0].Trim()
    if ($resolvedSdkVersion -cne $expectedSdkVersion) {
        throw "SDK mismatch: expected $expectedSdkVersion, got $resolvedSdkVersion"
    }

    $restoreArguments = @(
        'restore'
        'osu.Game.Tests\osu.Game.Tests.csproj'
        '--packages'
        $nugetPackages
        '-p:UseArtifactsOutput=true'
        "-p:ArtifactsPath=$artifactsPath"
        '-v:minimal'
    )
    $dotnetWorkStarted = $true
    $restoreResult = Invoke-NativeCapture `
        -FilePath $dotnetFull `
        -Arguments $restoreArguments `
        -WorkingDirectory $sourceFull
    Write-StepLog `
        -Path (Join-Path $logsPath 'restore.log') `
        -Step 'restore' `
        -Result $restoreResult `
        -Evidence @(
            "frozen_commit=$frozenCommit"
            "sdk_version=$expectedSdkVersion"
            'packages_lock_json_present=0'
        )
    if ($restoreResult.ExitCode -ne 0) {
        throw "Restore failed with exit code $($restoreResult.ExitCode)."
    }

    $assetFiles = @(Get-ChildItem `
        -LiteralPath (Join-Path $artifactsPath 'obj') `
        -Recurse `
        -Filter 'project.assets.json' `
        -File |
        Sort-Object FullName)
    if ($assetFiles.Count -ne 6) {
        throw "Expected 6 project.assets.json files, found $($assetFiles.Count)."
    }
    $assetEvidence = @($assetFiles | ForEach-Object {
        $relativePath = $_.FullName.Substring($artifactsPath.Length + 1)
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        "project_assets=$relativePath|bytes=$($_.Length)|sha256=$hash"
    })
    Write-StepLog `
        -Path (Join-Path $logsPath 'restore.log') `
        -Step 'restore' `
        -Result $restoreResult `
        -Evidence (@(
            "frozen_commit=$frozenCommit"
            "sdk_version=$expectedSdkVersion"
            'packages_lock_json_present=0'
            'generated_project_assets_count=6'
        ) + $assetEvidence)

    $buildArguments = @(
        'build'
        'osu.Game.Tests\osu.Game.Tests.csproj'
        '--no-restore'
        '--configuration'
        'Debug'
        '--artifacts-path'
        $artifactsPath
        '--verbosity'
        'minimal'
    )
    $buildResult = Invoke-NativeCapture `
        -FilePath $dotnetFull `
        -Arguments $buildArguments `
        -WorkingDirectory $sourceFull

    $zeroWarningsFound = @($buildResult.Lines | Where-Object {
        $_ -match '^\s*0\s+(?:Warning\(s\)|Warnings?)\.?\s*$'
    }).Count -gt 0
    $zeroErrorsFound = @($buildResult.Lines | Where-Object {
        $_ -match '^\s*0\s+(?:Error\(s\)|Errors?)\.?\s*$'
    }).Count -gt 0
    $buildEvidence = @(
        "zero_warnings_summary_found=$($zeroWarningsFound.ToString().ToLowerInvariant())"
        "zero_errors_summary_found=$($zeroErrorsFound.ToString().ToLowerInvariant())"
    )
    Write-StepLog `
        -Path (Join-Path $logsPath 'build.log') `
        -Step 'build' `
        -Result $buildResult `
        -Evidence $buildEvidence
    if ($buildResult.ExitCode -ne 0) {
        throw "Build failed with exit code $($buildResult.ExitCode)."
    }
    if (-not $zeroWarningsFound -or -not $zeroErrorsFound) {
        throw 'Build output did not contain explicit zero-warning and zero-error summaries.'
    }

    $testAssembly = Join-Path $artifactsPath 'bin\osu.Game.Tests\debug\osu.Game.Tests.dll'
    if (-not (Test-Path -LiteralPath $testAssembly -PathType Leaf)) {
        throw "Expected test assembly is missing: $testAssembly"
    }
    $testAssemblyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $testAssembly).Hash.ToLowerInvariant()

    $listArguments = @(
        'test'
        'osu.Game.Tests\osu.Game.Tests.csproj'
        '--no-build'
        '--no-restore'
        '--configuration'
        'Debug'
        '--artifacts-path'
        $artifactsPath
        '--list-tests'
        '--logger'
        'console;verbosity=minimal'
    )
    $listResult = Invoke-NativeCapture `
        -FilePath $dotnetFull `
        -Arguments $listArguments `
        -WorkingDirectory $sourceFull
    $listedTestCount = @($listResult.Lines | Where-Object {
        $_ -match '^\s{4}\S'
    }).Count
    Write-StepLog `
        -Path (Join-Path $logsPath 'list-tests.log') `
        -Step 'list-tests-only' `
        -Result $listResult `
        -Evidence @(
            "listed_test_count=$listedTestCount"
            "expected_listed_test_count=$expectedListedTestCount"
            'test_bodies_executed=0'
            'sentinel_TestCircleHitCentre_executed=0'
            'formal_0_75_input_created_or_run=0'
            'formal_HitAnimations_control_created_or_run=0'
            'formal_RawTime_logged=0'
            "test_assembly_sha256=$testAssemblyHash"
        )
    if ($listResult.ExitCode -ne 0) {
        throw "Test listing failed with exit code $($listResult.ExitCode)."
    }
    if ($listedTestCount -ne $expectedListedTestCount) {
        throw "Listed test count mismatch: expected $expectedListedTestCount, got $listedTestCount"
    }

    $finalHeadResult = Invoke-NativeCapture `
        -FilePath $gitPath `
        -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD^{commit}') `
        -WorkingDirectory $sourceFull
    if ($finalHeadResult.ExitCode -ne 0 -or
        $finalHeadResult.Lines.Count -ne 1 -or
        $finalHeadResult.Lines[0].Trim() -cne $frozenCommit) {
        throw 'Frozen source commit changed during the probe.'
    }

    $finalStatusResult = Invoke-NativeCapture `
        -FilePath $gitPath `
        -Arguments @('-C', $sourceFull, 'status', '--porcelain=v1', '--untracked-files=all') `
        -WorkingDirectory $sourceFull
    if ($finalStatusResult.ExitCode -ne 0 -or $finalStatusResult.Lines.Count -ne 0) {
        throw 'Source worktree became dirty during the probe.'
    }
    $finalSourceBuildOutputs = @(Get-SourceBuildOutputDirectories -Root $sourceFull)
    if ($finalSourceBuildOutputs.Count -ne 0) {
        throw "SourcePath contains bin/obj directories after the probe: $($finalSourceBuildOutputs.FullName -join ',')"
    }
}
catch {
    $failureMessages.Add($_.Exception.Message)
}
finally {
    if ($dotnetWorkStarted) {
        try {
            $shutdownResult = Invoke-NativeCapture `
                -FilePath $dotnetFull `
                -Arguments @('build-server', 'shutdown') `
                -WorkingDirectory $sourceFull
            Write-StepLog `
                -Path (Join-Path $logsPath 'build-server-shutdown.log') `
                -Step 'build-server-shutdown' `
                -Result $shutdownResult `
                -Evidence @()
            if ($shutdownResult.ExitCode -ne 0) {
                $failureMessages.Add(
                    "Build-server shutdown failed with exit code $($shutdownResult.ExitCode)."
                )
            }
        }
        catch {
            $failureMessages.Add("Build-server shutdown raised: $($_.Exception.Message)")
        }
    }

    $portableProcesses = @(Get-PortableDotnetProcesses -ResolvedDotnetPath $dotnetFull)
    for ($attempt = 0; $attempt -lt 20 -and $portableProcesses.Count -ne 0; $attempt++) {
        Start-Sleep -Milliseconds 500
        $portableProcesses = @(Get-PortableDotnetProcesses -ResolvedDotnetPath $dotnetFull)
    }
    if ($portableProcesses.Count -ne 0) {
        $failureMessages.Add(
            "Portable dotnet processes remain: $($portableProcesses.Id -join ',')"
        )
    }

    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable(
            $name,
            $previousEnvironment[$name],
            [System.EnvironmentVariableTarget]::Process
        )
    }
}

$finishedAt = Get-Date
$exitCode = if ($failureMessages.Count -eq 0) { 0 } else { 1 }
$status = if ($exitCode -eq 0) { 'SUCCESS' } else { 'FAILED' }
$portableProcessCount = @(Get-PortableDotnetProcesses -ResolvedDotnetPath $dotnetFull).Count

$runnerLogLines = @(
    'artifact=osu-neutral-replay'
    'artifact_version=0.1.0'
    "result=$status"
    "started_local=$($startedAt.ToString('yyyy-MM-ddTHH:mm:ss.fffK'))"
    "finished_local=$($finishedAt.ToString('yyyy-MM-ddTHH:mm:ss.fffK'))"
    "source=$sourceFull"
    "origin=$origin"
    "frozen_commit=$frozenCommit"
    "sdk_version=$expectedSdkVersion"
    "dotnet_exe_sha256=$resolvedDotnetSha256"
    "cache_root=$cacheRootFull"
    "listed_test_count=$listedTestCount"
    'test_bodies_executed=0'
    'Node_invocations=0'
    'WMI_or_CIM_invocations=0'
    'packages_lock_json_present=0'
    'source_bin_obj_directory_count=0'
    "portable_dotnet_process_count=$portableProcessCount"
    "failure_count=$($failureMessages.Count)"
)
foreach ($message in $failureMessages) {
    $runnerLogLines += "failure=$message"
}
Write-LfLines -Path (Join-Path $cacheRootFull 'probe-runner.log') -Lines $runnerLogLines
Write-LfLines -Path (Join-Path $cacheRootFull 'probe.exit.txt') -Lines @([string] $exitCode)

$runnerLogLines | Write-Output
exit $exitCode
