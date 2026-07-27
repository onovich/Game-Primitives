[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('config.baseline', 'config.variant')]
    [string] $ConfigurationId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2)]
    [int] $RepetitionIndex,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourceRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $DotnetPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $FormalOutputRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ExecutionPermitPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $PythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$runId = 'continuous-001'
$caseId = 'CA-R1'
$expectedCommit = '7eaaad799bb7912625c15af9407c2c67e6305d75'
$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$expectedSdkVersion = '8.0.100'
$expectedPythonPath = 'C:\Python314\python.exe'
$expectedPythonSha256 = 'cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b'
$expectedPythonBytes = 106328
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptRoot '..\..\..\..\..\..\..')
)
$runnerRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/run-footsies-r1-standalone-formal-v0.1.0.ps1'
$comparatorRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/compare-footsies-r1-v0.1.0.ps1'
$formalInputRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-formal-input-v0.1.0.json'
$testBodyRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/FormalProgram.cs'
$formalProjectRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/FootsiesR1Formal.csproj'
$nugetConfigRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/NuGet.config'
$unityCompatibilityRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/UnityCompatibility.cs'
$sourceContractRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/FrozenSourceContract.cs'
$assetLoaderRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/standalone/UnityYamlAssetLoader.cs'
$variantPatchRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch'
$buildRunnerRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/run-footsies-r1-standalone-build-smoke-v0.1.0.ps1'
$buildEvidenceRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/r1-standalone-build-evidence-v0.1.0.json'
$buildReadinessVerifierRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/verify-r1-build-readiness-v0.1.0.py'
$outputBoundaryRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/r1-formal-output-boundary-v0.1.0.ps1'
$processBoundaryRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/r1-process-boundary-v0.1.0.ps1'
$rawTraceSchemaRelativePath = 'research/calibration-tests/continuous-action-pilot/schema/ca-r1-raw-trace-0.1.0.schema.json'
$executionPermitVerifier = Join-Path `
    $repoRoot `
    'research\calibration-tests\continuous-action-pilot\tools\verify-formal-execution-permit.py'
$rawTraceVerifier = Join-Path `
    $repoRoot `
    'research\calibration-tests\continuous-action-pilot\tools\verify-formal-raw-trace.py'

function Assert-Condition {
    param(
        [bool] $Condition,
        [string] $Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-FixedPythonRuntime {
    param([Parameter(Mandatory = $true)][string] $RequestedPath)

    Assert-Condition `
        ([System.IO.Path]::IsPathRooted($RequestedPath)) `
        'PythonPath must be absolute.'
    $resolved = [System.IO.Path]::GetFullPath($RequestedPath)
    Assert-Condition `
        ([string]::Equals(
            $resolved,
            $expectedPythonPath,
            [System.StringComparison]::OrdinalIgnoreCase
        )) `
        'PythonPath must resolve to the frozen Python 3.14.3 runtime.'
    Assert-Condition `
        (Test-Path -LiteralPath $resolved -PathType Leaf) `
        'The frozen Python runtime is missing.'
    Assert-Condition `
        ((Get-Item -LiteralPath $resolved).Length -eq $expectedPythonBytes) `
        'The frozen Python runtime byte count differs.'
    Assert-Condition `
        ((Get-Sha256 $resolved) -ceq $expectedPythonSha256) `
        'The frozen Python runtime SHA-256 differs.'
    return (Resolve-Path -LiteralPath $resolved -ErrorAction Stop).ProviderPath
}

function Resolve-BoundArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][object] $Reference,
        [Parameter(Mandatory = $true)][string] $ExpectedRelativePath
    )

    Assert-Condition `
        ([string]$Reference.path -ceq $ExpectedRelativePath) `
        "Execution target selected the wrong path for $ExpectedRelativePath."
    Assert-Condition `
        ([string]$Reference.sha256 -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        "Execution target selected an invalid SHA-256 for $ExpectedRelativePath."
    $fullPath = Join-Path $RepositoryRoot $ExpectedRelativePath.Replace('/', '\')
    Assert-Condition `
        (Test-Path -LiteralPath $fullPath -PathType Leaf) `
        "Execution target artifact is missing: $fullPath"
    Assert-Condition `
        ((Get-Sha256 $fullPath) -ceq [string]$Reference.sha256) `
        "Execution target artifact hash mismatch for $ExpectedRelativePath."
    return (Resolve-Path -LiteralPath $fullPath -ErrorAction Stop).ProviderPath
}

function Invoke-ExecutionPermitVerifier {
    param(
        [Parameter(Mandatory = $true)][string] $VerifierPath,
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][string] $PermitPath,
        [Parameter(Mandatory = $true)][string] $ExpectedRunId,
        [Parameter(Mandatory = $true)][string] $ExpectedCaseId,
        [Parameter(Mandatory = $true)][string] $PythonExecutablePath
    )

    Assert-Condition `
        (Test-Path -LiteralPath $VerifierPath -PathType Leaf) `
        "Execution-permit verifier is missing: $VerifierPath"
    $verificationOutput = @(
        & $PythonExecutablePath -B $VerifierPath verify `
            --repo-root $RepositoryRoot `
            --permit-path $PermitPath `
            --case-id $ExpectedCaseId 2>&1
    )
    $verificationExitCode = $LASTEXITCODE
    Assert-Condition `
        ($verificationExitCode -eq 0) `
        ("Execution-permit verification failed: " + ($verificationOutput -join "`n"))
    Assert-Condition `
        ($verificationOutput.Count -eq 1) `
        'Execution-permit verifier returned an unexpected number of output lines.'
    try {
        $verification = $verificationOutput[0].ToString() | ConvertFrom-Json
    }
    catch {
        throw "Execution-permit verifier returned invalid JSON: $($_.Exception.Message)"
    }
    Assert-Condition `
        ($verification.status -ceq 'formal_execution_permit_verified') `
        'Execution-permit verifier did not report a verified permit.'
    Assert-Condition ($verification.run_id -ceq $ExpectedRunId) 'Execution-permit run_id mismatch.'
    Assert-Condition ($verification.case_id -ceq $ExpectedCaseId) 'Execution-permit case_id mismatch.'
    Assert-Condition `
        ($null -ne $verification.execution_target) `
        'Execution-permit verifier did not return an execution target.'
    Assert-Condition `
        ($verification.execution_target.case_id -ceq $ExpectedCaseId) `
        'Execution-permit target case_id mismatch.'
    Assert-Condition `
        ($verification.execution_permit_sha256 -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        'Execution-permit SHA-256 is invalid.'
    Assert-Condition `
        ($verification.prediction_set_digest -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        'Prediction-set digest is invalid.'
    Assert-Condition `
        ([string]$verification.python_runtime.runtime.executable_path -ceq
            'C:/Python314/python.exe' -and
         [long]$verification.python_runtime.runtime.bytes -eq
            $expectedPythonBytes -and
         [string]$verification.python_runtime.runtime.sha256 -ceq
            $expectedPythonSha256) `
        'Execution permit selected the wrong Python runtime.'
    return $verification
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

function Get-BoundFormalBuildOutput {
    param(
        [Parameter(Mandatory = $true)][string] $EvidencePath,
        [Parameter(Mandatory = $true)][string] $ExpectedConfigurationId
    )

    try {
        $evidence = Get-Content -Raw -LiteralPath $EvidencePath |
            ConvertFrom-Json
    }
    catch {
        throw "Bound build evidence is invalid JSON: $($_.Exception.Message)"
    }
    Assert-Condition `
        ($evidence.artifact_type -ceq 'continuous_action_r1_standalone_build_evidence') `
        'Bound build evidence has the wrong artifact_type.'
    Assert-Condition ($evidence.run_id -ceq $runId) 'Bound build evidence has the wrong run_id.'
    Assert-Condition ($evidence.case_id -ceq $caseId) 'Bound build evidence has the wrong case_id.'
    Assert-Condition `
        ($evidence.build_gate_status -ceq 'passed') `
        'Bound build evidence did not pass its build gate.'
    foreach ($field in @(
            'authorization_created',
            'comparator_executed',
            'formal_environment_present',
            'formal_input_executed',
            'formal_input_path_accepted',
            'formal_input_read',
            'formal_result_created',
            'formal_runner_executed',
            'permit_created',
            'predictions_created'
        )) {
        Assert-Condition `
            ($evidence.formal_execution.$field -eq $false) `
            "Bound build evidence formal flag is not false: $field"
    }
    Assert-Condition `
        ($evidence.reproducibility.verified -eq $true) `
        'Bound build evidence does not prove reproducibility.'
    Assert-Condition `
        (@($evidence.reproducibility.cache_roots).Count -eq 2) `
        'Bound build evidence must name two independent cache roots.'
    Assert-Condition `
        (@($evidence.reproducibility.evidence_files).Count -eq 2) `
        'Bound build evidence must bind two independent evidence files.'
    Assert-Condition `
        ([int]$evidence.reproducibility.formal_pdb_files_found -eq 0) `
        'Bound build evidence reports a formal PDB.'

    $configurations = @(
        $evidence.configurations |
            Where-Object { $_.configuration_id -ceq $ExpectedConfigurationId }
    )
    Assert-Condition `
        ($configurations.Count -eq 1) `
        'Bound build evidence does not contain exactly one selected configuration.'
    $configuration = $configurations[0]
    Assert-Condition `
        (
            [int]$configuration.restore_exit_code -eq 0 -and
            [int]$configuration.build_exit_code -eq 0 -and
            [int]$configuration.formal_restore_exit_code -eq 0 -and
            [int]$configuration.formal_build_exit_code -eq 0 -and
            [int]$configuration.warning_count -eq 0
        ) `
        'Bound build evidence selected a failed or warning-producing build.'
    $formalOutputs = @(
        $configuration.outputs |
            Where-Object { $_.output_kind -ceq 'formal_execution' }
    )
    Assert-Condition `
        ($formalOutputs.Count -eq 1) `
        'Bound build evidence does not contain exactly one formal assembly.'
    $formalOutput = $formalOutputs[0]
    $expectedOutputId = if ($ExpectedConfigurationId -ceq 'config.baseline') {
        'output.ca-r1.baseline-formal-assembly'
    }
    else {
        'output.ca-r1.variant-formal-assembly'
    }
    $reproducedSha256 = if ($ExpectedConfigurationId -ceq 'config.baseline') {
        [string]$evidence.reproducibility.formal_outputs.baseline_sha256
    }
    else {
        [string]$evidence.reproducibility.formal_outputs.variant_sha256
    }
    Assert-Condition `
        ([string]$formalOutput.output_id -ceq $expectedOutputId) `
        'Bound build evidence selected the wrong formal output ID.'
    Assert-Condition `
        ([string]$formalOutput.sha256 -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        'Bound build evidence selected an invalid formal assembly SHA-256.'
    Assert-Condition `
        ($reproducedSha256 -ceq [string]$formalOutput.sha256) `
        'Reproducibility evidence does not bind the selected formal assembly.'

    return [pscustomobject]@{
        evidence_sha256 = Get-Sha256 $EvidencePath
        output_id = [string]$formalOutput.output_id
        sha256 = [string]$formalOutput.sha256
    }
}

# Permit-first boundary: no source, toolchain, formal input, output, log, or
# fixture target is inspected before this verifier succeeds.
$resolvedPythonPath = Resolve-FixedPythonRuntime -RequestedPath $PythonPath
Assert-Condition `
    ([System.IO.Path]::IsPathRooted($ExecutionPermitPath)) `
    'ExecutionPermitPath must be absolute.'
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$executionPermit = Invoke-ExecutionPermitVerifier `
    -VerifierPath $executionPermitVerifier `
    -RepositoryRoot $repoRoot `
    -PermitPath $executionPermitFull `
    -ExpectedRunId $runId `
    -ExpectedCaseId $caseId `
    -PythonExecutablePath $resolvedPythonPath

$executionTarget = $executionPermit.execution_target
$boundRunner = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.formal_runner `
    -ExpectedRelativePath $runnerRelativePath
Assert-Condition `
    ([string]::Equals(
        [System.IO.Path]::GetFullPath($boundRunner),
        [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path),
        [System.StringComparison]::OrdinalIgnoreCase
    )) `
    'Execution target does not bind the running CA-R1 standalone formal runner.'
$boundFormalInput = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.formal_input `
    -ExpectedRelativePath $formalInputRelativePath
$formalInputSha256 = [string]$executionTarget.formal_input.sha256
$boundTestBody = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.test_body `
    -ExpectedRelativePath $testBodyRelativePath
$boundFormalProject = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.formal_project `
    -ExpectedRelativePath $formalProjectRelativePath
$boundNugetConfig = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.nuget_config `
    -ExpectedRelativePath $nugetConfigRelativePath
$boundUnityCompatibility = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.unity_compatibility `
    -ExpectedRelativePath $unityCompatibilityRelativePath
$boundSourceContract = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.source_contract `
    -ExpectedRelativePath $sourceContractRelativePath
$boundAssetLoader = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.asset_loader `
    -ExpectedRelativePath $assetLoaderRelativePath
$boundVariantPatch = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.variant_patch `
    -ExpectedRelativePath $variantPatchRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_runner `
    -ExpectedRelativePath $buildRunnerRelativePath
$boundBuildEvidence = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_evidence `
    -ExpectedRelativePath $buildEvidenceRelativePath
$boundBuildReadinessVerifier = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_readiness_verifier `
    -ExpectedRelativePath $buildReadinessVerifierRelativePath
$boundOutputBoundary = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.output_boundary `
    -ExpectedRelativePath $outputBoundaryRelativePath
$boundProcessBoundary = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.process_boundary `
    -ExpectedRelativePath $processBoundaryRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.comparator `
    -ExpectedRelativePath $comparatorRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$buildVerificationOutput = @(
    & $resolvedPythonPath -B $boundBuildReadinessVerifier verify `
        --repo-root $repoRoot `
        --evidence-path $boundBuildEvidence 2>&1
)
Assert-Condition `
    ($LASTEXITCODE -eq 0) `
    ("R1 build-readiness verification failed: " +
        ($buildVerificationOutput -join "`n"))
Assert-Condition `
    ($buildVerificationOutput.Count -eq 1) `
    'R1 build-readiness verifier returned an unexpected number of lines.'
try {
    $buildVerification = $buildVerificationOutput[0].ToString() |
        ConvertFrom-Json
}
catch {
    throw "R1 build-readiness verifier returned invalid JSON: $($_.Exception.Message)"
}
Assert-Condition `
    ($buildVerification.status -ceq 'r1_build_readiness_verified') `
    'R1 build-readiness verifier did not report success.'
Assert-Condition `
    ($buildVerification.formal_input_read -eq $false) `
    'R1 build-readiness verifier reported a formal-input read.'
Assert-Condition `
    ($null -ne $buildVerification.outputs.$ConfigurationId) `
    'R1 build-readiness verifier did not bind the selected configuration.'

$resolvedSourceRoot = (Resolve-Path -LiteralPath $SourceRoot -ErrorAction Stop).ProviderPath.TrimEnd('\')
$resolvedDotnetPath = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$null = . $boundOutputBoundary
$null = . $boundProcessBoundary
$outputLayout = Resolve-R1FormalOutputLayout `
    -Mode runner `
    -FormalOutputRoot $FormalOutputRoot `
    -RepositoryRoot $repoRoot `
    -SourceRoot $resolvedSourceRoot `
    -DotnetPath $resolvedDotnetPath `
    -ConfigurationId $ConfigurationId `
    -RepetitionIndex $RepetitionIndex
$resolvedOutputPath = [string]$outputLayout.raw_trace_path
$resolvedLogPath = [string]$outputLayout.runner_log_path
Assert-Condition ($resolvedSourceRoot -notmatch '\s') 'SourceRoot must not contain whitespace.'
Assert-Condition ($resolvedDotnetPath -notmatch '\s') 'DotnetPath must not contain whitespace.'
Assert-Condition `
    ((Get-Sha256 $resolvedDotnetPath) -ceq $expectedDotnetSha256) `
    'Portable dotnet SHA-256 mismatch.'
Assert-Condition `
    ((Get-Sha256 $boundFormalInput) -ceq $formalInputSha256) `
    'Formal input SHA-256 mismatch after target resolution.'
Assert-Condition `
    (@(Get-PortableDotnetPids -ResolvedDotnetPath $resolvedDotnetPath).Count -eq 0) `
    'The dedicated portable dotnet runtime is already in use.'

$sourceCommit = (& git.exe -C $resolvedSourceRoot rev-parse 'HEAD^{commit}').Trim()
Assert-Condition ($LASTEXITCODE -eq 0) 'Could not read the source commit.'
Assert-Condition ($sourceCommit -ceq $expectedCommit) 'Source commit mismatch.'
$sourceStatus = @(& git.exe -C $resolvedSourceRoot status --porcelain=v1 --untracked-files=all)
Assert-Condition ($LASTEXITCODE -eq 0) 'Could not read source status.'
Assert-Condition ($sourceStatus.Count -eq 0) 'The source repository is not clean.'

$outputDirectory = Split-Path -Parent $resolvedOutputPath
$logDirectory = Split-Path -Parent $resolvedLogPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
if ($logDirectory) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

$systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$temporaryRoot = Join-Path `
    $systemTemp `
    ('game-primitives-r1-standalone-' + [Guid]::NewGuid().ToString('N'))
$temporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
Assert-Condition `
    ($temporaryRoot.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase)) `
    'Temporary root escaped the system temp directory.'
$preparedSource = Join-Path $temporaryRoot 'source'
$fixtureProject = Join-Path $temporaryRoot 'fixture'
$artifactsPath = Join-Path $temporaryRoot 'artifacts'
$logsPath = Join-Path $temporaryRoot 'logs'
$nugetPackages = Join-Path $temporaryRoot 'nuget'
$dotnetHome = Join-Path $temporaryRoot 'dotnet-home'
$tempPath = Join-Path $temporaryRoot 'temp'
$processes = New-Object System.Collections.Generic.List[object]
$gitPath = (Get-Command git.exe -ErrorAction Stop | Select-Object -First 1).Source

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
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST'
    'GAME_PRIMITIVES_RUN_ID'
    'GAME_PRIMITIVES_CASE_ID'
    'GAME_PRIMITIVES_FORMAL_INPUT_SHA256'
    'GP_R1_SOURCE_ROOT'
    'GP_R1_CONFIGURATION_ID'
    'GP_R1_INPUT_PATH'
    'GP_R1_OUTPUT_PATH'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
}

$formalProcessRecord = $null
$rawVerificationText = $null
$formalBuildBinding = $null
try {
    New-Item -ItemType Directory -Path $temporaryRoot, $fixtureProject, $logsPath, `
        $nugetPackages, $dotnetHome, $tempPath | Out-Null
    Copy-Item -LiteralPath $boundFormalProject -Destination (Join-Path $fixtureProject 'FootsiesR1Formal.csproj')
    Copy-Item -LiteralPath $boundNugetConfig -Destination (Join-Path $fixtureProject 'NuGet.config')
    Copy-Item -LiteralPath $boundUnityCompatibility -Destination (Join-Path $fixtureProject 'UnityCompatibility.cs')
    Copy-Item -LiteralPath $boundSourceContract -Destination (Join-Path $fixtureProject 'FrozenSourceContract.cs')
    Copy-Item -LiteralPath $boundAssetLoader -Destination (Join-Path $fixtureProject 'UnityYamlAssetLoader.cs')
    Copy-Item -LiteralPath $boundTestBody -Destination (Join-Path $fixtureProject 'FormalProgram.cs')

    $cloneRecord = Invoke-R1TrackedProcess `
        -Step 'clone-frozen-source' `
        -FilePath $gitPath `
        -Arguments @('clone', '--shared', '--no-checkout', $resolvedSourceRoot, $preparedSource) `
        -WorkingDirectory $temporaryRoot `
        -StandardOutputPath (Join-Path $logsPath 'clone.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'clone.stderr')
    $processes.Add($cloneRecord)
    Assert-Condition ($cloneRecord.exit_code -eq 0) 'Could not clone frozen source.'

    $checkoutRecord = Invoke-R1TrackedProcess `
        -Step 'checkout-frozen-source' `
        -FilePath $gitPath `
        -Arguments @('-C', $preparedSource, 'checkout', '--detach', $expectedCommit) `
        -WorkingDirectory $preparedSource `
        -StandardOutputPath (Join-Path $logsPath 'checkout.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'checkout.stderr')
    $processes.Add($checkoutRecord)
    Assert-Condition ($checkoutRecord.exit_code -eq 0) 'Could not checkout frozen source.'

    if ($ConfigurationId -ceq 'config.variant') {
        $patchCopy = Join-Path $temporaryRoot 'variant.patch'
        Copy-Item -LiteralPath $boundVariantPatch -Destination $patchCopy
        $patchRecord = Invoke-R1TrackedProcess `
            -Step 'apply-frozen-variant' `
            -FilePath $gitPath `
            -Arguments @('-C', $preparedSource, 'apply', $patchCopy) `
            -WorkingDirectory $preparedSource `
            -StandardOutputPath (Join-Path $logsPath 'patch.stdout') `
            -StandardErrorPath (Join-Path $logsPath 'patch.stderr')
        $processes.Add($patchRecord)
        Assert-Condition ($patchRecord.exit_code -eq 0) 'Could not apply frozen variant patch.'
    }

    $preparedStatus = @(& $gitPath -C $preparedSource status --porcelain=v1 --untracked-files=all)
    Assert-Condition ($LASTEXITCODE -eq 0) 'Could not inspect prepared source.'
    $expectedStatus = if ($ConfigurationId -ceq 'config.variant') {
        @(' M Assets/Fighter/F00/F00.asset')
    }
    else {
        @()
    }
    Assert-Condition `
        (@(Compare-Object -ReferenceObject $expectedStatus -DifferenceObject $preparedStatus).Count -eq 0) `
        'Prepared source change allowlist mismatch.'

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

    $versionRecord = Invoke-R1TrackedProcess `
        -Step 'resolve-dotnet-version' `
        -FilePath $resolvedDotnetPath `
        -Arguments @('--version') `
        -WorkingDirectory $fixtureProject `
        -StandardOutputPath (Join-Path $logsPath 'version.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'version.stderr')
    $processes.Add($versionRecord)
    Assert-Condition ($versionRecord.exit_code -eq 0) 'Could not read portable SDK version.'
    Assert-Condition `
        ((Get-Content -Raw -LiteralPath (Join-Path $logsPath 'version.stdout')).Trim() -ceq $expectedSdkVersion) `
        'Portable SDK version mismatch.'

    $restoreRecord = Invoke-R1TrackedProcess `
        -Step 'restore-formal-fixture' `
        -FilePath $resolvedDotnetPath `
        -Arguments @(
            'restore'
            'FootsiesR1Formal.csproj'
            '--configfile'
            'NuGet.config'
            '--packages'
            $nugetPackages
            '-p:UseArtifactsOutput=true'
            "-p:ArtifactsPath=$artifactsPath"
            "-p:FootsiesSourceRoot=$preparedSource"
            '-p:UseSharedCompilation=false'
            '-nodeReuse:false'
            '--verbosity'
            'quiet'
        ) `
        -WorkingDirectory $fixtureProject `
        -StandardOutputPath (Join-Path $logsPath 'restore.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'restore.stderr')
    $processes.Add($restoreRecord)
    Assert-Condition ($restoreRecord.exit_code -eq 0) 'Formal fixture restore failed.'

    $buildRecord = Invoke-R1TrackedProcess `
        -Step 'build-formal-fixture' `
        -FilePath $resolvedDotnetPath `
        -Arguments @(
            'build'
            'FootsiesR1Formal.csproj'
            '--no-restore'
            '--configuration'
            'Release'
            '--artifacts-path'
            $artifactsPath
            "-p:FootsiesSourceRoot=$preparedSource"
            '-p:UseSharedCompilation=false'
            '-nodeReuse:false'
            '--verbosity'
            'minimal'
        ) `
        -WorkingDirectory $fixtureProject `
        -StandardOutputPath (Join-Path $logsPath 'build.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'build.stderr')
    $processes.Add($buildRecord)
    Assert-Condition ($buildRecord.exit_code -eq 0) 'Formal fixture build failed.'

    $formalDll = Join-Path $artifactsPath 'bin\FootsiesR1Formal\release\FootsiesR1Formal.dll'
    Assert-Condition (Test-Path -LiteralPath $formalDll -PathType Leaf) 'Formal assembly is missing.'
    Assert-Condition `
        (@(Get-ChildItem -LiteralPath (Split-Path -Parent $formalDll) -Filter '*.pdb' -File).Count -eq 0) `
        'Formal fixture unexpectedly emitted a PDB.'
    $formalBuildBinding = Get-BoundFormalBuildOutput `
        -EvidencePath $boundBuildEvidence `
        -ExpectedConfigurationId $ConfigurationId
    Assert-Condition `
        ((Get-Sha256 $formalDll) -ceq $formalBuildBinding.sha256) `
        'Built formal assembly differs from the permit-bound reproducible build evidence.'

    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
        $executionPermit.execution_permit_sha256,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
        $executionPermit.prediction_set_digest,
        'Process')
    [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_RUN_ID', $runId, 'Process')
    [System.Environment]::SetEnvironmentVariable('GAME_PRIMITIVES_CASE_ID', $caseId, 'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_FORMAL_INPUT_SHA256',
        $formalInputSha256,
        'Process')
    [System.Environment]::SetEnvironmentVariable('GP_R1_SOURCE_ROOT', $preparedSource, 'Process')
    [System.Environment]::SetEnvironmentVariable('GP_R1_CONFIGURATION_ID', $ConfigurationId, 'Process')
    [System.Environment]::SetEnvironmentVariable('GP_R1_INPUT_PATH', $boundFormalInput, 'Process')
    [System.Environment]::SetEnvironmentVariable('GP_R1_OUTPUT_PATH', $resolvedOutputPath, 'Process')

    $formalProcessRecord = Invoke-R1TrackedProcess `
        -Step 'execute-seven-event-formal-body' `
        -FilePath $resolvedDotnetPath `
        -Arguments @($formalDll, '--formal') `
        -WorkingDirectory $temporaryRoot `
        -StandardOutputPath (Join-Path $logsPath 'formal.stdout') `
        -StandardErrorPath (Join-Path $logsPath 'formal.stderr')
    $processes.Add($formalProcessRecord)
    Assert-Condition `
        ($formalProcessRecord.exit_code -eq 0) `
        "Formal body exited with code $($formalProcessRecord.exit_code)."
    Assert-Condition `
        (Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf) `
        'Formal body did not create the raw trace.'

    $rawVerificationOutput = @(
        & $resolvedPythonPath -B $rawTraceVerifier verify `
            --repo-root $repoRoot `
            --permit-path $executionPermitFull `
            --case-id $caseId `
            --trace-path $resolvedOutputPath `
            --configuration-id $ConfigurationId 2>&1
    )
    Assert-Condition `
        ($LASTEXITCODE -eq 0) `
        ("Raw trace verification failed: " + ($rawVerificationOutput -join "`n"))
    Assert-Condition ($rawVerificationOutput.Count -eq 1) 'Raw verifier output was not singular.'
    $rawVerificationText = $rawVerificationOutput[0].ToString()
}
finally {
    try {
        try {
            $shutdownStdout = Join-Path $logsPath 'shutdown.stdout'
            $shutdownStderr = Join-Path $logsPath 'shutdown.stderr'
            if ((Test-Path -LiteralPath $temporaryRoot) -and
                (Test-Path -LiteralPath $fixtureProject) -and
                (Test-Path -LiteralPath $resolvedDotnetPath)) {
                $shutdownRecord = Invoke-R1TrackedProcess `
                    -Step 'shutdown-dotnet-build-servers' `
                    -FilePath $resolvedDotnetPath `
                    -Arguments @('build-server', 'shutdown') `
                    -WorkingDirectory $fixtureProject `
                    -StandardOutputPath $shutdownStdout `
                    -StandardErrorPath $shutdownStderr `
                    -TimeoutMilliseconds 60000
                $processes.Add($shutdownRecord)
                Assert-Condition `
                    ($shutdownRecord.exit_code -eq 0) `
                    'Portable dotnet build-server shutdown failed.'
            }
        }
        finally {
            foreach ($name in $environmentNames) {
                [System.Environment]::SetEnvironmentVariable(
                    $name,
                    $previousEnvironment[$name],
                    'Process'
                )
            }
        }
    }
    finally {
        try {
            if (Test-Path -LiteralPath $temporaryRoot) {
                $resolvedTemporaryRoot = (
                    Get-Item -LiteralPath $temporaryRoot -Force
                ).FullName
                Assert-Condition `
                    ($resolvedTemporaryRoot.StartsWith(
                        $systemTemp,
                        [System.StringComparison]::OrdinalIgnoreCase
                    )) `
                    'Refusing to remove a temporary path outside the system temp directory.'
                Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force
            }
        }
        finally {
            Assert-Condition `
                (@(
                    Get-PortableDotnetPids `
                        -ResolvedDotnetPath $resolvedDotnetPath
                ).Count -eq 0) `
                'Portable dotnet process remained after formal execution.'
        }
    }
}

$log = [ordered]@{
    artifact_type = 'continuous_action_r1_standalone_formal_log'
    artifact_version = '0.1.0'
    run_id = $runId
    case_id = $caseId
    configuration_id = $ConfigurationId
    repetition_index = $RepetitionIndex
    execution_permit_sha256 = $executionPermit.execution_permit_sha256
    formal_input_sha256 = $formalInputSha256
    prediction_set_digest = $executionPermit.prediction_set_digest
    build_evidence_sha256 = $formalBuildBinding.evidence_sha256
    formal_assembly_output_id = $formalBuildBinding.output_id
    formal_assembly_sha256 = $formalBuildBinding.sha256
    raw_trace_sha256 = Get-Sha256 $resolvedOutputPath
    raw_trace_verification = $rawVerificationText | ConvertFrom-Json
    process_records = @($processes | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
}
[System.IO.File]::WriteAllText(
    $resolvedLogPath,
    (($log | ConvertTo-Json -Depth 12) + "`n"),
    $utf8NoBom
)
