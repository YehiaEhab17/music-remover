#!/bin/bash

rm -rf dist build

pyinstaller \
    --onefile \
    --noupx \
    \
    --add-binary "../.binaries/ffmpeg:.binaries" \
    \
    --collect-all torch \
    --collect-all audio_separator \
    --copy-metadata torch \
    --copy-metadata audio_separator \
    \
    ../app.py

./dist/app
