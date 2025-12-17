# Music Remover - Agent Guidelines

## Development Commands
- **Run application**: `python GUI/app.py`
- **Build executable**: `./compile_and_run.sh`
- **Test CUDA**: `python tests/cuda_test.py`
- **Install dependencies**: `pip install -r requirements.txt`

## Code Style Guidelines
- Follow PEP 8 for import ordering: stdlib → third-party → local imports
- Use 4 spaces for indentation (no tabs)
- Add type hints for function parameters and return values
- Use Path objects from pathlib for file operations
- Handle exceptions with specific error types and meaningful messages

## Project Structure
- `GUI/`: PyQt6 UI components (app.py, main.py, dialog.py)
- `logic/`: Business logic (demucs_utils.py, download.py, ffmpeg_utils.py, temp_utils.py)
- `tests/`: Test files (currently minimal)
- `.binaries/`: FFmpeg binaries
- `.models/`: AI model files

## Key Patterns
- Use QThread for long-running operations (downloads, processing)
- Emit pyqtSignal for progress updates and error handling
- Store user output in Path objects
- Clean temporary files after processing completes

## Notes
- main.py and dialog.py are auto-generated from .ui files - don't edit manually
- FFmpeg path is configured via environment variables (.env)
- GPU acceleration planned but not fully implemented
- Application supports multiple languages (English/Arabic)