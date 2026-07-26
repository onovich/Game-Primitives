[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$VcVarsPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This runner is intentionally incapable of accepting movement inputs. It
# builds the byte-frozen neutral harness and invokes it once with no arguments.
# Formal 25 x 8 ms trajectories and input-variable matrices are out of scope.

$expectedCommit = 'dbe4ddb10315479fc00086f08e25d968b4b43c49'
$expectedRemote = 'https://github.com/id-Software/Quake-III-Arena.git'
$expectedToolset = '14.50.35717'
$expectedCompiler = '19.50.35723'
$expectedHarnessHash = '28BA4E1F7B256533EA240D44E7FAA8D614BD780EFEEACCA6DACDF9914E05315D'
$expectedSourceHashes = [ordered]@{
    'code\game\bg_pmove.c'   = '3CED04AED8686D3DA051887DC8C4ACE88A24B45A6D0BB4E4D5238CD53CB7A7FC'
    'code\game\bg_slidemove.c' = '327FA83A0C523DA8A7E8B4FBBBBA40CF8870A28613459289EF0E8A865E6BD903'
    'code\game\q_math.c'      = '0BCA11954EFA4741C53C5B49492BF671FCBFC70925FD7DCCA09C7AB0D7FF0C29'
    'code\game\q_shared.h'    = '7C356992D3F8B722EEB0160C44A0515BD5A83538FFB86190CA138E352E874115'
    'code\game\bg_public.h'   = '29679E04BA6F0F730C5CA200410330E057609DA59E563E36D101F329FAFD09E7'
    'code\game\bg_local.h'    = '1F8953894410D670367A0BC68A687C4F27958F825E4987B6FCD2F77CA0D40FB1'
}
$expectedMarkers = @(
    'FP_ENV_PASS',
    'ABI_PACKING_PASS',
    'SNAPVECTOR_PASS',
    'EVENT_STUB_PASS',
    'EMPTY_WORLD_PASS',
    'NEUTRAL_PMOVE_PASS',
    'SMOKE_PASS'
)
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$scriptDirectory = Split-Path -Parent $PSCommandPath
$repositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $scriptDirectory '..\..\..\..\..\..\..')
)
$harnessPath = Join-Path $scriptDirectory 'q3-neutral-harness-v0.1.0.c'

function Get-FullExplicitPath {
    param(
        [string]$Value,
        [string]$Label
    )
    if (-not [System.IO.Path]::IsPathRooted($Value)) {
        throw "$Label must be an absolute path."
    }
    return [System.IO.Path]::GetFullPath($Value)
}

function Test-PathWithin {
    param(
        [string]$Candidate,
        [string]$Parent
    )
    $separator = [System.IO.Path]::DirectorySeparatorChar
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\', '/')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')
    return $candidateFull.Equals(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or $candidateFull.StartsWith(
        $parentFull + $separator,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Write-LfText {
    param(
        [string]$Path,
        [string]$Text
    )
    $normalized = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
}

function Write-LfLines {
    param(
        [string]$Path,
        [string[]]$Lines
    )
    $text = ''
    if ($Lines.Count -gt 0) {
        $text = ($Lines -join "`n") + "`n"
    }
    Write-LfText -Path $Path -Text $text
}

function Add-RunLog {
    param([string]$Text)
    [System.IO.File]::AppendAllText($script:runLog, "$Text`n", $utf8NoBom)
}

function Format-CommandArgument {
    param([string]$Argument)
    if ($Argument -match '[\s"&|<>^]') {
        return '"' + ($Argument -replace '"', '\"') + '"'
    }
    return $Argument
}

function Invoke-Captured {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPath,
        [string]$WorkingDirectory
    )

    $display = @((Format-CommandArgument $FilePath))
    foreach ($argument in $Arguments) {
        $display += Format-CommandArgument $argument
    }
    Add-RunLog ('COMMAND=' + ($display -join ' '))
    Add-RunLog "OUTPUT=$LogPath"

    $savedErrorAction = $ErrorActionPreference
    $capturedLines = @()
    $exitCode = -1
    Push-Location -LiteralPath $WorkingDirectory
    try {
        $ErrorActionPreference = 'Continue'
        $rawLines = @(& $FilePath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
        foreach ($line in $rawLines) {
            $capturedLines += $line.ToString()
        }
    } finally {
        $ErrorActionPreference = $savedErrorAction
        Pop-Location
    }

    Write-LfLines -Path $LogPath -Lines $capturedLines
    Add-RunLog "EXIT_CODE=$exitCode"
    return [pscustomobject]@{
        ExitCode = $exitCode
        Lines = $capturedLines
    }
}

function Assert-CommandPassed {
    param(
        [object]$Result,
        [string]$Label
    )
    if ($Result.ExitCode -ne 0) {
        throw "$Label failed with exit code $($Result.ExitCode)."
    }
}

$sourceFull = Get-FullExplicitPath -Value $SourcePath -Label 'SourcePath'
$outputFull = Get-FullExplicitPath -Value $OutputPath -Label 'OutputPath'
$vcvarsFull = Get-FullExplicitPath -Value $VcVarsPath -Label 'VcVarsPath'

if (-not (Test-Path -LiteralPath $sourceFull -PathType Container)) {
    throw "SourcePath is not a directory: $sourceFull"
}
if (-not (Test-Path -LiteralPath $vcvarsFull -PathType Leaf)) {
    throw "VcVarsPath is not a file: $vcvarsFull"
}
if (-not (Test-Path -LiteralPath $harnessPath -PathType Leaf)) {
    throw "Frozen harness is missing: $harnessPath"
}
if (Test-Path -LiteralPath $outputFull) {
    throw "OutputPath must be new and absent: $outputFull"
}
if (Test-PathWithin -Candidate $outputFull -Parent $repositoryRoot) {
    throw 'OutputPath must be outside the Game Primitives repository.'
}
if (Test-PathWithin -Candidate $outputFull -Parent $sourceFull) {
    throw 'OutputPath must not be inside the frozen source checkout.'
}

New-Item -ItemType Directory -Path $outputFull | Out-Null
$runLog = Join-Path $outputFull 'probe-run.log'
Write-LfText -Path $runLog -Text (
    "Q3 repo-local neutral compatibility probe`n" +
    "UTC_START=$([DateTime]::UtcNow.ToString('o'))`n" +
    "EXPECTED_COMMIT=$expectedCommit`n" +
    "FORMAL_TRAJECTORY=FORBIDDEN`n"
)

try {
    $harnessHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $harnessPath).Hash
    if ($harnessHash -ne $expectedHarnessHash) {
        throw 'Frozen harness SHA-256 mismatch; formal execution remains forbidden.'
    }
    Add-RunLog "HARNESS_SHA256=$harnessHash"

    $originResult = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'remote', 'get-url', 'origin') `
        -LogPath (Join-Path $outputFull 'source-origin.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $originResult 'Source origin check'
    if ($originResult.Lines.Count -ne 1 -or
        $originResult.Lines[0].Trim() -ne $expectedRemote) {
        throw 'Source origin is not the frozen official repository.'
    }

    $headResult = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'rev-parse', 'HEAD') `
        -LogPath (Join-Path $outputFull 'source-head.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $headResult 'Source HEAD check'
    if ($headResult.Lines.Count -ne 1 -or
        $headResult.Lines[0].Trim() -ne $expectedCommit) {
        throw 'Source checkout is not at the frozen commit.'
    }

    $statusBefore = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @(
            '-C',
            $sourceFull,
            'status',
            '--porcelain=v1',
            '--untracked-files=all'
        ) `
        -LogPath (Join-Path $outputFull 'source-status-before.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $statusBefore 'Source status check'
    if ($statusBefore.Lines.Count -ne 0) {
        throw 'Source checkout is dirty; probe refused.'
    }

    $diffBefore = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'diff', '--exit-code') `
        -LogPath (Join-Path $outputFull 'source-diff-before.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $diffBefore 'Unstaged source diff check'

    $cachedDiffBefore = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @('-C', $sourceFull, 'diff', '--cached', '--exit-code') `
        -LogPath (Join-Path $outputFull 'source-cached-diff-before.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $cachedDiffBefore 'Staged source diff check'

    $sourceHashLines = @()
    foreach ($relativePath in $expectedSourceHashes.Keys) {
        $absolutePath = Join-Path $sourceFull $relativePath
        if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
            throw "Frozen source file is missing: $relativePath"
        }
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $absolutePath).Hash
        if ($actualHash -ne $expectedSourceHashes[$relativePath]) {
            throw "Frozen source SHA-256 mismatch: $relativePath"
        }
        $sourceHashLines += "$actualHash  $relativePath"
    }
    Write-LfLines `
        -Path (Join-Path $outputFull 'source-sha256.log') `
        -Lines $sourceHashLines

    Add-RunLog (
        'COMMAND=' +
        (Format-CommandArgument $env:ComSpec) +
        ' /d /s /c ' +
        (Format-CommandArgument "`"$vcvarsFull`" >nul && set")
    )
    Add-RunLog ('OUTPUT=' + (Join-Path $outputFull 'vcvars64.log'))
    $savedErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $environmentLines = @(
            & $env:ComSpec /d /s /c "`"$vcvarsFull`" >nul && set" 2>&1
        )
        $vcvarsExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorAction
    }
    Add-RunLog "EXIT_CODE=$vcvarsExit"
    if ($vcvarsExit -ne 0) {
        throw "vcvars64 failed with exit code $vcvarsExit."
    }
    foreach ($lineValue in $environmentLines) {
        $line = $lineValue.ToString()
        if ($line -match '^([^=][^=]*)=(.*)$') {
            Set-Item -Path ('Env:' + $matches[1]) -Value $matches[2]
        }
    }
    if (-not $env:VCToolsVersion -or
        $env:VCToolsVersion.TrimEnd('\') -ne $expectedToolset) {
        throw 'vcvars64 selected an unexpected MSVC toolset.'
    }
    if ($env:VSCMD_ARG_TGT_ARCH -ne 'x64') {
        throw 'vcvars64 did not select x64.'
    }
    Write-LfText `
        -Path (Join-Path $outputFull 'vcvars64.log') `
        -Text "VCVARS64_PASS`nMSVC_TOOLSET_PASS`nTARGET_X64_PASS`n"

    $compilerPath = Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe'
    if (-not (Test-Path -LiteralPath $compilerPath -PathType Leaf)) {
        throw "MSVC compiler is missing: $compilerPath"
    }
    $gamePath = Join-Path $sourceFull 'code\game'
    $executablePath = Join-Path $outputFull 'q3-neutral-probe-v0.1.0.exe'
    $compileArguments = @(
        '/nologo',
        '/Bv',
        '/TC',
        '/Od',
        '/W4',
        '/fp:precise',
        '/DWIN32',
        "/I$gamePath",
        $harnessPath,
        (Join-Path $gamePath 'bg_pmove.c'),
        (Join-Path $gamePath 'bg_slidemove.c'),
        (Join-Path $gamePath 'q_math.c'),
        "/Fe$executablePath",
        '/link',
        '/INCREMENTAL:NO'
    )
    $buildResult = Invoke-Captured `
        -FilePath $compilerPath `
        -Arguments $compileArguments `
        -LogPath (Join-Path $outputFull 'build.log') `
        -WorkingDirectory $outputFull

    $warningLines = @(
        $buildResult.Lines |
        Where-Object { $_ -match '(?i)\bwarning\s+[A-Z]+\d+\s*:' }
    )
    if ($warningLines.Count -eq 0) {
        $warningLines = @('COMPATIBILITY_WARNINGS=NONE')
    }
    Write-LfLines `
        -Path (Join-Path $outputFull 'compatibility-warnings.log') `
        -Lines $warningLines

    Assert-CommandPassed $buildResult 'MSVC x64 build'
    if (-not ($buildResult.Lines -match [regex]::Escape($expectedCompiler))) {
        throw 'Build log does not identify the frozen compiler version.'
    }
    if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
        throw 'Expected neutral probe executable was not produced.'
    }
    Add-RunLog 'BUILD=PASS'

    $smokeResult = Invoke-Captured `
        -FilePath $executablePath `
        -Arguments @() `
        -LogPath (Join-Path $outputFull 'smoke.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $smokeResult 'Zero-input neutral smoke'

    $actualMarkers = @(
        $smokeResult.Lines |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -ne '' }
    )
    if ($actualMarkers.Count -ne $expectedMarkers.Count) {
        throw 'Smoke marker count mismatch; formal execution remains forbidden.'
    }
    for ($index = 0; $index -lt $expectedMarkers.Count; $index++) {
        if ($actualMarkers[$index] -ne $expectedMarkers[$index]) {
            throw 'Smoke marker mismatch; formal execution remains forbidden.'
        }
    }
    Add-RunLog 'SMOKE=PASS'

    $statusAfter = Invoke-Captured `
        -FilePath 'git.exe' `
        -Arguments @(
            '-C',
            $sourceFull,
            'status',
            '--porcelain=v1',
            '--untracked-files=all'
        ) `
        -LogPath (Join-Path $outputFull 'source-status-after.log') `
        -WorkingDirectory $outputFull
    Assert-CommandPassed $statusAfter 'Post-smoke source status check'
    if ($statusAfter.Lines.Count -ne 0) {
        throw 'Frozen source changed during the probe.'
    }

    $processName = [System.IO.Path]::GetFileNameWithoutExtension($executablePath)
    $residual = @(Get-Process -Name $processName -ErrorAction SilentlyContinue)
    if ($residual.Count -ne 0) {
        Add-RunLog 'RESIDUAL_PROCESS=FAIL'
        throw 'Neutral probe process remains running.'
    }
    Add-RunLog 'RESIDUAL_PROCESS=NONE'
    Add-RunLog 'VERDICT=PASS'
    Add-RunLog "UTC_END=$([DateTime]::UtcNow.ToString('o'))"

    $manifestPaths = @(
        $harnessPath,
        $PSCommandPath,
        $executablePath,
        (Join-Path $outputFull 'build.log'),
        (Join-Path $outputFull 'smoke.log'),
        (Join-Path $outputFull 'probe-run.log'),
        (Join-Path $outputFull 'source-origin.log'),
        (Join-Path $outputFull 'source-head.log'),
        (Join-Path $outputFull 'source-status-before.log'),
        (Join-Path $outputFull 'source-diff-before.log'),
        (Join-Path $outputFull 'source-cached-diff-before.log'),
        (Join-Path $outputFull 'source-sha256.log'),
        (Join-Path $outputFull 'vcvars64.log'),
        (Join-Path $outputFull 'compatibility-warnings.log'),
        (Join-Path $outputFull 'source-status-after.log')
    )
    foreach ($relativePath in $expectedSourceHashes.Keys) {
        $manifestPaths += Join-Path $sourceFull $relativePath
    }

    $manifestLines = @()
    foreach ($manifestPath in ($manifestPaths | Select-Object -Unique)) {
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath
        $manifestLines += "$($hash.Hash)  $manifestPath"
    }
    Write-LfLines `
        -Path (Join-Path $outputFull 'sha256-manifest.txt') `
        -Lines $manifestLines

    Write-Output 'BUILD_PASS'
    Write-Output 'SMOKE_PASS'
    Write-Output 'EVIDENCE_PASS'
    exit 0
} catch {
    Add-RunLog ('ERROR=' + $_.Exception.Message)
    Add-RunLog 'VERDICT=FAIL'
    Add-RunLog "UTC_END=$([DateTime]::UtcNow.ToString('o'))"
    Write-Error $_
    exit 1
}
