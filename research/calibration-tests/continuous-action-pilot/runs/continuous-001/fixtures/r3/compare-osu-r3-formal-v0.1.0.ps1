[CmdletBinding()]
param(
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
$caseId = 'CA-R3'
$expectedPythonPath = 'C:\Python314\python.exe'
$expectedPythonSha256 = 'cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b'
$expectedPythonBytes = 106328
$expectedSafetyGuardsSha256 =
    '53b714b3224057e6dc2f5b01d8c13529ea8a0b1b75cc0c25eb0d1083c76aa6be'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptRoot '..\..\..\..\..\..\..')
).TrimEnd('\')

$comparatorRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1'
$formalInputRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/formal-input-r3-v0.1.0.json'
$fixtureSpecRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-fixture-spec-v0.1.0.json'
$rawTraceSchemaRelativePath =
    'research/calibration-tests/continuous-action-pilot/schema/ca-r3-raw-trace-0.1.0.schema.json'

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).
        Hash.ToLowerInvariant()
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

function Resolve-FixedPythonRuntime {
    param([Parameter(Mandatory = $true)][string] $RequestedPath)

    if (-not [System.IO.Path]::IsPathRooted($RequestedPath)) {
        throw 'PythonPath must be absolute.'
    }
    $resolved = [System.IO.Path]::GetFullPath($RequestedPath)
    if (-not [string]::Equals(
            $resolved,
            $expectedPythonPath,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'PythonPath must resolve to the frozen Python 3.14.3 runtime.'
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw 'The frozen Python runtime is missing.'
    }
    if ((Get-Item -LiteralPath $resolved).Length -ne $expectedPythonBytes) {
        throw 'The frozen Python runtime byte count differs.'
    }
    Assert-Hash -Path $resolved -Expected $expectedPythonSha256
    return (Resolve-Path -LiteralPath $resolved -ErrorAction Stop).ProviderPath
}

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

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool] $Value,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not $Value) {
        throw "$Label must be true."
    }
}

function Resolve-BoundArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][object] $Reference,
        [Parameter(Mandatory = $true)][string] $ExpectedRelativePath
    )

    if ([string]$Reference.path -cne $ExpectedRelativePath -or
        [string]$Reference.sha256 -cnotmatch '^(?!0{64}$)[0-9a-f]{64}$') {
        throw (
            'Execution target selected an invalid artifact reference for ' +
            "$ExpectedRelativePath."
        )
    }
    $fullPath = Join-Path `
        $RepositoryRoot `
        $ExpectedRelativePath.Replace('/', '\')
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "Execution target artifact is missing: $fullPath"
    }
    Assert-Hash -Path $fullPath -Expected ([string]$Reference.sha256)
    return (Resolve-Path -LiteralPath $fullPath -ErrorAction Stop).ProviderPath
}

function Add-ProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]] $List,
        [Parameter(Mandatory = $true)] $Record
    )

    $List.Add([ordered]@{
        step = $Record.step
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

function Invoke-ExecutionPermitVerifier {
    param(
        [Parameter(Mandatory = $true)][string] $PermitPath,
        [Parameter(Mandatory = $true)][string] $PythonExecutablePath
    )

    if (-not [System.IO.Path]::IsPathRooted($PermitPath)) {
        throw 'ExecutionPermitPath must be absolute.'
    }
    $verifier = Join-Path `
        $repoRoot `
        'research\calibration-tests\continuous-action-pilot\tools\verify-formal-execution-permit.py'
    $run = Invoke-R3BootstrapProcess `
        -Step 'verify-formal-execution-permit' `
        -FilePath $PythonExecutablePath `
        -Arguments @(
            '-B',
            $verifier,
            'verify',
            '--repo-root',
            $repoRoot,
            '--permit-path',
            ([System.IO.Path]::GetFullPath($PermitPath)),
            '--case-id',
            $caseId
        ) `
        -WorkingDirectory $repoRoot `
        -TimeoutMilliseconds 60000
    if ($run.exit_code -ne 0) {
        throw (
            'Execution-permit verification failed: ' +
            ($run.stderr + $run.stdout).Trim()
        )
    }
    $lines = @(
        $run.stdout -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($lines.Count -ne 1) {
        throw 'Execution-permit verifier returned an unexpected number of lines.'
    }
    try {
        $value = $lines[0] | ConvertFrom-Json
    }
    catch {
        throw 'Execution-permit verifier did not return valid JSON.'
    }
    if ($value.status -cne 'formal_execution_permit_verified' -or
        $value.run_id -cne $runId -or
        $value.case_id -cne $caseId -or
        [string]$value.execution_permit_sha256 -cnotmatch
            '^(?!0{64}$)[0-9a-f]{64}$' -or
        [string]$value.prediction_set_digest -cnotmatch
            '^(?!0{64}$)[0-9a-f]{64}$') {
        throw 'Execution-permit verifier returned an invalid CA-R3 result.'
    }
    if (
        [string]$value.python_runtime.runtime.executable_path -cne
            'C:/Python314/python.exe' -or
        [long]$value.python_runtime.runtime.bytes -ne $expectedPythonBytes -or
        [string]$value.python_runtime.runtime.sha256 -cne
            $expectedPythonSha256
    ) {
        throw 'Execution permit selected the wrong Python runtime.'
    }
    return $value
}

function Invoke-RawTraceVerifier {
    param(
        [Parameter(Mandatory = $true)][string] $PermitPath,
        [Parameter(Mandatory = $true)][string] $TracePath,
        [Parameter(Mandatory = $true)][string] $ConfigurationId,
        [Parameter(Mandatory = $true)][string] $PythonExecutablePath,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]] $ProcessRecords
    )

    $verifier = Join-Path `
        $repoRoot `
        'research\calibration-tests\continuous-action-pilot\tools\verify-formal-raw-trace.py'
    $run = Invoke-R3ScopedProcess `
        -Step (
            'verify-' +
            $ConfigurationId +
            '-' +
            [System.IO.Path]::GetFileNameWithoutExtension($TracePath)
        ) `
        -FilePath $PythonExecutablePath `
        -Arguments @(
            '-B',
            $verifier,
            'verify',
            '--repo-root',
            $repoRoot,
            '--permit-path',
            $PermitPath,
            '--case-id',
            $caseId,
            '--trace-path',
            $TracePath,
            '--configuration-id',
            $ConfigurationId
        ) `
        -WorkingDirectory $repoRoot `
        -TimeoutMilliseconds 60000 `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord -List $ProcessRecords -Record $run
    if ($run.exit_code -ne 0) {
        throw (
            "Raw-trace verification failed for $ConfigurationId`: " +
            ($run.stderr + $run.stdout).Trim()
        )
    }
    $lines = @(
        $run.stdout -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($lines.Count -ne 1) {
        throw (
            "Raw-trace verifier returned an unexpected number of lines for " +
            "$ConfigurationId."
        )
    }
    try {
        $value = $lines[0] | ConvertFrom-Json
    }
    catch {
        throw "Raw-trace verifier did not return valid JSON for $ConfigurationId."
    }
    if ($value.status -cne 'formal_raw_trace_verified' -or
        $value.run_id -cne $runId -or
        $value.case_id -cne $caseId -or
        $value.configuration_id -cne $ConfigurationId -or
        [string]$value.formal_trace_sha256 -cnotmatch
            '^(?!0{64}$)[0-9a-f]{64}$') {
        throw "Raw-trace verifier returned an invalid result for $ConfigurationId."
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
    return $Value.ToString(
        [System.Globalization.CultureInfo]::InvariantCulture)
}

function ConvertTo-InvariantDecimal {
    param([Parameter(Mandatory = $true)][double] $Value)
    if ([double]::IsNaN($Value) -or [double]::IsInfinity($Value)) {
        throw 'Formal observation contains a non-finite decimal.'
    }
    return $Value.ToString(
        'R',
        [System.Globalization.CultureInfo]::InvariantCulture)
}

function New-ObservationRecords {
    param([Parameter(Mandatory = $true)] $Trace)

    $observation = $Trace.value.observation
    $configurationId = [string]$Trace.configuration_id
    $acceptedCount = if ([bool]$observation.candidate_accepted) { 1 } else { 0 }
    $adjudicationOffset =
        [double]$observation.adjudication_time_ms -
        [double]$observation.candidate_time_ms
    Assert-Equal `
        -Actual $adjudicationOffset `
        -Expected ([math]::Truncate($adjudicationOffset)) `
        -Label "$configurationId adjudication offset integer serialization"

    return @(
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0001'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (
                    ConvertTo-InvariantInteger -Value $acceptedCount
                ) `
                -Unit 'count'
            tolerance_rule_id = 'tol.c.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0002'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (
                    ConvertTo-InvariantInteger -Value ([long]$adjudicationOffset)
                ) `
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
                -SerializedValue (
                    ConvertTo-InvariantDecimal `
                        -Value ([double]$observation.raw_time_ms)
                ) `
                -Unit 'millisecond'
            tolerance_rule_id = 'tol.c.0002'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0005'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (
                    ConvertTo-InvariantInteger `
                        -Value ([long]$observation.notification_count)
                ) `
                -Unit 'count'
            tolerance_rule_id = 'tol.c.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.c.0006'
            actual_value = New-ActualValue `
                -ValueType 'decimal' `
                -SerializedValue (
                    ConvertTo-InvariantDecimal `
                        -Value ([double]$observation.reentry_closed_time_ms)
                ) `
                -Unit 'millisecond'
            tolerance_rule_id = 'tol.c.0002'
        }
    )
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
        reentry_allowed_after_candidate =
            $observation.reentry_allowed_after_candidate
        reentry_allowed_at_notification =
            $observation.reentry_allowed_at_notification
        reentry_closed_time_ms = $observation.reentry_closed_time_ms
        production_can_be_hit_after_result =
            $observation.production_can_be_hit_after_result
        time_offset_ms = $observation.time_offset_ms
    }
}

function Get-ProjectionJson {
    param([Parameter(Mandatory = $true)] $Trace)
    return (
        Get-MechanismProjection -Trace $Trace |
            ConvertTo-Json -Compress -Depth 8
    )
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

    $label =
        "$($Trace.configuration_id) repetition $($Trace.repetition_index)"
    $value = $Trace.value
    $observation = $value.observation
    $expectedCommitTime = 1000 + $Delay

    Assert-ExactString $value.artifact_type 'continuous_action_r3_trace' `
        "$label artifact type"
    Assert-ExactString $value.artifact_version '0.1.0' `
        "$label artifact version"
    Assert-ExactString $value.run_id $runId "$label run id"
    Assert-ExactString $value.case_id $caseId "$label case id"
    Assert-ExactString $value.configuration_id $Trace.configuration_id `
        "$label embedded configuration"
    Assert-ExactString $value.execution_permit_sha256 $ExecutionPermitSha256 `
        "$label execution permit"
    Assert-ExactString $value.formal_input_sha256 $FormalInputSha256 `
        "$label formal input"
    Assert-ExactString $value.prediction_set_digest $PredictionSetDigest `
        "$label prediction set"
    Assert-Equal $value.input.adjudication_delay_ms $Delay "$label delay"
    Assert-Equal $value.input.hit_animations $HitAnimations `
        "$label HitAnimations"
    Assert-Equal $value.input.candidate_count 1 "$label candidate count"
    Assert-Equal $value.input.candidate_time_ms 1000 `
        "$label input candidate time"
    Assert-Equal $value.input.object_start_time_ms 1000 `
        "$label object start time"
    Assert-Equal $value.input.overall_difficulty 5 `
        "$label overall difficulty"

    Assert-True ([bool]$observation.candidate_accepted) `
        "$label candidate acceptance"
    Assert-Equal $observation.candidate_time_ms 1000 `
        "$label observed candidate time"
    Assert-Equal $observation.adjudication_time_ms $expectedCommitTime `
        "$label adjudication time"
    Assert-Equal $observation.raw_time_ms $expectedCommitTime "$label RawTime"
    Assert-Equal $observation.notification_time_ms $expectedCommitTime `
        "$label notification time"
    Assert-Equal $observation.score_notification_time_ms $expectedCommitTime `
        "$label scoring notification time"
    Assert-Equal $observation.reentry_closed_time_ms $expectedCommitTime `
        "$label re-entry closure time"
    Assert-Equal $observation.time_offset_ms $Delay `
        "$label public time offset"
    Assert-True ([bool]$observation.judged) "$label Judged"
    Assert-Equal $observation.notification_count 1 `
        "$label notification count"
    Assert-Equal $observation.score_notification_count 1 `
        "$label scoring notification count"
    Assert-Equal $observation.score_judged_hits 1 `
        "$label scored judgement count"
    Assert-Equal $observation.production_can_be_hit_after_result $false `
        "$label post-result CanBeHit"
    Assert-Equal $observation.reentry_allowed_at_notification $false `
        "$label notification re-entry permission"

    $eventNames = @($observation.event_trace | ForEach-Object { $_.event })
    $expectedEvents = @(
        'candidate',
        'adjudication',
        'result_notification',
        'scoring_notification',
        'reentry_closed'
    )
    if (@(
            Compare-Object `
                -ReferenceObject $expectedEvents `
                -DifferenceObject $eventNames `
                -SyncWindow 0
        ).Count -ne 0) {
        throw "$label event order mismatch: $($eventNames -join ', ')"
    }
    if ([string]::IsNullOrWhiteSpace(
            [string]$observation.production_delegate_method
        ) -or
        [string]::IsNullOrWhiteSpace(
            [string]$observation.production_delegate_target_type
        )) {
        throw "$label did not identify the captured production delegate."
    }
}

function New-TraceArtifact {
    param([Parameter(Mandatory = $true)] $Trace)

    return [ordered]@{
        artifact_id = (
            $Trace.configuration_id +
            ('.repetition-{0:0000}.raw-trace' -f $Trace.repetition_index)
        )
        sha256 = $Trace.sha256
    }
}

# Permit first: no formal trace or output-root path is opened before the
# shared verifier succeeds. Only this hash-pinned safety helper is loaded.
$resolvedPythonPath = Resolve-FixedPythonRuntime -RequestedPath $PythonPath
$permit = Invoke-ExecutionPermitVerifier `
    -PermitPath $ExecutionPermitPath `
    -PythonExecutablePath $resolvedPythonPath
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$target = $permit.execution_target

$comparatorPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.comparator `
    -ExpectedRelativePath $comparatorRelativePath
if (-not [string]::Equals(
        [System.IO.Path]::GetFullPath($comparatorPath),
        [System.IO.Path]::GetFullPath($PSCommandPath),
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'Execution target does not bind the running CA-R3 comparator.'
}
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_input `
    -ExpectedRelativePath $formalInputRelativePath
$formalInputSha256 = [string]$target.formal_input.sha256
$fixtureSpecPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.fixture_spec `
    -ExpectedRelativePath $fixtureSpecRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$layout = Resolve-R3FormalOutputLayout `
    -Mode comparator `
    -FormalOutputRoot $FormalOutputRoot `
    -RepositoryRoot $repoRoot

$fixtureSpec =
    Get-Content -Raw -Encoding UTF8 -LiteralPath $fixtureSpecPath |
        ConvertFrom-Json
if ($fixtureSpec.repetition_count -ne 2 -or
    $fixtureSpec.stop_boundary_id -cne 'o.c.0032') {
    throw 'Permit-bound CA-R3 fixture spec has an invalid repetition contract.'
}

$processes = New-Object System.Collections.Generic.List[object]
$traces = @()
foreach ($descriptor in $layout.traces) {
    $verification = Invoke-RawTraceVerifier `
        -PermitPath $executionPermitFull `
        -TracePath $descriptor.path `
        -ConfigurationId $descriptor.configuration_id `
        -PythonExecutablePath $resolvedPythonPath `
        -ProcessRecords $processes
    if ([string]$verification.formal_input.sha256 -cne $formalInputSha256) {
        throw (
            "$($descriptor.configuration_id) repetition " +
            "$($descriptor.repetition_index) verifier returned the wrong " +
            'formal-input binding.'
        )
    }

    $sha256 = Get-Sha256 -Path $descriptor.path
    if ($sha256 -cne [string]$verification.formal_trace_sha256) {
        throw (
            "$($descriptor.configuration_id) repetition " +
            "$($descriptor.repetition_index) changed after strict validation."
        )
    }
    $trace = [pscustomobject]@{
        configuration_id = [string]$descriptor.configuration_id
        repetition_index = [int]$descriptor.repetition_index
        path = [string]$descriptor.path
        sha256 = $sha256
        value = (
            Get-Content -Raw -Encoding UTF8 -LiteralPath $descriptor.path |
                ConvertFrom-Json
        )
    }
    $tuple = Get-R3ConfigurationTuple `
        -ConfigurationId $trace.configuration_id
    Assert-TraceContract `
        -Trace $trace `
        -Delay $tuple.adjudication_delay_ms `
        -HitAnimations $tuple.hit_animations `
        -ExecutionPermitSha256 $executionPermitSha256 `
        -FormalInputSha256 $formalInputSha256 `
        -PredictionSetDigest $predictionSetDigest
    $traces += $trace
}

$byConfiguration = @{}
foreach ($configurationId in @(
        'config.baseline',
        'config.variant',
        'config.negative-a',
        'config.negative-b'
    )) {
    $pair = @(
        $traces |
            Where-Object { $_.configuration_id -ceq $configurationId } |
            Sort-Object repetition_index
    )
    if ($pair.Count -ne 2 -or
        $pair[0].repetition_index -ne 1 -or
        $pair[1].repetition_index -ne 2) {
        throw "$configurationId does not contain exactly repetitions 1 and 2."
    }
    Assert-ExactString `
        -Actual $pair[1].sha256 `
        -Expected $pair[0].sha256 `
        -Label "$configurationId repeatability trace bytes"
    Assert-ExactString `
        -Actual (Get-ProjectionJson -Trace $pair[1]) `
        -Expected (Get-ProjectionJson -Trace $pair[0]) `
        -Label "$configurationId repeatability projection"
    $byConfiguration[$configurationId] = $pair
}

$baseline = $byConfiguration['config.baseline'][0]
$variant = $byConfiguration['config.variant'][0]
$negativeA = $byConfiguration['config.negative-a'][0]
$negativeB = $byConfiguration['config.negative-b'][0]

Assert-ExactString `
    -Actual (Get-ProjectionJson -Trace $negativeA) `
    -Expected (Get-ProjectionJson -Trace $baseline) `
    -Label 'NEG-01 negative-a mechanism projection'
Assert-ExactString `
    -Actual (Get-ProjectionJson -Trace $negativeB) `
    -Expected (Get-ProjectionJson -Trace $negativeA) `
    -Label 'NEG-01 negative-b mechanism projection'

foreach ($field in @(
        'production_delegate_method',
        'production_delegate_target_type'
    )) {
    Assert-Equal `
        -Actual $variant.value.observation.$field `
        -Expected $baseline.value.observation.$field `
        -Label "primary invariant $field"
}
Assert-ExactString `
    -Actual (
        $variant.value.window_snapshot_ms |
            ConvertTo-Json -Compress
    ) `
    -Expected (
        $baseline.value.window_snapshot_ms |
            ConvertTo-Json -Compress
    ) `
    -Label 'primary hit-window snapshot'

$result = [ordered]@{
    artifact_type = 'formal_comparator_output'
    artifact_version = '0.1.0'
    run_id = $runId
    case_id = $caseId
    execution_permit_sha256 = $executionPermitSha256
    formal_input_sha256 = $formalInputSha256
    prediction_set_digest = $predictionSetDigest
    stop_boundary_id = 'o.c.0032'
    comparator_status = 'passed'
    configuration_artifacts = @(
        [ordered]@{
            configuration_id = 'config.baseline'
            artifacts = @(
                $byConfiguration['config.baseline'] |
                    ForEach-Object { New-TraceArtifact -Trace $_ }
            )
        },
        [ordered]@{
            configuration_id = 'config.variant'
            artifacts = @(
                $byConfiguration['config.variant'] |
                    ForEach-Object { New-TraceArtifact -Trace $_ }
            )
        }
    )
    observations = @(
        New-ObservationRecords -Trace $baseline
        New-ObservationRecords -Trace $variant
    )
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
                    configuration_id = 'config.negative-a'
                    artifacts = @(
                        $byConfiguration['config.negative-a'] |
                            ForEach-Object { New-TraceArtifact -Trace $_ }
                    )
                },
                [ordered]@{
                    configuration_id = 'config.negative-b'
                    artifacts = @(
                        $byConfiguration['config.negative-b'] |
                            ForEach-Object { New-TraceArtifact -Trace $_ }
                    )
                }
            )
        }
    )
}

$outputParent = Split-Path -Parent $layout.comparison_path
New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
Assert-R3NoReparsePoint -Path $outputParent
if (Test-Path -LiteralPath $layout.comparison_path) {
    throw 'R3 comparator output appeared after boundary validation.'
}
[System.IO.File]::WriteAllText(
    $layout.comparison_path,
    (($result | ConvertTo-Json -Depth 20) + "`n"),
    $utf8NoBom)

$result | ConvertTo-Json -Depth 20
