from pathlib import Path
import sys

def get_temp_path():
    temp_dir = get_resource_path(".music_remover_temp")

    temp_dir.mkdir(parents=True, exist_ok=True)

    return temp_dir


def get_resource_path(relative_path : str, return_path=True):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path.cwd().parent

    absolute_path = base_path / relative_path
    if return_path:
        return absolute_path
    else:
        return str(absolute_path)
