
import requests
import os
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

movie_key = os.getenv("MOVIE_KEY")

# Keep the database and offsets file alongside this script.
BASE_DIR = Path(__file__).resolve().parent
OFFSETS_FILE = BASE_DIR / "movie_offsets.json"
DB_FILE = BASE_DIR / "media.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()


def load_offsets():
    if OFFSETS_FILE.exists():
        with open(OFFSETS_FILE, "r") as file:
            return json.load(file)

    return {}


def save_offsets():
    # Write to a temporary file first to reduce the risk of
    # losing the offsets if the script stops during a write.
    temp_file = OFFSETS_FILE.with_suffix(".tmp")

    with open(temp_file, "w") as file:
        json.dump(next_movie_pages, file, indent=4)

    temp_file.replace(OFFSETS_FILE)


# Keys are genre IDs stored as strings in JSON.
next_movie_pages = load_offsets()


def fetch_movies_for_theme(genre_id, count=100, start_page=1):
    discover_url = "https://api.themoviedb.org/3/discover/movie"
    movies = []
    page = start_page
    retried_from_first_page = False

    while len(movies) < count:
        params = {
            "api_key": movie_key,
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "vote_count.gte": 100,
            "page": page,
        }

        response = requests.get(
            discover_url,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "results" not in data or "total_pages" not in data:
            raise ValueError(f"Unexpected TMDB response: {data}")

        total_pages = data["total_pages"]

        # If saved pagination is past the current end, restart
        # at page 1 rather than getting stuck on an invalid page.
        if page > total_pages:
            if retried_from_first_page or total_pages == 0:
                next_movie_pages[str(genre_id)] = 1
                break

            page = 1
            retried_from_first_page = True
            continue

        movies.extend(data["results"])

        # Prepare the next page in memory. We save it to disk
        # only after insert_movies() succeeds.
        if page >= total_pages:
            next_movie_pages[str(genre_id)] = 1
            break

        next_movie_pages[str(genre_id)] = page + 1

        if not data["results"]:
            break

        page += 1

    return movies[:count]


def insert_movies(movies, theme):
    for movie in movies:
        cursor.execute("""
            INSERT OR IGNORE INTO movies
            (tmdb_id, title, overview, theme, release_date,
             popularity, vote_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            movie["id"],
            movie["title"],
            movie["overview"],
            theme,
            movie["release_date"],
            movie["popularity"],
            movie["vote_count"]
        ))

    conn.commit()


def update_genre(genre_id, theme, count=10):
    # Use the saved page, or page 1 for a genre we haven't
    # processed before.
    start_page = next_movie_pages.get(str(genre_id), 1)

    print(
        f"Updating {theme}: starting at page {start_page}, "
        f"requesting up to {count} movies."
    )

    movies = fetch_movies_for_theme(
        genre_id,
        count=count,
        start_page=start_page
    )

    # Insert first. If insertion fails, the updated offset
    # won't be saved to disk.
    insert_movies(movies, theme)
    save_offsets()

    print(f"{theme}: fetched {len(movies)} movies successfully.")


try:
    # Correct TMDB movie genre IDs.
    genres = [
        (37, "western"),
        (28, "action"),
        (12, "adventure"),
        (35, "comedy"),
        (80, "crime"),
        (14, "fantasy"),
        (27, "horror"),
        (9648, "mystery"),
        (878, "science_fiction"),
        (53, "thriller"),
        (10752, "war"),
        (10749, "romance"),
    ]

    for genre_id, theme in genres:
        update_genre(genre_id, theme, count=10)

finally:
    conn.commit()
    conn.close()
