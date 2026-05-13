"""
tts/voiceover.py

Converts narration script to MP3 using:
1. Gemini TTS (primary)
2. ElevenLabs (fallback)
3. gTTS (final free fallback)
"""

import os
from pathlib import Path


# =========================================================
# GEMINI TTS
# =========================================================

def generate_with_gemini(script: str, output_path: str) -> str:
    """
    Gemini native audio generation.
    Requires:
    pip install google-genai
    """

    from google import genai

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=script,
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save binary audio
    with open(output_path, "wb") as f:
        f.write(response.candidates[0].content.parts[0].inline_data.data)

    print(f"[TTS] Gemini voiceover saved -> {output_path}")

    return output_path


# =========================================================
# ELEVENLABS
# =========================================================

def generate_with_elevenlabs(script: str, output_path: str) -> str:

    from elevenlabs.client import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY missing"
        )

    client = ElevenLabs(api_key=api_key)

    voice_id = os.getenv(
        "ELEVENLABS_VOICE_ID",
        "21m00Tcm4TlvDq8ikWAM"
    )

    audio = client.generate(
        text=script,
        voice=voice_id,
        model="eleven_multilingual_v2",
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

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

    tts = gTTS(
        text=script,
        lang="en"
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    tts.save(output_path)

    print(f"[TTS] gTTS voiceover saved -> {output_path}")

    return output_path


# =========================================================
# MAIN WRAPPER
# =========================================================

def generate_voiceover(
    script: str,
    output_path: str,
    provider: str = "gemini"
) -> str:

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        if provider == "gemini":
            return generate_with_gemini(
                script,
                output_path
            )

        elif provider == "elevenlabs":
            return generate_with_elevenlabs(
                script,
                output_path
            )

        else:
            return generate_with_gtts(
                script,
                output_path
            )

    except Exception as e:

        print(
            f"[TTS] {provider} failed ({e})"
        )

        # fallback chain
        if provider == "gemini":
            print("[TTS] Falling back to ElevenLabs...")
            return generate_voiceover(
                script,
                output_path,
                provider="elevenlabs"
            )

        elif provider == "elevenlabs":
            print("[TTS] Falling back to gTTS...")
            return generate_voiceover(
                script,
                output_path,
                provider="gtts"
            )

        raise e


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    import sys

    text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "This is a test of the voiceover system."
    )

    out = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "output/test_voiceover.mp3"
    )

    generate_voiceover(
        text,
        out
    )