# PRAHARI APK Build Script (PowerShell)
# Builds a debug-only unified wrapper for local evaluation. Release APKs use the signed CI workflow.

param (
    [string]$ServerUrl = "https://prahari.up.railway.app",
    [string]$OutputDir = "./dist/apks"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   PRAHARI - Local DEBUG APK Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Target Server URL: $ServerUrl" -ForegroundColor Yellow
Write-Host "Output Directory:  $OutputDir" -ForegroundColor Yellow
Write-Host ""

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (Test-Path -LiteralPath "mobile/android/gradlew.bat") {
    Write-Host "[1/3] Building with local Gradle..." -ForegroundColor Green
    Push-Location mobile/android
    ./gradlew.bat assembleUnifiedDebug -PSERVER_URL="$ServerUrl"
    if ($LASTEXITCODE -ne 0) { throw "Gradle debug build failed" }
    Copy-Item "app/build/outputs/apk/unified/debug/*.apk" -Destination "../../$OutputDir/prahari-unified-debug.apk" -Force
    Pop-Location
} else {
    Write-Host "[1/3] Gradle not found on host. Building via Docker container..." -ForegroundColor Green
    $absOut = (Get-Item -Path $OutputDir).FullName
    docker build -f mobile/Dockerfile.android --build-arg SERVER_URL="$ServerUrl" -t prahari-apk-builder .
    $volMount = $absOut + ":/dist"
    if ($LASTEXITCODE -ne 0) { throw "Docker debug build failed" }
    docker run --rm -e SERVER_URL="$ServerUrl" -v $volMount prahari-apk-builder
    if ($LASTEXITCODE -ne 0) { throw "Docker debug packaging failed" }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   DEBUG build complete (not for distribution):" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Get-ChildItem -Path $OutputDir -Filter "*.apk" | Select-Object Name, Length
