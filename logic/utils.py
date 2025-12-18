import sys
from pathlib import Path

from config import GENERIC_ERROR_MESSAGE, ERROR_MESSAGES


def get_temp_path() -> Path:
    temp_dir = get_resource_path(".music_remover_temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path.cwd()

    absolute_path = base_path / relative_path

    return absolute_path


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
    except Exception as e:
        return False, f"Directory validation failed: {str(e)}"
