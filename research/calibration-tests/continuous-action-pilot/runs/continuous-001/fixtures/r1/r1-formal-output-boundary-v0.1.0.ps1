Set-StrictMode -Version Latest

function Get-R1CanonicalPath {
    param([Parameter(Mandatory = $true)][string] $Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

function Test-R1SameOrChildPath {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

    $candidateFull = Get-R1CanonicalPath -Path $Candidate
    $parentFull = Get-R1CanonicalPath -Path $Parent
    return $candidateFull.Equals(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -or $candidateFull.StartsWith(
        $parentFull + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Test-R1PathsOverlap {
    param(
        [Parameter(Mandatory = $true)][string] $Left,
        [Parameter(Mandatory = $true)][string] $Right
    )

    return (Test-R1SameOrChildPath -Candidate $Left -Parent $Right) -or
        (Test-R1SameOrChildPath -Candidate $Right -Parent $Left)
}

function Assert-R1NoReparsePoint {
    param([Parameter(Mandatory = $true)][string] $Path)

    $cursor = Get-R1CanonicalPath -Path $Path
    while (-not [string]::IsNullOrEmpty($cursor)) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Formal output path crosses a reparse point: $cursor"
            }
        }
        $parent = [System.IO.Directory]::GetParent($cursor)
        if ($null -eq $parent -or
            $parent.FullName.Equals(
                $cursor,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            break
        }
        $cursor = $parent.FullName.TrimEnd('\')
    }
}

function Resolve-R1FormalOutputLayout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('runner', 'comparator')]
        [string] $Mode,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $FormalOutputRoot,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $RepositoryRoot,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $SourceRoot,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string] $DotnetPath,

        [ValidateNotNullOrEmpty()]
        [string] $ExpectedFormalOutputRoot = 'D:\GamePrimitivesFormalOutputs',

        [ValidateSet('config.baseline', 'config.variant')]
        [string] $ConfigurationId,

        [ValidateRange(1, 2)]
        [int] $RepetitionIndex
    )

    if (-not [System.IO.Path]::IsPathRooted($FormalOutputRoot)) {
        throw 'FormalOutputRoot must be absolute.'
    }
    $root = Get-R1CanonicalPath -Path $FormalOutputRoot
    $expectedRoot = Get-R1CanonicalPath -Path $ExpectedFormalOutputRoot
    if (-not $root.Equals(
            $expectedRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw "FormalOutputRoot must be exactly $expectedRoot"
    }
    $volumeRoot = [System.IO.Path]::GetPathRoot($root).TrimEnd('\')
    if ($root.Equals($volumeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'FormalOutputRoot must not be a volume root.'
    }
    if ((Test-Path -LiteralPath $root) -and
        -not (Test-Path -LiteralPath $root -PathType Container)) {
        throw 'FormalOutputRoot exists but is not a directory.'
    }

    $repository = Get-R1CanonicalPath -Path $RepositoryRoot
    $source = Get-R1CanonicalPath -Path $SourceRoot
    $dotnet = Get-R1CanonicalPath -Path $DotnetPath
    $toolchain = Get-R1CanonicalPath -Path (Split-Path -Parent $dotnet)
    foreach ($forbidden in @(
            [pscustomobject]@{ label = 'repository'; path = $repository }
            [pscustomobject]@{ label = 'source'; path = $source }
            [pscustomobject]@{ label = 'toolchain'; path = $toolchain }
        )) {
        if (Test-R1PathsOverlap -Left $root -Right $forbidden.path) {
            throw "FormalOutputRoot overlaps the $($forbidden.label) root."
        }
    }

    $caseRoot = Join-Path $root 'continuous-001\CA-R1'
    $baselineRep01 = Join-Path $caseRoot 'raw\config.baseline.rep-01.trace.json'
    $baselineRep02 = Join-Path $caseRoot 'raw\config.baseline.rep-02.trace.json'
    $variantRep01 = Join-Path $caseRoot 'raw\config.variant.rep-01.trace.json'
    $variantRep02 = Join-Path $caseRoot 'raw\config.variant.rep-02.trace.json'
    $baselineLogRep01 = Join-Path $caseRoot 'logs\config.baseline.rep-01.runner-log.json'
    $baselineLogRep02 = Join-Path $caseRoot 'logs\config.baseline.rep-02.runner-log.json'
    $variantLogRep01 = Join-Path $caseRoot 'logs\config.variant.rep-01.runner-log.json'
    $variantLogRep02 = Join-Path $caseRoot 'logs\config.variant.rep-02.runner-log.json'
    $comparison = Join-Path $caseRoot 'comparison\formal-comparator-output.json'
    foreach ($path in @(
            $root,
            (Split-Path -Parent $baselineRep01),
            (Split-Path -Parent $baselineLogRep01),
            (Split-Path -Parent $comparison)
        )) {
        Assert-R1NoReparsePoint -Path $path
    }

    if ($Mode -ceq 'runner') {
        if ([string]::IsNullOrEmpty($ConfigurationId) -or
            $RepetitionIndex -notin @(1, 2)) {
            throw 'Runner output validation requires configuration and repetition 1 or 2.'
        }
        $expectedOutput = if ($ConfigurationId -ceq 'config.baseline' -and
            $RepetitionIndex -eq 1) {
            $baselineRep01
        }
        elseif ($ConfigurationId -ceq 'config.baseline') {
            $baselineRep02
        }
        elseif ($RepetitionIndex -eq 1) {
            $variantRep01
        }
        else {
            $variantRep02
        }
        $expectedLog = if ($ConfigurationId -ceq 'config.baseline' -and
            $RepetitionIndex -eq 1) {
            $baselineLogRep01
        }
        elseif ($ConfigurationId -ceq 'config.baseline') {
            $baselineLogRep02
        }
        elseif ($RepetitionIndex -eq 1) {
            $variantLogRep01
        }
        else {
            $variantLogRep02
        }
        if ((Test-Path -LiteralPath $expectedOutput) -or
            (Test-Path -LiteralPath $expectedLog)) {
            throw 'Runner output or log already exists.'
        }
        return [pscustomobject]@{
            formal_output_root = $root
            case_root = $caseRoot
            repetition_index = $RepetitionIndex
            raw_trace_path = Get-R1CanonicalPath -Path $expectedOutput
            runner_log_path = Get-R1CanonicalPath -Path $expectedLog
        }
    }

    foreach ($trace in @(
            $baselineRep01,
            $baselineRep02,
            $variantRep01,
            $variantRep02
        )) {
        Assert-R1NoReparsePoint -Path $trace
        if (-not (Test-Path -LiteralPath $trace -PathType Leaf)) {
            throw "Comparator requires fixed raw-trace file: $trace"
        }
    }
    if (Test-Path -LiteralPath $comparison) {
        throw 'Comparator output already exists.'
    }
    return [pscustomobject]@{
        formal_output_root = $root
        case_root = $caseRoot
        baseline_rep01_path = Get-R1CanonicalPath -Path $baselineRep01
        baseline_rep02_path = Get-R1CanonicalPath -Path $baselineRep02
        variant_rep01_path = Get-R1CanonicalPath -Path $variantRep01
        variant_rep02_path = Get-R1CanonicalPath -Path $variantRep02
        comparator_output_path = Get-R1CanonicalPath -Path $comparison
    }
}
