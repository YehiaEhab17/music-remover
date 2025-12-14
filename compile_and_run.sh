#!/bin/bash

rm -rf dist build

pyinstaller \
    --onefile \
    --noupx \
    --paths=. \
    \
    --add-binary ".binaries/ffmpeg:.binaries" \
    \
    --collect-all torch \
    --collect-all torchcodec \
    --copy-metadata torch \
    --copy-metadata torchcodec \
    \
    --add-data ".models:.models" \
    GUI/app.py

./dist/app
