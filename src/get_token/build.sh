#!/bin/bash
# Build script for get_token binary

set -e

echo "Building get_token binary..."
echo

# Check if we're in the right directory
if [ ! -f "__main__.py" ]; then
    echo "Error: __main__.py not found. Run this script from src/get_token/"
    exit 1
fi

# Install dependencies if needed
echo "Installing dependencies..."
pip install -q -r requirements.txt
pip install -q pyinstaller

# Build with PyInstaller
echo "Building with PyInstaller..."
echo

# Check if default_credentials.json exists to bundle it
ADD_DATA=""
if [ -f "default_credentials.json" ]; then
    echo "✓ Found default_credentials.json - will bundle into binary"
    ADD_DATA="--add-data default_credentials.json:."
else
    echo "⚠ No default_credentials.json found - binary will not have bundled credentials"
fi

# Run PyInstaller with options
pyinstaller \
    --onefile \
    --name get_token \
    --console \
    --hidden-import google.auth.transport.requests \
    --hidden-import google.oauth2.credentials \
    --hidden-import google_auth_oauthlib.flow \
    $ADD_DATA \
    __main__.py

# Check if build was successful
if [ -f "dist/get_token" ]; then
    echo
    echo "✓ Build successful!"
    echo "Binary location: dist/get_token"
    echo
    echo "To test:"
    echo "  cd dist"
    echo "  ./get_token"
else
    echo
    echo "✗ Build failed"
    exit 1
fi

