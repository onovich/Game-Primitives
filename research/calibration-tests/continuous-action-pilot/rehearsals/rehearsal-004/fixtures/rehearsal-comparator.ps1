param(
  [Parameter(Mandatory = $true)]
  [int]$BaselineTotal,

  [Parameter(Mandatory = $true)]
  [int]$VariantTotal
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[ordered]@{
  artifact_type = "rehearsal_comparator_stdout"
  artifact_version = "0.1.0"
  run_id = "rehearsal-004"
  case_id = "CA-R2"
  comparator_id = "comparator.exact-total"
  observation_id = "obs.total-at-stop"
  baseline_total = $BaselineTotal
  variant_total = $VariantTotal
  comparison = if ($BaselineTotal -eq $VariantTotal) { "equal" } else { "different" }
} | ConvertTo-Json -Compress

