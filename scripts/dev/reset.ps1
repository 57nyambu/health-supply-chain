Write-Host "`nChecking all apps for valid migrations folders..." -ForegroundColor Cyan

# Get all subdirectories in the current folder (apps directory)
Get-ChildItem -Directory | ForEach-Object {
    $appPath = $_.FullName
    $migrationsPath = Join-Path $appPath "migrations"
    $initFile = Join-Path $migrationsPath "__init__.py"

    if (-not (Test-Path $migrationsPath)) {
        Write-Host "Creating 'migrations' folder for $($_.Name)..."
        New-Item -Path $migrationsPath -ItemType Directory | Out-Null
    }

    if (-not (Test-Path $initFile)) {
        Write-Host "Creating '__init__.py' in $($_.Name)\migrations..."
        New-Item -Path $initFile -ItemType File | Out-Null
    }
    else {
        Write-Host "'__init__.py' already exists in $($_.Name)\migrations"
    }
}

Write-Host "`nAll apps checked. Migrations folders are ready." -ForegroundColor Green
