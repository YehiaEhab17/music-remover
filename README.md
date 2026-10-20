# Music Remover

Remove background music from local or YouTube videos using AI source separation.

A PyQt6 desktop app that strips vocals/music from video files, powered by
[audio-separator](https://github.com/nomadkaraoke/python-audio-separator) and the
UVR MDX-Net ONNX model.

## Features

- **Local files**: process one or more video files from disk.
- **YouTube**: paste a link or a playlist; downloads via `yt-dlp`, then removes music.
- **GPU / TensorRT** acceleration options, plus CPU thread and chunking controls.
- **Benchmarking** mode to measure run time per file.
- Auto-cleans temporary files and keeps a log of every run.

## Requirements

- Python 3.x
- `ffmpeg` (bundled under `.binaries/`)

Install Python dependencies:

```bash
pip install -r misc/requirements.txt
```

> `requirements.txt` is the cross-platform base; `requirements_win.txt` adds
> Windows-specific packages.

## Usage

Run the app:

```bash
python app.py
```

Pick a source (From File / From Link / From Playlist), choose an output folder,
and press **Start**. Settings (GPU, TensorRT, chunking, benchmark) are available
from the gear button.

## Tech Stack

- **UI:** PyQt6
- **Separation:** `audio-separator` (UVR MDX-Net / VR models, ONNX)
- **Downloading:** `yt-dlp`
- **Audio/video processing:** `ffmpeg`, `pydub`, `soundfile`

## Structure

```
app.py                entry point + main window
GUI/                  PyQt6 UI (main, link dialog, settings)
logic/                music removal, download, ffmpeg, settings, benchmarking
misc/                 build scripts, requirements, PyInstaller spec
tests/                test suite
```
