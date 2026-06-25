import shutil
import sys
import time
from pathlib import Path
from datetime import datetime

from config import GENERIC_ERROR_MESSAGE, ERROR_MESSAGES, ROOT


def get_temp_path() -> Path:
    temp_dir = Path.home() / ".local" / "share" / "MusicRemover"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def clear_temp_dir(max_age_seconds: float | None = None) -> int:
    """Remove files/subdirs from the temp directory.

    Args:
        max_age_seconds: If set, only remove entries older than this many seconds.
                         If None, remove everything.

    Returns:
        Number of entries removed.
    """
    temp = get_temp_path()
    cutoff = time.time() - max_age_seconds if max_age_seconds is not None else 0
    removed = 0

    for entry in temp.iterdir():
        if entry.name == ".lock":
            continue
        try:
            if max_age_seconds is not None and entry.stat().st_mtime >= cutoff:
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass

    return removed


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = ROOT

    return base_path / relative_path


def get_error_message(error_str: str) -> str:
    """Get user-friendly error message based on error string."""
    error_lower = error_str.lower()

    for error_key, message in ERROR_MESSAGES.items():
        if error_key in error_lower:
            return message

    return GENERIC_ERROR_MESSAGE.format(error_details=error_str)


def validate_output_directory(path: Path) -> tuple[bool, str]:
    """Check if directory is writable."""
    try:
        test_file = path / ".write_test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        return True, "Directory is valid and writable"

    except PermissionError:
        return False, "Permission denied: Cannot write to this directory"
    except OSError as e:
        return False, f"Directory validation failed: {str(e)}"


def create_log() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path.home() / "Documents" / "Logs"
    log_path.mkdir(parents=True, exist_ok=True)
    log_filename = log_path / f"music_remover_{today}.log"

    return log_filename


def log(log_filename: Path, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(log_filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
