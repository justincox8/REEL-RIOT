import requests
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()
movie_key = os.getenv("MOVIE_KEY")
conn = sqlite3.connect("media.db")
cursor = conn.cursor()

def fetch_movies_for_theme(genre_id, count=100):
    discover_url = "https://api.themoviedb.org/3/discover/movie"
    movies = []
    page = 100
    while len(movies) < count:
        params = {
            "api_key": movie_key,
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "vote_count.gte": 100,  # filters out obscure/low-data movies
            "page": page,
        }
        response = requests.get(discover_url, params=params)
        data = response.json()
        movies.extend(data["results"])
        page += 1
        if page > data["total_pages"]:
            break
    return movies[:count]

def insert_movies(movies, theme):
    for movie in movies:
        cursor.execute("""
            INSERT OR IGNORE INTO movies (tmdb_id, title, overview, theme, release_date, popularity, vote_count)
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
western = fetch_movies_for_theme(37)
action =  fetch_movies_for_theme(12)
adventure =  fetch_movies_for_theme(16)
comedy =  fetch_movies_for_theme(18)
crime =  fetch_movies_for_theme(80)
fantasy =  fetch_movies_for_theme(14)
horror =  fetch_movies_for_theme(27)
mystery =  fetch_movies_for_theme(9648)
scienc_fiction =  fetch_movies_for_theme(878)
thriller =  fetch_movies_for_theme(53)
war =  fetch_movies_for_theme(752)
documentary =  fetch_movies_for_theme(99)
romance =  fetch_movies_for_theme(49)

insert_movies(western, "western")
insert_movies(action, "action")
insert_movies(adventure, "adventure")
insert_movies(comedy, "comedy")
insert_movies(crime, "crime")
insert_movies(fantasy, "fantasy")
insert_movies(horror, "horror")
insert_movies(mystery, "mystery")
insert_movies(scienc_fiction, "science_fiction")
insert_movies(thriller, "thriller")
insert_movies(war, "war")
insert_movies(documentary, "documentary")
insert_movies(romance, "romance")



conn.commit()
conn.close()
