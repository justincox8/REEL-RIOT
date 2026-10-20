import requests
import os
from dotenv import load_dotenv
import sqlite3
import time
from sentence_transformers import SentenceTransformer
import sentence_transformers
import pandas as pd
import numpy as np
import json
from pathlib import Path

load_dotenv()
movie_key = os.getenv("MOVIE_KEY")
conn = sqlite3.connect("media.db")
cursor = conn.cursor()
BASE_DIR = Path(__file__).resolve().parent
OFFSETS_FILE = BASE_DIR / "book_offsets.json"


def load_offsets():
    if OFFSETS_FILE.exists():
        with open(OFFSETS_FILE, "r") as file:
            return json.load(file)
    return {}


def save_offsets():
    temp_file = OFFSETS_FILE.with_suffix(".tmp")

    with open(temp_file, "w") as file:
        json.dump(book_offsets, file, indent=4)

    temp_file.replace(OFFSETS_FILE)


book_offsets = load_offsets()


def fetch_books_for_theme(subject, count=20, offset=0):
    i = 0
    url = f"https://openlibrary.org/subjects/{subject}.json"
    params = {
        "limit": count,
        "offset": offset,
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    books = []
    
    for work in data["works"]:
        work_key = work["key"]
        title = work["title"]
        authors = ", ".join(
            a["name"] for a in work.get("authors", [])
        )
        first_publish_year = work.get("first_publish_year")
    
        details_url = f"https://openlibrary.org{work_key}.json"
        details_response = requests.get(details_url, timeout=30)
        details_response.raise_for_status()
        details = details_response.json()
    
        description = details.get("description", "")
        if isinstance(description, dict):
            description = description.get("value", "")
    
        books.append({
            "openlibrary_id": work_key,
            "title": title,
            "author": authors,
            "description": description,
            "first_publish_year": first_publish_year,
        })
    
        i += 1
        print(f"{subject}: fetched book {i}/{count}")
    
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


subjects = [
    ("war", 10),
    ("western", 5),
    ("action", 10),
    ("adventure", 10),
    ("comedy", 10),
    ("crime", 10),
    ("fantasy", 5),
    ("horror", 10),
    ("mystery", 10),
    ("science_fiction", 5),
    ("thriller", 10),
    ("romance", 5),
]

try:
    for subject, count in subjects:
        # Start at the saved offset, or 0 for a new subject.
        offset = book_offsets.get(subject, 0)

        print(
            f"\nUpdating {subject}: offset={offset}, "
            f"count={count}"
        )

        books = fetch_books_for_theme(
            subject,
            count=count,
            offset=offset,
        )

        # Insert into the database first.
        insert_books(books, subject)

        # Advance by the number actually fetched.
        # Open Library's offset is zero-based.
        book_offsets[subject] = offset + len(books)

        # Persist after each successful subject.
        save_offsets()

        print(
            f"Finished {subject}: fetched {len(books)} books. "
            f"Next offset: {book_offsets[subject]}"
        )

finally:
    conn.close()



