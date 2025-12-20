# Remove old build folders
Remove-Item -Recurse -Force dist, build

# Build the app
pyinstaller `
    --onefile `
    --noupx `
    --add-binary "../.binaries/ffmpeg;.binaries" `
    --collect-all torch `
    --collect-all audio_separator `
    --copy-metadata torch `
    --copy-metadata audio_separator `
    ../app.py

# Run the compiled executable
& .\dist\app.exe
