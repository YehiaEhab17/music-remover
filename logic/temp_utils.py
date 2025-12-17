import sys
from pathlib import Path


def get_temp_path() -> Path:
    temp_dir = get_resource_path(".music_remover_temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path().cwd()

    absolute_path = base_path / relative_path

    return absolute_path
