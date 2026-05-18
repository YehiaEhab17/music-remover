#!/bin/bash
set -e

# Define the absolute path to the venv python
V_PY="../venv/bin/python"

# 1. Clean up old build artifacts
rm -rf dist build app.spec

# 2. Run PyInstaller as a module through the venv python
# This ensures it inherits the venv's site-packages and metadata
$V_PY -m PyInstaller \
    --onefile \
    --noupx \
    --add-binary "../.binaries/ffmpeg:.binaries" \
    --add-data "../.models/*:.models" \
    --collect-all torch \
    --collect-all audio_separator \
    --copy-metadata torch \
    --copy-metadata audio_separator \
    ../app.py

# 3. Run the resulting binary
./dist/app