[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FormalOutputRoot,

    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$DotnetPath,

    [Parameter(Mandatory = $true)]
    [string]$ExecutionPermitPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$runId = 'continuous-001'
$caseId = 'CA-R1'
$expectedPythonPath = 'C:\Python314\python.exe'
$expectedPythonSha256 = 'cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b'
$expectedPythonBytes = 106328
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

function Resolve-FixedPythonRuntime {
    param([Parameter(Mandatory = $true)][string]$RequestedPath)

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
        [string]$ExpectedCaseId,
        [string]$PythonExecutablePath
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

function Invoke-RawTraceVerifier {
    param(
        [string]$VerifierPath,
        [string]$RepositoryRoot,
        [string]$PermitPath,
        [string]$TracePath,
        [string]$ConfigurationId,
        [string]$PythonExecutablePath
    )

    Assert-Condition `
        (Test-Path -LiteralPath $VerifierPath -PathType Leaf) `
        "Raw-trace verifier is missing: $VerifierPath"
    $verificationOutput = @(
        & $PythonExecutablePath -B $VerifierPath verify `
            --repo-root $RepositoryRoot `
            --permit-path $PermitPath `
            --case-id 'CA-R1' `
            --trace-path $TracePath `
            --configuration-id $ConfigurationId 2>&1
    )
    $verificationExitCode = $LASTEXITCODE
    Assert-Condition `
        ($verificationExitCode -eq 0) `
        ("Raw-trace verification failed for ${ConfigurationId}: " +
            ($verificationOutput -join "`n"))
    Assert-Condition `
        ($verificationOutput.Count -eq 1) `
        "Raw-trace verifier returned an unexpected number of lines for $ConfigurationId."
    try {
        $verification = $verificationOutput[0].ToString() | ConvertFrom-Json
    }
    catch {
        throw "Raw-trace verifier returned invalid JSON for ${ConfigurationId}: $($_.Exception.Message)"
    }
    Assert-Condition `
        ($verification.status -ceq 'formal_raw_trace_verified') `
        "Raw-trace verifier did not verify $ConfigurationId."
    Assert-Condition ($verification.run_id -ceq 'continuous-001') 'Raw-trace run_id mismatch.'
    Assert-Condition ($verification.case_id -ceq 'CA-R1') 'Raw-trace case_id mismatch.'
    Assert-Condition `
        ($verification.configuration_id -ceq $ConfigurationId) `
        "Raw-trace configuration_id mismatch for $ConfigurationId."
    Assert-Condition `
        ([string]$verification.formal_trace_sha256 -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        "Raw-trace file SHA-256 is invalid for $ConfigurationId."
    Assert-Condition `
        ([string]$verification.normalized_trace_sha256 -cmatch '^(?!0{64}$)[0-9a-f]{64}$') `
        "Normalized trace SHA-256 is invalid for $ConfigurationId."
    Assert-Condition `
        ([string]$verification.normalized_trace_summary.record_kind -ceq 'compact_canonical_json') `
        "Raw-trace verifier returned the wrong record kind for $ConfigurationId."
    Assert-Condition `
        ($verification.normalized_trace_summary.trace_entry_count -eq 7) `
        "Raw-trace verifier returned the wrong entry count for $ConfigurationId."
    return $verification
}

function Load-Trace {
    param([string]$LiteralPath)
    $resolved = (Get-Item -LiteralPath $LiteralPath -Force).FullName
    $rawBytes = [System.IO.File]::ReadAllBytes($resolved)
    $trace = [System.Text.Encoding]::UTF8.GetString($rawBytes) | ConvertFrom-Json
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $rawSha256 = (
            [System.BitConverter]::ToString($algorithm.ComputeHash($rawBytes))
        ).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
    Assert-Condition ($trace.artifact_type -eq 'ca_r1_raw_trace') "Unexpected trace artifact_type: $resolved"
    Assert-Condition ($trace.case_id -eq 'CA-R1') "Unexpected trace case_id: $resolved"
    Assert-Condition ($trace.run_id -eq 'continuous-001') "Unexpected trace run_id: $resolved"
    Assert-Condition ($trace.trace_entries.Count -eq 7) "Expected seven trace entries: $resolved"
    return [pscustomobject]@{
        path = $resolved
        sha256 = $rawSha256
        value = $trace
    }
}

function Get-InputSignature {
    param($Trace)
    $parts = foreach ($entry in $Trace.trace_entries) {
        '{0}:{1}:{2}:{3}' -f $entry.sequence_index, $entry.event_id, $entry.attack_held, $entry.input_value
    }
    return $parts -join '|'
}

function Get-ZeroInvariant {
    param(
        $Trace,
        [string]$Field
    )
    foreach ($entry in $Trace.trace_entries) {
        if ([int]$entry.$Field -ne 0) {
            return $false
        }
    }
    return $true
}

function Get-TraceTotal {
    param(
        $Trace,
        [string]$Field
    )
    $total = 0
    foreach ($entry in $Trace.trace_entries) {
        $total += [int]$entry.$Field
    }
    return $total
}

function New-ActualValue {
    param(
        [string]$ValueType,
        [string]$SerializedValue,
        [AllowNull()]
        $Unit
    )
    return [ordered]@{
        serialized_value = $SerializedValue
        unit = $Unit
        value_type = $ValueType
    }
}

function New-ObservationRecords {
    param($TraceArtifact)

    $trace = $TraceArtifact.value
    $configurationId = [string]$trace.configuration_id
    $updateThreeEligible = [int]$trace.trace_entries[3].cancel_eligible_before -ne 0
    return @(
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.a.0001'
            actual_value = New-ActualValue `
                -ValueType 'id' `
                -SerializedValue ([int]$trace.trace_entries[2].after_buffer_action_id).ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit $null
            tolerance_rule_id = 'tol.a.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.a.0002'
            actual_value = New-ActualValue `
                -ValueType 'boolean' `
                -SerializedValue $updateThreeEligible.ToString().ToLowerInvariant() `
                -Unit $null
            tolerance_rule_id = 'tol.a.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.a.0003'
            actual_value = New-ActualValue `
                -ValueType 'id' `
                -SerializedValue ([int]$trace.trace_entries[6].after_action_id).ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit $null
            tolerance_rule_id = 'tol.a.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.a.0004'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (Get-TraceTotal $trace 'contact_count').ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit 'count'
            tolerance_rule_id = 'tol.a.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.a.0005'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (Get-TraceTotal $trace 'hit_count').ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit 'count'
            tolerance_rule_id = 'tol.a.0001'
        }
    )
}

# The repository verifier is intentionally the first operation that can open a
# formal-run artifact. It must succeed before either raw trace or the comparator
# output path is inspected.
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
$boundComparator = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.comparator `
    -ExpectedRelativePath $comparatorRelativePath
Assert-Condition `
    ([string]::Equals(
        [System.IO.Path]::GetFullPath($boundComparator),
        [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path),
        [System.StringComparison]::OrdinalIgnoreCase
    )) `
    'Execution target does not bind the running CA-R1 comparator.'
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.formal_runner `
    -ExpectedRelativePath $runnerRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.formal_input `
    -ExpectedRelativePath $formalInputRelativePath
$formalInputSha256 = [string]$executionTarget.formal_input.sha256
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.test_body `
    -ExpectedRelativePath $testBodyRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.formal_project `
    -ExpectedRelativePath $formalProjectRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.nuget_config `
    -ExpectedRelativePath $nugetConfigRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.unity_compatibility `
    -ExpectedRelativePath $unityCompatibilityRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.source_contract `
    -ExpectedRelativePath $sourceContractRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.asset_loader `
    -ExpectedRelativePath $assetLoaderRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.variant_patch `
    -ExpectedRelativePath $variantPatchRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_runner `
    -ExpectedRelativePath $buildRunnerRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_evidence `
    -ExpectedRelativePath $buildEvidenceRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.build_readiness_verifier `
    -ExpectedRelativePath $buildReadinessVerifierRelativePath
$boundOutputBoundary = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.output_boundary `
    -ExpectedRelativePath $outputBoundaryRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.process_boundary `
    -ExpectedRelativePath $processBoundaryRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$resolvedSourceRoot = (Resolve-Path -LiteralPath $SourceRoot -ErrorAction Stop).ProviderPath
$resolvedDotnetPath = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$null = . $boundOutputBoundary
$outputLayout = Resolve-R1FormalOutputLayout `
    -Mode comparator `
    -FormalOutputRoot $FormalOutputRoot `
    -RepositoryRoot $repoRoot `
    -SourceRoot $resolvedSourceRoot `
    -DotnetPath $resolvedDotnetPath
$resolvedOutputPath = [string]$outputLayout.comparator_output_path
$traceSpecifications = @(
    [pscustomobject]@{
        label = 'baseline rep-01'
        configuration_id = 'config.baseline'
        repetition_index = 1
        path = [string]$outputLayout.baseline_rep01_path
    }
    [pscustomobject]@{
        label = 'baseline rep-02'
        configuration_id = 'config.baseline'
        repetition_index = 2
        path = [string]$outputLayout.baseline_rep02_path
    }
    [pscustomobject]@{
        label = 'variant rep-01'
        configuration_id = 'config.variant'
        repetition_index = 1
        path = [string]$outputLayout.variant_rep01_path
    }
    [pscustomobject]@{
        label = 'variant rep-02'
        configuration_id = 'config.variant'
        repetition_index = 2
        path = [string]$outputLayout.variant_rep02_path
    }
)
$verifiedTraces = @(
    foreach ($specification in $traceSpecifications) {
        $verification = Invoke-RawTraceVerifier `
            -VerifierPath $rawTraceVerifier `
            -RepositoryRoot $repoRoot `
            -PermitPath $executionPermitFull `
            -TracePath $specification.path `
            -ConfigurationId $specification.configuration_id `
            -PythonExecutablePath $resolvedPythonPath
        Assert-Condition `
            ([string]$verification.formal_input.sha256 -ceq $formalInputSha256) `
            "$($specification.label) verifier returned the wrong formal-input binding."
        $trace = Load-Trace $specification.path
        Assert-Condition `
            ($trace.sha256 -ceq [string]$verification.formal_trace_sha256) `
            "$($specification.label) trace changed after strict verification."
        Assert-Condition `
            ($trace.value.configuration_id -ceq $specification.configuration_id) `
            "$($specification.label) trace has the wrong configuration_id."
        Assert-Condition `
            ($trace.value.formal_input_sha256 -ceq $formalInputSha256) `
            "$($specification.label) trace formal-input SHA-256 mismatch."
        Assert-Condition `
            ($trace.value.formal_input_id -ceq 'o.a.0002') `
            "$($specification.label) trace has an unexpected formal input ID."
        Assert-Condition `
            ($trace.value.stop_boundary_id -ceq 'o.a.0042') `
            "$($specification.label) trace has an unexpected stop boundary."
        Assert-Condition `
            ($trace.value.execution_permit_sha256 -ceq $executionPermit.execution_permit_sha256) `
            "$($specification.label) execution-permit SHA-256 mismatch."
        Assert-Condition `
            ($trace.value.prediction_set_digest -ceq $executionPermit.prediction_set_digest) `
            "$($specification.label) prediction-set digest mismatch."
        [pscustomobject]@{
            configuration_id = $specification.configuration_id
            repetition_index = $specification.repetition_index
            trace = $trace
        }
    }
)
$baselineRep01 = @(
    $verifiedTraces |
        Where-Object {
            $_.configuration_id -ceq 'config.baseline' -and
            $_.repetition_index -eq 1
        }
)[0].trace
$baselineRep02 = @(
    $verifiedTraces |
        Where-Object {
            $_.configuration_id -ceq 'config.baseline' -and
            $_.repetition_index -eq 2
        }
)[0].trace
$variantRep01 = @(
    $verifiedTraces |
        Where-Object {
            $_.configuration_id -ceq 'config.variant' -and
            $_.repetition_index -eq 1
        }
)[0].trace
$variantRep02 = @(
    $verifiedTraces |
        Where-Object {
            $_.configuration_id -ceq 'config.variant' -and
            $_.repetition_index -eq 2
        }
)[0].trace
Assert-Condition `
    ($baselineRep01.sha256 -ceq $baselineRep02.sha256) `
    'Baseline repetitions are not byte-identical.'
Assert-Condition `
    ($variantRep01.sha256 -ceq $variantRep02.sha256) `
    'Variant repetitions are not byte-identical.'
$baseline = $baselineRep01
$variant = $variantRep01

$sameInputTrace = (Get-InputSignature $baseline.value) -eq (Get-InputSignature $variant.value)
$sameBufferedRequest = [int]$baseline.value.trace_entries[2].after_buffer_action_id -eq [int]$variant.value.trace_entries[2].after_buffer_action_id
$zeroContacts = (Get-ZeroInvariant $baseline.value 'contact_count') -and (Get-ZeroInvariant $variant.value 'contact_count')
$zeroHits = (Get-ZeroInvariant $baseline.value 'hit_count') -and (Get-ZeroInvariant $variant.value 'hit_count')
$singleControlledDifference = [int]$baseline.value.controlled_value -ne [int]$variant.value.controlled_value

Assert-Condition $sameInputTrace 'Input traces differ.'
Assert-Condition $sameBufferedRequest 'The common buffered-request invariant differs.'
Assert-Condition $zeroContacts 'A contact was observed.'
Assert-Condition $zeroHits 'A hit was observed.'
Assert-Condition $singleControlledDifference 'Controlled values are not distinct.'

$observationRecords = @(
    New-ObservationRecords -TraceArtifact $baseline
    New-ObservationRecords -TraceArtifact $variant
)

$result = [ordered]@{
    artifact_type = 'formal_comparator_output'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R1'
    stop_boundary_id = 'o.a.0042'
    execution_permit_sha256 = $executionPermit.execution_permit_sha256
    formal_input_sha256 = $formalInputSha256
    prediction_set_digest = $executionPermit.prediction_set_digest
    comparator_status = 'passed'
    configuration_artifacts = @(
        [ordered]@{
            configuration_id = 'config.baseline'
            artifacts = @(
                [ordered]@{
                    artifact_id = 'config.baseline.repetition-0001.raw-trace'
                    sha256 = $baselineRep01.sha256
                }
                [ordered]@{
                    artifact_id = 'config.baseline.repetition-0002.raw-trace'
                    sha256 = $baselineRep02.sha256
                }
            )
        },
        [ordered]@{
            configuration_id = 'config.variant'
            artifacts = @(
                [ordered]@{
                    artifact_id = 'config.variant.repetition-0001.raw-trace'
                    sha256 = $variantRep01.sha256
                }
                [ordered]@{
                    artifact_id = 'config.variant.repetition-0002.raw-trace'
                    sha256 = $variantRep02.sha256
                }
            )
        }
    )
    observations = $observationRecords
    invariants = @(
        1..6 | ForEach-Object {
            [ordered]@{
                invariant_id = 'inv.a.{0:0000}' -f $_
                status = 'held'
            }
        }
    )
    negative_controls = @()
}

$outputDirectory = Split-Path -Parent $resolvedOutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
$jsonLine = $result | ConvertTo-Json -Depth 12 -Compress
[System.IO.File]::WriteAllText($resolvedOutputPath, $jsonLine + "`n", [System.Text.UTF8Encoding]::new($false))
