[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BaselineTrace,

    [Parameter(Mandatory = $true)]
    [string]$VariantTrace,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [string]$ExecutionPermitPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
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

function Invoke-RawTraceVerifier {
    param(
        [string]$VerifierPath,
        [string]$RepositoryRoot,
        [string]$PermitPath,
        [string]$TracePath,
        [string]$ConfigurationId
    )

    Assert-Condition `
        (Test-Path -LiteralPath $VerifierPath -PathType Leaf) `
        "Raw-trace verifier is missing: $VerifierPath"
    $verificationOutput = @(
        & python -B $VerifierPath verify `
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
    -Reference $executionTarget.support_artifacts.test_body_metadata `
    -ExpectedRelativePath $testBodyMetadataRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.support_artifacts.variant_patch `
    -ExpectedRelativePath $variantPatchRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $executionTarget.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$baselineTraceFull = [System.IO.Path]::GetFullPath($BaselineTrace)
$variantTraceFull = [System.IO.Path]::GetFullPath($VariantTrace)
$baselineVerification = Invoke-RawTraceVerifier `
    -VerifierPath $rawTraceVerifier `
    -RepositoryRoot $repoRoot `
    -PermitPath $executionPermitFull `
    -TracePath $baselineTraceFull `
    -ConfigurationId 'config.baseline'
$variantVerification = Invoke-RawTraceVerifier `
    -VerifierPath $rawTraceVerifier `
    -RepositoryRoot $repoRoot `
    -PermitPath $executionPermitFull `
    -TracePath $variantTraceFull `
    -ConfigurationId 'config.variant'
Assert-Condition `
    ([string]$baselineVerification.formal_input.sha256 -ceq $formalInputSha256) `
    'Baseline verifier returned the wrong formal-input binding.'
Assert-Condition `
    ([string]$variantVerification.formal_input.sha256 -ceq $formalInputSha256) `
    'Variant verifier returned the wrong formal-input binding.'

$baseline = Load-Trace $baselineTraceFull
$variant = Load-Trace $variantTraceFull
Assert-Condition `
    ($baseline.sha256 -ceq [string]$baselineVerification.formal_trace_sha256) `
    'Baseline trace changed after strict verification.'
Assert-Condition `
    ($variant.sha256 -ceq [string]$variantVerification.formal_trace_sha256) `
    'Variant trace changed after strict verification.'
Assert-Condition ($baseline.value.configuration_id -eq 'config.baseline') 'Baseline trace has the wrong configuration_id.'
Assert-Condition ($variant.value.configuration_id -eq 'config.variant') 'Variant trace has the wrong configuration_id.'
Assert-Condition ($baseline.value.formal_input_sha256 -eq $variant.value.formal_input_sha256) 'Formal input hashes differ.'
Assert-Condition `
    ($baseline.value.formal_input_sha256 -ceq $formalInputSha256) `
    'Baseline trace formal-input SHA-256 mismatch.'
Assert-Condition `
    ($variant.value.formal_input_sha256 -ceq $formalInputSha256) `
    'Variant trace formal-input SHA-256 mismatch.'
Assert-Condition ($baseline.value.formal_input_id -eq $variant.value.formal_input_id) 'Formal input IDs differ.'
Assert-Condition ($baseline.value.formal_input_id -eq 'o.a.0002') 'Unexpected formal input ID.'
Assert-Condition ($baseline.value.stop_boundary_id -eq $variant.value.stop_boundary_id) 'Stop boundaries differ.'
Assert-Condition ($baseline.value.stop_boundary_id -eq 'o.a.0042') 'Unexpected stop boundary.'
Assert-Condition `
    ($baseline.value.execution_permit_sha256 -eq $executionPermit.execution_permit_sha256) `
    'Baseline trace execution-permit SHA-256 mismatch.'
Assert-Condition `
    ($variant.value.execution_permit_sha256 -eq $executionPermit.execution_permit_sha256) `
    'Variant trace execution-permit SHA-256 mismatch.'
Assert-Condition `
    ($baseline.value.prediction_set_digest -eq $executionPermit.prediction_set_digest) `
    'Baseline trace prediction-set digest mismatch.'
Assert-Condition `
    ($variant.value.prediction_set_digest -eq $executionPermit.prediction_set_digest) `
    'Variant trace prediction-set digest mismatch.'

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
                    artifact_id = 'config.baseline.raw-trace'
                    sha256 = $baseline.sha256
                }
            )
        },
        [ordered]@{
            configuration_id = 'config.variant'
            artifacts = @(
                [ordered]@{
                    artifact_id = 'config.variant.raw-trace'
                    sha256 = $variant.sha256
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

$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
Assert-Condition (-not (Test-Path -LiteralPath $resolvedOutputPath)) 'Comparator output already exists.'
$outputDirectory = Split-Path -Parent $resolvedOutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
$jsonLine = $result | ConvertTo-Json -Depth 12 -Compress
[System.IO.File]::WriteAllText($resolvedOutputPath, $jsonLine + "`n", [System.Text.UTF8Encoding]::new($false))
