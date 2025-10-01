#!/bin/bash
# Build script for get_token binary

set -e

echo "Building get_token binary..."
echo

# Check if we're in the right directory
if [ ! -f "get_token.spec" ]; then
    echo "Error: get_token.spec not found. Run this script from src/get_token/"
    exit 1
fi

# Install dependencies if needed
echo "Installing dependencies..."
pip install -q -r requirements.txt
pip install -q pyinstaller

# Build with PyInstaller
echo "Building with PyInstaller..."
pyinstaller get_token.spec

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

