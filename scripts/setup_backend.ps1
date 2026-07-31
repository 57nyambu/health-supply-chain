param(
    [switch]$SkipSeed,
    [switch]$ForceRecreateVenv,
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

Write-Host "== AfyaSync backend setup ==" -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"

$envExamplePath = Join-Path $repoRoot ".env.example"
$envPath = Join-Path $repoRoot ".env"
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
        Write-Host "Created .env from .env.example" -ForegroundColor Yellow
        Write-Host "Update .env values before production use." -ForegroundColor Yellow
    } else {
        Write-Warning ".env.example was not found. Create .env manually."
    }
} else {
    Write-Host ".env already exists"
}

$venvPath = Join-Path $repoRoot $VenvDir
if ($ForceRecreateVenv -and (Test-Path $venvPath)) {
    Write-Host "Removing existing virtual environment: $VenvDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $VenvDir"
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        & py -3 -m venv $VenvDir
    } else {
        $pythonCmd = Get-Command python -ErrorAction Stop
        & $pythonCmd.Source -m venv $VenvDir
    }
} else {
    Write-Host "Using existing virtual environment at $VenvDir"
}

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Could not find venv python executable at $pythonExe"
}

Write-Host "Upgrading pip"
& $pythonExe -m pip install --upgrade pip

$requirementsPath = Join-Path $repoRoot "requirements.txt"
if (-not (Test-Path $requirementsPath)) {
    throw "requirements.txt not found at $requirementsPath"
}

Write-Host "Installing dependencies"
& $pythonExe -m pip install -r $requirementsPath

Write-Host "Running migrations"
& $pythonExe manage.py migrate

if (-not $SkipSeed) {
    Write-Host "Seeding demo facility data"
    & $pythonExe manage.py seed_facility_demo_data
} else {
    Write-Host "Skipping seed step"
}

Write-Host "Running Django system check"
& $pythonExe manage.py check

Write-Host "" 
Write-Host "Backend setup complete." -ForegroundColor Green
Write-Host "To start the API:" -ForegroundColor Green
Write-Host "$pythonExe manage.py runserver"
