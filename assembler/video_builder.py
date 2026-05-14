"""
assembler/video_builder.py - FFmpeg video assembler. Windows path-safe.
Fix: stderr is now captured and printed on error so merge failures are visible.
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def _ffmpeg_safe_path(path: str) -> str:
    """Escape path for use inside FFmpeg filter strings (Windows-safe)."""
    p = str(Path(path).resolve())
    if sys.platform == "win32":
        p = p.replace("\\", "/")
        if len(p) > 1 and p[1] == ":":
            p = p[0] + "\\:" + p[2:]
    return p


def _run(cmd: list, label: str) -> None:
    """Run an ffmpeg command and raise with visible error output on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n[Assembler] ❌ {label} failed!")
        print(f"[Assembler] CMD : {' '.join(cmd)}")
        print(f"[Assembler] ERR : {result.stderr[-1500:]}")   # last 1500 chars
        raise RuntimeError(f"FFmpeg step '{label}' failed. See error above.")


def get_audio_duration(audio_path: str) -> float:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
           "-show_streams", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "audio":
                dur = float(s.get("duration", 0))
                if dur > 0:
                    return dur
    except Exception:
        pass
    # fallback: use format duration
    cmd2 = ["ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", audio_path]
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    try:
        data2 = json.loads(result2.stdout)
        dur = float(data2.get("format", {}).get("duration", 120.0))
        return dur
    except Exception:
        return 120.0


def build_video(image_paths: list, audio_path: str, srt_path: str,
                output_path: str, resolution: str = "1920x1080", fps: int = 24) -> str:

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # ── Audio duration (minimum 110s for ~2min video) ──────────────────────
    audio_duration = get_audio_duration(audio_path)
    audio_duration = max(audio_duration, 110.0)
    slide_duration  = audio_duration / len(image_paths)
    width, height   = map(int, resolution.split("x"))

    print(f"[Assembler] Audio duration : {audio_duration:.1f}s")
    print(f"[Assembler] {len(image_paths)} images x {slide_duration:.1f}s each")

    # ── Step 1: render each image as a short clip ──────────────────────────
    clip_paths = []
    for i, img in enumerate(image_paths):
        clip_out = str(Path(output_path).parent / f"clip_{i:02d}.mp4")
        zoom = (
            f"scale={width*2}:{height*2},"
            f"zoompan=z='min(zoom+0.0004,1.05)':d={int(slide_duration*fps)}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps},"
            f"setsar=1"
        )
        _run(["ffmpeg", "-y", "-loop", "1", "-i", str(img),
              "-vf", zoom, "-t", str(slide_duration),
              "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
              clip_out], label=f"clip_{i:02d}")
        clip_paths.append(clip_out)
        print(f"[Assembler] Clip {i+1}/{len(image_paths)} done")

    # ── Step 2: concatenate clips into slideshow ───────────────────────────
    concat_list = str(Path(output_path).parent / "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_paths:
            safe = str(Path(c).resolve()).replace("\\", "/")
            f.write(f"file '{safe}'\n")

    slideshow = str(Path(output_path).parent / "slideshow.mp4")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
          "-i", concat_list, "-c", "copy", slideshow],
         label="concat slideshow")

    # ── Step 3: merge audio ────────────────────────────────────────────────
    # Re-encode video + audio together to avoid stream mismatch
    with_audio = str(Path(output_path).parent / "with_audio.mp4")
    _run(["ffmpeg", "-y",
          "-i", slideshow,
          "-i", audio_path,
          "-map", "0:v:0",
          "-map", "1:a:0",
          "-c:v", "libx264", "-preset", "fast",   # re-encode to ensure sync
          "-c:a", "aac", "-b:a", "192k",
          "-shortest",
          with_audio], label="merge audio")

    # ── Step 4: burn subtitles ─────────────────────────────────────────────
    style = (
        "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=40"
    )
    safe_srt = _ffmpeg_safe_path(srt_path)
    _run(["ffmpeg", "-y",
          "-i", with_audio,
          "-vf", f"subtitles='{safe_srt}':force_style='{style}'",
          "-c:v", "libx264", "-preset", "fast",
          "-c:a", "copy",
          output_path], label="burn subtitles")

    # ── Cleanup temp files ─────────────────────────────────────────────────
    for p in clip_paths + [concat_list, slideshow, with_audio]:
        try:
            os.remove(p)
        except OSError:
            pass

    print(f"[Assembler] ✅ Final video -> {output_path}")
    return output_path