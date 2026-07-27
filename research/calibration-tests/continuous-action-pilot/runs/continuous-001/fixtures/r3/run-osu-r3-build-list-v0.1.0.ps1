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
$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$expectedSdkVersion = '8.0.100'
$expectedObservationSha256 = '5907f3ea17699981cb48f298ed6addf83eea705388411c69293c26142d2e0535'
$expectedSafetyGuardsSha256 = '53b714b3224057e6dc2f5b01d8c13529ea8a0b1b75cc0c25eb0d1083c76aa6be'
$expectedDeterministicTargetsSha256 =
    'ab74e926c558134b1a92bf034bab6c7770fb75eebcb5b1c5b0158683e7d431cb'
$expectedLocks = [ordered]@{
    'osu.Game\packages.lock.json' = '48952c1c2acfc6634f8f0675dd0c9a43667808db3885711519c5a7562e0fa723'
    'osu.Game.Rulesets.Osu\packages.lock.json' = '2b1612fb68477937bbc4a86437138cd3ae850a25871eb18ce4a626022658d7ae'
    'osu.Game.Rulesets.Osu.Tests\packages.lock.json' = '86a9c02930a3ce76d3aac7facf7261324026f189c37785d1a7530afa72669a8a'
}
$projectRelativePath = 'osu.Game.Rulesets.Osu.Tests\osu.Game.Rulesets.Osu.Tests.csproj'
$observationRelativePath = 'osu.Game.Rulesets.Osu.Tests\TestSceneGamePrimitivesR3.cs'
$formalAssemblyRelativePath =
    'artifacts\bin\osu.Game.Rulesets.Osu.Tests\debug\osu.Game.Rulesets.Osu.Tests.dll'
$testFullyQualifiedName =
    'osu.Game.Rulesets.Osu.Tests.TestSceneGamePrimitivesR3.TestFormalAdjudicationSchedule'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptRoot '..\..\..\..\..\..\..')
).TrimEnd('\')

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Assert-Hash {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Expected
    )

    $actual = Get-Sha256 -Path $Path
    if ($actual -cne $Expected) {
        throw "SHA-256 mismatch for $Path. Expected $Expected, got $actual."
    }
}

function Write-Json {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )

    [System.IO.File]::WriteAllText(
        $Path,
        (($Value | ConvertTo-Json -Depth 20) + "`n"),
        $utf8NoBom)
}

function New-R3ExecutionTreeManifest {
    param(
        [Parameter(Mandatory = $true)][string] $ExecutionRoot,
        [Parameter(Mandatory = $true)][string] $AssemblyPath,
        [Parameter(Mandatory = $true)][string] $ManifestPath
    )

    $root = Get-R3CanonicalPath -Path $ExecutionRoot
    $assembly = Get-R3CanonicalPath -Path $AssemblyPath
    if (-not (Test-R3SameOrChildPath -Candidate $assembly -Parent $root) -or
        -not (Test-Path -LiteralPath $assembly -PathType Leaf)) {
        throw 'R3 formal assembly is outside the execution tree.'
    }
    Assert-R3NoReparsePoint -Path $root
    $treeItems = @(
        Get-ChildItem -LiteralPath $root -Recurse -Force
    )
    $reparseItems = @(
        $treeItems |
            Where-Object {
                ($_.Attributes -band
                    [System.IO.FileAttributes]::ReparsePoint) -ne 0
            }
    )
    if ($reparseItems.Count -ne 0) {
        throw 'R3 execution tree contains a reparse point.'
    }
    $pdbFiles = @(
        $treeItems |
            Where-Object {
                -not $_.PSIsContainer -and
                $_.Extension -ieq '.pdb' -and
                $_.BaseName -like 'osu.Game*'
            }
    )
    if ($pdbFiles.Count -ne 0) {
        throw 'R3 project outputs must not contain PDB files.'
    }

    $files = @(
        $treeItems |
            Where-Object { -not $_.PSIsContainer } |
            Sort-Object FullName |
            ForEach-Object {
                $relative = $_.FullName.Substring($root.Length).TrimStart('\')
                [ordered]@{
                    path = $relative.Replace('\', '/')
                    bytes = $_.Length
                    sha256 = Get-Sha256 -Path $_.FullName
                }
            }
    )
    if ($files.Count -eq 0) {
        throw 'R3 execution tree is empty.'
    }
    $totalBytes = [long]0
    foreach ($file in $files) {
        $totalBytes += [long]$file['bytes']
    }
    $assemblyRelative =
        $assembly.Substring($root.Length).TrimStart('\').Replace('\', '/')
    $manifest = [ordered]@{
        artifact_type = 'continuous_action_r3_execution_tree_manifest'
        artifact_version = '0.1.0'
        assembly_relative_path = $assemblyRelative
        file_count = $files.Count
        total_bytes = $totalBytes
        files = $files
    }
    Write-Json -Path $ManifestPath -Value $manifest
    $manifestFile = Get-Item -LiteralPath $ManifestPath
    return [ordered]@{
        execution_root = $root.Replace('\', '/')
        assembly_relative_path = $assemblyRelative
        file_count = $manifest.file_count
        total_bytes = $manifest.total_bytes
        manifest = [ordered]@{
            external_path = $manifestFile.FullName.Replace('\', '/')
            bytes = $manifestFile.Length
            sha256 = Get-Sha256 -Path $manifestFile.FullName
        }
    }
}

function Remove-R3DiscoveryEphemera {
    param(
        [Parameter(Mandatory = $true)][string] $ExecutionRoot
    )

    $root = Get-R3CanonicalPath -Path $ExecutionRoot
    Assert-R3NoReparsePoint -Path $root
    $removed = New-Object System.Collections.Generic.List[string]
    foreach ($name in @(
            '.msCoverageSourceRootsMapping_osu.Game.Rulesets.Osu.Tests',
            'nunit_random_seed.tmp'
        )) {
        $path = Get-R3CanonicalPath -Path (Join-Path $root $name)
        if (-not (Test-R3SameOrChildPath -Candidate $path -Parent $root)) {
            throw 'R3 discovery ephemera path escapes the execution tree.'
        }
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "R3 discovery ephemera is not a regular file: $name"
        }
        Assert-R3NoReparsePoint -Path $path
        Remove-Item -LiteralPath $path -Force
        $removed.Add($name)
    }
    return @($removed)
}

function Add-ProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]] $List,
        [Parameter(Mandatory = $true)] $Record,
        [Parameter(Mandatory = $true)][string] $Step
    )

    $List.Add([ordered]@{
        step = $Step
        pid = $Record.pid
        exit_code = $Record.exit_code
        alive_after = $Record.alive_after
        job_active_before_cleanup = $Record.job_active_before_cleanup
        job_active_after_cleanup = $Record.job_active_after_cleanup
        job_kill_on_close = $Record.job_kill_on_close
        timed_out = $Record.timed_out
    })
}

$safetyGuardsPath = Join-Path $scriptRoot 'r3-safety-guards-v0.1.0.ps1'
Assert-Hash -Path $safetyGuardsPath -Expected $expectedSafetyGuardsSha256
. $safetyGuardsPath

$sourceFull = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$cacheA = Assert-R3EmptyBuildRoot `
    -CacheRoot $CacheRoot `
    -RepositoryRoot $repoRoot `
    -SourceRoot $sourceFull `
    -DotnetPath $dotnetFull
$cacheB = Assert-R3EmptyBuildRoot `
    -CacheRoot ($cacheA + '-reproducibility') `
    -RepositoryRoot $repoRoot `
    -SourceRoot $sourceFull `
    -DotnetPath $dotnetFull
if (Test-R3PathsOverlap -Left $cacheA -Right $cacheB) {
    throw 'The two R3 reproducibility cache roots must be independent siblings.'
}

foreach ($formalEnvironmentName in @(
        'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
        'GAME_PRIMITIVES_FORMAL_INPUT_SHA256',
        'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
        'GAME_PRIMITIVES_RUN_ID',
        'GAME_PRIMITIVES_CASE_ID',
        'GAME_PRIMITIVES_R3_CONFIGURATION_ID',
        'GAME_PRIMITIVES_R3_OUTPUT_PATH',
        'GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS',
        'GAME_PRIMITIVES_R3_HIT_ANIMATIONS')) {
    if (-not [string]::IsNullOrEmpty(
            [System.Environment]::GetEnvironmentVariable(
                $formalEnvironmentName,
                'Process'))) {
        throw "Formal environment variable $formalEnvironmentName is forbidden in the R3 build/list probe."
    }
}

Assert-Hash -Path $dotnetFull -Expected $expectedDotnetSha256
if (@(Get-R3PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'The dedicated portable dotnet runtime is already in use.'
}

$observationSource = Join-Path $scriptRoot 'TestSceneGamePrimitivesR3.cs'
Assert-Hash -Path $observationSource -Expected $expectedObservationSha256
$deterministicTargetsSource =
    Join-Path $scriptRoot 'r3-deterministic-build-v0.1.0.targets'
Assert-Hash `
    -Path $deterministicTargetsSource `
    -Expected $expectedDeterministicTargetsSha256
$lockCopies = [ordered]@{
    'osu.Game\packages.lock.json' = 'osu.Game.packages.lock.json'
    'osu.Game.Rulesets.Osu\packages.lock.json' =
        'osu.Game.Rulesets.Osu.packages.lock.json'
    'osu.Game.Rulesets.Osu.Tests\packages.lock.json' =
        'osu.Game.Rulesets.Osu.Tests.packages.lock.json'
}
foreach ($entry in $lockCopies.GetEnumerator()) {
    Assert-Hash `
        -Path (Join-Path $scriptRoot "dependency-locks\$($entry.Value)") `
        -Expected $expectedLocks[$entry.Key]
}

Initialize-R3JobRuntime
$allProcesses = New-Object System.Collections.Generic.List[object]
$gitPath = (Get-Command git.exe -ErrorAction Stop | Select-Object -First 1).Source

$sourceCommitProbe = Invoke-R3ScopedProcess `
    -Step 'verify-source-commit' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD^{commit}') `
    -WorkingDirectory $sourceFull `
    -TimeoutMilliseconds 60000 `
    -OutputEncoding $utf8NoBom
Add-ProcessRecord -List $allProcesses -Record $sourceCommitProbe -Step 'verify-source-commit'
if ($sourceCommitProbe.exit_code -ne 0 -or
    $sourceCommitProbe.stdout.Trim() -cne $frozenCommit) {
    throw 'Frozen source commit mismatch.'
}

$originProbe = Invoke-R3ScopedProcess `
    -Step 'verify-source-origin' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'remote', 'get-url', 'origin') `
    -WorkingDirectory $sourceFull `
    -TimeoutMilliseconds 60000 `
    -OutputEncoding $utf8NoBom
Add-ProcessRecord -List $allProcesses -Record $originProbe -Step 'verify-source-origin'
if ($originProbe.exit_code -ne 0 -or
    $originProbe.stdout.Trim() -notmatch
        '^https://github\.com/ppy/osu(?:\.git)?/?$') {
    throw 'Source origin is not the official ppy/osu HTTPS remote.'
}

$statusProbe = Invoke-R3ScopedProcess `
    -Step 'verify-source-clean' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'status', '--porcelain=v1', '--untracked-files=all') `
    -WorkingDirectory $sourceFull `
    -TimeoutMilliseconds 60000 `
    -OutputEncoding $utf8NoBom
Add-ProcessRecord -List $allProcesses -Record $statusProbe -Step 'verify-source-clean'
if ($statusProbe.exit_code -ne 0 -or
    -not [string]::IsNullOrEmpty($statusProbe.stdout)) {
    throw 'SourcePath must be a clean frozen worktree.'
}

function Invoke-R3BuildReplay {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('replay-a', 'replay-b')]
        [string] $ReplayId,
        [Parameter(Mandatory = $true)][string] $ReplayRoot,
        [Parameter(Mandatory = $true)][string] $BuildStepName
    )

    New-Item -ItemType Directory -Path $ReplayRoot | Out-Null
    $preparedSource = Join-Path $ReplayRoot 'source'
    $logsPath = Join-Path $ReplayRoot 'logs'
    $artifactsPath = Join-Path $ReplayRoot 'artifacts'
    $nugetPackages = Join-Path $ReplayRoot 'nuget-packages'
    $dotnetHome = Join-Path $ReplayRoot 'dotnet-home'
    $tempPath = Join-Path $ReplayRoot 'temp'
    New-Item -ItemType Directory -Path @(
        $logsPath,
        $artifactsPath,
        $nugetPackages,
        $dotnetHome,
        $tempPath
    ) | Out-Null

    $replayProcesses = New-Object System.Collections.Generic.List[object]
    $suffix = if ($ReplayId -ceq 'replay-a') { '' } else { '-replay-b' }

    $clone = Invoke-R3ScopedProcess `
        -Step "clone-frozen-source$suffix" `
        -FilePath $gitPath `
        -Arguments @('clone', '--shared', '--no-checkout', $sourceFull, $preparedSource) `
        -WorkingDirectory $ReplayRoot `
        -StandardOutputPath (Join-Path $logsPath 'clone.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'clone.stderr') `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord `
        -List $replayProcesses `
        -Record $clone `
        -Step "clone-frozen-source$suffix"
    if ($clone.exit_code -ne 0) {
        throw "$ReplayId local clone failed."
    }

    $checkout = Invoke-R3ScopedProcess `
        -Step "checkout-frozen-commit$suffix" `
        -FilePath $gitPath `
        -Arguments @('-C', $preparedSource, 'checkout', '--detach', $frozenCommit) `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath (Join-Path $logsPath 'checkout.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'checkout.stderr') `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord `
        -List $replayProcesses `
        -Record $checkout `
        -Step "checkout-frozen-commit$suffix"
    if ($checkout.exit_code -ne 0) {
        throw "$ReplayId frozen checkout failed."
    }

    Copy-Item `
        -LiteralPath $observationSource `
        -Destination (Join-Path $preparedSource $observationRelativePath)
    Copy-Item `
        -LiteralPath $deterministicTargetsSource `
        -Destination (Join-Path $preparedSource 'Directory.Build.targets')
    foreach ($entry in $lockCopies.GetEnumerator()) {
        Copy-Item `
            -LiteralPath (Join-Path $scriptRoot "dependency-locks\$($entry.Value)") `
            -Destination (Join-Path $preparedSource $entry.Key)
    }
    Assert-Hash `
        -Path (Join-Path $preparedSource $observationRelativePath) `
        -Expected $expectedObservationSha256
    Assert-Hash `
        -Path (Join-Path $preparedSource 'Directory.Build.targets') `
        -Expected $expectedDeterministicTargetsSha256
    foreach ($entry in $expectedLocks.GetEnumerator()) {
        Assert-Hash `
            -Path (Join-Path $preparedSource $entry.Key) `
            -Expected $entry.Value
    }

    $preparedStatus = Invoke-R3ScopedProcess `
        -Step "verify-prepared-status$suffix" `
        -FilePath $gitPath `
        -Arguments @(
            '-C',
            $preparedSource,
            'status',
            '--porcelain=v1',
            '--untracked-files=all'
        ) `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath (Join-Path $logsPath 'prepared-status.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'prepared-status.stderr') `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord `
        -List $replayProcesses `
        -Record $preparedStatus `
        -Step "verify-prepared-status$suffix"
    $expectedStatus = @(
        '?? Directory.Build.targets',
        '?? osu.Game.Rulesets.Osu.Tests/TestSceneGamePrimitivesR3.cs',
        '?? osu.Game.Rulesets.Osu.Tests/packages.lock.json',
        '?? osu.Game.Rulesets.Osu/packages.lock.json',
        '?? osu.Game/packages.lock.json'
    )
    $actualStatus = @(
        $preparedStatus.stdout -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrEmpty($_) }
    )
    if ($preparedStatus.exit_code -ne 0 -or
        @(Compare-Object `
            -ReferenceObject $expectedStatus `
            -DifferenceObject $actualStatus).Count -ne 0) {
        throw "$ReplayId prepared source allowlist mismatch."
    }

    $environmentNames = @(
        'DOTNET_CLI_HOME',
        'NUGET_PACKAGES',
        'TEMP',
        'TMP',
        'DOTNET_SKIP_FIRST_TIME_EXPERIENCE',
        'DOTNET_CLI_TELEMETRY_OPTOUT',
        'DOTNET_NOLOGO',
        'DOTNET_CLI_UI_LANGUAGE',
        'VSLANG',
        'DOTNET_CLI_USE_MSBUILD_SERVER',
        'MSBUILDDISABLENODEREUSE'
    )
    $previousEnvironment = @{}
    foreach ($name in $environmentNames) {
        $previousEnvironment[$name] =
            [System.Environment]::GetEnvironmentVariable($name, 'Process')
    }

    $primaryError = $null
    $shutdownError = $null
    $version = $null
    $restore = $null
    $build = $null
    $list = $null
    $assemblyPath = $null
    try {
        [System.Environment]::SetEnvironmentVariable(
            'DOTNET_CLI_HOME',
            $dotnetHome,
            'Process')
        [System.Environment]::SetEnvironmentVariable(
            'NUGET_PACKAGES',
            $nugetPackages,
            'Process')
        [System.Environment]::SetEnvironmentVariable('TEMP', $tempPath, 'Process')
        [System.Environment]::SetEnvironmentVariable('TMP', $tempPath, 'Process')
        [System.Environment]::SetEnvironmentVariable(
            'DOTNET_SKIP_FIRST_TIME_EXPERIENCE',
            '1',
            'Process')
        [System.Environment]::SetEnvironmentVariable(
            'DOTNET_CLI_TELEMETRY_OPTOUT',
            '1',
            'Process')
        [System.Environment]::SetEnvironmentVariable('DOTNET_NOLOGO', '1', 'Process')
        [System.Environment]::SetEnvironmentVariable(
            'DOTNET_CLI_UI_LANGUAGE',
            'en-US',
            'Process')
        [System.Environment]::SetEnvironmentVariable('VSLANG', '1033', 'Process')
        [System.Environment]::SetEnvironmentVariable(
            'DOTNET_CLI_USE_MSBUILD_SERVER',
            '0',
            'Process')
        [System.Environment]::SetEnvironmentVariable(
            'MSBUILDDISABLENODEREUSE',
            '1',
            'Process')

        $version = Invoke-R3ScopedProcess `
            -Step "resolve-dotnet-version$suffix" `
            -FilePath $dotnetFull `
            -Arguments @('--version') `
            -WorkingDirectory $preparedSource `
            -StandardOutputPath (Join-Path $logsPath 'dotnet-version.stdout') `
            -StandardErrorPath (Join-Path $logsPath 'dotnet-version.stderr') `
            -OutputEncoding $utf8NoBom
        Add-ProcessRecord `
            -List $replayProcesses `
            -Record $version `
            -Step "resolve-dotnet-version$suffix"
        if ($version.exit_code -ne 0 -or
            $version.stdout.Trim() -cne $expectedSdkVersion) {
            throw "$ReplayId portable SDK version mismatch."
        }

        $pathMap = "$preparedSource=/frozen/osu"
        $deterministicProperties = @(
            '-p:ContinuousIntegrationBuild=true',
            '-p:Deterministic=true',
            '-p:DeterministicSourcePaths=true',
            '-p:DebugSymbols=false',
            '-p:DebugType=none',
            "-p:PathMap=$pathMap",
            '-p:UseSharedCompilation=false',
            '-nodeReuse:false'
        )

        $restoreLog = Join-Path $logsPath 'restore-msbuild.log'
        $restore = Invoke-R3ScopedProcess `
            -Step "locked-restore$suffix" `
            -FilePath $dotnetFull `
            -Arguments @(
                'restore',
                $projectRelativePath,
                '--locked-mode',
                '--packages',
                $nugetPackages,
                '-p:NuGetAudit=false',
                '-p:UseArtifactsOutput=true',
                "-p:ArtifactsPath=$artifactsPath"
            ) `
            -WorkingDirectory $preparedSource `
            -StandardOutputPath (Join-Path $logsPath 'restore.stdout') `
            -StandardErrorPath (Join-Path $logsPath 'restore.stderr') `
            -OutputEncoding $utf8NoBom
        Add-ProcessRecord `
            -List $replayProcesses `
            -Record $restore `
            -Step "locked-restore$suffix"
        if ($restore.exit_code -ne 0) {
            throw "$ReplayId locked restore failed."
        }
        [System.IO.File]::WriteAllText(
            $restoreLog,
            $restore.stdout + $restore.stderr,
            $utf8NoBom)

        $buildLog = Join-Path $logsPath 'build-msbuild.log'
        $build = Invoke-R3ScopedProcess `
            -Step $BuildStepName `
            -FilePath $dotnetFull `
            -Arguments (
                @(
                    'build',
                    $projectRelativePath,
                    '--no-restore',
                    '--configuration',
                    'Debug',
                    '--artifacts-path',
                    $artifactsPath
                ) + $deterministicProperties + @(
                    '--verbosity',
                    'normal'
                )
            ) `
            -WorkingDirectory $preparedSource `
            -StandardOutputPath $buildLog `
            -StandardErrorPath (Join-Path $logsPath 'build.stderr') `
            -OutputEncoding $utf8NoBom
        Add-ProcessRecord `
            -List $replayProcesses `
            -Record $build `
            -Step $BuildStepName
        if ($build.exit_code -ne 0) {
            throw "$ReplayId fixture build failed."
        }
        $buildText = $build.stdout + $build.stderr
        if (@([regex]::Matches(
                    $buildText,
                    'warning [A-Z]{2,}[0-9]+')).Count -ne 0) {
            throw "$ReplayId fixture build produced warnings."
        }

        $assemblyPath = Join-Path $ReplayRoot $formalAssemblyRelativePath
        if (-not (Test-Path -LiteralPath $assemblyPath -PathType Leaf)) {
            throw "$ReplayId formal assembly is missing: $assemblyPath"
        }
        $list = Invoke-R3ScopedProcess `
            -Step "list-formal-test-without-execution$suffix" `
            -FilePath $dotnetFull `
            -Arguments @(
                'vstest',
                $assemblyPath,
                '--ListTests'
            ) `
            -WorkingDirectory $tempPath `
            -StandardOutputPath (Join-Path $logsPath 'list-tests.stdout') `
            -StandardErrorPath (Join-Path $logsPath 'list-tests.stderr') `
            -OutputEncoding $utf8NoBom
        Add-ProcessRecord `
            -List $replayProcesses `
            -Record $list `
            -Step "list-formal-test-without-execution$suffix"
        if ($list.exit_code -ne 0 -or
            $list.stdout -notmatch 'TestFormalAdjudicationSchedule') {
            throw "$ReplayId formal test discovery failed."
        }
        if (Get-ChildItem `
                -LiteralPath $ReplayRoot `
                -Recurse `
                -File `
                -Filter '*.trace.json') {
            throw "$ReplayId created a formal trace during list-only discovery."
        }
    }
    catch {
        $primaryError = $_
    }
    finally {
        try {
            $shutdown = Invoke-R3ScopedProcess `
                -Step "shutdown-dotnet-build-servers$suffix" `
                -FilePath $dotnetFull `
                -Arguments @('build-server', 'shutdown') `
                -WorkingDirectory $preparedSource `
                -StandardOutputPath (Join-Path $logsPath 'shutdown.stdout') `
                -StandardErrorPath (Join-Path $logsPath 'shutdown.stderr') `
                -TimeoutMilliseconds 60000 `
                -OutputEncoding $utf8NoBom
            Add-ProcessRecord `
                -List $replayProcesses `
                -Record $shutdown `
                -Step "shutdown-dotnet-build-servers$suffix"
            if ($shutdown.exit_code -ne 0) {
                throw "$ReplayId build-server shutdown failed."
            }
        }
        catch {
            $shutdownError = $_
        }
        finally {
            foreach ($name in $environmentNames) {
                [System.Environment]::SetEnvironmentVariable(
                    $name,
                    $previousEnvironment[$name],
                    'Process')
            }
        }
    }
    if ($null -ne $primaryError) {
        throw $primaryError
    }
    if ($null -ne $shutdownError) {
        throw $shutdownError
    }

    $executionRoot = Split-Path -Parent $assemblyPath
    $removedDiscoveryEphemera =
        Remove-R3DiscoveryEphemera -ExecutionRoot $executionRoot
    $executionTree = New-R3ExecutionTreeManifest `
        -ExecutionRoot $executionRoot `
        -AssemblyPath $assemblyPath `
        -ManifestPath (Join-Path $ReplayRoot 'formal-execution-tree-manifest.json')
    $assembly = Get-Item -LiteralPath $assemblyPath
    $result = [ordered]@{
        replay_id = $ReplayId
        cache_root = $ReplayRoot.Replace('\', '/')
        prepared_source = $preparedSource.Replace('\', '/')
        artifacts_path = $artifactsPath.Replace('\', '/')
        assembly = [ordered]@{
            external_path = $assembly.FullName.Replace('\', '/')
            bytes = $assembly.Length
            sha256 = Get-Sha256 -Path $assembly.FullName
        }
        execution_tree = $executionTree
        locked_restore_exit_code = $restore.exit_code
        build_exit_code = $build.exit_code
        build_warning_count = 0
        test_discovery_exit_code = $list.exit_code
        removed_discovery_ephemera = @($removedDiscoveryEphemera)
        formal_test_discovered = $true
        formal_test_executed = $false
        formal_input_read = $false
        formal_input_executed = $false
        formal_result_created = $false
        process_records = @($replayProcesses | ForEach-Object { $_ })
    }
    foreach ($record in $replayProcesses) {
        $allProcesses.Add($record)
    }
    return $result
}

$replayA = Invoke-R3BuildReplay `
    -ReplayId 'replay-a' `
    -ReplayRoot $cacheA `
    -BuildStepName 'build-observation-fixture'
$replayB = Invoke-R3BuildReplay `
    -ReplayId 'replay-b' `
    -ReplayRoot $cacheB `
    -BuildStepName 'build-observation-fixture-replay-b'

if ($replayA.assembly.sha256 -cne $replayB.assembly.sha256 -or
    $replayA.assembly.bytes -ne $replayB.assembly.bytes) {
    throw (
        'R3 formal assemblies are not byte-identical across independent cache roots: ' +
        "$($replayA.assembly.sha256) vs $($replayB.assembly.sha256)"
    )
}
if ($replayA.execution_tree.manifest.sha256 -cne
        $replayB.execution_tree.manifest.sha256 -or
    $replayA.execution_tree.manifest.bytes -ne
        $replayB.execution_tree.manifest.bytes) {
    throw 'R3 execution-tree manifests differ across independent cache roots.'
}
if (@(Get-R3PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'Portable dotnet processes remained after the reproducibility probe.'
}

$summary = [ordered]@{
    artifact_type = 'continuous_action_r3_build_list_probe'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R3'
    source_commit = $frozenCommit
    project = $projectRelativePath.Replace('\', '/')
    observation_patch_sha256 = $expectedObservationSha256
    safety_guards_sha256 = $expectedSafetyGuardsSha256
    deterministic_build_targets_sha256 =
        $expectedDeterministicTargetsSha256
    dependency_lock_sha256 = $expectedLocks
    locked_restore = $true
    build_exit_code = 0
    build_warning_count = 0
    test_discovery_exit_code = 0
    formal_test_discovered = $true
    formal_test_executed = $false
    formal_input_read = $false
    formal_input_executed = $false
    formal_result_created = $false
    reproducibility = [ordered]@{
        independent_cache_roots = $true
        replay_count = 2
        byte_identical = $true
        formal_assembly_sha256 = $replayA.assembly.sha256
        formal_assembly_bytes = $replayA.assembly.bytes
        execution_tree_manifest_sha256 =
            $replayA.execution_tree.manifest.sha256
        execution_replay_id = 'replay-a'
        replays = @($replayA, $replayB)
    }
    process_records = @($allProcesses | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
}
Write-Json -Path (Join-Path $cacheA 'probe-summary.json') -Value $summary

$summary | ConvertTo-Json -Depth 20
