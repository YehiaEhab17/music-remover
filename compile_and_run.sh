#!/bin/bash
#todo: change to powershell

rm -rf dist build

pyinstaller --onefile --noupx --paths=. --add-binary ".binaries/ffmpeg.exe;.binaries" --add-binary ".binaries/ffprobe.exe;.binaries" --collect-all torch --copy-metadata torch --add-data ".models:.models" app.py

./dist/app
