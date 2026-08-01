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

$demoPassword = $env:DEMO_PASSWORD
if ([string]::IsNullOrWhiteSpace($demoPassword)) {
  $demoPassword = "AfyaSync@123"
}

$demoAdminEmail = $env:DEMO_ADMIN_EMAIL
if ([string]::IsNullOrWhiteSpace($demoAdminEmail)) {
  $demoAdminEmail = "admin@afyasync.dima.co.ke"
}

$demoFacilityEmail = $env:DEMO_FACILITY_EMAIL
if ([string]::IsNullOrWhiteSpace($demoFacilityEmail)) {
  $demoFacilityEmail = "facility@afyasync.dima.co.ke"
}

$demoReporterEmail = $env:DEMO_REPORTER_EMAIL
if ([string]::IsNullOrWhiteSpace($demoReporterEmail)) {
  $demoReporterEmail = "reporter@afyasync.dima.co.ke"
}

$configPath = Join-Path $PSScriptRoot "..\assets\js\config.js"
@"
window.AFYASYNC_CONFIG = {
  API_BASE_URL: "$apiBaseUrl",
  DEMO_LOGINS: [
    { label: "Admin", email: "$demoAdminEmail", password: "$demoPassword" },
    { label: "Facility", email: "$demoFacilityEmail", password: "$demoPassword" },
    { label: "Reporter", email: "$demoReporterEmail", password: "$demoPassword" },
  ],
};
"@ | Set-Content -Path $configPath -Encoding UTF8

Write-Host "Generated assets/js/config.js with API_BASE_URL=$apiBaseUrl and demo logins"
