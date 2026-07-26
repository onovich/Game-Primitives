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
$expectedObservationSha256 = 'f383e4604f6ab65ff66be6619fe6558da9083e6a57aecaadb24b292f234ef006'
$expectedLocks = [ordered]@{
    'osu.Game\packages.lock.json' = '48952c1c2acfc6634f8f0675dd0c9a43667808db3885711519c5a7562e0fa723'
    'osu.Game.Rulesets.Osu\packages.lock.json' = '2b1612fb68477937bbc4a86437138cd3ae850a25871eb18ce4a626022658d7ae'
    'osu.Game.Rulesets.Osu.Tests\packages.lock.json' = '86a9c02930a3ce76d3aac7facf7261324026f189c37785d1a7530afa72669a8a'
}
$projectRelativePath = 'osu.Game.Rulesets.Osu.Tests\osu.Game.Rulesets.Osu.Tests.csproj'
$observationRelativePath = 'osu.Game.Rulesets.Osu.Tests\TestSceneGamePrimitivesR3.cs'
$testFullyQualifiedName = 'osu.Game.Rulesets.Osu.Tests.TestSceneGamePrimitivesR3.TestFormalAdjudicationSchedule'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-FullPath {
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
    return $candidateFull.Equals($parentFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($parentFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Assert-Hash {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Expected
    )

    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actual -cne $Expected) {
        throw "SHA-256 mismatch for $Path. Expected $Expected, got $actual."
    }
}

function Invoke-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [string] $StandardOutputPath,
        [string] $StandardErrorPath,
        [int] $TimeoutMilliseconds = 600000
    )

    foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            throw "$Step received an argument that requires unsupported command-line quoting: $argument"
        }
    }

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
    if (-not $process.Start()) {
        throw "$Step failed to start."
    }
    $pidStarted = $process.Id
    if (-not $process.WaitForExit($TimeoutMilliseconds)) {
        Stop-Process -Id $pidStarted -Force -ErrorAction SilentlyContinue
        throw "$Step timed out; terminated PID $pidStarted."
    }
    $standardOutput = $process.StandardOutput.ReadToEnd()
    $standardError = $process.StandardError.ReadToEnd()
    $exitCode = $process.ExitCode

    if (-not [string]::IsNullOrEmpty($StandardOutputPath)) {
        [System.IO.File]::WriteAllText($StandardOutputPath, $standardOutput, $utf8NoBom)
    }
    if (-not [string]::IsNullOrEmpty($StandardErrorPath)) {
        [System.IO.File]::WriteAllText($StandardErrorPath, $standardError, $utf8NoBom)
    }

    $aliveAfter = @(Get-Process -Id $pidStarted -ErrorAction SilentlyContinue).Count
    if ($aliveAfter -ne 0) {
        throw "$Step PID $pidStarted remained alive after process exit."
    }

    return [pscustomobject]@{
        step = $Step
        pid = $pidStarted
        exit_code = $exitCode
        alive_after = $aliveAfter
    }
}

function Get-PortableDotnetPids {
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

function Write-Json {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )

    $text = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($Path, $text + "`n", $utf8NoBom)
}

$sourceFull = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$cacheFull = (Get-FullPath -Path $CacheRoot).TrimEnd('\')
$repoRoot = (& git.exe -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($repoRoot)) {
    throw 'Unable to resolve the Game Primitives repository root.'
}

if ($sourceFull -match '\s' -or $cacheFull -match '\s') {
    throw 'SourcePath and CacheRoot must not contain whitespace for this frozen runner.'
}
if (Test-IsSameOrChildPath -Candidate $cacheFull -Parent $repoRoot) {
    throw 'CacheRoot must be outside the Game Primitives repository.'
}
if ((Test-IsSameOrChildPath -Candidate $cacheFull -Parent $sourceFull) -or
    (Test-IsSameOrChildPath -Candidate $sourceFull -Parent $cacheFull)) {
    throw 'CacheRoot and SourcePath must not overlap.'
}
if (Test-Path -LiteralPath $cacheFull) {
    if (@(Get-ChildItem -LiteralPath $cacheFull -Force).Count -ne 0) {
        throw "CacheRoot must be new or empty: $cacheFull"
    }
}

foreach ($formalEnvironmentName in @(
        'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256'
        'GAME_PRIMITIVES_FORMAL_INPUT_SHA256'
        'GAME_PRIMITIVES_PREDICTION_SET_DIGEST'
        'GAME_PRIMITIVES_RUN_ID'
        'GAME_PRIMITIVES_CASE_ID')) {
    if (-not [string]::IsNullOrEmpty(
            [System.Environment]::GetEnvironmentVariable($formalEnvironmentName, 'Process'))) {
        throw "Formal environment variable $formalEnvironmentName must not be present during the build/list-only preparation probe."
    }
}

Assert-Hash -Path $dotnetFull -Expected $expectedDotnetSha256
if (@(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'The dedicated portable dotnet runtime is already in use; refusing to mix process ownership.'
}

$resolvedCommit = (& git.exe -C $sourceFull rev-parse 'HEAD^{commit}').Trim()
if ($LASTEXITCODE -ne 0 -or $resolvedCommit -cne $frozenCommit) {
    throw "Frozen source commit mismatch: $resolvedCommit"
}
$origin = (& git.exe -C $sourceFull remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -notmatch '^https://github\.com/ppy/osu(?:\.git)?/?$') {
    throw "Source origin is not the official ppy/osu HTTPS remote: $origin"
}
$sourceStatus = @(& git.exe -C $sourceFull status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0 -or $sourceStatus.Count -ne 0) {
    throw 'SourcePath must be a clean frozen worktree.'
}

$observationSource = Join-Path $PSScriptRoot 'TestSceneGamePrimitivesR3.cs'
Assert-Hash -Path $observationSource -Expected $expectedObservationSha256
foreach ($entry in $expectedLocks.GetEnumerator()) {
    $lockSourceName = ([System.IO.Path]::GetFileName(
        [System.IO.Path]::GetDirectoryName($entry.Key))) + '.packages.lock.json'
    if ($entry.Key -eq 'osu.Game\packages.lock.json') {
        $lockSourceName = 'osu.Game.packages.lock.json'
    }
    elseif ($entry.Key -eq 'osu.Game.Rulesets.Osu\packages.lock.json') {
        $lockSourceName = 'osu.Game.Rulesets.Osu.packages.lock.json'
    }
    else {
        $lockSourceName = 'osu.Game.Rulesets.Osu.Tests.packages.lock.json'
    }
    Assert-Hash -Path (Join-Path $PSScriptRoot "dependency-locks\$lockSourceName") -Expected $entry.Value
}

New-Item -ItemType Directory -Path $cacheFull | Out-Null
$preparedSource = Join-Path $cacheFull 'source'
$logsPath = Join-Path $cacheFull 'logs'
$artifactsPath = Join-Path $cacheFull 'artifacts'
$nugetPackages = Join-Path $cacheFull 'nuget-packages'
$dotnetHome = Join-Path $cacheFull 'dotnet-home'
$tempPath = Join-Path $cacheFull 'temp'
New-Item -ItemType Directory -Path $logsPath, $artifactsPath, $nugetPackages, $dotnetHome, $tempPath | Out-Null

$processes = New-Object System.Collections.Generic.List[object]
$gitPath = (Get-Command git.exe -ErrorAction Stop | Select-Object -First 1).Source
$cloneResult = Invoke-TrackedProcess `
    -Step 'clone-frozen-source' `
    -FilePath $gitPath `
    -Arguments @('clone', '--shared', '--no-checkout', $sourceFull, $preparedSource) `
    -WorkingDirectory $cacheFull `
    -StandardOutputPath (Join-Path $logsPath 'clone.stdout') `
    -StandardErrorPath (Join-Path $logsPath 'clone.stderr')
$processes.Add($cloneResult)
if ($cloneResult.exit_code -ne 0) {
    throw "Local clone failed with exit code $($cloneResult.exit_code)."
}

$checkoutResult = Invoke-TrackedProcess `
    -Step 'checkout-frozen-commit' `
    -FilePath $gitPath `
    -Arguments @('-C', $preparedSource, 'checkout', '--detach', $frozenCommit) `
    -WorkingDirectory $preparedSource `
    -StandardOutputPath (Join-Path $logsPath 'checkout.stdout') `
    -StandardErrorPath (Join-Path $logsPath 'checkout.stderr')
$processes.Add($checkoutResult)
if ($checkoutResult.exit_code -ne 0) {
    throw "Frozen checkout failed with exit code $($checkoutResult.exit_code)."
}

Copy-Item -LiteralPath $observationSource -Destination (Join-Path $preparedSource $observationRelativePath)
$lockCopies = [ordered]@{
    'osu.Game\packages.lock.json' = 'osu.Game.packages.lock.json'
    'osu.Game.Rulesets.Osu\packages.lock.json' = 'osu.Game.Rulesets.Osu.packages.lock.json'
    'osu.Game.Rulesets.Osu.Tests\packages.lock.json' = 'osu.Game.Rulesets.Osu.Tests.packages.lock.json'
}
foreach ($entry in $lockCopies.GetEnumerator()) {
    Copy-Item `
        -LiteralPath (Join-Path $PSScriptRoot "dependency-locks\$($entry.Value)") `
        -Destination (Join-Path $preparedSource $entry.Key)
}

Assert-Hash -Path (Join-Path $preparedSource $observationRelativePath) -Expected $expectedObservationSha256
foreach ($entry in $expectedLocks.GetEnumerator()) {
    Assert-Hash -Path (Join-Path $preparedSource $entry.Key) -Expected $entry.Value
}

$preparedStatus = @(& $gitPath -C $preparedSource status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect prepared source status.'
}
$expectedStatus = @(
    '?? osu.Game.Rulesets.Osu.Tests/TestSceneGamePrimitivesR3.cs'
    '?? osu.Game.Rulesets.Osu.Tests/packages.lock.json'
    '?? osu.Game.Rulesets.Osu/packages.lock.json'
    '?? osu.Game/packages.lock.json'
)
if (@(Compare-Object -ReferenceObject $expectedStatus -DifferenceObject $preparedStatus).Count -ne 0) {
    throw "Prepared source differs from the four additive files:`n$($preparedStatus -join "`n")"
}

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
    'DOTNET_CLI_USE_MSBUILD_SERVER'
    'MSBUILDDISABLENODEREUSE'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
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
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_USE_MSBUILD_SERVER', '0', 'Process')
[System.Environment]::SetEnvironmentVariable('MSBUILDDISABLENODEREUSE', '1', 'Process')

$completed = $false
try {
    $versionOutput = Join-Path $logsPath 'dotnet-version.stdout'
    $versionResult = Invoke-TrackedProcess `
        -Step 'resolve-dotnet-version' `
        -FilePath $dotnetFull `
        -Arguments @('--version') `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath $versionOutput `
        -StandardErrorPath (Join-Path $logsPath 'dotnet-version.stderr')
    $processes.Add($versionResult)
    if ($versionResult.exit_code -ne 0 -or
        (Get-Content -Raw -LiteralPath $versionOutput).Trim() -cne $expectedSdkVersion) {
        throw 'Portable .NET SDK version mismatch.'
    }

    $restoreLog = Join-Path $logsPath 'restore-msbuild.log'
    $restoreResult = Invoke-TrackedProcess `
        -Step 'locked-restore' `
        -FilePath $dotnetFull `
        -Arguments @(
            'restore'
            $projectRelativePath
            '--locked-mode'
            '--packages'
            $nugetPackages
            '-p:NuGetAudit=false'
            '-p:UseArtifactsOutput=true'
            "-p:ArtifactsPath=$artifactsPath"
            '-p:UseSharedCompilation=false'
            '-nodeReuse:false'
            '--verbosity'
            'quiet'
            "-flp:logfile=$restoreLog;verbosity=normal"
        ) `
        -WorkingDirectory $preparedSource
    $processes.Add($restoreResult)
    if ($restoreResult.exit_code -ne 0) {
        throw "Locked restore failed with exit code $($restoreResult.exit_code)."
    }

    $buildLog = Join-Path $logsPath 'build-msbuild.log'
    $buildResult = Invoke-TrackedProcess `
        -Step 'build-observation-fixture' `
        -FilePath $dotnetFull `
        -Arguments @(
            'build'
            $projectRelativePath
            '--no-restore'
            '--configuration'
            'Debug'
            '--artifacts-path'
            $artifactsPath
            '-p:UseSharedCompilation=false'
            '-nodeReuse:false'
            '--verbosity'
            'quiet'
            "-flp:logfile=$buildLog;verbosity=normal"
        ) `
        -WorkingDirectory $preparedSource
    $processes.Add($buildResult)
    if ($buildResult.exit_code -ne 0) {
        throw "Fixture build failed with exit code $($buildResult.exit_code)."
    }
    if (@(Select-String -Path $buildLog -Pattern 'warning [A-Z]{2,}[0-9]+').Count -ne 0) {
        throw 'Fixture build produced compiler or analyzer warnings.'
    }

    $listOutput = Join-Path $logsPath 'list-tests.stdout'
    $listResult = Invoke-TrackedProcess `
        -Step 'list-formal-test-without-execution' `
        -FilePath $dotnetFull `
        -Arguments @(
            'test'
            $projectRelativePath
            '--no-build'
            '--no-restore'
            '--configuration'
            'Debug'
            '--artifacts-path'
            $artifactsPath
            '--list-tests'
            '--filter'
            "FullyQualifiedName=$testFullyQualifiedName"
            '--logger'
            'console;verbosity=normal'
        ) `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath $listOutput `
        -StandardErrorPath (Join-Path $logsPath 'list-tests.stderr')
    $processes.Add($listResult)
    if ($listResult.exit_code -ne 0) {
        throw "Test discovery failed with exit code $($listResult.exit_code)."
    }
    $listText = Get-Content -Raw -LiteralPath $listOutput
    if ($listText -notmatch 'TestFormalAdjudicationSchedule') {
        throw 'The formal CA-R3 test was not discoverable.'
    }
    if (Get-ChildItem -LiteralPath $cacheFull -Recurse -File -Filter '*.trace.json') {
        throw 'A formal trace unexpectedly appeared during list-only discovery.'
    }

    $completed = $true
}
finally {
    $shutdownResult = Invoke-TrackedProcess `
        -Step 'shutdown-dotnet-build-servers' `
        -FilePath $dotnetFull `
        -Arguments @('build-server', 'shutdown') `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath (Join-Path $logsPath 'shutdown.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'shutdown.stderr') `
        -TimeoutMilliseconds 60000
    $processes.Add($shutdownResult)

    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}

$remaining = @(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull)
if ($remaining.Count -ne 0) {
    throw "Portable dotnet processes remained after shutdown: $($remaining -join ', ')"
}
if (-not $completed) {
    throw 'R3 build/list-only preparation did not complete.'
}

$summary = [ordered]@{
    artifact_type = 'continuous_action_r3_build_list_probe'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R3'
    source_commit = $frozenCommit
    project = $projectRelativePath.Replace('\', '/')
    observation_patch_sha256 = $expectedObservationSha256
    dependency_lock_sha256 = $expectedLocks
    locked_restore = $true
    build_exit_code = 0
    build_warning_count = 0
    test_discovery_exit_code = 0
    formal_test_discovered = $true
    formal_test_executed = $false
    formal_input_executed = $false
    formal_result_created = $false
    process_records = @($processes | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
}
Write-Json -Path (Join-Path $cacheFull 'probe-summary.json') -Value $summary

$summary | ConvertTo-Json -Depth 12
