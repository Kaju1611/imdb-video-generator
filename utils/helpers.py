"""
utils/helpers.py - Shared utilities: paths, env loading, dependency checks.
"""

import os
import re
import json
import platform
from pathlib import Path
from datetime import datetime


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[\s]+", "_", name)[:60]


def make_output_dir(movie_title: str, imdb_id: str, base_dir: str = "output") -> dict:
    root = Path(base_dir) / f"{sanitize_filename(movie_title)}_{imdb_id}"
    paths = {
        "root":      str(root),
        "visuals":   str(root / "visuals"),
        "audio":     str(root / "voiceover.mp3"),
        "subtitles": str(root / "subtitles.srt"),
        "script":    str(root / "script.txt"),
        "video":     str(root / "final_video.mp4"),
        "metadata":  str(root / "metadata.json"),
    }
    for key in ("root", "visuals"):
        Path(paths[key]).mkdir(parents=True, exist_ok=True)
    return paths


def save_metadata(movie_data, script: str, paths: dict) -> None:
    data = {"generated_at": datetime.utcnow().isoformat(),
            "movie": movie_data.__dict__,
            "script_word_count": len(script.split()),
            "paths": paths}
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_dependencies() -> bool:
    import shutil
    ok = True
    is_win = platform.system() == "Windows"
    hint = ("Download from https://www.gyan.dev/ffmpeg/builds/ and add to PATH"
            if is_win else "sudo apt install ffmpeg")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"[Utils] Found: {tool}")
        else:
            print(f"[Utils] Missing: {tool}  ->  {hint}")
            ok = False
    return ok


def load_env() -> None:
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        print("[Utils] .env loaded")
    else:
        print("[Utils] No .env file found - using system environment variables")
