from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List
import re, json, time, sys


@dataclass
class MovieData:
    imdb_id: str
    title: str
    year: str
    rating: str
    director: str
    cast: List[str]
    genres: List[str]
    plot: str


def scrape_imdb(url) -> MovieData:
    movie_id = re.search(r"(tt\d+)", url).group(1)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(f"https://www.imdb.com/title/{movie_id}/")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        script = soup.find("script", {"type": "application/ld+json"})
        d = json.loads(script.string)

        return MovieData(
            imdb_id=movie_id,
            title=d.get("name", "Unknown"),
            year=d.get("datePublished", "")[:4],
            rating=str(d.get("aggregateRating", {}).get("ratingValue", "N/A")),
            director=", ".join(p["name"] for p in (d.get("director") or []) if isinstance(p, dict)),
            cast=[a["name"] for a in d.get("actor", [])[:5]],
            genres=d.get("genre", []),
            plot=d.get("description", ""),
        )
    finally:
        driver.quit()


# ✅ Alias so main.py can do: from scraper.imdb_scraper import scrape
scrape = scrape_imdb


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scraper.imdb_scraper <imdb_url>")
        sys.exit(1)

    movie = scrape_imdb(sys.argv[1])
    print("\nTitle:   ", movie.title)
    print("Year:    ", movie.year)
    print("Rating:  ", movie.rating)
    print("Director:", movie.director)
    print("Cast:    ", movie.cast)
    print("Genres:  ", movie.genres)
    print("Plot:    ", movie.plot[:200], "...")