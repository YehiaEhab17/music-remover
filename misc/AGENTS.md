# Music Remover - Agent Guidelines

## Development Commands
- **Run application**: `python GUI/app.py`
- **Build executable**: `./compile_and_run.sh`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run all tests**: `python -m pytest tests/` (install pytest if needed)
- **Run single test**: `python -m pytest tests/cuda_test.py -v`
- **Lint code**: `ruff check .` (install ruff if needed)
- **Format code**: `ruff format .` (install ruff if needed)
- **Type check**: `mypy .` (install mypy if needed)

## Code Style Guidelines
- Follow PEP 8: stdlib → third-party → local imports, 4 spaces indentation, 88 char line length
- Add type hints for all function parameters and return values using `typing` module
- Use `pathlib.Path` objects for file operations, never plain strings
- Handle exceptions with specific types; use ERROR_MESSAGES from config.py for user-friendly messages
- Use descriptive names: snake_case for variables/functions, PascalCase for classes
- Prefer f-strings over .format() or % formatting
- Use QThread for async operations with pyqtSignal for progress/error updates
- Clean temporary files after processing; validate paths before use
- Use PyQt6 for GUI components and audio-separator for music removal logic

## Project Structure
- `GUI/`: PyQt6 UI components (app.py, main.py, dialog.py - main.py/dialog.py auto-generated)
- `logic/`: Business logic (download_utils.py, ffmpeg_utils.py, music_removal.py, utils.py)
- `tests/`: Test files (minimal - expand with unit/integration tests)
- `.binaries/`: FFmpeg binaries, `.models/`: AI model files