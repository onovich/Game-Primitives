[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BuildEvidencePath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExecutionPermitPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedCommit = 'dbe4ddb10315479fc00086f08e25d968b4b43c49'
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$scriptDirectory = Split-Path -Parent $PSCommandPath
$comparatorPath = Join-Path $scriptDirectory 'compare-q3-formal-traces-v0.1.0.ps1'
$processRecords = @()

function Get-FullExistingFile {
    param([string]$Value, [string]$Label)
    if (-not [System.IO.Path]::IsPathRooted($Value)) {
        throw "$Label must be an absolute path."
    }
    $full = [System.IO.Path]::GetFullPath($Value)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "$Label is not an existing file: $full"
    }
    return $full
}

function Write-LfText {
    param([string]$Path, [string]$Text)
    $normalized = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
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

    $repoRoot = Find-RepositoryRoot
    $verifier = Join-Path `
        $repoRoot `
        'research/calibration-tests/continuous-action-pilot/tools/verify-formal-execution-permit.py'
    $output = @(
        & python -B $verifier verify `
            --repo-root $repoRoot `
            --permit-path $PermitPath `
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
    if ($value.status -cne 'formal_execution_permit_verified' `
        -or $value.run_id -cne 'continuous-001' `
        -or $value.case_id -cne 'CA-R2' `
        -or [string]$value.execution_permit_sha256 -cnotmatch '^(?!0{64})[0-9a-f]{64}$' `
        -or [string]$value.prediction_set_digest -cnotmatch '^(?!0{64})[0-9a-f]{64}$') {
        throw 'Execution-permit verifier returned an invalid CA-R2 result.'
    }
    return $value
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Invoke-RecordedProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$StdoutPath,
        [string]$StderrPath,
        [string]$Label
    )
    $argumentLine = ($Arguments | ForEach-Object {
        ConvertTo-ProcessArgument $_
    }) -join ' '
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $argumentLine
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Could not start $Label."
    }
    $startedPid = $process.Id
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $stdoutText = $stdoutTask.Result
    $stderrText = $stderrTask.Result
    $exitCode = $process.ExitCode
    $process.Dispose()
    Write-LfText -Path $StdoutPath -Text $stdoutText
    Write-LfText -Path $StderrPath -Text $stderrText
    $script:processRecords += [ordered]@{
        label = $Label
        pid = $startedPid
        exit_code = $exitCode
    }
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode."
    }
    return [pscustomobject]@{
        ExitCode = $exitCode
        Pid = $startedPid
    }
}

function Assert-ArtifactHash {
    param([object]$Artifact, [string]$Label)
    $path = Get-FullExistingFile -Value $Artifact.path -Label $Label
    $actual = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $path
    ).Hash.ToLowerInvariant()
    if ($actual -ne $Artifact.sha256) {
        throw "$Label SHA-256 mismatch."
    }
    return $path
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
            $PSCommandPath
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
            $comparatorPath
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

function Assert-BuildArtifactMatchesTarget {
    param(
        [object]$BuildArtifact,
        [string]$TargetPath,
        [object]$TargetReference,
        [string]$Label
    )
    $buildPath = Assert-ArtifactHash $BuildArtifact $Label
    if (-not $buildPath.Equals(
        [System.IO.Path]::GetFullPath($TargetPath),
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or [string]$BuildArtifact.sha256 -cne [string]$TargetReference.sha256) {
        throw "$Label build evidence differs from the execution target."
    }
    return $buildPath
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

# The shared verifier is the only authorization boundary. It runs before the
# formal input is opened and before any trace or output path is created.
if (-not [System.IO.Path]::IsPathRooted($ExecutionPermitPath)) {
    throw 'ExecutionPermitPath must be absolute.'
}
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$permit = Invoke-ExecutionPermitVerifier -PermitPath $executionPermitFull
$repositoryRoot = Find-RepositoryRoot
$targetArtifacts = Assert-ExecutionTarget `
    -RepositoryRoot $repositoryRoot `
    -PermitResult $permit
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$buildEvidenceFull = Get-FullExistingFile $BuildEvidencePath 'BuildEvidencePath'
$comparatorFull = Get-FullExistingFile $comparatorPath 'Comparator'
if (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    throw 'OutputPath must be absolute.'
}
$outputFull = [System.IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $outputFull) {
    throw 'OutputPath must be new and absent.'
}

$buildEvidence = Get-Content -Raw -Encoding utf8 -LiteralPath $buildEvidenceFull |
    ConvertFrom-Json

if ($buildEvidence.artifact_type -ne 'q3_r2_formal_fixture_build_evidence' `
    -or $buildEvidence.run_id -ne 'continuous-001' `
    -or $buildEvidence.case_id -ne 'CA-R2' `
    -or $buildEvidence.source.commit_sha -ne $expectedCommit `
    -or $buildEvidence.source.clean_before_and_after -ne $true `
    -or $buildEvidence.platform_scope -ne 'MSVC-x64' `
    -or $buildEvidence.formal_input_executed -ne $false `
    -or $buildEvidence.formal_result_created -ne $false `
    -or $buildEvidence.self_tests.baseline -ne 'passed' `
    -or $buildEvidence.self_tests.variant -ne 'passed' `
    -or $buildEvidence.self_tests.comparator_fictional -ne 'passed' `
    -or $buildEvidence.self_tests.guarded_formal_refusal -ne 'passed') {
    throw 'Build evidence is not the frozen, pre-gate-passing CA-R2 build.'
}

$baselineExecutable = Assert-ArtifactHash `
    $buildEvidence.artifacts.baseline_executable `
    'Baseline executable'
$variantExecutable = Assert-ArtifactHash `
    $buildEvidence.artifacts.variant_executable `
    'Variant executable'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.formal_input `
    $targetArtifacts.formal_input `
    $permit.execution_target.formal_input `
    'Formal input'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.formal_harness `
    $targetArtifacts.test_body `
    $permit.execution_target.test_body `
    'Formal harness'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.fixture_header `
    $targetArtifacts.harness_header `
    $permit.execution_target.support_artifacts.harness_header `
    'Harness header'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.compatibility_layer `
    $targetArtifacts.compatibility_source `
    $permit.execution_target.support_artifacts.compatibility_source `
    'Compatibility layer'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.compatibility_patch `
    $targetArtifacts.compatibility_patch `
    $permit.execution_target.support_artifacts.compatibility_patch `
    'Compatibility patch'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.observation_patch `
    $targetArtifacts.observation_patch `
    $permit.execution_target.support_artifacts.observation_patch `
    'Observation patch'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.variant_patch `
    $targetArtifacts.variant_patch `
    $permit.execution_target.support_artifacts.variant_patch `
    'Variant patch'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.comparator `
    $targetArtifacts.comparator `
    $permit.execution_target.comparator `
    'Comparator'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.build_runner `
    $targetArtifacts.build_runner `
    $permit.execution_target.support_artifacts.build_runner `
    'Build runner'
$null = Assert-BuildArtifactMatchesTarget `
    $buildEvidence.artifacts.guarded_formal_runner `
    $targetArtifacts.formal_runner `
    $permit.execution_target.formal_runner `
    'Guarded formal runner'

$buildHash = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $buildEvidenceFull
).Hash.ToLowerInvariant()

New-Item -ItemType Directory -Path $outputFull | Out-Null
$runLog = Join-Path $outputFull 'formal-run.log'
Write-LfText -Path $runLog -Text (
    "CA-R2 guarded formal execution`n" +
    "UTC_START=$([DateTime]::UtcNow.ToString('o'))`n" +
    "EXECUTION_PERMIT_SHA256=$executionPermitSha256`n" +
    "PREDICTION_SET_DIGEST=$predictionSetDigest`n"
)

$savedEnvironment = [ordered]@{}
foreach ($name in @(
    'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
    'GAME_PRIMITIVES_RUN_ID',
    'GAME_PRIMITIVES_CASE_ID'
)) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable(
        $name,
        'Process'
    )
}

try {
    $env:GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256 = $executionPermitSha256
    $env:GAME_PRIMITIVES_PREDICTION_SET_DIGEST = $predictionSetDigest
    $env:GAME_PRIMITIVES_RUN_ID = 'continuous-001'
    $env:GAME_PRIMITIVES_CASE_ID = 'CA-R2'

    $tracePaths = [ordered]@{
        baseline_a = Join-Path $outputFull 'baseline-replica-a.jsonl'
        baseline_b = Join-Path $outputFull 'baseline-replica-b.jsonl'
        variant_a = Join-Path $outputFull 'variant-replica-a.jsonl'
        variant_b = Join-Path $outputFull 'variant-replica-b.jsonl'
    }
    $rawTraceVerifications = [ordered]@{}
    foreach ($run in @(
        [ordered]@{
            Label = 'baseline-a'
            Configuration = 'config.baseline'
            Executable = $baselineExecutable
            Trace = $tracePaths.baseline_a
        },
        [ordered]@{
            Label = 'baseline-b'
            Configuration = 'config.baseline'
            Executable = $baselineExecutable
            Trace = $tracePaths.baseline_b
        },
        [ordered]@{
            Label = 'variant-a'
            Configuration = 'config.variant'
            Executable = $variantExecutable
            Trace = $tracePaths.variant_a
        },
        [ordered]@{
            Label = 'variant-b'
            Configuration = 'config.variant'
            Executable = $variantExecutable
            Trace = $tracePaths.variant_b
        }
    )) {
        $stdout = Join-Path $outputFull "$($run.Label).stdout.log"
        $stderr = Join-Path $outputFull "$($run.Label).stderr.log"
        Invoke-RecordedProcess `
            -FilePath $run.Executable `
            -Arguments @(
                '--formal',
                '--output',
                $run.Trace
            ) `
            -WorkingDirectory $outputFull `
            -StdoutPath $stdout `
            -StderrPath $stderr `
            -Label $run.Label | Out-Null
        $stdoutLines = @(Get-Content -Encoding utf8 -LiteralPath $stdout)
        $stderrLines = @(Get-Content -Encoding utf8 -LiteralPath $stderr)
        if ($stdoutLines.Count -ne 1 `
            -or $stdoutLines[0].Trim() -ne 'FORMAL_EXECUTION_COMPLETE' `
            -or $stderrLines.Count -ne 0 `
            -or -not (Test-Path -LiteralPath $run.Trace -PathType Leaf)) {
            throw "$($run.Label) formal marker or trace mismatch."
        }
        $rawTraceVerifications[$run.Label] = Invoke-RawTraceVerifier `
            -RepositoryRoot $repositoryRoot `
            -PermitPath $executionPermitFull `
            -TracePath $run.Trace `
            -ConfigurationId $run.Configuration
    }

    $comparatorResult = Join-Path $outputFull 'comparator-result.json'
    Invoke-RecordedProcess `
        -FilePath 'powershell.exe' `
        -Arguments @(
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            $comparatorFull,
            '-ExecutionPermitPath',
            $executionPermitFull,
            '-BaselineReplicaA',
            $tracePaths.baseline_a,
            '-BaselineReplicaB',
            $tracePaths.baseline_b,
            '-VariantReplicaA',
            $tracePaths.variant_a,
            '-VariantReplicaB',
            $tracePaths.variant_b,
            '-OutputPath',
            $comparatorResult
        ) `
        -WorkingDirectory $outputFull `
        -StdoutPath (Join-Path $outputFull 'comparator.stdout.log') `
        -StderrPath (Join-Path $outputFull 'comparator.stderr.log') `
        -Label 'comparator' | Out-Null
    $comparatorStdout = @(
        Get-Content -Encoding utf8 -LiteralPath (
            Join-Path $outputFull 'comparator.stdout.log'
        )
    )
    if ($comparatorStdout.Count -ne 1 `
        -or $comparatorStdout[0].Trim() -ne 'COMPARATOR_PASS') {
        throw 'Comparator marker mismatch.'
    }

    $alive = @(
        $processRecords |
        ForEach-Object { Get-Process -Id $_.pid -ErrorAction SilentlyContinue }
    )
    if ($alive.Count -ne 0) {
        throw 'A directly started formal process remains alive.'
    }

    $invocation = [ordered]@{
        artifact_type = 'q3_r2_formal_invocation'
        artifact_version = '0.1.0'
        run_id = 'continuous-001'
        case_id = 'CA-R2'
        execution_permit_sha256 = $executionPermitSha256
        prediction_set_digest = $predictionSetDigest
        build_evidence_sha256 = $buildHash
        processes = $processRecords
        raw_trace_verifications = $rawTraceVerifications
        outputs = @(
            $tracePaths.Keys | ForEach-Object {
                [ordered]@{
                    artifact_id = $_
                    path = $tracePaths[$_]
                    sha256 = (
                        Get-FileHash `
                            -Algorithm SHA256 `
                            -LiteralPath $tracePaths[$_]
                    ).Hash.ToLowerInvariant()
                }
            }
        )
        comparator_result = [ordered]@{
            path = $comparatorResult
            sha256 = (
                Get-FileHash -Algorithm SHA256 -LiteralPath $comparatorResult
            ).Hash.ToLowerInvariant()
        }
        completed_at = [DateTime]::UtcNow.ToString('o')
    }
    Write-LfText `
        -Path (Join-Path $outputFull 'formal-invocation.json') `
        -Text (($invocation | ConvertTo-Json -Depth 20) + "`n")
    Write-LfText `
        -Path $runLog `
        -Text (
            (Get-Content -Raw -Encoding utf8 -LiteralPath $runLog) +
            "FORMAL_EXECUTION=COMPLETE`n" +
            "COMPARATOR=PASS`n" +
            "UTC_END=$([DateTime]::UtcNow.ToString('o'))`n"
        )
    Write-Output 'FORMAL_EXECUTION_COMPLETE'
    Write-Output 'COMPARATOR_PASS'
    exit 0
} finally {
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable(
            $name,
            $savedEnvironment[$name],
            'Process'
        )
    }
}
