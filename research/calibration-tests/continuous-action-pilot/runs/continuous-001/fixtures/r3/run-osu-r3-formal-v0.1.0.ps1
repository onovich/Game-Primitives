[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'config.baseline',
        'config.variant',
        'config.negative-a',
        'config.negative-b'
    )]
    [string] $ConfigurationId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2)]
    [int] $RepetitionIndex,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourcePath,

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
$caseId = 'CA-R3'
$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$expectedSdkVersion = '8.0.100'
$expectedPythonPath = 'C:\Python314\python.exe'
$expectedPythonSha256 = 'cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b'
$expectedPythonBytes = 106328
$expectedSafetyGuardsSha256 =
    '53b714b3224057e6dc2f5b01d8c13529ea8a0b1b75cc0c25eb0d1083c76aa6be'
$testFullyQualifiedName =
    'osu.Game.Rulesets.Osu.Tests.TestSceneGamePrimitivesR3.TestFormalAdjudicationSchedule'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptRoot '..\..\..\..\..\..\..')
).TrimEnd('\')

$runnerRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/run-osu-r3-formal-v0.1.0.ps1'
$formalInputRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/formal-input-r3-v0.1.0.json'
$buildRunnerRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1'
$fixtureSpecRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-fixture-spec-v0.1.0.json'
$dependencyLockSetRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/dependency-lock-set-v0.1.0.json'
$buildEvidenceRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/r3-build-list-evidence-v0.1.0.json'
$testBodyRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/TestSceneGamePrimitivesR3.cs'
$comparatorRelativePath =
    'research/calibration-tests/continuous-action-pilot/runs/continuous-001/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1'
$rawTraceSchemaRelativePath =
    'research/calibration-tests/continuous-action-pilot/schema/ca-r3-raw-trace-0.1.0.schema.json'

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
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

function Resolve-BoundArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][object] $Reference,
        [Parameter(Mandatory = $true)][string] $ExpectedRelativePath
    )

    if ([string]$Reference.path -cne $ExpectedRelativePath -or
        [string]$Reference.sha256 -cnotmatch '^(?!0{64}$)[0-9a-f]{64}$') {
        throw "Execution target selected an invalid artifact reference for $ExpectedRelativePath."
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
    $result = Invoke-R3BootstrapProcess `
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
    if ($result.exit_code -ne 0) {
        throw (
            'Execution-permit verification failed: ' +
            ($result.stderr + $result.stdout).Trim()
        )
    }
    $lines = @(
        $result.stdout -split "`r?`n" |
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
        [Parameter(Mandatory = $true)][string] $ExpectedConfigurationId,
        [Parameter(Mandatory = $true)][string] $PythonExecutablePath,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]] $ProcessRecords
    )

    $verifier = Join-Path `
        $repoRoot `
        'research\calibration-tests\continuous-action-pilot\tools\verify-formal-raw-trace.py'
    $run = Invoke-R3ScopedProcess `
        -Step 'verify-formal-raw-trace' `
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
            $ExpectedConfigurationId
        ) `
        -WorkingDirectory $repoRoot `
        -TimeoutMilliseconds 60000 `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord -List $ProcessRecords -Record $run
    if ($run.exit_code -ne 0) {
        throw (
            'Raw-trace verification failed: ' +
            ($run.stderr + $run.stdout).Trim()
        )
    }
    $lines = @(
        $run.stdout -split "`r?`n" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($lines.Count -ne 1) {
        throw 'Raw-trace verifier returned an unexpected number of lines.'
    }
    try {
        $value = $lines[0] | ConvertFrom-Json
    }
    catch {
        throw 'Raw-trace verifier did not return valid JSON.'
    }
    if ($value.status -cne 'formal_raw_trace_verified' -or
        $value.run_id -cne $runId -or
        $value.case_id -cne $caseId -or
        $value.configuration_id -cne $ExpectedConfigurationId -or
        [string]$value.formal_trace_sha256 -cnotmatch
            '^(?!0{64}$)[0-9a-f]{64}$') {
        throw 'Raw-trace verifier returned an invalid CA-R3 result.'
    }
    return $value
}

function Assert-R3ExecutionTreeManifest {
    param(
        [Parameter(Mandatory = $true)] $Replay,
        [Parameter(Mandatory = $true)][string] $LockedAssemblySha256,
        [Parameter(Mandatory = $true)][string] $LockedManifestSha256,
        [Parameter(Mandatory = $true)][string] $SourceRoot,
        [Parameter(Mandatory = $true)][string] $DotnetExecutable,
        [Parameter(Mandatory = $true)][string] $OutputRoot
    )

    foreach ($value in @(
            [string]$Replay.cache_root,
            [string]$Replay.execution_tree.execution_root,
            [string]$Replay.execution_tree.manifest.external_path,
            [string]$Replay.assembly.external_path
        )) {
        if (-not [System.IO.Path]::IsPathRooted($value)) {
            throw 'Permit-bound R3 execution-tree paths must be absolute.'
        }
    }

    $cacheRoot = Assert-R3SafeRoot `
        -CandidateRoot ([string]$Replay.cache_root) `
        -RepositoryRoot $repoRoot `
        -SourceRoot $SourceRoot `
        -DotnetPath $DotnetExecutable `
        -Label 'ExecutionReplayCacheRoot'
    $executionRoot = Assert-R3SafeRoot `
        -CandidateRoot ([string]$Replay.execution_tree.execution_root) `
        -RepositoryRoot $repoRoot `
        -SourceRoot $SourceRoot `
        -DotnetPath $DotnetExecutable `
        -Label 'ExecutionTreeRoot'
    if (-not (Test-R3SameOrChildPath `
            -Candidate $executionRoot `
            -Parent $cacheRoot)) {
        throw 'R3 execution tree escapes its permit-bound replay cache.'
    }
    if (Test-R3PathsOverlap -Left $executionRoot -Right $OutputRoot) {
        throw 'R3 execution tree overlaps the formal output root.'
    }

    $manifestPath = [System.IO.Path]::GetFullPath(
        [string]$Replay.execution_tree.manifest.external_path)
    if (-not (Test-R3SameOrChildPath `
            -Candidate $manifestPath `
            -Parent $cacheRoot) -or
        (Test-R3SameOrChildPath `
            -Candidate $manifestPath `
            -Parent $executionRoot) -or
        -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'R3 execution-tree manifest has an invalid external path.'
    }
    Assert-R3NoReparsePoint -Path $manifestPath
    $manifestFile = Get-Item -LiteralPath $manifestPath
    if ($manifestFile.Length -ne
            [long]$Replay.execution_tree.manifest.bytes -or
        (Get-Sha256 -Path $manifestPath) -cne
            [string]$Replay.execution_tree.manifest.sha256 -or
        [string]$Replay.execution_tree.manifest.sha256 -cne
            $LockedManifestSha256) {
        throw 'R3 execution-tree manifest differs from permit-bound evidence.'
    }

    $manifest =
        Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath |
            ConvertFrom-Json
    if ($manifest.artifact_type -cne
            'continuous_action_r3_execution_tree_manifest' -or
        $manifest.artifact_version -cne '0.1.0' -or
        [int]$manifest.file_count -lt 1 -or
        [int]$manifest.file_count -ne @($manifest.files).Count -or
        [string]$manifest.assembly_relative_path -notmatch
            '^[^/\\]+\.dll$') {
        throw 'R3 execution-tree manifest structure is invalid.'
    }

    Assert-R3NoReparsePoint -Path $executionRoot
    $treeItems = @(
        Get-ChildItem -LiteralPath $executionRoot -Recurse -Force
    )
    if (@(
            $treeItems |
                Where-Object {
                    ($_.Attributes -band
                        [System.IO.FileAttributes]::ReparsePoint) -ne 0
                }
        ).Count -ne 0) {
        throw 'R3 execution tree contains a reparse point.'
    }
    $actualFiles = @(
        $treeItems |
            Where-Object { -not $_.PSIsContainer } |
            Sort-Object FullName
    )
    if ($actualFiles.Count -ne [int]$manifest.file_count -or
        $actualFiles.Count -ne [int]$Replay.execution_tree.file_count) {
        throw 'R3 execution-tree file count differs from its manifest.'
    }

    $manifestByPath = @{}
    foreach ($entry in @($manifest.files)) {
        $relative = [string]$entry.path
        if ($relative -notmatch '^[^:\\]+(?:/[^:\\]+)*$' -or
            $manifestByPath.ContainsKey($relative)) {
            throw 'R3 execution-tree manifest contains an unsafe file path.'
        }
        $manifestByPath[$relative] = $entry
    }
    $totalBytes = [long]0
    foreach ($file in $actualFiles) {
        $relative =
            $file.FullName.Substring($executionRoot.Length).
                TrimStart('\').Replace('\', '/')
        if (-not $manifestByPath.ContainsKey($relative)) {
            throw "R3 execution tree has an unbound file: $relative"
        }
        $entry = $manifestByPath[$relative]
        if ($file.Length -ne [long]$entry.bytes -or
            (Get-Sha256 -Path $file.FullName) -cne [string]$entry.sha256) {
            throw "R3 execution-tree file differs from its manifest: $relative"
        }
        $totalBytes += $file.Length
    }
    if ($totalBytes -ne [long]$manifest.total_bytes -or
        $totalBytes -ne [long]$Replay.execution_tree.total_bytes) {
        throw 'R3 execution-tree byte count differs from its manifest.'
    }

    $assemblyPath = Get-R3CanonicalPath -Path (
        Join-Path `
            $executionRoot `
            ([string]$manifest.assembly_relative_path).Replace('/', '\')
    )
    if (-not (Test-R3SameOrChildPath `
            -Candidate $assemblyPath `
            -Parent $executionRoot) -or
        $assemblyPath -cne (
            Get-R3CanonicalPath -Path ([string]$Replay.assembly.external_path)
        ) -or
        (Get-Sha256 -Path $assemblyPath) -cne $LockedAssemblySha256 -or
        (Get-Sha256 -Path $assemblyPath) -cne
            [string]$Replay.assembly.sha256) {
        throw 'R3 formal assembly differs from permit-bound readiness.'
    }

    return [pscustomobject]@{
        execution_root = $executionRoot
        assembly_path = $assemblyPath
        assembly_sha256 = $LockedAssemblySha256
        manifest_path = $manifestPath
        manifest_sha256 = $LockedManifestSha256
        file_count = [int]$manifest.file_count
        total_bytes = $totalBytes
    }
}

function Copy-R3VerifiedExecutionTree {
    param(
        [Parameter(Mandatory = $true)] $VerifiedTree,
        [Parameter(Mandatory = $true)][string] $DestinationRoot
    )

    $destination = Get-R3CanonicalPath -Path $DestinationRoot
    if (Test-Path -LiteralPath $destination) {
        throw 'R3 staged execution-tree destination already exists.'
    }
    New-Item -ItemType Directory -Path $destination | Out-Null
    Assert-R3NoReparsePoint -Path $destination
    foreach ($item in @(
            Get-ChildItem -LiteralPath $VerifiedTree.execution_root -Force
        )) {
        Copy-Item `
            -LiteralPath $item.FullName `
            -Destination $destination `
            -Recurse
    }
    Assert-R3NoReparsePoint -Path $destination

    $manifest =
        Get-Content -Raw -Encoding UTF8 -LiteralPath $VerifiedTree.manifest_path |
            ConvertFrom-Json
    $actualFiles = @(
        Get-ChildItem -LiteralPath $destination -Recurse -Force |
            Where-Object { -not $_.PSIsContainer } |
            Sort-Object FullName
    )
    if ($actualFiles.Count -ne [int]$manifest.file_count) {
        throw 'R3 staged execution-tree file count differs from its manifest.'
    }
    $manifestByPath = @{}
    foreach ($entry in @($manifest.files)) {
        $manifestByPath[[string]$entry.path] = $entry
    }
    foreach ($file in $actualFiles) {
        $relative =
            $file.FullName.Substring($destination.Length).
                TrimStart('\').Replace('\', '/')
        if (-not $manifestByPath.ContainsKey($relative)) {
            throw "R3 staged execution tree has an unbound file: $relative"
        }
        $entry = $manifestByPath[$relative]
        if ($file.Length -ne [long]$entry.bytes -or
            (Get-Sha256 -Path $file.FullName) -cne [string]$entry.sha256) {
            throw "R3 staged execution-tree file differs from its manifest: $relative"
        }
    }
    $assemblyPath = Get-R3CanonicalPath -Path (
        Join-Path `
            $destination `
            ([string]$manifest.assembly_relative_path).Replace('/', '\')
    )
    if ((Get-Sha256 -Path $assemblyPath) -cne
            [string]$VerifiedTree.assembly_sha256) {
        throw 'R3 staged formal assembly differs from permit-bound readiness.'
    }
    return [pscustomobject]@{
        execution_root = $destination
        assembly_path = $assemblyPath
        assembly_sha256 = [string]$VerifiedTree.assembly_sha256
    }
}

# Permit first: no source, toolchain, formal input, build cache, or formal
# output path is opened before the shared verifier succeeds.
$resolvedPythonPath = Resolve-FixedPythonRuntime -RequestedPath $PythonPath
$permit = Invoke-ExecutionPermitVerifier `
    -PermitPath $ExecutionPermitPath `
    -PythonExecutablePath $resolvedPythonPath
$executionPermitFull = [System.IO.Path]::GetFullPath($ExecutionPermitPath)
$executionPermitSha256 = [string]$permit.execution_permit_sha256
$predictionSetDigest = [string]$permit.prediction_set_digest
$target = $permit.execution_target

$formalRunnerPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_runner `
    -ExpectedRelativePath $runnerRelativePath
if (-not [string]::Equals(
        [System.IO.Path]::GetFullPath($formalRunnerPath),
        [System.IO.Path]::GetFullPath($PSCommandPath),
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Execution target does not bind the running CA-R3 formal runner.'
}
$formalInputPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.formal_input `
    -ExpectedRelativePath $formalInputRelativePath
$formalInputSha256 = [string]$target.formal_input.sha256
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.build_runner `
    -ExpectedRelativePath $buildRunnerRelativePath
$fixtureSpecPath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.fixture_spec `
    -ExpectedRelativePath $fixtureSpecRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.dependency_lock_set `
    -ExpectedRelativePath $dependencyLockSetRelativePath
$buildEvidencePath = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.support_artifacts.build_list_evidence `
    -ExpectedRelativePath $buildEvidenceRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.test_body `
    -ExpectedRelativePath $testBodyRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.comparator `
    -ExpectedRelativePath $comparatorRelativePath
$null = Resolve-BoundArtifact `
    -RepositoryRoot $repoRoot `
    -Reference $target.raw_trace_schema `
    -ExpectedRelativePath $rawTraceSchemaRelativePath

$sourceFull =
    (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull =
    (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
Assert-Hash -Path $dotnetFull -Expected $expectedDotnetSha256
$layout = Resolve-R3FormalOutputLayout `
    -Mode runner `
    -FormalOutputRoot $FormalOutputRoot `
    -RepositoryRoot $repoRoot `
    -SourceRoot $sourceFull `
    -DotnetPath $dotnetFull `
    -ConfigurationId $ConfigurationId `
    -RepetitionIndex $RepetitionIndex
if (@(Get-R3PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'The dedicated portable dotnet runtime is already in use.'
}

$buildEvidence =
    Get-Content -Raw -Encoding UTF8 -LiteralPath $buildEvidencePath |
        ConvertFrom-Json
$lockedAssemblySha256 =
    [string]$buildEvidence.reproducibility.formal_assembly_sha256
$lockedManifestSha256 =
    [string]$buildEvidence.reproducibility.execution_tree_manifest_sha256
$executionReplayId =
    [string]$buildEvidence.reproducibility.execution_replay_id
if ($buildEvidence.artifact_type -cne
        'continuous_action_r3_build_list_evidence' -or
    $buildEvidence.build_gate_status -cne 'passed' -or
    $buildEvidence.reproducibility.independent_cache_roots -ne $true -or
    $buildEvidence.reproducibility.replay_count -ne 2 -or
    $buildEvidence.reproducibility.byte_identical -ne $true -or
    $executionReplayId -cne 'replay-a' -or
    $lockedAssemblySha256 -cnotmatch '^(?!0{64}$)[0-9a-f]{64}$' -or
    $lockedManifestSha256 -cnotmatch '^(?!0{64}$)[0-9a-f]{64}$') {
    throw 'Permit-bound R3 build evidence is not reproducibility-ready.'
}
$executionReplays = @(
    $buildEvidence.reproducibility.replays |
        Where-Object { $_.replay_id -ceq $executionReplayId }
)
if ($executionReplays.Count -ne 1) {
    throw 'Permit-bound R3 build evidence lacks its unique execution replay.'
}
$executionTree = Assert-R3ExecutionTreeManifest `
    -Replay $executionReplays[0] `
    -LockedAssemblySha256 $lockedAssemblySha256 `
    -LockedManifestSha256 $lockedManifestSha256 `
    -SourceRoot $sourceFull `
    -DotnetExecutable $dotnetFull `
    -OutputRoot $layout.formal_output_root

# The formal input is opened only after permit verification and output-root
# rejection plus execution-tree verification have both succeeded.
$formalInput =
    Get-Content -Raw -Encoding UTF8 -LiteralPath $formalInputPath |
        ConvertFrom-Json
if ($formalInput.run_id -cne $runId -or
    $formalInput.case_id -cne $caseId -or
    $formalInput.formal_input_id -cne 'o.c.0002' -or
    $formalInput.stop_boundary_id -cne 'o.c.0032' -or
    $formalInput.time_base.time_base_id -cne 'o.c.0022' -or
    $formalInput.pre_gate_guard.expected_result_included -ne $false) {
    throw 'Formal input does not match the frozen CA-R3 contract.'
}

$fixtureSpec =
    Get-Content -Raw -Encoding UTF8 -LiteralPath $fixtureSpecPath |
        ConvertFrom-Json
if ($fixtureSpec.repetition_count -ne 2 -or
    $fixtureSpec.controlled_variable.variable_id -cne 'o.c.0001' -or
    $fixtureSpec.stop_boundary_id -cne 'o.c.0032' -or
    $fixtureSpec.time_base_id -cne 'o.c.0022') {
    throw 'Fixture spec identifiers or repetition count are invalid.'
}
$configurationTuple = Get-R3ConfigurationTuple -ConfigurationId $ConfigurationId
$declaredConfigurations = @($fixtureSpec.configurations) +
    @($fixtureSpec.negative_control.configurations)
$declared = @(
    $declaredConfigurations |
        Where-Object { $_.configuration_id -ceq $ConfigurationId }
)
if ($declared.Count -ne 1 -or
    [int]$declared[0].adjudication_delay_ms -ne
        $configurationTuple.adjudication_delay_ms -or
    [bool]$declared[0].hit_animations -ne
        $configurationTuple.hit_animations) {
    throw 'Requested configuration differs from the permit-bound fixture spec.'
}

$systemTemp = Get-R3CanonicalPath -Path ([System.IO.Path]::GetTempPath())
$temporaryRoot = Join-Path `
    $systemTemp `
    ('game-primitives-r3-formal-' + [Guid]::NewGuid().ToString('N'))
$temporaryRoot = Get-R3CanonicalPath -Path $temporaryRoot
if (-not (Test-R3SameOrChildPath `
        -Candidate $temporaryRoot `
        -Parent $systemTemp) -or
    (Test-R3PathsOverlap -Left $temporaryRoot -Right $layout.formal_output_root)) {
    throw 'R3 test scratch root is not an independent owned temp directory.'
}
Assert-R3NoReparsePoint -Path $temporaryRoot

$testResults = Join-Path $temporaryRoot 'test-results'
$processLogs = Join-Path $temporaryRoot 'process-logs'
$processes = New-Object System.Collections.Generic.List[object]
$traceVerification = $null
$traceCreatedByInvocation = $false
$primaryError = $null
$cleanupError = $null
$environmentNames = @(
    'DOTNET_CLI_HOME',
    'NUGET_PACKAGES',
    'TEMP',
    'TMP',
    'DOTNET_SKIP_FIRST_TIME_EXPERIENCE',
    'DOTNET_CLI_TELEMETRY_OPTOUT',
    'DOTNET_NOLOGO',
    'DOTNET_CLI_UI_LANGUAGE',
    'VSLANG',
    'DOTNET_CLI_USE_MSBUILD_SERVER',
    'MSBUILDDISABLENODEREUSE',
    'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
    'GAME_PRIMITIVES_FORMAL_INPUT_SHA256',
    'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
    'GAME_PRIMITIVES_RUN_ID',
    'GAME_PRIMITIVES_CASE_ID',
    'GAME_PRIMITIVES_R3_CONFIGURATION_ID',
    'GAME_PRIMITIVES_R3_OUTPUT_PATH',
    'GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS',
    'GAME_PRIMITIVES_R3_HIT_ANIMATIONS'
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] =
        [System.Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    New-Item -ItemType Directory -Path @(
        $temporaryRoot,
        $testResults,
        $processLogs
    ) | Out-Null
    $stagedExecutionTree = Copy-R3VerifiedExecutionTree `
        -VerifiedTree $executionTree `
        -DestinationRoot (Join-Path $temporaryRoot 'execution-tree')

    [System.Environment]::SetEnvironmentVariable(
        'DOTNET_CLI_HOME',
        (Join-Path $temporaryRoot 'dotnet-home'),
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'NUGET_PACKAGES',
        (Join-Path $temporaryRoot 'nuget-packages'),
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'TEMP',
        (Join-Path $temporaryRoot 'temp'),
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'TMP',
        (Join-Path $temporaryRoot 'temp'),
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'DOTNET_SKIP_FIRST_TIME_EXPERIENCE',
        '1',
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'DOTNET_CLI_TELEMETRY_OPTOUT',
        '1',
        'Process')
    [System.Environment]::SetEnvironmentVariable('DOTNET_NOLOGO', '1', 'Process')
    [System.Environment]::SetEnvironmentVariable(
        'DOTNET_CLI_UI_LANGUAGE',
        'en-US',
        'Process')
    [System.Environment]::SetEnvironmentVariable('VSLANG', '1033', 'Process')
    [System.Environment]::SetEnvironmentVariable(
        'DOTNET_CLI_USE_MSBUILD_SERVER',
        '0',
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'MSBUILDDISABLENODEREUSE',
        '1',
        'Process')

    $version = Invoke-R3ScopedProcess `
        -Step 'verify-formal-dotnet-version' `
        -FilePath $dotnetFull `
        -Arguments @('--version') `
        -WorkingDirectory $temporaryRoot `
        -StandardOutputPath (Join-Path $processLogs 'dotnet-version.stdout') `
        -StandardErrorPath (Join-Path $processLogs 'dotnet-version.stderr') `
        -TimeoutMilliseconds 60000 `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord -List $processes -Record $version
    if ($version.exit_code -ne 0 -or
        $version.stdout.Trim() -cne $expectedSdkVersion) {
        throw 'R3 formal toolchain version differs from the frozen SDK.'
    }

    foreach ($name in @(
            (Split-Path -Parent $layout.trace_path),
            (Split-Path -Parent $layout.runner_log_path)
        )) {
        New-Item -ItemType Directory -Path $name -Force | Out-Null
        Assert-R3NoReparsePoint -Path $name
    }
    if ((Test-Path -LiteralPath $layout.trace_path) -or
        (Test-Path -LiteralPath $layout.runner_log_path)) {
        throw 'R3 fixed output appeared after boundary validation.'
    }

    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256',
        $executionPermitSha256,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_FORMAL_INPUT_SHA256',
        $formalInputSha256,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_PREDICTION_SET_DIGEST',
        $predictionSetDigest,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_RUN_ID',
        $runId,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_CASE_ID',
        $caseId,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_R3_CONFIGURATION_ID',
        $ConfigurationId,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_R3_OUTPUT_PATH',
        $layout.trace_path,
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS',
        $configurationTuple.adjudication_delay_ms.ToString(
            [System.Globalization.CultureInfo]::InvariantCulture),
        'Process')
    [System.Environment]::SetEnvironmentVariable(
        'GAME_PRIMITIVES_R3_HIT_ANIMATIONS',
        $configurationTuple.hit_animations.ToString().ToLowerInvariant(),
        'Process')

    $safeName =
        $ConfigurationId.Replace('.', '-').Replace('_', '-') +
        ('-repetition-{0:0000}' -f $RepetitionIndex)
    $test = Invoke-R3ScopedProcess `
        -Step 'execute-r3-formal-repetition' `
        -FilePath $dotnetFull `
        -Arguments @(
            'vstest',
            $stagedExecutionTree.assembly_path,
            "--Tests:$testFullyQualifiedName",
            "--ResultsDirectory:$testResults",
            "--Logger:trx;LogFileName=$safeName.trx"
        ) `
        -WorkingDirectory $temporaryRoot `
        -StandardOutputPath (Join-Path $processLogs "$safeName.stdout") `
        -StandardErrorPath (Join-Path $processLogs "$safeName.stderr") `
        -TimeoutMilliseconds 600000 `
        -OutputEncoding $utf8NoBom
    Add-ProcessRecord -List $processes -Record $test
    if ($test.exit_code -ne 0) {
        throw "R3 formal test exited with code $($test.exit_code)."
    }
    if (-not (Test-Path -LiteralPath $layout.trace_path -PathType Leaf)) {
        throw 'R3 formal test did not create its fixed raw trace.'
    }
    $traceCreatedByInvocation = $true
    $postExecutionTree = Assert-R3ExecutionTreeManifest `
        -Replay $executionReplays[0] `
        -LockedAssemblySha256 $lockedAssemblySha256 `
        -LockedManifestSha256 $lockedManifestSha256 `
        -SourceRoot $sourceFull `
        -DotnetExecutable $dotnetFull `
        -OutputRoot $layout.formal_output_root
    if ($postExecutionTree.assembly_sha256 -cne
            $executionTree.assembly_sha256 -or
        $postExecutionTree.manifest_sha256 -cne
            $executionTree.manifest_sha256) {
        throw 'R3 execution tree changed during the formal test.'
    }

    $traceVerification = Invoke-RawTraceVerifier `
        -PermitPath $executionPermitFull `
        -TracePath $layout.trace_path `
        -ExpectedConfigurationId $ConfigurationId `
        -PythonExecutablePath $resolvedPythonPath `
        -ProcessRecords $processes
    if ([string]$traceVerification.formal_input.sha256 -cne
        $formalInputSha256) {
        throw 'R3 raw-trace verifier returned the wrong formal-input binding.'
    }

    $trace =
        Get-Content -Raw -Encoding UTF8 -LiteralPath $layout.trace_path |
            ConvertFrom-Json
    if ($trace.run_id -cne $runId -or
        $trace.case_id -cne $caseId -or
        $trace.configuration_id -cne $ConfigurationId -or
        $trace.execution_permit_sha256 -cne $executionPermitSha256 -or
        $trace.formal_input_sha256 -cne $formalInputSha256 -or
        $trace.prediction_set_digest -cne $predictionSetDigest -or
        $trace.input.adjudication_delay_ms -ne
            $configurationTuple.adjudication_delay_ms -or
        $trace.input.hit_animations -ne
            $configurationTuple.hit_animations) {
        throw 'R3 raw trace does not bind the requested configuration.'
    }
}
catch {
    $primaryError = $_
}
finally {
    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable(
            $name,
            $previousEnvironment[$name],
            'Process')
    }
    if ($null -ne $primaryError -and
        $traceCreatedByInvocation -and
        (Test-Path -LiteralPath $layout.trace_path -PathType Leaf)) {
        Remove-Item -LiteralPath $layout.trace_path -Force
    }
    try {
        Remove-R3OwnedTempDirectory `
            -Path $temporaryRoot `
            -SystemTempRoot $systemTemp
    }
    catch {
        $cleanupError = $_
    }
}

if (@(Get-R3PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'Portable dotnet processes remained after R3 formal invocation.'
}
if ($null -ne $primaryError) {
    throw $primaryError
}
if ($null -ne $cleanupError) {
    throw $cleanupError
}

$runnerLog = [ordered]@{
    artifact_type = 'continuous_action_r3_formal_runner_log'
    artifact_version = '0.1.0'
    run_id = $runId
    case_id = $caseId
    configuration_id = $ConfigurationId
    repetition_index = $RepetitionIndex
    execution_permit_sha256 = $executionPermitSha256
    prediction_set_digest = $predictionSetDigest
    formal_input_sha256 = $formalInputSha256
    fixture_spec_sha256 = [string]$target.support_artifacts.fixture_spec.sha256
    build_evidence_sha256 =
        [string]$target.support_artifacts.build_list_evidence.sha256
    binary_sha256 = $executionTree.assembly_sha256
    readiness_binary_sha256 = $lockedAssemblySha256
    locked_binary_matches_readiness = $true
    execution_tree_manifest_sha256 = $executionTree.manifest_sha256
    execution_tree_file_count = $executionTree.file_count
    raw_trace = [ordered]@{
        path = $layout.trace_path.Replace('\', '/')
        sha256 = Get-Sha256 -Path $layout.trace_path
        verification = $traceVerification
    }
    process_records = @($processes | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
    environment_restored = $true
    owned_temp_removed = $true
    comparator_executed = $false
}
[System.IO.File]::WriteAllText(
    $layout.runner_log_path,
    (($runnerLog | ConvertTo-Json -Depth 20) + "`n"),
    $utf8NoBom)

$runnerLog | ConvertTo-Json -Depth 20
