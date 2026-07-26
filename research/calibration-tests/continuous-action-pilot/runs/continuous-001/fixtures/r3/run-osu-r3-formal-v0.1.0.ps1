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
    [string] $CacheRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ExecutionPermitPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$projectRelativePath = 'osu.Game.Rulesets.Osu.Tests\osu.Game.Rulesets.Osu.Tests.csproj'
$testFullyQualifiedName = 'osu.Game.Rulesets.Osu.Tests.TestSceneGamePrimitivesR3.TestFormalAdjudicationSchedule'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

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

function Resolve-BoundArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][object] $Reference,
        [Parameter(Mandatory = $true)][string] $ExpectedRelativePath
    )

    if ([string]$Reference.path -cne $ExpectedRelativePath -or
        [string]$Reference.sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$') {
        throw "Execution target selected an invalid artifact reference for $ExpectedRelativePath."
    }
    $fullPath = Join-Path $RepositoryRoot $ExpectedRelativePath.Replace('/', '\')
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "Execution target artifact is missing: $fullPath"
    }
    Assert-Hash -Path $fullPath -Expected ([string]$Reference.sha256)
    return (Resolve-Path -LiteralPath $fullPath -ErrorAction Stop).ProviderPath
}

function Find-RepositoryRoot {
    $candidate = [System.IO.DirectoryInfo]::new($PSScriptRoot)
    while ($null -ne $candidate) {
        $tool = Join-Path `
            $candidate.FullName `
            'research/calibration-tests/continuous-action-pilot/tools/verify-formal-execution-permit.py'
        if (Test-Path -LiteralPath $tool -PathType Leaf) {
            return $candidate.FullName
        }
        $candidate = $candidate.Parent
    }
    throw 'Could not locate the repository root or execution-permit verifier.'
}

function Invoke-ExecutionPermitVerifier {
    param([string] $PermitPath)

    $repoRoot = Find-RepositoryRoot
    $verifier = Join-Path `
        $repoRoot `
        'research/calibration-tests/continuous-action-pilot/tools/verify-formal-execution-permit.py'
    $output = @(
        & python -B $verifier verify `
            --repo-root $repoRoot `
            --permit-path $PermitPath `
            --case-id 'CA-R3'
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Execution-permit verification failed with exit code $LASTEXITCODE."
    }
    if ($output.Count -ne 1) {
        throw 'Execution-permit verifier returned an unexpected number of output lines.'
    }
    try {
        $value = $output[0] | ConvertFrom-Json
    } catch {
        throw 'Execution-permit verifier did not return valid JSON.'
    }
    if ($value.status -cne 'formal_execution_permit_verified' `
        -or $value.run_id -cne 'continuous-001' `
        -or $value.case_id -cne 'CA-R3' `
        -or [string]$value.execution_permit_sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$' `
        -or [string]$value.prediction_set_digest -cnotmatch '^(?!0{64})[0-9a-f]{64}$') {
        throw 'Execution-permit verifier returned an invalid CA-R3 result.'
    }
    return $value
}

function Invoke-RawTraceVerifier {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][string] $VerifierPath,
        [Parameter(Mandatory = $true)][string] $PermitPath,
        [Parameter(Mandatory = $true)][string] $TracePath,
        [Parameter(Mandatory = $true)][string] $ConfigurationId
    )

    $output = @(
        & python -B $VerifierPath verify `
            --repo-root $RepositoryRoot `
            --permit-path $PermitPath `
            --case-id 'CA-R3' `
            --trace-path $TracePath `
            --configuration-id $ConfigurationId
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Raw-trace verification failed with exit code $LASTEXITCODE for $ConfigurationId."
    }
    if ($output.Count -ne 1) {
        throw "Raw-trace verifier returned an unexpected number of lines for $ConfigurationId."
    }
    try {
        $value = $output[0] | ConvertFrom-Json
    } catch {
        throw "Raw-trace verifier did not return valid JSON for $ConfigurationId."
    }
    if ($value.status -cne 'formal_raw_trace_verified' -or
        $value.run_id -cne 'continuous-001' -or
        $value.case_id -cne 'CA-R3' -or
        $value.configuration_id -cne $ConfigurationId -or
        [string]$value.formal_trace_sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$' -or
        [string]$value.normalized_trace_sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$') {
        throw "Raw-trace verifier returned an invalid CA-R3 result for $ConfigurationId."
    }
    return $value
}

function Invoke-TrackedProcess {
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
    [System.IO.File]::WriteAllText($StandardOutputPath, $standardOutput, $utf8NoBom)
    [System.IO.File]::WriteAllText($StandardErrorPath, $standardError, $utf8NoBom)

    $aliveAfter = @(Get-Process -Id $pidStarted -ErrorAction SilentlyContinue).Count
    if ($aliveAfter -ne 0) {
        throw "$Step PID $pidStarted remained alive after exit."
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

function Assert-ConfigurationTuple {
    param(
        [Parameter(Mandatory = $true)][string] $ConfigurationId,
        [Parameter(Mandatory = $true)][int] $Delay,
        [Parameter(Mandatory = $true)][bool] $HitAnimations
    )

    $valid = switch ($ConfigurationId) {
        'config.baseline' { $Delay -eq 0 -and $HitAnimations; break }
        'config.variant' { $Delay -eq 75 -and $HitAnimations; break }
        'negative_control_a' { $Delay -eq 0 -and $HitAnimations; break }
        'negative_control_b' { $Delay -eq 0 -and -not $HitAnimations; break }
        default { $false }
    }
    if (-not $valid) {
        throw "Invalid locked configuration tuple: $ConfigurationId / $Delay / $HitAnimations"
    }
}

# The shared verifier is the only authorization boundary. It runs before the
# formal input is opened and before any trace or output directory is created.
if (-not [System.IO.Path]::IsPathRooted($ExecutionPermitPath)) {
    throw 'ExecutionPermitPath must be absolute.'
}
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$permit = Invoke-ExecutionPermitVerifier -PermitPath $executionPermitFull
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$target = $permit.execution_target
$repoRoot = Find-RepositoryRoot

$formalRunnerPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_runner `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/run-osu-r3-formal-v0.1.0.ps1'
if (-not [string]::Equals(
        [System.IO.Path]::GetFullPath($formalRunnerPath),
        [System.IO.Path]::GetFullPath($PSCommandPath),
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Execution target does not bind the running CA-R3 formal runner.'
}
$formalInputPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_input `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/formal-input-r3-v0.1.0.json'
$formalInputSha256 = [string]$target.formal_input.sha256
$buildRunner = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.build_runner `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1'
$fixtureSpecPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.fixture_spec `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-fixture-spec-v0.1.0.json'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.dependency_lock_set `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/dependency-lock-set-v0.1.0.json'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.build_list_evidence `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-build-list-evidence-v0.1.0.json'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.test_body `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/TestSceneGamePrimitivesR3.cs'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.comparator `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.raw_trace_schema `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/schema/ca-r3-raw-trace-0.1.0.schema.json'
$rawTraceVerifier = Join-Path `
    $repoRoot `
    'research/calibration-tests/continuous-action-pilot/tools/verify-formal-raw-trace.py'
if (-not (Test-Path -LiteralPath $rawTraceVerifier -PathType Leaf)) {
    throw 'The permit-bound raw-trace verifier is missing.'
}

$sourceFull = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$cacheFull = [System.IO.Path]::GetFullPath(
    $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($CacheRoot)).TrimEnd('\')
if ($sourceFull -match '\s' -or $cacheFull -match '\s') {
    throw 'SourcePath and CacheRoot must not contain whitespace for this frozen runner.'
}
if (Test-Path -LiteralPath $cacheFull) {
    if (@(Get-ChildItem -LiteralPath $cacheFull -Force).Count -ne 0) {
        throw "CacheRoot must be new or empty: $cacheFull"
    }
}
Assert-Hash -Path $dotnetFull -Expected $expectedDotnetSha256
if (@(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'The dedicated portable dotnet runtime is already in use.'
}

$formalInput = Get-Content -Raw -Encoding UTF8 -LiteralPath $formalInputPath | ConvertFrom-Json
if ($formalInput.run_id -cne 'continuous-001' -or
    $formalInput.case_id -cne 'CA-R3' -or
    $formalInput.formal_input_id -cne 'o.c.0002' -or
    $formalInput.stop_boundary_id -cne 'o.c.0032' -or
    $formalInput.time_base.time_base_id -cne 'o.c.0022' -or
    $formalInput.pre_gate_guard.expected_result_included -ne $false) {
    throw 'Formal input does not match the frozen CA-R3 contract.'
}

$fixtureSpec = Get-Content -Raw -Encoding UTF8 -LiteralPath $fixtureSpecPath | ConvertFrom-Json
if ($fixtureSpec.controlled_variable.variable_id -cne 'o.c.0001' -or
    $fixtureSpec.stop_boundary_id -cne 'o.c.0032' -or
    $fixtureSpec.time_base_id -cne 'o.c.0022') {
    throw 'Fixture spec identifiers do not close against the neutral envelope.'
}
$invariantIds = @($fixtureSpec.invariants | ForEach-Object { $_.invariant_id })
$expectedInvariantIds = 1..7 | ForEach-Object { "inv.c.$($_.ToString('0000'))" }
if (@(Compare-Object -ReferenceObject $expectedInvariantIds -DifferenceObject $invariantIds).Count -ne 0) {
    throw 'Fixture spec invariant ids do not match inv.c.0001 through inv.c.0007.'
}

$configurations = @()
$configurations += @($fixtureSpec.configurations)
$configurations += @($fixtureSpec.negative_control.configurations)
if ($configurations.Count -ne 4) {
    throw 'Fixture spec must contain two primary and two NEG-01 configurations.'
}
foreach ($configuration in $configurations) {
    Assert-ConfigurationTuple `
        -ConfigurationId ([string]$configuration.configuration_id) `
        -Delay ([int]$configuration.adjudication_delay_ms) `
        -HitAnimations ([bool]$configuration.hit_animations)
}

New-Item -ItemType Directory -Path $cacheFull | Out-Null
$preparationRoot = Join-Path $cacheFull 'preparation'
$tracePath = Join-Path $cacheFull 'traces'
$resultPath = Join-Path $cacheFull 'test-results'
$logsPath = Join-Path $cacheFull 'formal-logs'
New-Item -ItemType Directory -Path $tracePath, $resultPath, $logsPath | Out-Null

& $buildRunner `
    -SourcePath $sourceFull `
    -DotnetPath $dotnetFull `
    -CacheRoot $preparationRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $preparationRoot 'probe-summary.json') -PathType Leaf)) {
    throw 'Build/list-only preparation did not produce its summary.'
}
$probe = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $preparationRoot 'probe-summary.json') | ConvertFrom-Json
if ($probe.locked_restore -ne $true -or
    $probe.build_exit_code -ne 0 -or
    $probe.build_warning_count -ne 0 -or
    $probe.formal_test_discovered -ne $true -or
    $probe.formal_test_executed -ne $false) {
    throw 'Build/list-only preparation summary is not gate-ready.'
}

$preparedSource = Join-Path $preparationRoot 'source'
$artifactsPath = Join-Path $preparationRoot 'artifacts'
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
    'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256'
    'GAME_PRIMITIVES_FORMAL_INPUT_SHA256'
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST'
    'GAME_PRIMITIVES_RUN_ID'
    'GAME_PRIMITIVES_CASE_ID'
    'GAME_PRIMITIVES_R3_CONFIGURATION_ID'
    'GAME_PRIMITIVES_R3_OUTPUT_PATH'
    'GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS'
    'GAME_PRIMITIVES_R3_HIT_ANIMATIONS'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
}

[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_HOME', (Join-Path $preparationRoot 'dotnet-home'), 'Process')
[System.Environment]::SetEnvironmentVariable('NUGET_PACKAGES', (Join-Path $preparationRoot 'nuget-packages'), 'Process')
[System.Environment]::SetEnvironmentVariable('TEMP', (Join-Path $preparationRoot 'temp'), 'Process')
[System.Environment]::SetEnvironmentVariable('TMP', (Join-Path $preparationRoot 'temp'), 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_SKIP_FIRST_TIME_EXPERIENCE', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_TELEMETRY_OPTOUT', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_NOLOGO', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_UI_LANGUAGE', 'en-US', 'Process')
[System.Environment]::SetEnvironmentVariable('VSLANG', '1033', 'Process')
[System.Environment]::SetEnvironmentVariable('DOTNET_CLI_USE_MSBUILD_SERVER', '0', 'Process')
[System.Environment]::SetEnvironmentVariable('MSBUILDDISABLENODEREUSE', '1', 'Process')
[System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256', $executionPermitSha256, 'Process')
[System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_FORMAL_INPUT_SHA256', $formalInputSha256, 'Process')
[System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_PREDICTION_SET_DIGEST', $predictionSetDigest, 'Process')
[System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_RUN_ID', 'continuous-001', 'Process')
[System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_CASE_ID', 'CA-R3', 'Process')

$processes = New-Object System.Collections.Generic.List[object]
$traceVerifications = New-Object System.Collections.Generic.List[object]
$completed = $false
try {
    foreach ($configuration in $configurations) {
        $configurationId = [string]$configuration.configuration_id
        $delay = [int]$configuration.adjudication_delay_ms
        $animations = [bool]$configuration.hit_animations
        Assert-ConfigurationTuple -ConfigurationId $configurationId -Delay $delay -HitAnimations $animations

        $traceOutput = Join-Path $tracePath "$configurationId.trace.json"
        if (Test-Path -LiteralPath $traceOutput) {
            throw "Refusing to overwrite formal trace: $traceOutput"
        }

        [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_R3_CONFIGURATION_ID', $configurationId, 'Process')
        [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_R3_OUTPUT_PATH', $traceOutput, 'Process')
        [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS', $delay.ToString(), 'Process')
        [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_R3_HIT_ANIMATIONS', $animations.ToString().ToLowerInvariant(), 'Process')

        try {
            $safeName = $configurationId.Replace('.', '-').Replace('_', '-')
            $run = Invoke-TrackedProcess `
                -Step "execute-$configurationId" `
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
                    '--filter'
                    "FullyQualifiedName=$testFullyQualifiedName"
                    '--results-directory'
                    $resultPath
                    '--logger'
                    "trx;LogFileName=$safeName.trx"
                    '--logger'
                    'console;verbosity=normal'
                ) `
                -WorkingDirectory $preparedSource `
                -StandardOutputPath (Join-Path $logsPath "$safeName.stdout") `
                -StandardErrorPath (Join-Path $logsPath "$safeName.stderr")
            $processes.Add($run)
            if ($run.exit_code -ne 0) {
                throw "$configurationId formal execution failed with exit code $($run.exit_code)."
            }
        }
        finally {
            foreach ($name in @(
                    'GAME_PRIMITIVES_R3_CONFIGURATION_ID'
                    'GAME_PRIMITIVES_R3_OUTPUT_PATH'
                    'GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS'
                    'GAME_PRIMITIVES_R3_HIT_ANIMATIONS')) {
                [System.Environment]::SetEnvironmentVariable($name, $null, 'Process')
            }
        }

        if (-not (Test-Path -LiteralPath $traceOutput -PathType Leaf)) {
            throw "$configurationId did not produce its single formal trace."
        }
        $traceVerification = Invoke-RawTraceVerifier `
            -RepositoryRoot $repoRoot `
            -VerifierPath $rawTraceVerifier `
            -PermitPath $executionPermitFull `
            -TracePath $traceOutput `
            -ConfigurationId $configurationId
        if ([string]$traceVerification.formal_input.sha256 -cne $formalInputSha256) {
            throw "$configurationId trace verifier returned the wrong formal-input binding."
        }
        $traceVerifications.Add($traceVerification)

        $trace = Get-Content -Raw -Encoding UTF8 -LiteralPath $traceOutput | ConvertFrom-Json
        if ($trace.run_id -cne 'continuous-001' -or
            $trace.case_id -cne 'CA-R3' -or
            $trace.execution_permit_sha256 -cne $executionPermitSha256 -or
            $trace.formal_input_sha256 -cne $formalInputSha256 -or
            $trace.prediction_set_digest -cne $predictionSetDigest -or
            $trace.configuration_id -cne $configurationId -or
            $trace.input.adjudication_delay_ms -ne $delay -or
            $trace.input.hit_animations -ne $animations) {
            throw "$configurationId trace does not bind the locked configuration tuple."
        }
    }
    $completed = $true
}
finally {
    $shutdown = Invoke-TrackedProcess `
        -Step 'shutdown-dotnet-build-servers' `
        -FilePath $dotnetFull `
        -Arguments @('build-server', 'shutdown') `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath (Join-Path $logsPath 'shutdown.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'shutdown.stderr') `
        -TimeoutMilliseconds 60000
    $processes.Add($shutdown)

    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}

$remaining = @(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull)
if ($remaining.Count -ne 0) {
    throw "Portable dotnet processes remained after formal execution: $($remaining -join ', ')"
}
if (-not $completed) {
    throw 'CA-R3 formal execution did not complete.'
}

$summary = [ordered]@{
    artifact_type = 'continuous_action_r3_formal_execution_summary'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R3'
    execution_permit_sha256 = $executionPermitSha256
    prediction_set_digest = $predictionSetDigest
    formal_input_sha256 = $formalInputSha256
    fixture_spec_sha256 = [string]$target.support_artifacts.fixture_spec.sha256
    configuration_ids = @($configurations | ForEach-Object { $_.configuration_id })
    trace_artifacts = @(
        Get-ChildItem -LiteralPath $tracePath -File -Filter '*.trace.json' |
            Sort-Object Name |
            ForEach-Object {
                [ordered]@{
                    name = $_.Name
                    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
                }
            }
    )
    trace_verifications = @($traceVerifications | ForEach-Object { $_ })
    process_records = @($processes | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
    comparator_executed = $false
}
[System.IO.File]::WriteAllText(
    (Join-Path $cacheFull 'formal-execution-summary.json'),
    ($summary | ConvertTo-Json -Depth 12) + "`n",
    $utf8NoBom)

$summary | ConvertTo-Json -Depth 12
