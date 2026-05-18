import os
import stat
import json
import time
import urllib.request
from pathlib import Path

from config import ROOT

BIN_DIR = ROOT / ".binaries"
BIN_DIR.mkdir(parents=True, exist_ok=True)

if os.name == "nt":
    YTDLP_BIN_NAME = "yt-dlp.exe"
    YTDLP_URL = "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp.exe"
elif os.name == "posix":
    # Darwin (macOS) vs Linux
    import platform

    if platform.system() == "Darwin":
        YTDLP_BIN_NAME = "yt-dlp_macos"
        YTDLP_URL = "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp_macos"
    else:
        YTDLP_BIN_NAME = "yt-dlp"
        YTDLP_URL = "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp_linux"
else:
    YTDLP_BIN_NAME = "yt-dlp"
    YTDLP_URL = (
        "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp"
    )

YTDLP_PATH = BIN_DIR / YTDLP_BIN_NAME
VERSION_FILE = BIN_DIR / "yt-dlp-version.txt"


def get_ytdlp_path() -> Path:
    return YTDLP_PATH


def get_latest_ytdlp_version() -> str:
    """Gets the latest yt-dlp nightly version tag from GitHub."""
    try:
        # A HEAD request is faster, but urlopen handles redirects natively
        req = urllib.request.Request(
            "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest",
            method="HEAD",
        )
        response = urllib.request.urlopen(req, timeout=5)
        # url will be something like: https://github.com/yt-dlp/yt-dlp-master-builds/releases/tag/2026.05.16.203101
        tag = response.url.split("/")[-1]
        return tag
    except Exception as e:
        print(f"Failed to fetch latest yt-dlp version: {e}")
        return ""


def check_and_download_ytdlp():
    """Checks the latest version and downloads if it's newer or missing."""
    latest_version = get_latest_ytdlp_version()

    current_version = ""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, "r") as f:
            current_version = f.read().strip()

    should_download = False
    if not YTDLP_PATH.exists():
        should_download = True
    elif latest_version and latest_version != current_version:
        should_download = True

    if should_download:
        print(
            f"Updating yt-dlp to version {latest_version or 'latest'} from {YTDLP_URL}..."
        )
        try:
            temp_path = YTDLP_PATH.with_suffix(".tmp")

            # Download with a user agent just in case
            req = urllib.request.Request(
                YTDLP_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with (
                urllib.request.urlopen(req) as response,
                open(temp_path, "wb") as out_file,
            ):
                out_file.write(response.read())

            # Move and replace
            if temp_path.exists():
                if YTDLP_PATH.exists():
                    try:
                        YTDLP_PATH.unlink()
                    except OSError:
                        pass  # Might be locked on Windows, but we'll try
                temp_path.rename(YTDLP_PATH)

            if os.name == "posix":
                st = os.stat(YTDLP_PATH)
                os.chmod(YTDLP_PATH, st.st_mode | stat.S_IEXEC)

            if latest_version:
                with open(VERSION_FILE, "w") as f:
                    f.write(latest_version)

        except Exception as e:
            print(f"Failed to download/update yt-dlp: {e}")


def fetch_gist_config(gist_url: str) -> dict:
    """Fetches the JSON config from a gist."""
    if not gist_url:
        return {}
    try:
        req = urllib.request.Request(gist_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"Failed to fetch gist config: {e}")
        return {}
