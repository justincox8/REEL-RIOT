from sentence_transformers import SentenceTransformer
import sentence_transformers
import requests
import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect("media.db")
cursor = conn.cursor()
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
def save_embeddings(table_name, ids, embeddings):
    for row_id, embedding in zip(ids, embeddings):
        blob = np.array(embedding, dtype=np.float32).tobytes()
        conn.execute(
            f"UPDATE {table_name} SET embedding = ? WHERE id = ?", (blob, int(row_id))
        )
    conn.commit()


def load_embeddings(table_name):
    df = pd.read_sql_query(f"SELECT id, title, embedding FROM {table_name}", conn)
    df["embedding"] = df["embedding"].apply(
        lambda b: np.frombuffer(b, dtype=np.float32)
    )
    return df
#for recalculating embeddings when needed
# Pull the text + id for each table fresh from the database
movies_df = pd.read_sql_query("SELECT id, title, overview FROM movies", conn)

books_df = pd.read_sql_query(
    "SELECT id, title, description FROM books", conn
)
songs_df = pd.read_sql_query(
    "SELECT id, title, theme FROM songs", conn
)

# Recalculate embeddings using your existing model
movie_embeddings = model.encode(
    movies_df["overview"].fillna("").tolist(),
    show_progress_bar=True
)

book_embeddings = model.encode(
    books_df["description"].fillna("").tolist(),
    show_progress_bar=True
)

song_embeddings = model.encode(
    songs_df["theme"].fillna("").tolist(),
    show_progress_bar=True
)

# Update the existing embedding columns
save_embeddings("movies", movies_df["id"], movie_embeddings)
save_embeddings("books", books_df["id"], book_embeddings)
save_embeddings("songs", songs_df["id"], song_embeddings)

conn.close()

print("All movie, book, and song embeddings have been recalculated.")
