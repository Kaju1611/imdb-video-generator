"""
visuals/fetcher.py

Fetch movie images using multiple free sources (no TMDb, no Pexels):
  1. OMDb API         — official poster (free key)
  2. Wikidata SPARQL  — no key needed
  3. Wikipedia API    — no key needed
  4. DuckDuckGo       — no key needed
  5. Title cards      — guaranteed Pillow fallback (8 distinct layouts)

Add to .env:
  OMDB_API_KEY=your_key      # https://www.omdbapi.com/apikey.aspx  (free)
"""

import os
import re
import time
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from scraper.imdb_scraper import MovieData

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


# ═══════════════════════════════════════════════════════════════
# SOURCE 1 — OMDb  (official poster, free key)
# ═══════════════════════════════════════════════════════════════

def fetch_from_omdb(movie: MovieData) -> list:
    """
    Fetch the official poster from OMDb.
    Free key: https://www.omdbapi.com/apikey.aspx
    """
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        print("[Visuals] OMDb: no OMDB_API_KEY in .env, skipping")
        return []
    try:
        r = requests.get("https://www.omdbapi.com/",
                         params={"apikey": api_key, "i": movie.imdb_id, "plot": "short"},
                         timeout=10)
        data = r.json()
        poster = data.get("Poster", "")
        if poster and poster != "N/A":
            print(f"[Visuals] OMDb: found poster")
            return [poster]
    except Exception as e:
        print(f"[Visuals] OMDb fetch failed: {e}")
    return []


# ═══════════════════════════════════════════════════════════════
# SOURCE 2 — Wikidata SPARQL  (no key needed)
# ═══════════════════════════════════════════════════════════════

def fetch_from_wikidata(movie: MovieData, max_images: int = 5) -> list:
    """Fetch poster/image URLs via Wikidata SPARQL — completely free, no key."""
    urls = []
    try:
        query = f"""
        SELECT ?image WHERE {{
          ?film wdt:P345 "{movie.imdb_id}" .
          ?film wdt:P18 ?image .
        }} LIMIT {max_images}
        """
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={**HEADERS, "Accept": "application/sparql-results+json"},
            timeout=15
        )
        if r.content:
            for binding in r.json().get("results", {}).get("bindings", []):
                url = binding.get("image", {}).get("value", "")
                if url:
                    urls.append(url)
            print(f"[Visuals] Wikidata: found {len(urls)} images")
    except Exception as e:
        print(f"[Visuals] Wikidata fetch failed: {e}")
    return urls


# ═══════════════════════════════════════════════════════════════
# SOURCE 3 — Wikipedia  (no key needed)
# ═══════════════════════════════════════════════════════════════

def fetch_from_wikipedia(movie: MovieData, max_images: int = 10) -> list:
    urls = []
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        resp = requests.get(search_url, params={
            "action": "query", "list": "search",
            "srsearch": f"{movie.title} {movie.year or ''} film",
            "format": "json", "srlimit": 3,
        }, headers=HEADERS, timeout=10)

        if not resp.content:
            return []

        results = resp.json().get("query", {}).get("search", [])
        if not results:
            return []

        page_title = results[0]["title"]
        print(f"[Visuals] Wikipedia page: {page_title}")

        resp2 = requests.get(search_url, params={
            "action": "query", "titles": page_title,
            "prop": "images", "imlimit": 50, "format": "json",
        }, headers=HEADERS, timeout=10)

        if not resp2.content:
            return []

        pages = resp2.json().get("query", {}).get("pages", {})
        image_titles = []
        seen_names = set()
        for page in pages.values():
            for img in page.get("images", []):
                name = img["title"]
                if any(s in name.lower() for s in
                       ["icon", "flag", "logo", "commons", "wikimedia",
                        "symbol", "map", "stub", "question", "edit", "arrow"]):
                    continue
                if name.lower().endswith((".jpg", ".jpeg", ".png")):
                    base = name.lower().split("file:")[-1]
                    if base not in seen_names:
                        seen_names.add(base)
                        image_titles.append(name)

        for title in image_titles[:max_images * 2]:
            r = requests.get(search_url, params={
                "action": "query", "titles": title,
                "prop": "imageinfo", "iiprop": "url|size", "format": "json",
            }, headers=HEADERS, timeout=10)
            if not r.content:
                continue
            for p in r.json().get("query", {}).get("pages", {}).values():
                info = p.get("imageinfo", [])
                if info and info[0].get("width", 0) >= 300 and info[0].get("height", 0) >= 200:
                    urls.append(info[0]["url"])
            time.sleep(0.2)

        print(f"[Visuals] Wikipedia: found {len(urls)} images")
    except Exception as e:
        print(f"[Visuals] Wikipedia fetch failed: {e}")
    return urls


# ═══════════════════════════════════════════════════════════════
# SOURCE 4 — DuckDuckGo  (no key needed)
# ═══════════════════════════════════════════════════════════════

def fetch_from_duckduckgo(movie: MovieData, max_images: int = 15) -> list:
    urls = []
    try:
        query = f"{movie.title} {movie.year or ''} movie film still"
        resp = requests.get("https://duckduckgo.com/",
                            params={"q": query}, headers=HEADERS, timeout=10)
        if not resp.content:
            return []

        vqd_match = re.search(r"vqd=['\"]([\d-]+)['\"]", resp.text)
        if not vqd_match:
            return []

        resp2 = requests.get("https://duckduckgo.com/i.js", params={
            "l": "us-en", "o": "json", "q": query,
            "vqd": vqd_match.group(1), "f": ",,,", "p": "1",
        }, headers=HEADERS, timeout=10)

        if not resp2.content:
            return []

        seen = set()
        for r in resp2.json().get("results", []):
            if len(urls) >= max_images:
                break
            src = r.get("image", "")
            if src and src.startswith("http") and src not in seen:
                seen.add(src)
                urls.append(src)

        print(f"[Visuals] DuckDuckGo: found {len(urls)} images")
    except Exception as e:
        print(f"[Visuals] DuckDuckGo fetch failed: {e}")
    return urls


# ═══════════════════════════════════════════════════════════════
# Download helper with deduplication
# ═══════════════════════════════════════════════════════════════

def _image_hash(img: Image.Image) -> str:
    small = img.resize((16, 16)).convert("L")
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)


def download_image(url: str, dest_path: str, seen_hashes: set) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        if img.width < 300 or img.height < 200:
            return False
        h = _image_hash(img)
        if h in seen_hashes:
            print(f"[Visuals] Skipping duplicate image")
            return False
        seen_hashes.add(h)
        img = img.resize((1920, 1080), Image.LANCZOS)
        img.save(dest_path, "JPEG", quality=90)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# Title card fallback — 8 distinct layouts
# ═══════════════════════════════════════════════════════════════

def _load_font(size: int):
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                 "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int = 45) -> list:
    words = text.split()
    lines, line = [], ""
    for word in words:
        if len(line) + len(word) + 1 <= max_chars:
            line = (line + " " + word).strip()
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def make_title_card(movie: MovieData, output_path: str, index: int = 1) -> str:
    W, H = 1920, 1080
    themes = [
        {"bg": (10, 10, 25),  "accent": (220, 170, 50),  "text": (255, 245, 210)},
        {"bg": (25, 10, 10),  "accent": (200, 80,  80),  "text": (255, 230, 220)},
        {"bg": (10, 25, 15),  "accent": (60,  180, 100), "text": (220, 255, 230)},
        {"bg": (10, 15, 30),  "accent": (80,  140, 220), "text": (210, 230, 255)},
        {"bg": (25, 15, 25),  "accent": (180, 80,  200), "text": (240, 220, 255)},
        {"bg": (25, 20, 10),  "accent": (220, 140, 40),  "text": (255, 240, 210)},
        {"bg": (10, 25, 25),  "accent": (40,  200, 200), "text": (210, 255, 255)},
        {"bg": (20, 20, 20),  "accent": (200, 200, 200), "text": (255, 255, 255)},
    ]
    t = themes[(index - 1) % 8]
    bg, accent, tcol = t["bg"], t["accent"], t["text"]
    card_type = (index - 1) % 8

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 12], fill=accent)
    draw.rectangle([0, H - 12, W, H], fill=accent)

    if card_type == 0:
        draw.text((W//2, H//2 - 90), movie.title, fill=tcol, font=_load_font(100), anchor="mm")
        draw.text((W//2, H//2 + 30), str(movie.year or ""), fill=accent, font=_load_font(70), anchor="mm")
        draw.text((W//2, H//2 + 120), f"IMDb  ⭐  {movie.rating} / 10", fill=tcol, font=_load_font(46), anchor="mm")
    elif card_type == 1:
        draw.text((W//2, 200), "A film by", fill=accent, font=_load_font(50), anchor="mm")
        draw.text((W//2, H//2), movie.director or "Unknown Director", fill=tcol, font=_load_font(96), anchor="mm")
        draw.text((W//2, H - 180), movie.title, fill=(170, 170, 170), font=_load_font(42), anchor="mm")
    elif card_type == 2:
        draw.text((W//2, 200), "IMDb Rating", fill=accent, font=_load_font(54), anchor="mm")
        draw.text((W//2, H//2), f"{movie.rating}", fill=tcol, font=_load_font(200), anchor="mm")
        draw.text((W//2, H - 180), f"out of 10  •  {movie.title}", fill=(170, 170, 170), font=_load_font(40), anchor="mm")
    elif card_type == 3:
        draw.text((W//2, 200), movie.title, fill=tcol, font=_load_font(72), anchor="mm")
        draw.text((W//2, 330), "Genre", fill=accent, font=_load_font(44), anchor="mm")
        y = H//2 - 20
        for g in (movie.genres or ["Drama"])[:4]:
            draw.text((W//2, y), g, fill=tcol, font=_load_font(58), anchor="mm")
            y += 80
    elif card_type == 4:
        draw.text((W//2, 180), "Starring", fill=accent, font=_load_font(54), anchor="mm")
        y = 310
        for actor in (movie.cast[:4] if movie.cast else ["Unknown"]):
            draw.text((W//2, y), actor, fill=tcol, font=_load_font(66), anchor="mm")
            y += 90
        draw.text((W//2, H - 180), movie.title, fill=(150, 150, 150), font=_load_font(36), anchor="mm")
    elif card_type == 5:
        draw.text((W//2, 160), movie.title, fill=accent, font=_load_font(64), anchor="mm")
        plot = movie.plot or "A timeless cinematic masterpiece."
        lines = _wrap_text(plot[:180], max_chars=48)
        y = 320
        for line in lines[:5]:
            draw.text((W//2, y), line, fill=tcol, font=_load_font(44), anchor="mm")
            y += 64
    elif card_type == 6:
        draw.text((W//2, H//2 - 80), str(movie.year or ""), fill=accent, font=_load_font(240), anchor="mm")
        draw.text((W//2, H//2 + 120), movie.title, fill=tcol, font=_load_font(62), anchor="mm")
    else:
        draw.text((W//2, 160), movie.title, fill=tcol, font=_load_font(80), anchor="mm")
        draw.line([(200, 230), (W - 200, 230)], fill=accent, width=3)
        draw.text((W//2, 300), f"{movie.year}   •   Directed by {movie.director or 'N/A'}", fill=accent, font=_load_font(42), anchor="mm")
        draw.text((W//2, 400), f"⭐  {movie.rating} / 10", fill=tcol, font=_load_font(58), anchor="mm")
        if movie.genres:
            draw.text((W//2, 500), "  •  ".join(movie.genres[:3]), fill=(180, 180, 180), font=_load_font(40), anchor="mm")
        if movie.cast:
            draw.text((W//2, 600), "Starring: " + ", ".join(movie.cast[:3]), fill=(160, 160, 160), font=_load_font(36), anchor="mm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    print(f"[Visuals] Title card layout-{card_type+1} saved -> {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════════
# MAIN FETCHER — tries all sources in priority order
# ═══════════════════════════════════════════════════════════════

def fetch_visuals(movie: MovieData, output_dir: str, num_images: int = 24) -> list:
    """
    Priority order:
      OMDb → Wikidata → Wikipedia → DuckDuckGo → Title cards
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved = []
    seen_hashes = set()
    image_urls = []

    # 1. OMDb poster
    image_urls += fetch_from_omdb(movie)

    # 2. Wikidata
    if len(image_urls) < num_images:
        image_urls += fetch_from_wikidata(movie)

    # 3. Wikipedia
    if len(image_urls) < num_images:
        image_urls += fetch_from_wikipedia(movie, max_images=15)

    # 4. DuckDuckGo
    if len(image_urls) < num_images:
        print("[Visuals] Trying DuckDuckGo...")
        image_urls += fetch_from_duckduckgo(movie, max_images=20)

    # Deduplicate URLs
    seen_urls = set()
    unique_urls = []
    for u in image_urls:
        if u not in seen_urls:
            seen_urls.add(u)
            unique_urls.append(u)

    # Download all unique images
    for url in unique_urls:
        if len(saved) >= num_images:
            break
        dest = f"{output_dir}/frame_{len(saved)+1:02d}.jpg"
        if download_image(url, dest, seen_hashes):
            saved.append(dest)
            print(f"[Visuals] Downloaded frame_{len(saved):02d}.jpg")

    # Fill remaining with distinct title cards
    while len(saved) < num_images:
        idx = len(saved) + 1
        path = f"{output_dir}/frame_{idx:02d}.jpg"
        make_title_card(movie, path, index=idx)
        saved.append(path)

    print(f"[Visuals] Total: {len(saved)} frames ready")
    return sorted(saved)


if __name__ == "__main__":
    import sys
    from scraper.imdb_scraper import scrape
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.imdb.com/title/tt0111161/"
    movie = scrape(url)
    images = fetch_visuals(movie, f"output/{movie.imdb_id}/visuals")
    print(f"\n{len(images)} images ready.")