#!/bin/bash
set -e

SERVER_URL=${1:-"https://swasti.up.railway.app"}
OUTPUT_DIR=${2:-"./dist/apks"}

echo "=========================================="
echo "   SWASTI — Mobile APK Builder"
echo "=========================================="
echo "Target Server URL: $SERVER_URL"
echo "Output Directory:  $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

if command -v ./gradlew &> /dev/null; then
    echo "[1/3] Building with local Gradle..."
    cd mobile/android
    ./gradlew assemblePersonnelDebug assembleCommanderDebug assembleWelfareDebug assembleUnifiedDebug -PSERVER_URL="$SERVER_URL"
    cp app/build/outputs/apk/unified/debug/*.apk "../../$OUTPUT_DIR/swasti-unified.apk"
    cp app/build/outputs/apk/personnel/debug/*.apk "../../$OUTPUT_DIR/swasti-personnel.apk"
    cp app/build/outputs/apk/commander/debug/*.apk "../../$OUTPUT_DIR/swasti-commander.apk"
    cp app/build/outputs/apk/welfare/debug/*.apk "../../$OUTPUT_DIR/swasti-welfare.apk"
    cd ../..
else
    echo "[1/3] Gradle not found on host. Building via Docker container..."
    docker build -f mobile/Dockerfile.apk --build-arg SERVER_URL="$SERVER_URL" -t swasti-apk-builder .
    docker run --rm -e SERVER_URL="$SERVER_URL" -v "$(pwd)/$OUTPUT_DIR:/dist" prahari-apk-builder
fi

echo ""
echo "=========================================="
echo "   Build Complete! Generated APKs:"
echo "=========================================="
ls -lh "$OUTPUT_DIR"/*.apk 2>/dev/null || echo "Check $OUTPUT_DIR for generated APKs"
