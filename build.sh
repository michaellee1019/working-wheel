#!/bin/sh
cd `dirname $0`

# Create a virtual environment to run our code
VENV_NAME="venv"
PYTHON="$VENV_NAME/bin/python"

if ! $PYTHON -m pip install pyinstaller -Uqq; then
    exit 1
fi

# Build with PyInstaller - include all necessary Google API dependencies
$PYTHON -m PyInstaller \
    --onefile \
    --hidden-import="googleapiclient" \
    --hidden-import="google.auth" \
    --hidden-import="google.auth.transport.requests" \
    --hidden-import="google.oauth2.credentials" \
    --hidden-import="google_auth_oauthlib.flow" \
    --hidden-import="googleapiclient.discovery" \
    --collect-all google \
    --collect-all googleapiclient \
    --collect-all google_auth_oauthlib \
    src/main.py

tar -czvf dist/archive.tar.gz meta.json ./dist/main
