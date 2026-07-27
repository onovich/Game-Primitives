[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

. (Join-Path $PSScriptRoot 'r1-formal-output-boundary-v0.1.0.ps1')

function Expect-Rejection {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][scriptblock] $Action
    )

    try {
        & $Action
    }
    catch {
        return [pscustomobject]@{
            negative_control = $Name
            passed = $true
            message = $_.Exception.Message
        }
    }
    throw "Negative control unexpectedly succeeded: $Name"
}

$systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$scratch = Join-Path $systemTemp (
    'game-primitives-r1-output-boundary-' + [Guid]::NewGuid().ToString('N')
)
$scratch = [System.IO.Path]::GetFullPath($scratch)
$junctionPath = $null
if (-not $scratch.StartsWith(
        $systemTemp,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'Output-boundary self-test escaped the system temp directory.'
}

try {
    $repository = Join-Path $scratch 'repository'
    $source = Join-Path $scratch 'source'
    $toolchain = Join-Path $scratch 'toolchain'
    $dotnet = Join-Path $toolchain 'dotnet.exe'
    $outputRoot = Join-Path $scratch 'formal-output'
    $junctionTarget = Join-Path $scratch 'escaped-target'
    $junctionPath = Join-Path $scratch 'formal-output-junction'
    New-Item -ItemType Directory -Path $repository, $source, $toolchain | Out-Null
    New-Item -ItemType Directory -Path $junctionTarget | Out-Null
    New-Item -ItemType Junction -Path $junctionPath -Target $junctionTarget |
        Out-Null
    [System.IO.File]::WriteAllBytes($dotnet, [byte[]](0))

    $baselineRep01 = Join-Path $outputRoot (
        'continuous-001\CA-R1\raw\config.baseline.rep-01.trace.json'
    )
    $baselineRep02 = Join-Path $outputRoot (
        'continuous-001\CA-R1\raw\config.baseline.rep-02.trace.json'
    )
    $variantRep01 = Join-Path $outputRoot (
        'continuous-001\CA-R1\raw\config.variant.rep-01.trace.json'
    )
    $variantRep02 = Join-Path $outputRoot (
        'continuous-001\CA-R1\raw\config.variant.rep-02.trace.json'
    )
    $comparison = Join-Path $outputRoot (
        'continuous-001\CA-R1\comparison\formal-comparator-output.json'
    )

    $positive = Resolve-R1FormalOutputLayout `
        -Mode runner `
        -FormalOutputRoot $outputRoot `
        -ExpectedFormalOutputRoot $outputRoot `
        -RepositoryRoot $repository `
        -SourceRoot $source `
        -DotnetPath $dotnet `
        -ConfigurationId config.baseline `
        -RepetitionIndex 1

    $negatives = @(
        Expect-Rejection -Name 'repository_overlap' -Action {
            Resolve-R1FormalOutputLayout `
                -Mode runner `
                -FormalOutputRoot $repository `
                -ExpectedFormalOutputRoot $repository `
                -RepositoryRoot $repository `
                -SourceRoot $source `
                -DotnetPath $dotnet `
                -ConfigurationId config.baseline `
                -RepetitionIndex 1
        }
        Expect-Rejection -Name 'source_overlap' -Action {
            Resolve-R1FormalOutputLayout `
                -Mode runner `
                -FormalOutputRoot $source `
                -ExpectedFormalOutputRoot $source `
                -RepositoryRoot $repository `
                -SourceRoot $source `
                -DotnetPath $dotnet `
                -ConfigurationId config.baseline `
                -RepetitionIndex 1
        }
        Expect-Rejection -Name 'toolchain_overlap' -Action {
            Resolve-R1FormalOutputLayout `
                -Mode runner `
                -FormalOutputRoot $toolchain `
                -ExpectedFormalOutputRoot $toolchain `
                -RepositoryRoot $repository `
                -SourceRoot $source `
                -DotnetPath $dotnet `
                -ConfigurationId config.baseline `
                -RepetitionIndex 1
        }
        Expect-Rejection -Name 'reparse_escape' -Action {
            Resolve-R1FormalOutputLayout `
                -Mode runner `
                -FormalOutputRoot $junctionPath `
                -ExpectedFormalOutputRoot $junctionPath `
                -RepositoryRoot $repository `
                -SourceRoot $source `
                -DotnetPath $dotnet `
                -ConfigurationId config.baseline `
                -RepetitionIndex 1
        }
        Expect-Rejection -Name 'unexpected_root' -Action {
            Resolve-R1FormalOutputLayout `
                -Mode runner `
                -FormalOutputRoot $outputRoot `
                -ExpectedFormalOutputRoot (Join-Path $scratch 'different-root') `
                -RepositoryRoot $repository `
                -SourceRoot $source `
                -DotnetPath $dotnet `
                -ConfigurationId config.baseline `
                -RepetitionIndex 1
        }
    )

    New-Item -ItemType Directory -Path (Split-Path -Parent $baselineRep01) -Force |
        Out-Null
    [System.IO.File]::WriteAllText($baselineRep01, "{}")
    $negatives += Expect-Rejection -Name 'overwrite' -Action {
        Resolve-R1FormalOutputLayout `
            -Mode runner `
            -FormalOutputRoot $outputRoot `
            -ExpectedFormalOutputRoot $outputRoot `
            -RepositoryRoot $repository `
            -SourceRoot $source `
            -DotnetPath $dotnet `
            -ConfigurationId config.baseline `
            -RepetitionIndex 1
    }

    [System.IO.File]::WriteAllText($baselineRep02, "{}")
    [System.IO.File]::WriteAllText($variantRep01, "{}")
    [System.IO.File]::WriteAllText($variantRep02, "{}")
    $comparator = Resolve-R1FormalOutputLayout `
        -Mode comparator `
        -FormalOutputRoot $outputRoot `
        -ExpectedFormalOutputRoot $outputRoot `
        -RepositoryRoot $repository `
        -SourceRoot $source `
        -DotnetPath $dotnet

    [ordered]@{
        artifact_type = 'continuous_action_r1_output_boundary_self_test'
        artifact_version = '0.1.0'
        run_id = 'continuous-001'
        case_id = 'CA-R1'
        status = 'passed'
        runner_positive_path = $positive.raw_trace_path.Replace('\', '/')
        comparator_positive_path = $comparator.comparator_output_path.Replace('\', '/')
        negative_controls = @($negatives)
        formal_input_read = $false
        formal_input_executed = $false
        formal_runner_executed = $false
        comparator_executed = $false
    } | ConvertTo-Json -Depth 8 -Compress
}
finally {
    if ($null -ne $junctionPath -and
        (Test-Path -LiteralPath $junctionPath)) {
        Remove-Item -LiteralPath $junctionPath -Force
    }
    if (Test-Path -LiteralPath $scratch) {
        $resolved = (Get-Item -LiteralPath $scratch -Force).FullName
        if (-not $resolved.StartsWith(
                $systemTemp,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            throw 'Refusing to remove output-boundary self-test outside system temp.'
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
