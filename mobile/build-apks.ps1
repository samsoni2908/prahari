# SWASTI APK Build Script (PowerShell)
# Builds APKs for Personnel, Commander, and Welfare (Admin excluded)

param (
    [string]$ServerUrl = "https://swasti.up.railway.app",
    [string]$OutputDir = "./dist/apks"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SWASTI - Mobile APK Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Target Server URL: $ServerUrl" -ForegroundColor Yellow
Write-Host "Output Directory:  $OutputDir" -ForegroundColor Yellow
Write-Host ""

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (Get-Command gradlew -ErrorAction SilentlyContinue) {
    Write-Host "[1/3] Building with local Gradle..." -ForegroundColor Green
    Push-Location mobile/android
    ./gradlew assemblePersonnelDebug assembleCommanderDebug assembleWelfareDebug assembleUnifiedDebug -PSERVER_URL="$ServerUrl"
    Copy-Item "app/build/outputs/apk/unified/debug/*.apk" -Destination "../../$OutputDir/swasti-unified.apk" -Force
    Copy-Item "app/build/outputs/apk/personnel/debug/*.apk" -Destination "../../$OutputDir/swasti-personnel.apk" -Force
    Copy-Item "app/build/outputs/apk/commander/debug/*.apk" -Destination "../../$OutputDir/swasti-commander.apk" -Force
    Copy-Item "app/build/outputs/apk/welfare/debug/*.apk" -Destination "../../$OutputDir/swasti-welfare.apk" -Force
    Pop-Location
} else {
    Write-Host "[1/3] Gradle not found on host. Building via Docker container..." -ForegroundColor Green
    $absOut = (Get-Item -Path $OutputDir).FullName
    docker build -f mobile/Dockerfile.apk --build-arg SERVER_URL="$ServerUrl" -t swasti-apk-builder .
    $volMount = $absOut + ":/dist"
    docker run --rm -e SERVER_URL="$ServerUrl" -v $volMount prahari-apk-builder
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Build Complete! Generated APKs:" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Get-ChildItem -Path $OutputDir -Filter "*.apk" | Select-Object Name, Length
