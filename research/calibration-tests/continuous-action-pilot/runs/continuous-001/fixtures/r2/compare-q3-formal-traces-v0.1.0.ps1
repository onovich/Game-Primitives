[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$SelfTest,

    [string]$ExecutionPermitPath,
    [string]$BaselineReplicaA,
    [string]$BaselineReplicaB,
    [string]$VariantReplicaA,
    [string]$VariantReplicaB,
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$formalEnvironmentNames = @(
    'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
    'GAME_PRIMITIVES_RUN_ID',
    'GAME_PRIMITIVES_CASE_ID'
)

function Assert-Condition {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
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
    param([string]$PermitPath)

    if ([string]::IsNullOrWhiteSpace($PermitPath)) {
        throw 'ExecutionPermitPath is required for formal comparison.'
    }
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
            --case-id 'CA-R2'
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
    Assert-Condition `
        ($value.status -ceq 'formal_execution_permit_verified' `
            -and $value.run_id -ceq 'continuous-001' `
            -and $value.case_id -ceq 'CA-R2') `
        'Verifier returned the wrong formal execution context.'
    Assert-Condition `
        ([string]$value.execution_permit_sha256 -cmatch '^(?!0{64})[0-9a-f]{64}$') `
        'Verifier returned an invalid execution-permit SHA-256.'
    Assert-Condition `
        ([string]$value.prediction_set_digest -cmatch '^(?!0{64})[0-9a-f]{64}$') `
        'Verifier returned an invalid prediction-set digest.'
    return $value
}

function Resolve-BoundTargetArtifact {
    param(
        [string]$RepositoryRoot,
        [object]$Reference,
        [string]$ExpectedRelativePath,
        [string]$Label,
        [AllowNull()]
        [string]$ExpectedFullPath
    )
    if ($null -eq $Reference `
        -or [string]$Reference.path -cne $ExpectedRelativePath `
        -or [string]$Reference.sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$') {
        throw "$Label execution-target reference is invalid."
    }
    $relative = $ExpectedRelativePath.Replace(
        '/',
        [System.IO.Path]::DirectorySeparatorChar
    )
    $full = [System.IO.Path]::GetFullPath(
        (Join-Path $RepositoryRoot $relative)
    )
    $rootPrefix = [System.IO.Path]::GetFullPath($RepositoryRoot).TrimEnd(
        [char[]]@('\', '/')
    ) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith(
        $rootPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or -not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "$Label execution-target path is absent or escapes the repository."
    }
    if (-not [string]::IsNullOrEmpty($ExpectedFullPath) `
        -and -not $full.Equals(
            [System.IO.Path]::GetFullPath($ExpectedFullPath),
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw "$Label execution-target path does not select the invoked artifact."
    }
    $actual = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $full
    ).Hash.ToLowerInvariant()
    if ($actual -cne [string]$Reference.sha256) {
        throw "$Label execution-target SHA-256 mismatch."
    }
    return $full
}

function Assert-ExecutionTarget {
    param(
        [string]$RepositoryRoot,
        [object]$PermitResult
    )
    $target = $PermitResult.execution_target
    if ($null -eq $target -or $target.case_id -cne 'CA-R2') {
        throw 'Execution permit did not return the CA-R2 execution target.'
    }
    $base = 'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r2'
    $support = $target.support_artifacts
    if ($null -eq $support) {
        throw 'CA-R2 execution target lacks support artifacts.'
    }
    return [pscustomobject]@{
        formal_runner = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $target.formal_runner `
            "$base/run-q3-formal-guarded-v0.1.0.ps1" `
            'Formal runner' `
            $null
        formal_input = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $target.formal_input `
            "$base/r2-formal-input-v0.1.0.json" `
            'Formal input' `
            $null
        test_body = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $target.test_body `
            "$base/q3-formal-harness-v0.1.0.c" `
            'Formal harness' `
            $null
        comparator = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $target.comparator `
            "$base/compare-q3-formal-traces-v0.1.0.ps1" `
            'Comparator' `
            $PSCommandPath
        build_runner = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.build_runner `
            "$base/build-q3-formal-fixture-v0.1.0.ps1" `
            'Build runner' `
            $null
        compatibility_patch = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.compatibility_patch `
            "$base/q3-msvc-x64-compatibility-v0.1.0.patch" `
            'Compatibility patch' `
            $null
        compatibility_source = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.compatibility_source `
            "$base/q3-formal-compatibility-v0.1.0.c" `
            'Compatibility source' `
            $null
        harness_header = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.harness_header `
            "$base/q3-formal-fixture-v0.1.0.h" `
            'Harness header' `
            $null
        observation_patch = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.observation_patch `
            "$base/q3-observation-v0.1.0.patch" `
            'Observation patch' `
            $null
        variant_patch = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $support.variant_patch `
            "$base/q3-entry-latch-variant-v0.1.0.patch" `
            'Variant patch' `
            $null
        raw_trace_schema = Resolve-BoundTargetArtifact `
            $RepositoryRoot `
            $target.raw_trace_schema `
            'research/calibration-tests/continuous-action-pilot/schema/ca-r2-raw-trace-0.1.0.schema.json' `
            'Raw-trace schema' `
            $null
    }
}

function Invoke-RawTraceVerifier {
    param(
        [string]$RepositoryRoot,
        [string]$PermitPath,
        [string]$TracePath,
        [string]$ConfigurationId
    )
    $verifier = Join-Path `
        $RepositoryRoot `
        'research/calibration-tests/continuous-action-pilot/tools/verify-formal-raw-trace.py'
    if (-not (Test-Path -LiteralPath $verifier -PathType Leaf)) {
        throw 'Strict formal raw-trace verifier is absent.'
    }
    $output = @(
        & python -B $verifier verify `
            --repo-root $RepositoryRoot `
            --permit-path $PermitPath `
            --case-id 'CA-R2' `
            --trace-path $TracePath `
            --configuration-id $ConfigurationId
    )
    if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1) {
        throw 'Strict CA-R2 raw-trace verification failed.'
    }
    try {
        $value = $output[0] | ConvertFrom-Json
    } catch {
        throw 'Strict CA-R2 raw-trace verifier returned invalid JSON.'
    }
    $traceHash = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $TracePath
    ).Hash.ToLowerInvariant()
    if ($value.status -cne 'formal_raw_trace_verified' `
        -or $value.run_id -cne 'continuous-001' `
        -or $value.case_id -cne 'CA-R2' `
        -or $value.configuration_id -cne $ConfigurationId `
        -or $value.formal_trace_sha256 -cne $traceHash) {
        throw 'Strict CA-R2 raw-trace verifier returned the wrong trace binding.'
    }
    return $value
}

function Assert-FormalEnvironmentAbsent {
    foreach ($name in $formalEnvironmentNames) {
        Assert-Condition `
            ([string]::IsNullOrEmpty(
                [Environment]::GetEnvironmentVariable($name, 'Process')
            )) `
            "Self-test refuses formal environment variable $name."
    }
}

function Get-ZeroOrDirectionCategory {
    param([object]$Value, [string]$Label)
    try {
        $numericValue = [double]$Value
    } catch {
        throw "$Label is not numeric."
    }
    Assert-Condition `
        (-not [double]::IsNaN($numericValue) `
            -and -not [double]::IsInfinity($numericValue)) `
        "$Label is not finite."

    # tol.b.0002 is categorical, not an epsilon: +0 and -0 are the
    # same zero class; every non-zero value maps to an integer direction.
    if ($numericValue -eq 0.0) {
        return 0
    }
    if ($numericValue -gt 0.0) {
        return 1
    }
    return -1
}

function ConvertTo-DirectionToken {
    param([object]$Value, [string]$Label)
    $category = Get-ZeroOrDirectionCategory -Value $Value -Label $Label
    switch ($category) {
        -1 { return 'negative' }
        0 { return 'zero' }
        1 { return 'positive' }
        default { throw "$Label produced an unknown direction category." }
    }
}

function Get-OrderedDirectionSequence {
    param([object]$Trace)
    $tokens = for ($index = 0; $index -lt $Trace.Steps.Count; $index++) {
        $used = $Trace.Steps[$index].used_cmd
        $step = $index.ToString(
            '000',
            [System.Globalization.CultureInfo]::InvariantCulture
        )
        $forward = ConvertTo-DirectionToken `
            -Value $used.forwardmove `
            -Label "Step $index used forward direction"
        $right = ConvertTo-DirectionToken `
            -Value $used.rightmove `
            -Label "Step $index used right direction"
        "$step`:forward=$forward,right=$right"
    }
    return $tokens -join '|'
}

function Get-TraceTotal {
    param([object]$Trace, [string]$Field)
    $total = 0
    foreach ($step in $Trace.Steps) {
        $total += [int]$step.$Field
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
    param([object]$Trace)
    $configurationId = [string]$Trace.Header.configuration_id
    $stopStep = $Trace.Steps[24]
    return @(
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.b.0001'
            actual_value = New-ActualValue `
                -ValueType 'string' `
                -SerializedValue (Get-OrderedDirectionSequence $Trace) `
                -Unit $null
            tolerance_rule_id = 'tol.b.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.b.0002'
            actual_value = New-ActualValue `
                -ValueType 'direction' `
                -SerializedValue (ConvertTo-DirectionToken `
                    -Value $stopStep.velocity[1] `
                    -Label "$configurationId stop-boundary velocity Y") `
                -Unit 'engine_unit_per_second'
            tolerance_rule_id = 'tol.b.0002'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.b.0003'
            actual_value = New-ActualValue `
                -ValueType 'direction' `
                -SerializedValue (ConvertTo-DirectionToken `
                    -Value $stopStep.origin[1] `
                    -Label "$configurationId stop-boundary origin Y") `
                -Unit 'engine_unit'
            tolerance_rule_id = 'tol.b.0002'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.b.0004'
            actual_value = New-ActualValue `
                -ValueType 'integer' `
                -SerializedValue (Get-TraceTotal $Trace 'numtouch').ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit 'count'
            tolerance_rule_id = 'tol.b.0001'
        },
        [ordered]@{
            configuration_id = $configurationId
            observation_id = 'obs.b.0005'
            actual_value = New-ActualValue `
                -ValueType 'id' `
                -SerializedValue ([int]$Trace.Steps[0].branch_id).ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture) `
                -Unit $null
            tolerance_rule_id = 'tol.b.0001'
        }
    )
}

function Get-CommandSignature {
    param([object]$Command)
    return @(
        [int]$Command.serverTime,
        [int]$Command.angles[0],
        [int]$Command.angles[1],
        [int]$Command.angles[2],
        [int]$Command.buttons,
        [int]$Command.weapon,
        [int]$Command.forwardmove,
        [int]$Command.rightmove,
        [int]$Command.upmove
    ) -join ','
}

function Assert-PreservedCommandFields {
    param([object]$Raw, [object]$Used, [int]$Step)
    foreach ($field in @('serverTime', 'buttons', 'weapon', 'upmove')) {
        Assert-Condition `
            ([int]$Raw.$field -eq [int]$Used.$field) `
            "Step $Step changed preserved command field $field."
    }
    for ($angle = 0; $angle -lt 3; $angle++) {
        Assert-Condition `
            ([int]$Raw.angles[$angle] -eq [int]$Used.angles[$angle]) `
            "Step $Step changed preserved command angle $angle."
    }
}

function Assert-Trace {
    param(
        [object]$Trace,
        [string]$ExpectedConfiguration,
        [string]$ExpectedFormalInputSha256,
        [string]$ExpectedExecutionPermitSha256,
        [string]$ExpectedPredictionSetDigest
    )

    Assert-Condition ($null -ne $Trace.Header) 'Trace header is missing.'
    Assert-Condition ($null -ne $Trace.Stop) 'Trace stop record is missing.'
    Assert-Condition ($Trace.Steps.Count -eq 25) 'Trace must contain 25 steps.'
    Assert-Condition `
        ($Trace.Header.run_id -ceq 'continuous-001') `
        'Trace run_id mismatch.'
    Assert-Condition ($Trace.Header.case_id -ceq 'CA-R2') 'Trace case_id mismatch.'
    Assert-Condition `
        ($Trace.Header.configuration_id -ceq $ExpectedConfiguration) `
        'Trace configuration mismatch.'
    Assert-Condition `
        ($Trace.Header.input_sha256 -ceq $ExpectedFormalInputSha256) `
        'Trace formal-input SHA-256 mismatch.'
    Assert-Condition `
        ($Trace.Header.execution_permit_sha256 -ceq $ExpectedExecutionPermitSha256) `
        'Trace execution-permit SHA-256 mismatch.'
    Assert-Condition `
        ($Trace.Header.prediction_set_digest -ceq $ExpectedPredictionSetDigest) `
        'Trace prediction-set digest mismatch.'
    Assert-Condition `
        ($Trace.Header.source_commit -ceq 'dbe4ddb10315479fc00086f08e25d968b4b43c49') `
        'Trace source commit mismatch.'
    Assert-Condition ([int]$Trace.Header.step_count -eq 25) 'Step count mismatch.'
    Assert-Condition ([int]$Trace.Header.step_ms -eq 8) 'Step duration mismatch.'

    $firstForward = [int]$Trace.Steps[0].raw_cmd.forwardmove
    $firstRight = [int]$Trace.Steps[0].raw_cmd.rightmove
    for ($index = 0; $index -lt 25; $index++) {
        $step = $Trace.Steps[$index]
        $raw = $step.raw_cmd
        $used = $step.used_cmd
        Assert-Condition ([int]$step.step_index -eq $index) "Step index mismatch at $index."
        Assert-Condition `
            ([int]$raw.serverTime -eq (($index + 1) * 8)) `
            "Raw command time mismatch at step $index."
        Assert-PreservedCommandFields -Raw $raw -Used $used -Step $index
        Assert-Condition ([int]$step.branch_id -eq 6) "Non-air branch at step $index."
        Assert-Condition ([int]$step.branch_calls -eq 1) "Branch count mismatch at step $index."
        Assert-Condition ([int]$step.air_move_calls -eq 1) "Air observation mismatch at step $index."
        Assert-Condition ([int]$step.trace_calls -gt 0) "No trace call at step $index."
        Assert-Condition `
            ([int]$step.pointcontents_calls -gt 0) `
            "No pointcontents call at step $index."
        Assert-Condition ([int]$step.event_calls -eq 0) "Unexpected event at step $index."
        Assert-Condition ([int]$step.printf_calls -eq 0) "Unexpected debug path at step $index."
        Assert-Condition ([int]$step.snap_calls -eq 1) "Snap count mismatch at step $index."
        Assert-Condition ([int]$step.trace_violation -eq 0) "Trace violation at step $index."
        Assert-Condition ([int]$step.numtouch -eq 0) "Unexpected touch at step $index."
        Assert-Condition ([int]$step.watertype -eq 0) "Unexpected water type at step $index."
        Assert-Condition ([int]$step.waterlevel -eq 0) "Unexpected water level at step $index."
        Assert-Condition `
            ([int]$step.commandTime -eq (($index + 1) * 8)) `
            "State command time mismatch at step $index."

        if ($ExpectedConfiguration -eq 'config.baseline') {
            Assert-Condition `
                ([int]$used.forwardmove -eq [int]$raw.forwardmove `
                    -and [int]$used.rightmove -eq [int]$raw.rightmove) `
                "Baseline did not resample raw direction at step $index."
        } else {
            Assert-Condition `
                ([int]$used.forwardmove -eq $firstForward `
                    -and [int]$used.rightmove -eq $firstRight) `
                "Variant did not preserve the entry direction at step $index."
        }
    }
    Assert-Condition ([int]$Trace.Stop.rule_time_ms -eq 200) 'Stop time mismatch.'
    Assert-Condition ([int]$Trace.Stop.steps_completed -eq 25) 'Stop step count mismatch.'
    Assert-Condition ($Trace.Stop.invariants_passed -eq $true) 'Harness invariants failed.'
}

function Assert-Pair {
    param([object]$Baseline, [object]$Variant)

    Assert-Condition `
        ($Baseline.Header.input_sha256 -eq $Variant.Header.input_sha256) `
        'Baseline and variant input hashes differ.'
    Assert-Condition `
        ($Baseline.Header.execution_permit_sha256 -eq $Variant.Header.execution_permit_sha256) `
        'Baseline and variant execution-permit hashes differ.'
    Assert-Condition `
        ($Baseline.Header.prediction_set_digest -eq $Variant.Header.prediction_set_digest) `
        'Baseline and variant prediction-set digests differ.'

    for ($index = 0; $index -lt 25; $index++) {
        $baselineStep = $Baseline.Steps[$index]
        $variantStep = $Variant.Steps[$index]
        Assert-Condition `
            ((Get-CommandSignature $baselineStep.raw_cmd) -eq (
                Get-CommandSignature $variantStep.raw_cmd
            )) `
            "Raw input differs between configurations at step $index."
    }

    $baselineStop = $Baseline.Steps[24]
    $variantStop = $Variant.Steps[24]
    $baselineVelocityY = Get-ZeroOrDirectionCategory `
        -Value $baselineStop.velocity[1] `
        -Label 'Baseline stop-boundary velocity Y'
    $baselineOriginY = Get-ZeroOrDirectionCategory `
        -Value $baselineStop.origin[1] `
        -Label 'Baseline stop-boundary origin Y'
    $variantVelocityY = Get-ZeroOrDirectionCategory `
        -Value $variantStop.velocity[1] `
        -Label 'Variant stop-boundary velocity Y'
    $variantOriginY = Get-ZeroOrDirectionCategory `
        -Value $variantStop.origin[1] `
        -Label 'Variant stop-boundary origin Y'

    Assert-Condition `
        ($baselineVelocityY -ne 0) `
        'Resampling trace has zero stop-boundary velocity Y.'
    Assert-Condition `
        ($baselineOriginY -ne 0) `
        'Resampling trace has zero stop-boundary origin Y.'
    Assert-Condition `
        ($variantVelocityY -eq 0) `
        'Entry-latch trace has non-zero stop-boundary velocity Y.'
    Assert-Condition `
        ($variantOriginY -eq 0) `
        'Entry-latch trace has non-zero stop-boundary origin Y.'
}

function Read-Trace {
    param(
        [string]$Path,
        [string]$ExpectedRawSha256
    )
    if (-not [System.IO.Path]::IsPathRooted($Path) `
        -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Trace path must be an existing absolute file: $Path"
    }
    $full = [System.IO.Path]::GetFullPath($Path)
    $rawBytes = [System.IO.File]::ReadAllBytes($full)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $actualRawSha256 = (
            [System.BitConverter]::ToString(
                $sha256.ComputeHash($rawBytes)
            )
        ).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
    Assert-Condition `
        ($actualRawSha256 -ceq $ExpectedRawSha256) `
        'Trace bytes changed after strict raw-trace verification.'
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    try {
        $traceText = $strictUtf8.GetString($rawBytes)
    } catch {
        throw 'Verified trace bytes are no longer valid UTF-8.'
    }
    $records = @()
    $reader = [System.IO.StringReader]::new($traceText)
    while ($null -ne ($line = $reader.ReadLine())) {
        if ($line.Trim() -eq '') {
            continue
        }
        $records += $line | ConvertFrom-Json
    }
    $reader.Dispose()
    return [pscustomobject]@{
        Header = @($records | Where-Object record_type -eq 'run_header')[0]
        Steps = @($records | Where-Object record_type -eq 'step')
        Stop = @($records | Where-Object record_type -eq 'stop')[0]
        Path = $full
        RawSha256 = $actualRawSha256
    }
}

function New-FictionalTrace {
    param([string]$Configuration)
    $steps = @()
    for ($index = 0; $index -lt 25; $index++) {
        $rawForward = if ($index -lt 5) { 11 } else { 0 }
        $rawRight = if ($index -lt 5) { 0 } else { 13 }
        $usedForward = if ($Configuration -eq 'config.baseline') {
            $rawForward
        } else {
            11
        }
        $usedRight = if ($Configuration -eq 'config.baseline') {
            $rawRight
        } else {
            0
        }
        $y = if ($Configuration -eq 'config.baseline' -and $index -ge 5) {
            2
        } else {
            0
        }
        $commandTime = ($index + 1) * 8
        $raw = [pscustomobject]@{
            serverTime = $commandTime
            angles = @(0, 0, 0)
            buttons = 0
            weapon = 0
            forwardmove = $rawForward
            rightmove = $rawRight
            upmove = 0
        }
        $used = [pscustomobject]@{
            serverTime = $commandTime
            angles = @(0, 0, 0)
            buttons = 0
            weapon = 0
            forwardmove = $usedForward
            rightmove = $usedRight
            upmove = 0
        }
        $steps += [pscustomobject]@{
            record_type = 'step'
            step_index = $index
            raw_cmd = $raw
            used_cmd = $used
            branch_id = 6
            branch_calls = 1
            air_move_calls = 1
            trace_calls = 1
            pointcontents_calls = 1
            event_calls = 0
            printf_calls = 0
            snap_calls = 1
            trace_violation = 0
            numtouch = 0
            watertype = 0
            waterlevel = 0
            commandTime = $commandTime
            origin = @(0, $y, 0)
            velocity = @(0, $y, 0)
        }
    }
    return [pscustomobject]@{
        Header = [pscustomobject]@{
            run_id = 'continuous-001'
            case_id = 'CA-R2'
            configuration_id = $Configuration
            source_commit = 'dbe4ddb10315479fc00086f08e25d968b4b43c49'
            input_sha256 = ('1' * 64)
            execution_permit_sha256 = ('2' * 64)
            prediction_set_digest = ('3' * 64)
            step_count = 25
            step_ms = 8
        }
        Steps = $steps
        Stop = [pscustomobject]@{
            rule_time_ms = 200
            steps_completed = 25
            invariants_passed = $true
        }
    }
}

if ($SelfTest) {
    foreach ($formalPath in @(
        $ExecutionPermitPath,
        $BaselineReplicaA,
        $BaselineReplicaB,
        $VariantReplicaA,
        $VariantReplicaB,
        $OutputPath
    )) {
        Assert-Condition `
            ([string]::IsNullOrWhiteSpace($formalPath)) `
            'Self-test cannot be combined with permit, trace, or output paths.'
    }
    Assert-FormalEnvironmentAbsent
    $fictionalBaseline = New-FictionalTrace -Configuration 'config.baseline'
    $fictionalVariant = New-FictionalTrace -Configuration 'config.variant'
    Assert-Trace `
        -Trace $fictionalBaseline `
        -ExpectedConfiguration 'config.baseline' `
        -ExpectedFormalInputSha256 ('1' * 64) `
        -ExpectedExecutionPermitSha256 ('2' * 64) `
        -ExpectedPredictionSetDigest ('3' * 64)
    Assert-Trace `
        -Trace $fictionalVariant `
        -ExpectedConfiguration 'config.variant' `
        -ExpectedFormalInputSha256 ('1' * 64) `
        -ExpectedExecutionPermitSha256 ('2' * 64) `
        -ExpectedPredictionSetDigest ('3' * 64)
    Assert-Pair -Baseline $fictionalBaseline -Variant $fictionalVariant

    $badPreservation = (
        $fictionalBaseline | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    )
    $badPreservation.Steps[7].used_cmd.serverTime = 999
    $rejected = $false
    try {
        Assert-Trace `
            -Trace $badPreservation `
            -ExpectedConfiguration 'config.baseline' `
            -ExpectedFormalInputSha256 ('1' * 64) `
            -ExpectedExecutionPermitSha256 ('2' * 64) `
            -ExpectedPredictionSetDigest ('3' * 64)
    } catch {
        $rejected = $true
    }
    Assert-Condition $rejected 'Comparator accepted a changed preserved command field.'

    $badInputBinding = (
        $fictionalBaseline | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    )
    $badInputBinding.Header.input_sha256 = '4' * 64
    $rejected = $false
    try {
        Assert-Trace `
            -Trace $badInputBinding `
            -ExpectedConfiguration 'config.baseline' `
            -ExpectedFormalInputSha256 ('1' * 64) `
            -ExpectedExecutionPermitSha256 ('2' * 64) `
            -ExpectedPredictionSetDigest ('3' * 64)
    } catch {
        $rejected = $true
    }
    Assert-Condition $rejected 'Comparator accepted the wrong formal-input hash.'

    $badCriterion = (
        $fictionalVariant | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    )
    $badCriterion.Steps[24].origin[1] = 1
    $rejected = $false
    try {
        Assert-Pair -Baseline $fictionalBaseline -Variant $badCriterion
    } catch {
        $rejected = $true
    }
    Assert-Condition $rejected 'Comparator accepted a violated Y criterion.'

    $negativeZero = (
        $fictionalVariant | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    )
    $negativeZero.Steps[24].origin[1] = [double]-0.0
    $negativeZero.Steps[24].velocity[1] = [double]-0.0
    Assert-Pair -Baseline $fictionalBaseline -Variant $negativeZero

    $tinyNonZero = (
        $fictionalVariant | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    )
    $tinyNonZero.Steps[24].origin[1] = 0.000000000001
    $rejected = $false
    try {
        Assert-Pair -Baseline $fictionalBaseline -Variant $tinyNonZero
    } catch {
        $rejected = $true
    }
    Assert-Condition `
        $rejected `
        'Comparator treated a non-zero value as zero under tol.b.0002.'
    Write-Output 'COMPARATOR_SELF_TEST_PASS'
    exit 0
}

# The permit is reverified before any formal trace or output path is opened.
$permit = Invoke-ExecutionPermitVerifier -PermitPath $ExecutionPermitPath
$repositoryRoot = Find-RepositoryRoot
$null = Assert-ExecutionTarget `
    -RepositoryRoot $repositoryRoot `
    -PermitResult $permit
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$formalInputSha256 = [string]$permit.execution_target.formal_input.sha256

foreach ($required in @(
    $BaselineReplicaA,
    $BaselineReplicaB,
    $VariantReplicaA,
    $VariantReplicaB,
    $OutputPath
)) {
    if ([string]::IsNullOrWhiteSpace($required)) {
        throw 'Formal comparator paths are required outside self-test mode.'
    }
}
if (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    throw 'OutputPath must be absolute.'
}
$outputFull = [System.IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $outputFull) {
    throw 'OutputPath must be new and absent.'
}

$rawBaselineA = Invoke-RawTraceVerifier `
    -RepositoryRoot $repositoryRoot `
    -PermitPath $ExecutionPermitPath `
    -TracePath $BaselineReplicaA `
    -ConfigurationId 'config.baseline'
$rawBaselineB = Invoke-RawTraceVerifier `
    -RepositoryRoot $repositoryRoot `
    -PermitPath $ExecutionPermitPath `
    -TracePath $BaselineReplicaB `
    -ConfigurationId 'config.baseline'
$rawVariantA = Invoke-RawTraceVerifier `
    -RepositoryRoot $repositoryRoot `
    -PermitPath $ExecutionPermitPath `
    -TracePath $VariantReplicaA `
    -ConfigurationId 'config.variant'
$rawVariantB = Invoke-RawTraceVerifier `
    -RepositoryRoot $repositoryRoot `
    -PermitPath $ExecutionPermitPath `
    -TracePath $VariantReplicaB `
    -ConfigurationId 'config.variant'

$baselineA = Read-Trace `
    $BaselineReplicaA `
    ([string]$rawBaselineA.formal_trace_sha256)
$baselineB = Read-Trace `
    $BaselineReplicaB `
    ([string]$rawBaselineB.formal_trace_sha256)
$variantA = Read-Trace `
    $VariantReplicaA `
    ([string]$rawVariantA.formal_trace_sha256)
$variantB = Read-Trace `
    $VariantReplicaB `
    ([string]$rawVariantB.formal_trace_sha256)

Assert-Condition `
    ($baselineA.RawSha256 -ceq $baselineB.RawSha256) `
    'Baseline replicas are not byte-identical.'
Assert-Condition `
    ($variantA.RawSha256 -ceq $variantB.RawSha256) `
    'Variant replicas are not byte-identical.'
Assert-Trace `
    -Trace $baselineA `
    -ExpectedConfiguration 'config.baseline' `
    -ExpectedFormalInputSha256 $formalInputSha256 `
    -ExpectedExecutionPermitSha256 $executionPermitSha256 `
    -ExpectedPredictionSetDigest $predictionSetDigest
Assert-Trace `
    -Trace $baselineB `
    -ExpectedConfiguration 'config.baseline' `
    -ExpectedFormalInputSha256 $formalInputSha256 `
    -ExpectedExecutionPermitSha256 $executionPermitSha256 `
    -ExpectedPredictionSetDigest $predictionSetDigest
Assert-Trace `
    -Trace $variantA `
    -ExpectedConfiguration 'config.variant' `
    -ExpectedFormalInputSha256 $formalInputSha256 `
    -ExpectedExecutionPermitSha256 $executionPermitSha256 `
    -ExpectedPredictionSetDigest $predictionSetDigest
Assert-Trace `
    -Trace $variantB `
    -ExpectedConfiguration 'config.variant' `
    -ExpectedFormalInputSha256 $formalInputSha256 `
    -ExpectedExecutionPermitSha256 $executionPermitSha256 `
    -ExpectedPredictionSetDigest $predictionSetDigest
Assert-Pair -Baseline $baselineA -Variant $variantA

$observationRecords = @(
    New-ObservationRecords -Trace $baselineA
    New-ObservationRecords -Trace $variantA
)

$result = [ordered]@{
    artifact_type = 'formal_comparator_output'
    artifact_version = '0.1.0'
    run_id = 'continuous-001'
    case_id = 'CA-R2'
    execution_permit_sha256 = $executionPermitSha256
    prediction_set_digest = $predictionSetDigest
    formal_input_sha256 = $formalInputSha256
    stop_boundary_id = 'o.b.0030'
    comparator_status = 'passed'
    configuration_artifacts = @(
        [ordered]@{
            configuration_id = 'config.baseline'
            artifacts = @(
                [ordered]@{
                    artifact_id = 'config.baseline.replica-a'
                    sha256 = $baselineA.RawSha256
                },
                [ordered]@{
                    artifact_id = 'config.baseline.replica-b'
                    sha256 = $baselineB.RawSha256
                }
            )
        },
        [ordered]@{
            configuration_id = 'config.variant'
            artifacts = @(
                [ordered]@{
                    artifact_id = 'config.variant.replica-a'
                    sha256 = $variantA.RawSha256
                },
                [ordered]@{
                    artifact_id = 'config.variant.replica-b'
                    sha256 = $variantB.RawSha256
                }
            )
        }
    )
    observations = $observationRecords
    invariants = @(
        1..7 | ForEach-Object {
            [ordered]@{
                invariant_id = 'inv.b.{0:0000}' -f $_
                status = 'held'
            }
        }
    )
    negative_controls = @()
}
[System.IO.File]::WriteAllText(
    $outputFull,
    (($result | ConvertTo-Json -Depth 20) -replace "`r`n", "`n") + "`n",
    $utf8NoBom
)
Write-Output 'COMPARATOR_PASS'
