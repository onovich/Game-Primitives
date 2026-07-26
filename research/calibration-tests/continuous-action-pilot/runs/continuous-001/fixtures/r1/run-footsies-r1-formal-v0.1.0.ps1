[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('config.baseline', 'config.variant')]
    [string]$ConfigurationId,

    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$UnityExe,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [Parameter(Mandatory = $true)]
    [string]$ExecutionPermitPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$expectedCommit = '7eaaad799bb7912625c15af9407c2c67e6305d75'
$expectedUnitySha256 = '3972bacc7abfe37dadf4d09cf6ce095efa558649547d32adba81addbf101ffe0'
$runId = 'continuous-001'
$caseId = 'CA-R1'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptRoot '..\..\..\..\..\..\..')
)
$runnerRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/run-footsies-r1-formal-v0.1.0.ps1'
$comparatorRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/compare-footsies-r1-v0.1.0.ps1'
$formalInputRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-formal-input-v0.1.0.json'
$testBodyRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-observation-v0.1.0.cs'
$testBodyMetadataRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-observation-v0.1.0.cs.meta'
$variantPatchRelativePath = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch'
$rawTraceSchemaRelativePath = 'research/calibration-tests/continuous-action-pilot/schema/ca-r1-raw-trace-0.1.0.schema.json'
$executionPermitVerifier = Join-Path `
    $repoRoot `
    'research\calibration-tests\continuous-action-pilot\tools\verify-formal-execution-permit.py'

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Get-Sha256 {
    param([string]$LiteralPath)
    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-ExistingFile {
    param([string]$LiteralPath)
    $item = Get-Item -LiteralPath $LiteralPath -Force
    Assert-Condition (-not $item.PSIsContainer) "Expected a file: $LiteralPath"
    return $item.FullName
}

function Resolve-ExistingDirectory {
    param([string]$LiteralPath)
    $item = Get-Item -LiteralPath $LiteralPath -Force
    Assert-Condition $item.PSIsContainer "Expected a directory: $LiteralPath"
    return $item.FullName
}

function Resolve-BoundArtifact {
    param(
        [string]$RepositoryRoot,
        [object]$Reference,
        [string]$ExpectedRelativePath
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
        [string]$VerifierPath,
        [string]$RepositoryRoot,
        [string]$PermitPath,
        [string]$ExpectedRunId,
        [string]$ExpectedCaseId
    )

    Assert-Condition `
        (Test-Path -LiteralPath $VerifierPath -PathType Leaf) `
        "Execution-permit verifier is missing: $VerifierPath"
    $verificationOutput = @(
        & python -B $VerifierPath verify `
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
    return $verification
}

# The repository verifier is intentionally the first operation that can open a
# formal-run artifact. It must succeed before source, toolchain, input, trace,
# log, or output paths are inspected.
Assert-Condition `
    ([System.IO.Path]::IsPathRooted($ExecutionPermitPath)) `
    'ExecutionPermitPath must be absolute.'
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$executionPermit = Invoke-ExecutionPermitVerifier `
    -VerifierPath $executionPermitVerifier `
    -RepositoryRoot $repoRoot `
    -PermitPath $executionPermitFull `
    -ExpectedRunId $runId `
    -ExpectedCaseId $caseId

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
    'Execution target does not bind the running CA-R1 formal runner.'
$boundFormalInput = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.formal_input `
    -ExpectedRelativePath $formalInputRelativePath
$formalInputSha256 = [string]$executionTarget.formal_input.sha256
$observationSource = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.test_body `
    -ExpectedRelativePath $testBodyRelativePath
$observationMeta = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.test_body_metadata `
    -ExpectedRelativePath $testBodyMetadataRelativePath
$variantPatch = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.variant_patch `
    -ExpectedRelativePath $variantPatchRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.comparator `
    -ExpectedRelativePath $comparatorRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$resolvedSourceRoot = Resolve-ExistingDirectory $SourceRoot
$resolvedUnityExe = Resolve-ExistingFile $UnityExe
$resolvedInputPath = $boundFormalInput

Assert-Condition ((Get-Sha256 $resolvedUnityExe) -eq $expectedUnitySha256) 'Unity executable SHA-256 mismatch.'
Assert-Condition ((Get-Sha256 $resolvedInputPath) -ceq $formalInputSha256) 'Formal input SHA-256 mismatch.'

$sourceCommit = (& git -C $resolvedSourceRoot rev-parse HEAD).Trim()
Assert-Condition ($LASTEXITCODE -eq 0) 'Could not read the source commit.'
Assert-Condition ($sourceCommit -eq $expectedCommit) 'Source commit mismatch.'
$sourceStatus = @(& git -C $resolvedSourceRoot status --porcelain=v1 --untracked-files=all)
Assert-Condition ($LASTEXITCODE -eq 0) 'Could not read source status.'
Assert-Condition ($sourceStatus.Count -eq 0) 'The source repository is not clean.'

$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$resolvedLogPath = [System.IO.Path]::GetFullPath($LogPath)
Assert-Condition (-not (Test-Path -LiteralPath $resolvedOutputPath)) 'Output path already exists.'
Assert-Condition (-not (Test-Path -LiteralPath $resolvedLogPath)) 'Log path already exists.'

$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('game-primitives-r1-' + [Guid]::NewGuid().ToString('N'))
$temporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
$systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
Assert-Condition ($temporaryRoot.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase)) 'Temporary root escaped the system temp directory.'
$worktree = Join-Path $temporaryRoot 'project'
$worktreeRegistered = $false

try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    & git -C $resolvedSourceRoot worktree add --detach $worktree $expectedCommit
    Assert-Condition ($LASTEXITCODE -eq 0) 'Could not create detached formal worktree.'
    $worktreeRegistered = $true

    $editorDirectory = Join-Path $worktree 'Assets\Editor'
    New-Item -ItemType Directory -Path $editorDirectory -Force | Out-Null
    $copiedObservationSource = Join-Path $editorDirectory 'GamePrimitivesR1Fixture.cs'
    $copiedObservationMeta = Join-Path $editorDirectory 'GamePrimitivesR1Fixture.cs.meta'
    Copy-Item -LiteralPath $observationSource -Destination $copiedObservationSource
    Copy-Item -LiteralPath $observationMeta -Destination $copiedObservationMeta
    Assert-Condition `
        ((Get-Sha256 $copiedObservationSource) -ceq [string]$executionTarget.test_body.sha256) `
        'Copied CA-R1 test body no longer matches the execution target.'
    Assert-Condition `
        ((Get-Sha256 $copiedObservationMeta) -ceq [string]$executionTarget.support_artifacts.test_body_metadata.sha256) `
        'Copied CA-R1 test-body metadata no longer matches the execution target.'

    if ($ConfigurationId -eq 'config.variant') {
        Assert-Condition `
            ((Get-Sha256 $variantPatch) -ceq [string]$executionTarget.support_artifacts.variant_patch.sha256) `
            'CA-R1 variant patch changed after execution-target verification.'
        & git -C $worktree apply --whitespace=nowarn $variantPatch
        Assert-Condition ($LASTEXITCODE -eq 0) 'Could not apply the frozen rule variant patch.'
    }

    $changed = @(& git -C $worktree status --porcelain=v1 --untracked-files=all)
    Assert-Condition ($LASTEXITCODE -eq 0) 'Could not inspect formal worktree changes.'
    $allowed = @(
        '?? Assets/Editor/GamePrimitivesR1Fixture.cs',
        '?? Assets/Editor/GamePrimitivesR1Fixture.cs.meta'
    )
    if ($ConfigurationId -eq 'config.variant') {
        $allowed += ' M Assets/Fighter/F00/F00.asset'
    }
    $changedText = ($changed | Sort-Object) -join "`n"
    $allowedText = ($allowed | Sort-Object) -join "`n"
    Assert-Condition ($changedText -eq $allowedText) 'Formal worktree change allowlist mismatch.'

    $outputDirectory = Split-Path -Parent $resolvedOutputPath
    $logDirectory = Split-Path -Parent $resolvedLogPath
    if ($outputDirectory) {
        New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
    }
    if ($logDirectory) {
        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    }

    $env:GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256 = $executionPermit.execution_permit_sha256
    $env:GAME_PRIMITIVES_PREDICTION_SET_DIGEST = $executionPermit.prediction_set_digest
    $env:GAME_PRIMITIVES_RUN_ID = $executionPermit.run_id
    $env:GAME_PRIMITIVES_CASE_ID = $executionPermit.case_id
    $env:GAME_PRIMITIVES_FORMAL_INPUT_SHA256 = $formalInputSha256
    $env:GP_R1_CONFIGURATION_ID = $ConfigurationId
    $env:GP_R1_INPUT_PATH = $resolvedInputPath
    $env:GP_R1_OUTPUT_PATH = $resolvedOutputPath

    & $resolvedUnityExe `
        -batchmode `
        -nographics `
        -quit `
        -projectPath $worktree `
        -executeMethod GamePrimitives.ContinuousActionR1.Run `
        -logFile $resolvedLogPath
    $unityExitCode = $LASTEXITCODE
    Assert-Condition ($unityExitCode -eq 0) "Unity formal fixture exited with code $unityExitCode."
    Assert-Condition (Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf) 'Formal fixture did not create its raw output.'
}
finally {
    Remove-Item Env:\GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256 -ErrorAction SilentlyContinue
    Remove-Item Env:\GAME_PRIMITIVES_PREDICTION_SET_DIGEST -ErrorAction SilentlyContinue
    Remove-Item Env:\GAME_PRIMITIVES_RUN_ID -ErrorAction SilentlyContinue
    Remove-Item Env:\GAME_PRIMITIVES_CASE_ID -ErrorAction SilentlyContinue
    Remove-Item Env:\GAME_PRIMITIVES_FORMAL_INPUT_SHA256 -ErrorAction SilentlyContinue
    Remove-Item Env:\GP_R1_CONFIGURATION_ID -ErrorAction SilentlyContinue
    Remove-Item Env:\GP_R1_INPUT_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\GP_R1_OUTPUT_PATH -ErrorAction SilentlyContinue

    if ($worktreeRegistered) {
        & git -C $resolvedSourceRoot worktree remove --force $worktree 2>$null
        & git -C $resolvedSourceRoot worktree prune 2>$null
    }
    if (Test-Path -LiteralPath $temporaryRoot) {
        $resolvedTemporaryRoot = (Get-Item -LiteralPath $temporaryRoot -Force).FullName
        Assert-Condition ($resolvedTemporaryRoot.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase)) 'Refusing to remove a temporary path outside the system temp directory.'
        Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force
    }
}
