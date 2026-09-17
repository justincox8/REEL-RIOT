import requests
import os
from dotenv import load_dotenv
import sqlite3
import time
from sentence_transformers import SentenceTransformer
import sentence_transformers
import pandas as pd
import numpy as np


load_dotenv()
movie_key = os.getenv("MOVIE_KEY")
conn = sqlite3.connect("media.db")
cursor = conn.cursor()


def fetch_books_for_theme(subject, count=20):
    i = 0
    url = f"https://openlibrary.org/subjects/{subject}.json"
    params = {"limit": count}
    response = requests.get(url, params=params)
    data = response.json()

    books = []
    for work in data["works"]:
        work_key = work["key"]  # e.g. "/works/OL45804W"
        title = work["title"]
        authors = ", ".join(a["name"] for a in work.get("authors", []))
        first_publish_year = work.get("first_publish_year")

        # Second call to get the description text
        details_url = f"https://openlibrary.org{work_key}.json"
        details_response = requests.get(details_url)
        details = details_response.json()

        description = details.get("description", "")
        if isinstance(description, dict):
            description = description.get("value", "")

        books.append(
            {
                "openlibrary_id": work_key,
                "title": title,
                "author": authors,
                "description": description,
                "first_publish_year": first_publish_year,
            }
        )
        i += 1
        print(i)
    return books


def insert_books(books, theme):
    for book in books:
        cursor.execute(
            """
            INSERT OR IGNORE INTO books (openlibrary_id, title, author, description, theme, first_publish_year)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                book["openlibrary_id"],
                book["title"],
                book["author"],
                book["description"],
                theme,
                book["first_publish_year"],
            ),
        )
    conn.commit()

import requests

def fetch_single_book(title):
    search_url = "https://openlibrary.org/search.json"
    params = {"q": title, "limit": 1}
    response = requests.get(search_url, params=params)
    data = response.json()

    if not data["docs"]:
        return None

    doc = data["docs"][0]
    work_key = doc["key"]  # e.g. "/works/OL12345W"

    details_url = f"https://openlibrary.org{work_key}.json"
    details_response = requests.get(details_url)
    details = details_response.json()

    description = details.get("description", "")
    if isinstance(description, dict):
        description = description.get("value", "")

    return {
        "openlibrary_id": work_key,
        "title": doc.get("title"),
        "author": ", ".join(doc.get("author_name", [])),
        "description": description,
        "first_publish_year": doc.get("first_publish_year")
    }
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


book = fetch_single_book("Johnny Got His Gun")
if book:
    insert_books([book], "war")
new_book_text = book["description"]  # from the dict you just inserted
new_embedding = model.encode([new_book_text])[0]  # [0] since encode expects/returns a list

blob = np.array(new_embedding, dtype=np.float32).tobytes()
conn.execute(
    "UPDATE books SET embedding = ? WHERE openlibrary_id = ?",
    (blob, book["openlibrary_id"])
)
conn.commit()

war = fetch_books_for_theme("war", count=300)
western = fetch_books_for_theme("western", count=300)
action = fetch_books_for_theme("action", count=300)
adventure = fetch_books_for_theme("adventure", count=300)
comedy = fetch_books_for_theme("comedy", count=300)
crime = fetch_books_for_theme("crime", count=300)
fantasy = fetch_books_for_theme("fantasy", count=300)
horror = fetch_books_for_theme("horror", count=300)
mystery = fetch_books_for_theme("mystery", count=300)
science_fiction = fetch_books_for_theme("science_fiction", count=300)
thriller = fetch_books_for_theme("thriller", count=300)
romance = fetch_books_for_theme("romance", count=300)

insert_books(war, "war")
insert_books(western, "western")
insert_books(action, "action")
insert_books(adventure, "adventure")
insert_books(comedy, "comedy")
insert_books(crime, "crime")
insert_books(fantasy, "fantasy")
insert_books(horror, "horror")
insert_books(mystery, "mystery")
insert_books(science_fiction, "science_fiction")
insert_books(thriller, "thriller")
insert_books(romance, "romance")



