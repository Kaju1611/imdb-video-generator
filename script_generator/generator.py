"""
script_generator/generator.py
Gemini narration script generator (~300 words = ~2 minutes).
"""

import os
from scraper.imdb_scraper import MovieData

SYSTEM_PROMPT = """You are a professional video scriptwriter creating engaging 2-minute
movie summary videos. Target: 280-320 words (approx 2 min at 150 wpm).

Structure in this order:
1. HOOK (10-15 words) - grab attention immediately
2. INTRO - movie title, year, director
3. GENRE & TONE - set expectations
4. PLOT SUMMARY - 3-4 sentences, no spoilers
5. CAST HIGHLIGHTS - mention top 2-3 actors
6. RATINGS - IMDb score
7. CALL TO ACTION - end on a punchy note

Write conversationally. Short sentences. Plain spoken text only, no markdown."""


def generate_script(movie: MovieData) -> str:
    from google import genai
    from google.genai import types
    import os

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Check your .env file.")

    client = genai.Client(api_key=api_key)

    cast_str = ", ".join(movie.cast) if movie.cast else "an acclaimed cast"
    genres_str = ", ".join(movie.genres) if movie.genres else "multiple genres"

    prompt = (
        f"Title: {movie.title}\n"
        f"Year: {movie.year}\n"
        f"Director: {movie.director or 'N/A'}\n"
        f"Genres: {genres_str}\n"
        f"IMDb Rating: {movie.rating}/10\n"
        f"Plot: {movie.plot or 'N/A'}\n"
        f"Cast: {cast_str}\n\n"
        f"Write the 2-minute spoken script now."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.75,
            max_output_tokens=600,
        ),
    )

    return response.text.strip()

if __name__ == "__main__":
    import sys
    from scraper.imdb_scraper import scrape
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.imdb.com/title/tt0111161/"
    script = generate_script(scrape(url))
    print(script)
    print(f"\nWord count: {len(script.split())}")