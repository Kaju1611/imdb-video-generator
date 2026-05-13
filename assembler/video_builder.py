"""
assembler/video_builder.py - FFmpeg video assembler. Windows path-safe.
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


def get_audio_duration(audio_path: str) -> float:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    for s in data.get("streams", []):
        if s.get("codec_type") == "audio":
            return float(s.get("duration", 120.0))
    return 120.0


def build_video(image_paths: list, audio_path: str, srt_path: str,
                output_path: str, resolution: str = "1920x1080", fps: int = 24) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio_duration = get_audio_duration(audio_path)
    slide_duration = audio_duration / len(image_paths)
    width, height = map(int, resolution.split("x"))

    print(f"[Assembler] {len(image_paths)} images x {slide_duration:.1f}s each")

    clip_paths = []
    for i, img in enumerate(image_paths):
        clip_out = str(Path(output_path).parent / f"clip_{i:02d}.mp4")
        zoom = (f"scale={width*2}:{height*2},"
                f"zoompan=z='min(zoom+0.0004,1.05)':d={int(slide_duration*fps)}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={fps},"
                f"setsar=1")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img),
                        "-vf", zoom, "-t", str(slide_duration),
                        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                        clip_out], check=True, capture_output=True)
        clip_paths.append(clip_out)
        print(f"[Assembler] Clip {i+1}/{len(image_paths)} done")

    concat_list = str(Path(output_path).parent / "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_paths:
            f.write(f"file '{str(Path(c).resolve()).replace(chr(92), '/')}'\n")

    slideshow = str(Path(output_path).parent / "slideshow.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list, "-c", "copy", slideshow],
                   check=True, capture_output=True)

    with_audio = str(Path(output_path).parent / "with_audio.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", slideshow, "-i", audio_path,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-shortest", with_audio], check=True, capture_output=True)

    style = ("FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=40")
    subprocess.run(["ffmpeg", "-y", "-i", with_audio,
                    "-vf", f"subtitles='{_ffmpeg_safe_path(srt_path)}':force_style='{style}'",
                    "-c:a", "copy", output_path], check=True, capture_output=True)

    for p in clip_paths + [concat_list, slideshow, with_audio]:
        try: os.remove(p)
        except OSError: pass

    print(f"[Assembler] Final video -> {output_path}")
    return output_path
