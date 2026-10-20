import json
from pathlib import Path


XDG_CONFIG_DIR = Path.home() / ".config" / "music-remover"
SETTINGS_FILE = XDG_CONFIG_DIR / "settings.json"

DEFAULTS = {
    "gpu_enabled": True,
    "use_tensorrt": False,
    "gpu_threads": 1,
    "chunking_enabled": True,
    "chunk_duration_secs": 60,
    "cpu_threads": 2,
    "retry_failed_chunks": True,
    "default_quality": "720p",
    "default_output_path": "",
    "default_remove_music": True,
    "benchmarking_enabled": False,
}


def load() -> dict:
    settings = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save(settings: dict) -> None:
    XDG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULTS)
    merged.update(settings)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(merged, f, indent=2)
