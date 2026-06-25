# Real-Time Preview via Write-and-Play (Approach B)

## Overview
When enabled in settings, the app launches a video player on the output file **while FFmpeg is still writing it**. Since processing is 6x realtime, the user can start watching immediately and the video finishes before playback catches up.

## Key Technical Details

**Growing file playback**: mpv (and libmpv-based players like Haruna) handle growing files natively — they periodically re-read the file size and play new content. VLC and ffplay also support this. The critical requirement is `movflags=faststart` on the FFmpeg output so the moov atom (file index) is written at the beginning instead of the end.

**Player detection**: Check for available players at startup using `shutil.which()`. Supported players: mpv → Haruna → QMPlay2 → VLC → ffplay.

**Batch behavior**: Each file launches its own player instance. Processing is sequential (file 2 starts after file 1's processing completes), so the player for file 1 is still running. Player instances are independent — user watches them at their own pace. No killing.

## Files to Modify

### 1. `config.py` — Add player constants
Add after `AUDIO_SETTINGS`:
```python
PREVIEW_PLAYERS = ["mpv", "haruna", "qmplay2", "vlc", "ffplay"]
```

### 2. `logic/settings_manager.py` — Add defaults
Add to `DEFAULTS`:
```python
"preview_enabled": False,
"preview_player": "mpv",
```

### 3. `logic/preview.py` — New file: Player management
```python
import shutil
import subprocess
from pathlib import Path
from config import PREVIEW_PLAYERS

def detect_players() -> dict[str, bool]:
    """Check which preview players are available."""
    return {p: shutil.which(p) is not None for p in PREVIEW_PLAYERS}

def find_best_player() -> str | None:
    """Return the first available player, or None."""
    for player in PREVIEW_PLAYERS:
        if shutil.which(player):
            return player
    return None

def get_player_args(player: str, file_path: Path) -> list[str]:
    """Return the command to launch a player on a file."""
    if player in ("mpv", "haruna"):
        return [player, "--force-seekable=yes", "--keep-open=yes", str(file_path)]
    elif player == "qmplay2":
        return [player, str(file_path)]
    elif player == "vlc":
        return [player, "--play-and-exit", str(file_path)]
    elif player == "ffplay":
        return [player, "-autoexit", str(file_path)]
    return [player, str(file_path)]

def launch_player(player: str, file_path: Path) -> subprocess.Popen | None:
    """Launch a player on the given file. Returns the Popen object."""
    args = get_player_args(player, file_path)
    try:
        return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return None
```

### 4. `logic/ffmpeg_utils.py` — Modify `combine_video()`
- Add `movflags=faststart` to FFmpeg command (critical for growing file playback)
- Add `async_mode=False` parameter: when `True`, return the Popen object instead of waiting

```python
def combine_video(input_audio, input_video, output_dir, async_mode=False):
    # ... existing command building ...
    command = [... "-movflags", "+faststart", ...]

    if async_mode:
        return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        subprocess.run(command, check=True, capture_output=True, text=True)
```

### 5. `logic/music_removal.py` — Launch player during combine
- Add `preview_enabled` and `preview_player` parameters to `MusicRemoverThread.__init__()`
- In `_combine()`, if preview enabled:
  - Call `combine_video()` in async mode
  - Wait ~2 seconds for moov atom + initial frames
  - Launch the player on the output file
  - Wait for FFmpeg to finish
- Add `_player_process` attribute for tracking

### 6. `GUI/settings.py` — Add UI elements
- Add `preview_checkbox` (QCheckBox) — "Real-time Preview"
- Add `preview_player_combo` (QComboBox) — dropdown with player options
- Add `preview_player_label` (QLabel) — "Preview Player:"
- Position after benchmarking checkbox, before clear cache button
- Dialog height: 530 → ~590

### 7. `GUI/settings_dialog.py` — Wire up new settings
- Load/save `preview_enabled` and `preview_player`
- Enable/disable player combo based on checkbox state
- Detect available players and show status (like GPU status)

### 8. `app.py` — Pass preview settings
- Pass `preview_enabled` and `preview_player` to `MusicRemoverThread`

## Flow
```
User clicks Start
  → Split (extract audio + video)
  → Process ML (chunks or whole file)
  → Combine starts (FFmpeg with faststart, async mode)
  → Wait 2s for moov atom + initial frames
  → Launch mpv/haruna/vlc on output file
  → User watches video in real-time
  → FFmpeg finishes writing
  → Player continues to end naturally
  → Cleanup temp files
```
