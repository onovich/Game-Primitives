param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("baseline", "variant")]
  [string]$Configuration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rawInput = @(2, 5)
$total = 0
$sampledValues = @()
$steps = @()
$configurationValue = if ($Configuration -eq "baseline") { 0 } else { 1 }

for ($index = 0; $index -lt $rawInput.Count; $index++) {
  $sampledValue = if ($configurationValue -eq 0) {
    $rawInput[$index]
  } else {
    $rawInput[0]
  }

  $before = $total
  $total = $total + $sampledValue
  $sampledValues += $sampledValue
  $steps += [ordered]@{
    step = $index + 1
    raw_value = $rawInput[$index]
    sampled_value = $sampledValue
    total_before = $before
    total_after = $total
  }
}

[ordered]@{
  artifact_type = "rehearsal_fixture_stdout"
  artifact_version = "0.1.0"
  run_id = "rehearsal-001"
  case_id = "CA-R2"
  configuration_id = "config.$Configuration"
  variable_id = "v-q"
  variable_value = $configurationValue
  initial_total = 0
  raw_input = $rawInput
  sampled_values = $sampledValues
  steps = $steps
  stop_boundary_id = "stop.after-step-2"
  total_at_stop = $total
} | ConvertTo-Json -Compress -Depth 8

