"""
subtitles/generator.py
Generates a .srt subtitle file from audio using faster-whisper
(works on Python 3.13), or directly from the script as a fallback.
"""

import os
import re
from pathlib import Path


def seconds_to_srt(s: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def generate_from_audio(audio_path: str, output_path: str) -> str:
    """
    Transcribe audio with faster-whisper and save a .srt file.
    faster-whisper supports Python 3.13 unlike openai-whisper.
    """
    from faster_whisper import WhisperModel

    print("[Subtitles] Loading Whisper model (base)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    print(f"[Subtitles] Transcribing {audio_path}...")
    segments, _ = model.transcribe(audio_path, beam_size=5)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_srt(seg.start)} --> {seconds_to_srt(seg.end)}\n")
            f.write(seg.text.strip() + "\n\n")

    print(f"[Subtitles] SRT saved -> {output_path}")
    return output_path


def generate_from_script(script: str, total_duration: float, output_path: str) -> str:
    """
    Create a .srt by evenly distributing sentences over the duration.
    Fast fallback — no audio transcription needed.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
    if not sentences:
        sentences = [script]

    seg_duration = total_duration / len(sentences)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences):
            start = i * seg_duration
            end = start + seg_duration - 0.1
            f.write(f"{i + 1}\n")
            f.write(f"{seconds_to_srt(start)} --> {seconds_to_srt(end)}\n")
            f.write(sentence + "\n\n")

    print(f"[Subtitles] Script-based SRT saved -> {output_path}")
    return output_path


def generate_subtitles(
    script: str,
    audio_path: str,
    output_path: str,
    target_duration: float = 120.0,
    use_whisper: bool = True,
) -> str:
    """
    Generate subtitles — tries faster-whisper first, falls back to script timing.
    """
    if use_whisper and os.path.exists(audio_path):
        try:
            return generate_from_audio(audio_path, output_path)
        except Exception as e:
            print(f"[Subtitles] Whisper failed ({e}), using script-based timing.")

    return generate_from_script(script, target_duration, output_path)


if __name__ == "__main__":
    import sys
    audio = sys.argv[1] if len(sys.argv) > 1 else "output/test_voiceover.mp3"
    out   = sys.argv[2] if len(sys.argv) > 2 else "output/subtitles.srt"
    generate_subtitles("Sample script.", audio, out)