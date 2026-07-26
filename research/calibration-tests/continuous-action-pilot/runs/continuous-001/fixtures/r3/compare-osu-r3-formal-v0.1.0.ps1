[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $TraceDirectory,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $OutputPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $ExecutionPermitPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)] $Actual,
        [Parameter(Mandatory = $true)] $Expected,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if ($Actual -ne $Expected) {
        throw "$Label mismatch. Expected '$Expected', got '$Actual'."
    }
}

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool] $Value,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not $Value) {
        throw "$Label must be true."
    }
}

function Assert-ExactString {
    param(
        [AllowNull()] $Actual,
        [Parameter(Mandatory = $true)][string] $Expected,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if ([string]$Actual -cne $Expected) {
        throw "$Label mismatch. Expected '$Expected', got '$Actual'."
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
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash.ToLowerInvariant()
    if ($actual -cne [string]$Reference.sha256) {
        throw "Execution target artifact hash mismatch for $ExpectedRelativePath."
    }
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

    if (-not [System.IO.Path]::IsPathRooted($PermitPath)) {
        throw 'ExecutionPermitPath must be absolute.'
    }
    $permitFull = [System.IO.Path]::GetFullPath($PermitPath)
    $repoRoot = Find-RepositoryRoot
    $verifier = Join-Path `
        $repoRoot `
        'research/calibration-tests/continuous-action-pilot/tools/verify-formal-execution-permit.py'
    $output = @(
        & python -B $verifier verify `
            --repo-root $repoRoot `
            --permit-path $permitFull `
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

function New-ActualValue {
    param(
        [Parameter(Mandatory = $true)][string] $ValueType,
        [Parameter(Mandatory = $true)][string] $SerializedValue,
        [AllowNull()] $Unit
    )

    return [ordered]@{
        serialized_value = $SerializedValue
        unit = $Unit
        value_type = $ValueType
    }
}

function ConvertTo-InvariantInteger {
    param([Parameter(Mandatory = $true)][long] $Value)
    return $Value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
}

function ConvertTo-InvariantDecimal {
    param([Parameter(Mandatory = $true)][double] $Value)
    if ([double]::IsNaN($Value) -or [double]::IsInfinity($Value)) {
        throw 'Formal observation contains a non-finite decimal.'
    }
    return $Value.ToString('R', [System.Globalization.CultureInfo]::InvariantCulture)
}

function New-ObservationRecords {
    param([Parameter(Mandatory = $true)] $Trace)

    $observation = $Trace.value.observation
    $configurationId = [string]$Trace.configuration_id
    $acceptedCount = if ([bool]$observation.candidate_accepted) { 1 } else { 0 }
    $adjudicationOffset = [double]$observation.adjudication_time_ms -
        [double]$observation.candidate_time_ms
    Assert-Equal `
        $adjudicationOffset `
        ([math]::Truncate($adjudicationOffset)) `
        "$configurationId adjudication offset integer serialization"

    return @(
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0001'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (ConvertTo-InvariantInteger $acceptedCount) `
                -Unit 'count'
            tolerance_rule_id = 'tol.c.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0002'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (ConvertTo-InvariantInteger ([long]$adjudicationOffset)) `
                -Unit 'millisecond'
            tolerance_rule_id = 'tol.c.0002'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0003'
            actual_value = New-ActualValue `
                -ValueType 'id' `
                -SerializedValue ([string]$observation.result) `
                -Unit $null
            tolerance_rule_id = 'tol.c.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0004'
            actual_value = New-ActualValue `
                -ValueType 'decimal' `
                -SerializedValue (ConvertTo-InvariantDecimal ([double]$observation.raw_time_ms)) `
                -Unit 'millisecond'
            tolerance_rule_id = 'tol.c.0002'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0005'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (ConvertTo-InvariantInteger ([long]$observation.notification_count)) `
                -Unit 'count'
            tolerance_rule_id = 'tol.c.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0006'
            actual_value = New-ActualValue `
                -ValueType 'decimal' `
                -SerializedValue (ConvertTo-InvariantDecimal ([double]$observation.reentry_closed_time_ms)) `
                -Unit 'millisecond'
            tolerance_rule_id = 'tol.c.0002'
        }
    )
}

function Get-Trace {
    param(
        [Parameter(Mandatory = $true)][string] $Directory,
        [Parameter(Mandatory = $true)][string] $ConfigurationId
    )

    $path = Join-Path $Directory "$ConfigurationId.trace.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing trace for $ConfigurationId`: $path"
    }
    return [pscustomobject]@{
        configuration_id = $ConfigurationId
        path = $path
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        value = Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
    }
}

function Get-MechanismProjection {
    param([Parameter(Mandatory = $true)] $Trace)

    $observation = $Trace.value.observation
    return [ordered]@{
        candidate_accepted = $observation.candidate_accepted
        candidate_time_ms = $observation.candidate_time_ms
        adjudication_time_ms = $observation.adjudication_time_ms
        raw_time_ms = $observation.raw_time_ms
        result = $observation.result
        judged = $observation.judged
        notification_count = $observation.notification_count
        notification_time_ms = $observation.notification_time_ms
        score_notification_count = $observation.score_notification_count
        score_notification_time_ms = $observation.score_notification_time_ms
        score_judged_hits = $observation.score_judged_hits
        score_combo = $observation.score_combo
        score_total = $observation.score_total
        reentry_allowed_after_candidate = $observation.reentry_allowed_after_candidate
        reentry_allowed_at_notification = $observation.reentry_allowed_at_notification
        reentry_closed_time_ms = $observation.reentry_closed_time_ms
        production_can_be_hit_after_result = $observation.production_can_be_hit_after_result
        time_offset_ms = $observation.time_offset_ms
    }
}

function Assert-TraceContract {
    param(
        [Parameter(Mandatory = $true)] $Trace,
        [Parameter(Mandatory = $true)][int] $Delay,
        [Parameter(Mandatory = $true)][bool] $HitAnimations,
        [Parameter(Mandatory = $true)][string] $ExecutionPermitSha256,
        [Parameter(Mandatory = $true)][string] $FormalInputSha256,
        [Parameter(Mandatory = $true)][string] $PredictionSetDigest
    )

    $value = $Trace.value
    $observation = $value.observation
    $expectedCommitTime = 1000 + $Delay

    Assert-Equal $value.artifact_type 'continuous_action_r3_trace' "$($Trace.configuration_id) artifact type"
    Assert-Equal $value.artifact_version '0.1.0' "$($Trace.configuration_id) artifact version"
    Assert-ExactString $value.run_id 'continuous-001' "$($Trace.configuration_id) run id"
    Assert-ExactString $value.case_id 'CA-R3' "$($Trace.configuration_id) case id"
    Assert-ExactString $value.configuration_id $Trace.configuration_id "$($Trace.configuration_id) embedded configuration"
    Assert-ExactString $value.execution_permit_sha256 $ExecutionPermitSha256 "$($Trace.configuration_id) execution permit"
    Assert-ExactString $value.formal_input_sha256 $FormalInputSha256 "$($Trace.configuration_id) formal input"
    Assert-ExactString $value.prediction_set_digest $PredictionSetDigest "$($Trace.configuration_id) prediction set"
    Assert-Equal $value.input.adjudication_delay_ms $Delay "$($Trace.configuration_id) delay"
    Assert-Equal $value.input.hit_animations $HitAnimations "$($Trace.configuration_id) HitAnimations"
    Assert-Equal $value.input.candidate_count 1 "$($Trace.configuration_id) candidate count"
    Assert-Equal $value.input.candidate_time_ms 1000 "$($Trace.configuration_id) input candidate time"
    Assert-Equal $value.input.object_start_time_ms 1000 "$($Trace.configuration_id) object start time"
    Assert-Equal $value.input.overall_difficulty 5 "$($Trace.configuration_id) overall difficulty"

    Assert-True ([bool]$observation.candidate_accepted) "$($Trace.configuration_id) candidate acceptance"
    Assert-Equal $observation.candidate_time_ms 1000 "$($Trace.configuration_id) observed candidate time"
    Assert-Equal $observation.adjudication_time_ms $expectedCommitTime "$($Trace.configuration_id) adjudication time"
    Assert-Equal $observation.raw_time_ms $expectedCommitTime "$($Trace.configuration_id) RawTime"
    Assert-Equal $observation.notification_time_ms $expectedCommitTime "$($Trace.configuration_id) notification time"
    Assert-Equal $observation.score_notification_time_ms $expectedCommitTime "$($Trace.configuration_id) scoring notification time"
    Assert-Equal $observation.reentry_closed_time_ms $expectedCommitTime "$($Trace.configuration_id) re-entry closure time"
    Assert-Equal $observation.time_offset_ms $Delay "$($Trace.configuration_id) public time offset"
    Assert-True ([bool]$observation.judged) "$($Trace.configuration_id) Judged"
    Assert-Equal $observation.notification_count 1 "$($Trace.configuration_id) notification count"
    Assert-Equal $observation.score_notification_count 1 "$($Trace.configuration_id) scoring notification count"
    Assert-Equal $observation.score_judged_hits 1 "$($Trace.configuration_id) scored judgement count"
    Assert-Equal $observation.production_can_be_hit_after_result $false "$($Trace.configuration_id) post-result CanBeHit"
    Assert-Equal $observation.reentry_allowed_at_notification $false "$($Trace.configuration_id) notification re-entry permission"

    $eventNames = @($observation.event_trace | ForEach-Object { $_.event })
    $expectedEvents = @('candidate', 'adjudication', 'result_notification', 'scoring_notification', 'reentry_closed')
    if (@(Compare-Object -ReferenceObject $expectedEvents -DifferenceObject $eventNames -SyncWindow 0).Count -ne 0) {
        throw "$($Trace.configuration_id) event order mismatch: $($eventNames -join ', ')"
    }
    if ([string]::IsNullOrWhiteSpace([string]$observation.production_delegate_method) -or
        [string]::IsNullOrWhiteSpace([string]$observation.production_delegate_target_type)) {
        throw "$($Trace.configuration_id) did not identify the captured production delegate."
    }
}

# The permit is reverified before any formal trace or output path is opened.
$permit = Invoke-ExecutionPermitVerifier -PermitPath $ExecutionPermitPath
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$target = $permit.execution_target
$repoRoot = Find-RepositoryRoot
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)

$comparatorPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.comparator `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1'
if (-not [string]::Equals(
        [System.IO.Path]::GetFullPath($comparatorPath),
        [System.IO.Path]::GetFullPath($PSCommandPath),
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Execution target does not bind the running CA-R3 comparator.'
}
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_input `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/formal-input-r3-v0.1.0.json'
$formalInputSha256 = [string]$target.formal_input.sha256
$fixtureSpec = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.fixture_spec `
    -ExpectedRelativePath 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-fixture-spec-v0.1.0.json'
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

$traceFull = (Resolve-Path -LiteralPath $TraceDirectory -ErrorAction Stop).ProviderPath
$outputFull = [System.IO.Path]::GetFullPath(
    $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath))
if (Test-Path -LiteralPath $outputFull) {
    throw "Refusing to overwrite comparator output: $outputFull"
}

$traceVerificationByConfiguration = @{}
foreach ($configurationId in @(
        'config.baseline',
        'config.variant',
        'negative_control_a',
        'negative_control_b')) {
    $tracePath = Join-Path $traceFull "$configurationId.trace.json"
    $verification = Invoke-RawTraceVerifier `
        -RepositoryRoot $repoRoot `
        -VerifierPath $rawTraceVerifier `
        -PermitPath $executionPermitFull `
        -TracePath $tracePath `
        -ConfigurationId $configurationId
    if ([string]$verification.formal_input.sha256 -cne $formalInputSha256) {
        throw "$configurationId trace verifier returned the wrong formal-input binding."
    }
    $traceVerificationByConfiguration[$configurationId] = $verification
}

$baseline = Get-Trace -Directory $traceFull -ConfigurationId 'config.baseline'
$variant = Get-Trace -Directory $traceFull -ConfigurationId 'config.variant'
$negativeA = Get-Trace -Directory $traceFull -ConfigurationId 'negative_control_a'
$negativeB = Get-Trace -Directory $traceFull -ConfigurationId 'negative_control_b'
foreach ($trace in @($baseline, $variant, $negativeA, $negativeB)) {
    if ($trace.sha256 -cne
        [string]$traceVerificationByConfiguration[$trace.configuration_id].formal_trace_sha256) {
        throw "$($trace.configuration_id) trace changed after strict validation."
    }
}

Assert-TraceContract `
    -Trace $baseline `
    -Delay 0 `
    -HitAnimations $true `
    -ExecutionPermitSha256 $executionPermitSha256 `
    -FormalInputSha256 $formalInputSha256 `
    -PredictionSetDigest $predictionSetDigest
Assert-TraceContract `
    -Trace $variant `
    -Delay 75 `
    -HitAnimations $true `
    -ExecutionPermitSha256 $executionPermitSha256 `
    -FormalInputSha256 $formalInputSha256 `
    -PredictionSetDigest $predictionSetDigest
Assert-TraceContract `
    -Trace $negativeA `
    -Delay 0 `
    -HitAnimations $true `
    -ExecutionPermitSha256 $executionPermitSha256 `
    -FormalInputSha256 $formalInputSha256 `
    -PredictionSetDigest $predictionSetDigest
Assert-TraceContract `
    -Trace $negativeB `
    -Delay 0 `
    -HitAnimations $false `
    -ExecutionPermitSha256 $executionPermitSha256 `
    -FormalInputSha256 $formalInputSha256 `
    -PredictionSetDigest $predictionSetDigest

$baselineProjection = Get-MechanismProjection -Trace $baseline | ConvertTo-Json -Compress -Depth 8
$negativeAProjection = Get-MechanismProjection -Trace $negativeA | ConvertTo-Json -Compress -Depth 8
$negativeBProjection = Get-MechanismProjection -Trace $negativeB | ConvertTo-Json -Compress -Depth 8
Assert-Equal $negativeAProjection $baselineProjection 'repeatability projection'
Assert-Equal $negativeBProjection $negativeAProjection 'NEG-01 mechanism projection'

foreach ($field in @('production_delegate_method', 'production_delegate_target_type')) {
    Assert-Equal $variant.value.observation.$field $baseline.value.observation.$field "primary invariant $field"
}
Assert-Equal `
    ($variant.value.window_snapshot_ms | ConvertTo-Json -Compress) `
    ($baseline.value.window_snapshot_ms | ConvertTo-Json -Compress) `
    'primary hit-window snapshot'

$observationRecords = @(
    New-ObservationRecords -Trace $baseline
    New-ObservationRecords -Trace $variant
)

$result = [ordered]@{
    artifact_type = 'formal_comparator_output'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R3'
    execution_permit_sha256 = $executionPermitSha256
    formal_input_sha256 = $formalInputSha256
    prediction_set_digest = $predictionSetDigest
    stop_boundary_id = 'o.c.0032'
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
        1..7 | ForEach-Object {
            [ordered]@{
                invariant_id = 'inv.c.{0:0000}' -f $_
                status = 'held'
            }
        }
    )
    negative_controls = @(
        [ordered]@{
            control_id = 'NEG-01'
            status = 'held'
            configuration_artifacts = @(
                [ordered]@{
                    configuration_id = 'negative_control_a'
                    artifacts = @(
                        [ordered]@{
                            artifact_id = 'negative_control_a.raw-trace'
                            sha256 = $negativeA.sha256
                        }
                    )
                },
                [ordered]@{
                    configuration_id = 'negative_control_b'
                    artifacts = @(
                        [ordered]@{
                            artifact_id = 'negative_control_b.raw-trace'
                            sha256 = $negativeB.sha256
                        }
                    )
                }
            )
        }
    )
}

$outputParent = Split-Path -Parent $outputFull
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    throw "Comparator output directory does not exist: $outputParent"
}
[System.IO.File]::WriteAllText(
    $outputFull,
    ($result | ConvertTo-Json -Depth 12) + "`n",
    $utf8NoBom)

$result | ConvertTo-Json -Depth 12
