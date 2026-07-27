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
    [string] $CacheRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$frozenCommit = '7eaaad799bb7912625c15af9407c2c67e6305d75'
$expectedOrigin = '^https://github\.com/hifight/Footsies(?:\.git)?/?$'
$expectedDotnetSha256 = 'b9eace03c8471717e3f98873527005dbd9a92367b954f8c48484d2b7b78efbac'
$expectedSdkVersion = '8.0.100'
$expectedPatchSha256 = '8ad1a91f40579f38e3867ba8905b53c0d94749716821a7bf3edf670c998fc9bb'
$expectedBaselineAssetSha256 = '3eb1d810b4070f616dcfe031ccd027604d9a6f799a4fdbc95f1a7e318004702d'
$expectedVariantAssetSha256 = '16230b19cf15d51b93e3c50a7115c39fe9608e4e07e0f98f0b09cbb5691773db'
$controlledAsset = 'Assets/Fighter/F00/F00.asset'
$projectName = 'FootsiesR1Standalone'
$projectFile = 'FootsiesR1Standalone.csproj'
$formalProjectName = 'FootsiesR1Formal'
$formalProjectFile = 'FootsiesR1Formal.csproj'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$expectedSourceHashes = [ordered]@{
    'Assets/Script/Fighter.cs' = 'ff100562dfb7b330a35d42af51cb21edccb6f118e9b512c3fd0a8e62484d3885'
    'Assets/Script/FighterData.cs' = '0a46f53828bcc13fece2ddeb2989fbff20cd02900ada6da6406a148f6eea79b8'
    'Assets/Script/ActionData.cs' = 'cec8787a25727007a73359d97f239f726be6b3006162b23bdc8b1eadea7836ed'
    'Assets/Script/InputData.cs' = 'e7468e13c8ddd2d783113b9e7bc1f2ae63fd6970933fd1fbcac2b7ca20836a6b'
    'Assets/Script/AttackData.cs' = '62d52cd9dc77778f81c46f9890212ec93657ab110b94407662449ec3a68d7a1a'
    'Assets/Script/ActionDataContainer.cs' = '385380bad8aec0b7996d15dc0cd6eb1f74f243b77d2087b03706111f0940c10a'
    'Assets/Script/AttackDataContainer.cs' = 'd46a0960a612ff2fbcb67595e8645e6a24d7d2d031738466333ee796816b7959'
    'Assets/Script/MotionDataContainer.cs' = 'b6970e204ed6f2f34d5ac2a5ee8153ef2ac8aa93108d17c1d134fb00958c01a1'
    'Assets/Fighter/F00/Actions/B_ATTACK.asset' = 'ac51fdc1f7d97e89d6dd0ad687e31f3fa382f2ba2560ef421a60e9a7d9a18e0c'
    'Assets/Fighter/F00/Actions/B_SPECIAL.asset' = 'e0dd0c3cca3f4f60574ecc5d0f84c8366c037a19c407d7808b62789f892d8e2b'
    'Assets/Fighter/F00/Actions/BACKWARD.asset' = 'b9a18a933abecfce8ed50ee43cb42498aafd1b083c7cc46db78bcdf9d5ba445d'
    'Assets/Fighter/F00/Actions/DAMAGE.asset' = 'bb4a4564156bcef05fcb5200e159fae80afb7c86f25ab139c7d392516e292f5d'
    'Assets/Fighter/F00/Actions/DASH_BACKWARD.asset' = 'b34a13cbd988c0f43141add3f20b9bd8ecbca5339d7d73d151027b833532d26b'
    'Assets/Fighter/F00/Actions/DASH_FORWARD.asset' = '0eb87d42b3f70923cacf9949d495ffaab384756d964038fe42f5260316127f6b'
    'Assets/Fighter/F00/Actions/DEAD.asset' = 'ac8ce3335ac5d91ce5e6803666b70508471367ef71be7a8ec56ab8e682817306'
    'Assets/Fighter/F00/Actions/FORWARD.asset' = 'f652a62e245fa35672aaddf12576d6eea79ec9a264651132a42d4de5b801221c'
    'Assets/Fighter/F00/Actions/GUARD_BREAK.asset' = '4f14140a4c6969c1696ea712e437027431537f59707e614cbc8352a6feb8363b'
    'Assets/Fighter/F00/Actions/GUARD_CROUCH.asset' = 'cc8fedc680f17c4396c2f96d707b5db257f6a0821525e0fa47ee8d1742873a88'
    'Assets/Fighter/F00/Actions/GUARD_M.asset' = '9f56804bc1d7628e808063f894dfffdd6696914657bb4ad6533f14ccb9640191'
    'Assets/Fighter/F00/Actions/GUARD_PROXIMITY.asset' = 'acb469c290f97ebbc0edb61a03c95e69fd11679d65936bacd91e59f4284d2054'
    'Assets/Fighter/F00/Actions/GUARD_STAND.asset' = 'c8f88f6d1410bc8385e14c9a5c6f77325b0879582ebd146357eaab5416c1de24'
    'Assets/Fighter/F00/Actions/STAND.asset' = 'd2731601b6d29196eda063ee341ffd5b6abfe84e85ccb87cd22b7eb27410742b'
    'Assets/Fighter/F00/Actions/N_ATTACK.asset' = '214ccb908da225afab9d3e98a01866aafa460f4eae262377328ee3b651b87d89'
    'Assets/Fighter/F00/Actions/N_SPECIAL.asset' = '6f6ec455860147e2915f6e24a74a7aebf07de1086d73f488b88c386c5f254ae8'
    'Assets/Fighter/F00/Actions/WIN.asset' = 'd60a3f9455c69ab230a54c7c1badeed52f1a637bec7dbe9314a0c7c31c6f60eb'
}

$expectedFixtureHashes = [ordered]@{
    'FootsiesR1Standalone.csproj' = '48aa3ceb01298e29f7b4d83582bf3ce9e60f37729e6880f0113b806a3228b1d6'
    'FootsiesR1Formal.csproj' = 'ba39e4d8a7c8c676fd23b66b4cd0d197863bb48b83d2907b57e5647cc8cf4060'
    'NuGet.config' = '5256a7e3e07d2c5c94f7a1e6c45f39aab011c659c5e2d53e452dea525ce04575'
    'UnityCompatibility.cs' = '041c5f88f372dab9956dbad5a03cfee1dff5085aaaaabf4b1137585642536b28'
    'FrozenSourceContract.cs' = '57c0c7ed48de388da0b2fef3e2de6160839a73ecc53b03de9b6270dc37f0d11f'
    'UnityYamlAssetLoader.cs' = 'fe8f55c7ea3e2e5d58eb228e4d8a83a095298c7d7cd2c7e8fd9386a56acb30e4'
    'Program.cs' = '61d09d65adf46eb67eede00ff4e556fff0438d0425b07eccfea3a0a99354eaf1'
    'FormalProgram.cs' = '49c86348f4edbc8b3b9e241dfc80c5f37c69055b0c9698c711b7a1edf4d3f5b1'
}

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string] $Path)
    return [System.IO.Path]::GetFullPath(
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    )
}

function Test-IsSameOrChildPath {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\')
    return $candidateFull.Equals($parentFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $candidateFull.StartsWith($parentFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

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
            throw "$Step received an argument that requires unsupported quoting: $argument"
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
    $startedPid = $process.Id
    $standardOutputTask = $process.StandardOutput.ReadToEndAsync()
    $standardErrorTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutMilliseconds)) {
        Stop-Process -Id $startedPid -Force -ErrorAction SilentlyContinue
        throw "$Step timed out; terminated owned PID $startedPid."
    }
    $standardOutput = $standardOutputTask.GetAwaiter().GetResult()
    $standardError = $standardErrorTask.GetAwaiter().GetResult()
    $exitCode = $process.ExitCode
    [System.IO.File]::WriteAllText($StandardOutputPath, $standardOutput, $utf8NoBom)
    [System.IO.File]::WriteAllText($StandardErrorPath, $standardError, $utf8NoBom)

    $aliveAfter = @(Get-Process -Id $startedPid -ErrorAction SilentlyContinue).Count
    if ($aliveAfter -ne 0) {
        throw "$Step PID $startedPid remained alive after process exit."
    }

    return [pscustomobject]@{
        step = $Step
        pid = $startedPid
        exit_code = $exitCode
        alive_after = $aliveAfter
    }
}

function Invoke-Recorded {
    param(
        [Parameter(Mandatory = $true)][string] $Step,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [int] $TimeoutMilliseconds = 600000
    )

    $stdout = Join-Path $logsPath ($Step + '.stdout')
    $stderr = Join-Path $logsPath ($Step + '.stderr')
    $result = Invoke-TrackedProcess `
        -Step $Step `
        -FilePath $FilePath `
        -Arguments $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -StandardOutputPath $stdout `
        -StandardErrorPath $stderr `
        -TimeoutMilliseconds $TimeoutMilliseconds
    $processes.Add($result)
    return $result
}

function Assert-Success {
    param(
        [Parameter(Mandatory = $true)] $ProcessRecord,
        [Parameter(Mandatory = $true)][string] $Description
    )
    if ($ProcessRecord.exit_code -ne 0) {
        throw "$Description failed with exit code $($ProcessRecord.exit_code)."
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

function Write-Json {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )

    $text = $Value | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($Path, $text + "`n", $utf8NoBom)
}

function Get-EvidenceFile {
    param([Parameter(Mandatory = $true)][string] $Path)
    $item = Get-Item -LiteralPath $Path
    return [ordered]@{
        external_path = $item.FullName.Replace('\', '/')
        bytes = $item.Length
        sha256 = Get-Sha256 -Path $item.FullName
    }
}

function Assert-SmokeResult {
    param(
        [Parameter(Mandatory = $true)] $Value,
        [Parameter(Mandatory = $true)][string] $Configuration,
        [Parameter(Mandatory = $true)][bool] $ControlledValue,
        [Parameter(Mandatory = $true)][string] $AssetSha256
    )

    if ($Value.artifact_type -cne 'continuous_action_r1_synthetic_smoke' -or
        $Value.artifact_version -cne '0.1.0' -or
        $Value.run_id -cne 'continuous-001' -or
        $Value.case_id -cne 'CA-R1' -or
        $Value.source_commit -cne $frozenCommit -or
        $Value.configuration_id -cne $Configuration) {
        throw "Synthetic smoke identity mismatch for $Configuration."
    }
    if ($Value.controlled_asset.path -cne $controlledAsset -or
        $Value.controlled_asset.field -cne 'canCancelOnWhiff' -or
        $Value.controlled_asset.sha256 -cne $AssetSha256 -or
        [bool]$Value.controlled_asset.value -ne $ControlledValue) {
        throw "Synthetic smoke control binding mismatch for $Configuration."
    }
    if ([int]$Value.synthetic_sequence.event_count -ne 6 -or
        -not [bool]$Value.synthetic_sequence.differs_from_formal_event_count -or
        @($Value.synthetic_sequence.inputs).Count -ne 6) {
        throw "Synthetic smoke was not the frozen six-event nonformal sequence."
    }
    $expectedInputs = @(4, 0, 0, 4, 0, 0)
    if (@(Compare-Object -SyncWindow 0 -ReferenceObject $expectedInputs `
                -DifferenceObject @($Value.synthetic_sequence.inputs)).Count -ne 0) {
        throw "Synthetic smoke input values changed for $Configuration."
    }
    if (@($Value.observations).Count -ne 6 -or
        -not [bool]$Value.assertions.branch_assertion_passed -or
        -not [bool]$Value.assertions.source_hashes_verified -or
        -not [bool]$Value.assertions.exact_fighter_source_compiled) {
        throw "Synthetic smoke assertions failed for $Configuration."
    }

    $formal = $Value.formal_execution
    foreach ($property in @(
            'formal_environment_present'
            'formal_input_path_accepted'
            'formal_input_read'
            'formal_input_executed'
            'formal_runner_executed'
            'comparator_executed'
            'formal_result_created')) {
        if ([bool]$formal.$property) {
            throw "Synthetic smoke reported forbidden formal state $property."
        }
    }
}

$sourceFull = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).ProviderPath.TrimEnd('\')
$dotnetFull = (Resolve-Path -LiteralPath $DotnetPath -ErrorAction Stop).ProviderPath
$cacheFull = (Get-FullPath -Path $CacheRoot).TrimEnd('\')
$repoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..\..\..\..')
).ProviderPath.TrimEnd('\')
$standaloneSource = Join-Path $PSScriptRoot 'standalone'
$patchSource = Join-Path $PSScriptRoot 'footsies-r1-whiff-cancel-v0.1.0.patch'

if ($sourceFull -match '\s' -or $cacheFull -match '\s' -or $dotnetFull -match '\s') {
    throw 'SourcePath, DotnetPath, and CacheRoot must not contain whitespace.'
}
if (Test-IsSameOrChildPath -Candidate $cacheFull -Parent $repoRoot) {
    throw 'CacheRoot must be outside the Game Primitives repository.'
}
if ((Test-IsSameOrChildPath -Candidate $cacheFull -Parent $sourceFull) -or
    (Test-IsSameOrChildPath -Candidate $sourceFull -Parent $cacheFull)) {
    throw 'CacheRoot and SourcePath must not overlap.'
}
if (Test-Path -LiteralPath $cacheFull) {
    if (@(Get-ChildItem -LiteralPath $cacheFull -Force).Count -ne 0) {
        throw "CacheRoot must be new or empty: $cacheFull"
    }
}

foreach ($formalEnvironmentName in @(
        'GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256'
        'GAME_PRIMITIVES_FORMAL_INPUT_SHA256'
        'GAME_PRIMITIVES_PREDICTION_SET_DIGEST'
        'GAME_PRIMITIVES_RUN_ID'
        'GAME_PRIMITIVES_CASE_ID')) {
    if (-not [string]::IsNullOrEmpty(
            [System.Environment]::GetEnvironmentVariable($formalEnvironmentName, 'Process'))) {
        throw "Formal environment variable $formalEnvironmentName is forbidden in the synthetic build/smoke probe."
    }
}

Assert-Hash -Path $dotnetFull -Expected $expectedDotnetSha256
Assert-Hash -Path $patchSource -Expected $expectedPatchSha256
foreach ($entry in $expectedFixtureHashes.GetEnumerator()) {
    Assert-Hash -Path (Join-Path $standaloneSource $entry.Key) -Expected $entry.Value
}
if (@(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull).Count -ne 0) {
    throw 'The dedicated portable dotnet runtime is already in use; refusing mixed process ownership.'
}

New-Item -ItemType Directory -Path $cacheFull | Out-Null
$logsPath = Join-Path $cacheFull 'logs'
$baselineSource = Join-Path $cacheFull 'source-baseline'
$variantSource = Join-Path $cacheFull 'source-variant'
$projectPath = Join-Path $cacheFull 'fixture-project'
$artifactsBaseline = Join-Path $cacheFull 'artifacts-baseline'
$artifactsVariant = Join-Path $cacheFull 'artifacts-variant'
$nugetPackages = Join-Path $cacheFull 'nuget-packages'
$dotnetHome = Join-Path $cacheFull 'dotnet-home'
$tempPath = Join-Path $cacheFull 'temp'
New-Item -ItemType Directory -Path $logsPath, $projectPath, $nugetPackages, $dotnetHome, $tempPath | Out-Null
Copy-Item -Path (Join-Path $standaloneSource '*') -Destination $projectPath -Recurse
$patchCopy = Join-Path $cacheFull 'variant.patch'
Copy-Item -LiteralPath $patchSource -Destination $patchCopy
Assert-Hash -Path $patchCopy -Expected $expectedPatchSha256

$processes = New-Object System.Collections.Generic.List[object]
$gitPath = (Get-Command git.exe -ErrorAction Stop | Select-Object -First 1).Source

$sourceCommitResult = Invoke-Recorded `
    -Step 'verify-source-commit' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD^{commit}') `
    -WorkingDirectory $sourceFull
Assert-Success $sourceCommitResult 'Source commit verification'
$resolvedCommit = (Get-Content -Raw -LiteralPath (Join-Path $logsPath 'verify-source-commit.stdout')).Trim()
if ($resolvedCommit -cne $frozenCommit) {
    throw "Frozen source commit mismatch: $resolvedCommit"
}

$originResult = Invoke-Recorded `
    -Step 'verify-source-origin' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'remote', 'get-url', 'origin') `
    -WorkingDirectory $sourceFull
Assert-Success $originResult 'Source origin verification'
$origin = (Get-Content -Raw -LiteralPath (Join-Path $logsPath 'verify-source-origin.stdout')).Trim()
if ($origin -notmatch $expectedOrigin) {
    throw "Source origin is not the frozen official HTTPS remote: $origin"
}

$statusResult = Invoke-Recorded `
    -Step 'verify-source-clean' `
    -FilePath $gitPath `
    -Arguments @('-C', $sourceFull, 'status', '--porcelain=v1', '--untracked-files=all') `
    -WorkingDirectory $sourceFull
Assert-Success $statusResult 'Source worktree verification'
$sourceStatusText = Get-Content -Raw -LiteralPath (
    Join-Path $logsPath 'verify-source-clean.stdout'
)
if (-not [string]::IsNullOrEmpty($sourceStatusText)) {
    throw 'SourcePath must be a clean frozen worktree.'
}

foreach ($entry in $expectedSourceHashes.GetEnumerator()) {
    Assert-Hash `
        -Path (Join-Path $sourceFull $entry.Key.Replace('/', '\')) `
        -Expected $entry.Value
}
Assert-Hash -Path (Join-Path $sourceFull $controlledAsset.Replace('/', '\')) `
    -Expected $expectedBaselineAssetSha256

foreach ($configuration in @(
        [pscustomobject]@{ label = 'baseline'; path = $baselineSource }
        [pscustomobject]@{ label = 'variant'; path = $variantSource })) {
    $cloneResult = Invoke-Recorded `
        -Step ("clone-" + $configuration.label) `
        -FilePath $gitPath `
        -Arguments @('clone', '--shared', '--no-checkout', $sourceFull, $configuration.path) `
        -WorkingDirectory $cacheFull
    Assert-Success $cloneResult ("Clone " + $configuration.label)

    $checkoutResult = Invoke-Recorded `
        -Step ("checkout-" + $configuration.label) `
        -FilePath $gitPath `
        -Arguments @('-C', $configuration.path, 'checkout', '--detach', $frozenCommit) `
        -WorkingDirectory $configuration.path
    Assert-Success $checkoutResult ("Checkout " + $configuration.label)

    foreach ($entry in $expectedSourceHashes.GetEnumerator()) {
        Assert-Hash `
            -Path (Join-Path $configuration.path $entry.Key.Replace('/', '\')) `
            -Expected $entry.Value
    }
}

$patchCheckResult = Invoke-Recorded `
    -Step 'variant-patch-check' `
    -FilePath $gitPath `
    -Arguments @('-C', $variantSource, 'apply', '--check', $patchCopy) `
    -WorkingDirectory $variantSource
Assert-Success $patchCheckResult 'Variant patch check'
$patchApplyResult = Invoke-Recorded `
    -Step 'variant-patch-apply' `
    -FilePath $gitPath `
    -Arguments @('-C', $variantSource, 'apply', $patchCopy) `
    -WorkingDirectory $variantSource
Assert-Success $patchApplyResult 'Variant patch application'

$baselineStatusResult = Invoke-Recorded `
    -Step 'verify-baseline-status' `
    -FilePath $gitPath `
    -Arguments @('-C', $baselineSource, 'status', '--porcelain=v1', '--untracked-files=all') `
    -WorkingDirectory $baselineSource
Assert-Success $baselineStatusResult 'Baseline status verification'
$baselineStatusText = Get-Content -Raw -LiteralPath (
    Join-Path $logsPath 'verify-baseline-status.stdout'
)
if (-not [string]::IsNullOrEmpty($baselineStatusText)) {
    throw 'Prepared baseline checkout is not clean.'
}

$variantStatusResult = Invoke-Recorded `
    -Step 'verify-variant-status' `
    -FilePath $gitPath `
    -Arguments @('-C', $variantSource, 'status', '--porcelain=v1', '--untracked-files=all') `
    -WorkingDirectory $variantSource
Assert-Success $variantStatusResult 'Variant status verification'
$variantStatus = (
    Get-Content -Raw -LiteralPath (Join-Path $logsPath 'verify-variant-status.stdout')
).TrimEnd("`r", "`n")
if ($variantStatus -cne ' M Assets/Fighter/F00/F00.asset') {
    throw "Variant checkout changed an unexpected path: $variantStatus"
}

$variantDiffResult = Invoke-Recorded `
    -Step 'verify-variant-diff' `
    -FilePath $gitPath `
    -Arguments @('-C', $variantSource, 'diff', '--no-ext-diff', '--', $controlledAsset) `
    -WorkingDirectory $variantSource
Assert-Success $variantDiffResult 'Variant diff verification'
$variantDiffText = [System.IO.File]::ReadAllText(
    (Join-Path $logsPath 'verify-variant-diff.stdout')
)
$normalizedVariantDiff = [regex]::Replace(
    $variantDiffText,
    '(?m)^index [0-9a-f]+\.\.[0-9a-f]+ [0-9]+\r?\n',
    ''
)
$expectedPatchText = [System.IO.File]::ReadAllText($patchCopy)
if (-not [string]::Equals(
        $normalizedVariantDiff,
        $expectedPatchText,
        [System.StringComparison]::Ordinal)) {
    throw 'Variant diff differs from the existing frozen one-line patch.'
}

Assert-Hash -Path (Join-Path $baselineSource $controlledAsset.Replace('/', '\')) `
    -Expected $expectedBaselineAssetSha256
Assert-Hash -Path (Join-Path $variantSource $controlledAsset.Replace('/', '\')) `
    -Expected $expectedVariantAssetSha256
foreach ($entry in $expectedSourceHashes.GetEnumerator()) {
    Assert-Hash `
        -Path (Join-Path $variantSource $entry.Key.Replace('/', '\')) `
        -Expected $entry.Value
}

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
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
}

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

$completed = $false
try {
    $versionResult = Invoke-Recorded `
        -Step 'resolve-dotnet-version' `
        -FilePath $dotnetFull `
        -Arguments @('--version') `
        -WorkingDirectory $projectPath
    Assert-Success $versionResult 'Portable SDK version check'
    $resolvedVersion = (
        Get-Content -Raw -LiteralPath (Join-Path $logsPath 'resolve-dotnet-version.stdout')
    ).Trim()
    if ($resolvedVersion -cne $expectedSdkVersion) {
        throw "Portable .NET SDK version mismatch: $resolvedVersion"
    }

    foreach ($build in @(
            [pscustomobject]@{
                label = 'baseline'
                source = $baselineSource
                artifacts = $artifactsBaseline
            }
            [pscustomobject]@{
                label = 'variant'
                source = $variantSource
                artifacts = $artifactsVariant
            })) {
        $restoreResult = Invoke-Recorded `
            -Step ("restore-" + $build.label) `
            -FilePath $dotnetFull `
            -Arguments @(
                'restore'
                $projectFile
                '--configfile'
                'NuGet.config'
                '--packages'
                $nugetPackages
                '-p:UseArtifactsOutput=true'
                "-p:ArtifactsPath=$($build.artifacts)"
                "-p:FootsiesSourceRoot=$($build.source)"
                '-p:UseSharedCompilation=false'
                '-nodeReuse:false'
                '--verbosity'
                'quiet'
            ) `
            -WorkingDirectory $projectPath
        Assert-Success $restoreResult ("Restore " + $build.label)

        $buildResult = Invoke-Recorded `
            -Step ("build-" + $build.label) `
            -FilePath $dotnetFull `
            -Arguments @(
                'build'
                $projectFile
                '--no-restore'
                '--configuration'
                'Release'
                '--artifacts-path'
                $build.artifacts
                "-p:FootsiesSourceRoot=$($build.source)"
                '-p:UseSharedCompilation=false'
                '-nodeReuse:false'
                '--verbosity'
                'minimal'
            ) `
            -WorkingDirectory $projectPath
        Assert-Success $buildResult ("Build " + $build.label)

        $buildText =
            (Get-Content -Raw -LiteralPath (Join-Path $logsPath ("build-" + $build.label + '.stdout'))) +
            (Get-Content -Raw -LiteralPath (Join-Path $logsPath ("build-" + $build.label + '.stderr')))
        if (@([regex]::Matches($buildText, 'warning [A-Z]{2,}[0-9]+')).Count -ne 0) {
            throw "Standalone $($build.label) build produced compiler or analyzer warnings."
        }

        $formalRestoreResult = Invoke-Recorded `
            -Step ("restore-formal-" + $build.label) `
            -FilePath $dotnetFull `
            -Arguments @(
                'restore'
                $formalProjectFile
                '--configfile'
                'NuGet.config'
                '--packages'
                $nugetPackages
                '-p:UseArtifactsOutput=true'
                "-p:ArtifactsPath=$($build.artifacts)"
                "-p:FootsiesSourceRoot=$($build.source)"
                '-p:UseSharedCompilation=false'
                '-nodeReuse:false'
                '--verbosity'
                'quiet'
            ) `
            -WorkingDirectory $projectPath
        Assert-Success $formalRestoreResult ("Formal restore " + $build.label)

        $formalBuildResult = Invoke-Recorded `
            -Step ("build-formal-" + $build.label) `
            -FilePath $dotnetFull `
            -Arguments @(
                'build'
                $formalProjectFile
                '--no-restore'
                '--configuration'
                'Release'
                '--artifacts-path'
                $build.artifacts
                "-p:FootsiesSourceRoot=$($build.source)"
                '-p:UseSharedCompilation=false'
                '-nodeReuse:false'
                '--verbosity'
                'minimal'
            ) `
            -WorkingDirectory $projectPath
        Assert-Success $formalBuildResult ("Formal build " + $build.label)

        $formalBuildText =
            (Get-Content -Raw -LiteralPath (Join-Path $logsPath ("build-formal-" + $build.label + '.stdout'))) +
            (Get-Content -Raw -LiteralPath (Join-Path $logsPath ("build-formal-" + $build.label + '.stderr')))
        if (@([regex]::Matches($formalBuildText, 'warning [A-Z]{2,}[0-9]+')).Count -ne 0) {
            throw "Formal $($build.label) build produced compiler or analyzer warnings."
        }
    }

    $baselineDll = Join-Path $artifactsBaseline "bin\$projectName\release\$projectName.dll"
    $variantDll = Join-Path $artifactsVariant "bin\$projectName\release\$projectName.dll"
    if (-not (Test-Path -LiteralPath $baselineDll) -or
        -not (Test-Path -LiteralPath $variantDll)) {
        throw 'Standalone build did not produce both expected assemblies.'
    }
    $baselineDllHash = Get-Sha256 -Path $baselineDll
    $variantDllHash = Get-Sha256 -Path $variantDll
    $baselineFormalDll = Join-Path $artifactsBaseline "bin\$formalProjectName\release\$formalProjectName.dll"
    $variantFormalDll = Join-Path $artifactsVariant "bin\$formalProjectName\release\$formalProjectName.dll"
    if (-not (Test-Path -LiteralPath $baselineFormalDll) -or
        -not (Test-Path -LiteralPath $variantFormalDll)) {
        throw 'Static build did not produce both permit-bound formal test-body assemblies.'
    }
    $baselineFormalDllHash = Get-Sha256 -Path $baselineFormalDll
    $variantFormalDllHash = Get-Sha256 -Path $variantFormalDll

    $baselineSmokeResult = Invoke-Recorded `
        -Step 'smoke-baseline' `
        -FilePath $dotnetFull `
        -Arguments @(
            $baselineDll
            '--synthetic-smoke'
            '--source-root'
            $baselineSource
            '--configuration'
            'config.baseline'
    ) `
        -WorkingDirectory $cacheFull
    Assert-Success $baselineSmokeResult 'Baseline synthetic smoke'
    $baselineSmokeError = Get-Content -Raw -LiteralPath (
        Join-Path $logsPath 'smoke-baseline.stderr'
    )
    if (-not [string]::IsNullOrEmpty($baselineSmokeError)) {
        throw 'Baseline synthetic smoke wrote to stderr.'
    }

    $variantSmokeResult = Invoke-Recorded `
        -Step 'smoke-variant' `
        -FilePath $dotnetFull `
        -Arguments @(
            $variantDll
            '--synthetic-smoke'
            '--source-root'
            $variantSource
            '--configuration'
            'config.variant'
        ) `
        -WorkingDirectory $cacheFull
    Assert-Success $variantSmokeResult 'Variant synthetic smoke'
    $variantSmokeError = Get-Content -Raw -LiteralPath (
        Join-Path $logsPath 'smoke-variant.stderr'
    )
    if (-not [string]::IsNullOrEmpty($variantSmokeError)) {
        throw 'Variant synthetic smoke wrote to stderr.'
    }

    $baselineSmoke = Get-Content -Raw -LiteralPath (
        Join-Path $logsPath 'smoke-baseline.stdout'
    ) | ConvertFrom-Json
    $variantSmoke = Get-Content -Raw -LiteralPath (
        Join-Path $logsPath 'smoke-variant.stdout'
    ) | ConvertFrom-Json
    Assert-SmokeResult `
        -Value $baselineSmoke `
        -Configuration 'config.baseline' `
        -ControlledValue $false `
        -AssetSha256 $expectedBaselineAssetSha256
    Assert-SmokeResult `
        -Value $variantSmoke `
        -Configuration 'config.variant' `
        -ControlledValue $true `
        -AssetSha256 $expectedVariantAssetSha256

    $completed = $true
}
finally {
    $shutdownResult = Invoke-Recorded `
        -Step 'shutdown-dotnet-build-servers' `
        -FilePath $dotnetFull `
        -Arguments @('build-server', 'shutdown') `
        -WorkingDirectory $projectPath `
        -TimeoutMilliseconds 60000
    Assert-Success $shutdownResult 'Portable build-server shutdown'

    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
}

$remaining = @(Get-PortableDotnetPids -ResolvedDotnetPath $dotnetFull)
if ($remaining.Count -ne 0) {
    throw "Owned portable dotnet processes remained after shutdown: $($remaining -join ', ')"
}
if (-not $completed) {
    throw 'R1 standalone build/synthetic-smoke preparation did not complete.'
}

$logEvidence = @(
    Get-ChildItem -LiteralPath $logsPath -File |
        Sort-Object Name |
        ForEach-Object { Get-EvidenceFile -Path $_.FullName }
)
$sourceHashEvidence = @(
    $expectedSourceHashes.GetEnumerator() |
        ForEach-Object {
            [ordered]@{
                path = $_.Key
                sha256 = $_.Value
            }
        }
)
$fixtureHashEvidence = @(
    $expectedFixtureHashes.GetEnumerator() |
        ForEach-Object {
            [ordered]@{
                path = "standalone/$($_.Key)"
                sha256 = $_.Value
            }
        }
)

$summary = [ordered]@{
    '$schema' = 'https://github.com/onovich/Game-Primitives/blob/main/research/calibration-tests/continuous-action-pilot/schema/r1-standalone-build-evidence-0.1.0.schema.json'
    artifact_type = 'continuous_action_r1_standalone_build_evidence'
    artifact_version = '0.1.0'
    created_at = [DateTime]::UtcNow.ToString('o')
    run_id = 'continuous-001'
    case_id = 'CA-R1'
    build_gate_status = 'passed'
    source = [ordered]@{
        repository_url = 'https://github.com/hifight/Footsies'
        commit = $frozenCommit
        input_checkout_clean = $true
        baseline_checkout_clean = $true
        source_artifacts = $sourceHashEvidence
    }
    controlled_variant = [ordered]@{
        asset_path = $controlledAsset
        field = 'canCancelOnWhiff'
        patch_sha256 = $expectedPatchSha256
        changed_paths = @($controlledAsset)
        baseline_asset_sha256 = $expectedBaselineAssetSha256
        variant_asset_sha256 = $expectedVariantAssetSha256
        baseline_value = $false
        variant_value = $true
    }
    fixture = [ordered]@{
        project = 'standalone/FootsiesR1Standalone.csproj'
        fixture_artifacts = $fixtureHashEvidence
        exact_frozen_fighter_bytes_compiled = $true
        compatibility_layer_contains_rule_logic = $false
        baseline_assembly_sha256 = $baselineDllHash
        variant_assembly_sha256 = $variantDllHash
        baseline_variant_compiled_source_hashes_identical = $true
        formal_project = 'standalone/FootsiesR1Formal.csproj'
        formal_test_body_compiled = $true
        formal_test_body_executed = $false
        baseline_formal_assembly_sha256 = $baselineFormalDllHash
        variant_formal_assembly_sha256 = $variantFormalDllHash
    }
    builds = @(
        [ordered]@{
            configuration_id = 'config.baseline'
            restore_exit_code = 0
            build_exit_code = 0
            formal_restore_exit_code = 0
            formal_build_exit_code = 0
            warning_count = 0
        }
        [ordered]@{
            configuration_id = 'config.variant'
            restore_exit_code = 0
            build_exit_code = 0
            formal_restore_exit_code = 0
            formal_build_exit_code = 0
            warning_count = 0
        }
    )
    synthetic_smoke = [ordered]@{
        event_count = 6
        inputs = @(4, 0, 0, 4, 0, 0)
        differs_from_seven_event_formal_input = $true
        baseline_exit_code = 0
        variant_exit_code = 0
        baseline_branch_assertion_passed = $true
        variant_branch_assertion_passed = $true
    }
    formal_execution = [ordered]@{
        formal_environment_present = $false
        formal_input_path_accepted = $false
        formal_input_read = $false
        formal_input_executed = $false
        formal_runner_executed = $false
        comparator_executed = $false
        authorization_created = $false
        permit_created = $false
        predictions_created = $false
        formal_result_created = $false
    }
    process_records = @($processes | ForEach-Object { $_ })
    portable_dotnet_remaining = @()
    evidence_files = $logEvidence
}

$summaryPath = Join-Path $cacheFull 'build-smoke-evidence.json'
Write-Json -Path $summaryPath -Value $summary
$summary | ConvertTo-Json -Depth 20
