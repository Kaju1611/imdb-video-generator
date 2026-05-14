"""
tts/voiceover.py

Converts narration script to MP3 using:
1. Gemini TTS (primary)
2. ElevenLabs (fallback)
3. gTTS (final free fallback)
"""

import os
import wave
import struct
from pathlib import Path


# =========================================================
# GEMINI TTS
# =========================================================

def generate_with_gemini(script: str, output_path: str) -> str:
    """
    Gemini native audio generation with correct AUDIO modality.
    Requires: pip install google-genai
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3.1-flash-tts-preview",   # best available TTS model
        contents=script,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"      # deep, documentary-style voice
                    )
                )
            )
        )
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Gemini TTS returns raw PCM audio — convert to WAV first, then save
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    mime_type  = response.candidates[0].content.parts[0].inline_data.mime_type or ""

    # If it's already mp3/wav just write it directly
    if "mp3" in mime_type or "mpeg" in mime_type:
        with open(output_path, "wb") as f:
            f.write(audio_data)
    else:
        # Raw PCM (L16) → WAV wrapper so ffmpeg can read it
        wav_path = output_path.replace(".mp3", ".wav")
        _pcm_to_wav(audio_data, wav_path, sample_rate=24000)
        # Convert WAV → MP3 via ffmpeg
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, output_path],
            check=True, capture_output=True
        )
        Path(wav_path).unlink(missing_ok=True)

    print(f"[TTS] Gemini voiceover saved -> {output_path}")
    return output_path


def _pcm_to_wav(pcm_data: bytes, wav_path: str, sample_rate: int = 24000,
                channels: int = 1, bit_depth: int = 16) -> None:
    """Wrap raw PCM bytes in a proper WAV container."""
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bit_depth // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


# =========================================================
# ELEVENLABS
# =========================================================

def generate_with_elevenlabs(script: str, output_path: str) -> str:

    from elevenlabs.client import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY missing")

    client   = ElevenLabs(api_key=api_key)
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    audio = client.generate(
        text=script,
        voice=voice_id,
        model="eleven_multilingual_v2",
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"[TTS] ElevenLabs voiceover saved -> {output_path}")
    return output_path


# =========================================================
# GTTS FREE FALLBACK
# =========================================================

def generate_with_gtts(script: str, output_path: str) -> str:

    from gtts import gTTS

    tts = gTTS(text=script, lang="en")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tts.save(output_path)

    print(f"[TTS] gTTS voiceover saved -> {output_path}")
    return output_path


# =========================================================
# MAIN WRAPPER  (Gemini → ElevenLabs → gTTS)
# =========================================================

def generate_voiceover(
    script: str,
    output_path: str,
    provider: str = "gemini"
) -> str:

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        if provider == "gemini":
            return generate_with_gemini(script, output_path)
        elif provider == "elevenlabs":
            return generate_with_elevenlabs(script, output_path)
        else:
            return generate_with_gtts(script, output_path)

    except Exception as e:
        print(f"[TTS] {provider} failed ({e})")

        if provider == "gemini":
            print("[TTS] Falling back to ElevenLabs...")
            return generate_voiceover(script, output_path, provider="elevenlabs")
        elif provider == "elevenlabs":
            print("[TTS] Falling back to gTTS...")
            return generate_voiceover(script, output_path, provider="gtts")

        raise e


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "This is a test of the voiceover system."
    out  = sys.argv[2] if len(sys.argv) > 2 else "output/test_voiceover.mp3"
    generate_voiceover(text, out)