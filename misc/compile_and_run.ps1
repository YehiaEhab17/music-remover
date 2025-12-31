# Remove old build folders
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# Build the app
pyinstaller `
    --onefile `
    --noupx `
    --add-binary "../.binaries/ffmpeg.exe;.binaries" `
    --add-data "../.models/*;.models" `
    --collect-all torch `
    --collect-all audio_separator `
    --copy-metadata torch `
    --copy-metadata audio_separator `
    ..\app.py

# Run the compiled executable
& .\dist\app.exe
