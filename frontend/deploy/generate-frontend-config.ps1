$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $parts = $_ -split "=", 2
    if ($parts.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim())
    }
  }
}

$apiBaseUrl = $env:API_BASE_URL
if ([string]::IsNullOrWhiteSpace($apiBaseUrl)) {
  $apiBaseUrl = "http://localhost:8000/api/v1"
}

$configPath = Join-Path $PSScriptRoot "..\assets\js\config.js"
@"
window.AFYASYNC_CONFIG = {
  API_BASE_URL: "$apiBaseUrl",
};
"@ | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Generated assets/js/config.js with API_BASE_URL=$apiBaseUrl"
