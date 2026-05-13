"""
visuals/fetcher.py
Fetches movie images without TMDb.
Strategy (in order):
  1. Wikipedia API          — free, no key, works in India
  2. DuckDuckGo image scrape — no key needed
  3. Pillow title-card       — guaranteed fallback
"""

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


# ── 1. Wikipedia ──────────────────────────────────────────────────────────────

def fetch_from_wikipedia(movie: MovieData, max_images: int = 8) -> list:
    """
    Search Wikipedia for the movie and extract all image URLs from its page.
    Completely free, no API key, works everywhere.
    """
    urls = []
    try:
        # Search Wikipedia for the movie
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{movie.title} {movie.year or ''} film",
            "format": "json",
            "srlimit": 3,
        }
        resp = requests.get(search_url, params=search_params, headers=HEADERS, timeout=10)
        results = resp.json().get("query", {}).get("search", [])
        if not results:
            return []

        page_title = results[0]["title"]
        print(f"[Visuals] Wikipedia page: {page_title}")

        # Get all images from that page
        images_params = {
            "action": "query",
            "titles": page_title,
            "prop": "images",
            "imlimit": 30,
            "format": "json",
        }
        resp = requests.get(search_url, params=images_params, headers=HEADERS, timeout=10)
        pages = resp.json().get("query", {}).get("pages", {})
        image_titles = []
        for page in pages.values():
            for img in page.get("images", []):
                name = img["title"]
                # skip icons, flags, logos
                if any(skip in name.lower() for skip in
                       ["icon", "flag", "logo", "commons", "wikimedia", "symbol", "map"]):
                    continue
                if name.lower().endswith((".jpg", ".jpeg", ".png")):
                    image_titles.append(name)

        # Resolve each image title to a direct URL
        for title in image_titles[:max_images]:
            info_params = {
                "action": "query",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }
            r = requests.get(search_url, params=info_params, headers=HEADERS, timeout=10)
            pages2 = r.json().get("query", {}).get("pages", {})
            for p in pages2.values():
                info = p.get("imageinfo", [])
                if info:
                    urls.append(info[0]["url"])
            time.sleep(0.2)  # be polite to Wikipedia

        print(f"[Visuals] Wikipedia: found {len(urls)} images")

    except Exception as e:
        print(f"[Visuals] Wikipedia fetch failed: {e}")

    return urls


# ── 2. DuckDuckGo image scrape ────────────────────────────────────────────────

def fetch_from_duckduckgo(movie: MovieData, max_images: int = 8) -> list:
    """
    Scrape DuckDuckGo image search results.
    No API key needed, works in India.
    """
    urls = []
    try:
        query = f"{movie.title} {movie.year or ''} movie film still"
        ddg_url = "https://duckduckgo.com/"

        # Step 1: get vqd token
        resp = requests.get(ddg_url, params={"q": query}, headers=HEADERS, timeout=10)
        vqd_match = re.search(r"vqd=['\"]([\d-]+)['\"]", resp.text)
        if not vqd_match:
            return []

        vqd = vqd_match.group(1)

        # Step 2: fetch image results
        img_url = "https://duckduckgo.com/i.js"
        params = {
            "l": "us-en",
            "o": "json",
            "q": query,
            "vqd": vqd,
            "f": ",,,",
            "p": "1",
        }
        resp = requests.get(img_url, params=params, headers=HEADERS, timeout=10)
        results = resp.json().get("results", [])

        for r in results[:max_images]:
            img_src = r.get("image", "")
            if img_src and img_src.startswith("http"):
                urls.append(img_src)

        print(f"[Visuals] DuckDuckGo: found {len(urls)} images")

    except Exception as e:
        print(f"[Visuals] DuckDuckGo fetch failed: {e}")

    return urls


# ── 3. Download helper ────────────────────────────────────────────────────────

def download_image(url: str, dest_path: str) -> bool:
    """Download one image. Returns True on success."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        # Only save if reasonably sized (skip tiny icons)
        if img.width < 200 or img.height < 150:
            return False
        img.save(dest_path, "JPEG", quality=90)
        return True
    except Exception:
        return False


# ── 4. Title card fallback ────────────────────────────────────────────────────

def make_title_card(movie: MovieData, output_path: str, index: int = 1) -> str:
    """Generate a styled dark title card using Pillow."""
    W, H = 1920, 1080
    # Alternate background shades for variety
    shades = [(15, 15, 30), (20, 10, 20), (10, 20, 15), (25, 15, 10)]
    bg = shades[(index - 1) % len(shades)]
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Try Windows Arial, fall back to default
    def load_font(size):
        for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                     "C:/Windows/Fonts/arial.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    # Decorative top bar
    draw.rectangle([0, 0, W, 8], fill=(180, 140, 60))

    # Title
    draw.text((W // 2, H // 2 - 80), movie.title,
              fill=(255, 245, 220), font=load_font(88), anchor="mm")

    # Year + rating
    meta = f"{movie.year or ''}     ⭐ {movie.rating or 'N/A'} / 10"
    draw.text((W // 2, H // 2 + 20), meta,
              fill=(200, 190, 170), font=load_font(46), anchor="mm")

    # Genres
    if movie.genres:
        draw.text((W // 2, H // 2 + 100), "  ·  ".join(movie.genres),
                  fill=(150, 140, 120), font=load_font(34), anchor="mm")

    # Director
    if movie.director:
        draw.text((W // 2, H - 80), f"Dir. {movie.director}",
                  fill=(120, 110, 100), font=load_font(30), anchor="mm")

    # Bottom bar
    draw.rectangle([0, H - 8, W, H], fill=(180, 140, 60))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=92)
    print(f"[Visuals] Title card saved -> {output_path}")
    return output_path


# ── Main fetcher ──────────────────────────────────────────────────────────────

def fetch_visuals(movie: MovieData, output_dir: str, num_images: int = 8) -> list:
    """
    Fetch movie images using Wikipedia → DuckDuckGo → title cards.
    No TMDb, no API key, works in India.

    Args:
        movie: MovieData from scraper
        output_dir: Directory to save images
        num_images: Number of frames needed

    Returns:
        Sorted list of local image file paths
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved = []

    # Try Wikipedia first
    image_urls = fetch_from_wikipedia(movie, max_images=num_images * 2)

    # Fall back to DuckDuckGo if not enough
    if len(image_urls) < num_images:
        print("[Visuals] Not enough from Wikipedia, trying DuckDuckGo...")
        ddg_urls = fetch_from_duckduckgo(movie, max_images=num_images * 2)
        image_urls += ddg_urls

    # Download all found URLs
    for i, url in enumerate(image_urls):
        if len(saved) >= num_images:
            break
        dest = f"{output_dir}/frame_{len(saved)+1:02d}.jpg"
        if download_image(url, dest):
            saved.append(dest)
            print(f"[Visuals] Downloaded frame_{len(saved):02d}.jpg")

    # Fill remaining with title cards
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