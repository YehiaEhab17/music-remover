import csv
from datetime import datetime
from pathlib import Path

from config import DEFAULT_MODEL

BENCHMARK_DIR = Path.home() / "Documents" / "Benchmarks"
BENCHMARK_FILE = BENCHMARK_DIR / "music_remover_benchmark.csv"

FIELDS = [
    "timestamp",
    "source_type",
    "filename",
    "video_duration_sec",
    "resolution",
    "gpu_enabled",
    "chunking_enabled",
    "chunk_duration_secs",
    "default_quality",
    "model_name",
    "split_time_sec",
    "processing_time_sec",
    "combine_time_sec",
    "pipeline_time_sec",
    "overall_time_sec",
    "chunked",
    "num_chunks",
    "input_size_mb",
    "audio_size_mb",
    "clean_audio_size_mb",
    "output_size_mb",
    "error",
]


class BenchmarkRecorder:
    def __init__(self, enabled: bool, settings: dict) -> None:
        self._enabled = enabled
        if not enabled:
            return
        self._settings = dict(settings)
        self._row: dict[str, object] = {}
        self.reset()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def reset(self) -> None:
        if not self._enabled:
            return
        self._row = {field: "" for field in FIELDS}
        self._row["timestamp"] = datetime.now().isoformat()
        s = self._settings
        self._row["gpu_enabled"] = s.get("gpu_enabled", "")
        self._row["chunking_enabled"] = s.get("chunking_enabled", "")
        self._row["chunk_duration_secs"] = s.get("chunk_duration_secs", "")
        self._row["default_quality"] = s.get("default_quality", "")
        self._row["model_name"] = DEFAULT_MODEL

    def set_video_info(
        self,
        *,
        source_type: str = "",
        filename: str = "",
        duration_sec: float = 0,
        resolution: str = "",
    ) -> None:
        if not self._enabled:
            return
        self._row["source_type"] = source_type
        self._row["filename"] = filename
        if duration_sec:
            self._row["video_duration_sec"] = round(duration_sec, 1)
        self._row["resolution"] = resolution

    def set_phase_time(self, phase: str, seconds: float) -> None:
        if not self._enabled:
            return
        self._row[f"{phase}_time_sec"] = round(seconds, 2)

    def set_file_size(self, name: str, file_path: Path) -> None:
        if not self._enabled:
            return
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            self._row[f"{name}_size_mb"] = round(size_mb, 2)
        except OSError:
            pass

    def set_chunk_info(self, chunked: bool, num_chunks: int = 0) -> None:
        if not self._enabled:
            return
        self._row["chunked"] = "yes" if chunked else "no"
        self._row["num_chunks"] = num_chunks

    def set_pipeline_time(self, seconds: float) -> None:
        if not self._enabled:
            return
        self._row["pipeline_time_sec"] = round(seconds, 2)

    def set_overall_time(self, seconds: float) -> None:
        if not self._enabled:
            return
        self._row["overall_time_sec"] = round(seconds, 2)

    def set_error(self, error: str) -> None:
        if not self._enabled:
            return
        self._row["error"] = str(error)

    def has_error(self) -> bool:
        return bool(self._row.get("error"))

    def write(self) -> None:
        if not self._enabled:
            return
        BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
        exists = BENCHMARK_FILE.exists()
        with open(BENCHMARK_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(self._row)
