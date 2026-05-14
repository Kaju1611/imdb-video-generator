"""
main.py - Entry point for the IMDb to 2-minute video pipeline.

Usage:
    python main.py <imdb_url> [--skip-whisper]
"""

import sys
import argparse
from utils.helpers import load_env, check_dependencies, make_output_dir, save_metadata


def run_pipeline(imdb_url: str, skip_whisper: bool = False) -> str:
    print("\n" + "=" * 60)
    print("  IMDb to 2-Minute Video Generator")
    print("=" * 60 + "\n")

    load_env()
    if not check_dependencies():
        sys.exit(1)

    print("\n[Step 1/6] Scraping IMDb...")
    from scraper.imdb_scraper import scrape
    movie = scrape(imdb_url)
    print(f"[Step 1/6] Found: {movie.title} ({movie.year})")

    paths = make_output_dir(movie.title, movie.imdb_id)
    print(f"[Main] Output directory: {paths['root']}")

    print("\n[Step 2/6] Generating narration script...")
    from script_generator.generator import generate_script
    script = generate_script(movie)
    with open(paths["script"], "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[Step 2/6] Script ready ({len(script.split())} words)")

    print("\n[Step 3/6] Generating voiceover...")
    from tts.voiceover import generate_voiceover
    generate_voiceover(script, paths["audio"])
    print(f"[Step 3/6] Audio saved -> {paths['audio']}")

    print("\n[Step 4/6] Fetching visuals...")
    from visuals.fetcher import fetch_visuals
    image_paths = fetch_visuals(movie, paths["visuals"], num_images=30)
    print(f"[Step 4/6] {len(image_paths)} images ready")

    print("\n[Step 5/6] Generating subtitles...")
    from subtitles.generator import generate_subtitles
    generate_subtitles(script=script, audio_path=paths["audio"],
                       output_path=paths["subtitles"], use_whisper=not skip_whisper)
    print(f"[Step 5/6] Subtitles saved -> {paths['subtitles']}")

    print("\n[Step 6/6] Assembling final video...")
    from assembler.video_builder import build_video
    build_video(image_paths=image_paths, audio_path=paths["audio"],
                srt_path=paths["subtitles"], output_path=paths["video"])

    save_metadata(movie, script, paths)

    print("\n" + "=" * 60)
    print(f"  Done! Video ready at:")
    print(f"  {paths['video']}")
    print("=" * 60 + "\n")
    return paths["video"]


def main():
    parser = argparse.ArgumentParser(description="Generate a 2-minute video from an IMDb listing.")
    parser.add_argument("imdb_url", help="e.g. https://www.imdb.com/title/tt0111161/")
    parser.add_argument("--skip-whisper", action="store_true",
                        help="Use script-based subtitle timing instead of Whisper")
    args = parser.parse_args()
    run_pipeline(args.imdb_url, skip_whisper=args.skip_whisper)


if __name__ == "__main__":
    main()
