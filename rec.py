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
            f"UPDATE {table_name} SET embedding = ? WHERE id = ?",
            (blob, int(row_id))
        )
    conn.commit()


def load_embeddings(table_name):
    df = pd.read_sql_query(f"SELECT id, title, embedding FROM {table_name}", conn)
    df["embedding"] = df["embedding"].apply(lambda b: np.frombuffer(b, dtype=np.float32))
    return df


songs_df = load_embeddings("songs")
movies_df = load_embeddings("movies")
books_df = load_embeddings("books")


song_embeddings = np.stack(songs_df["embedding"].to_numpy())
movie_embeddings = np.stack(movies_df["embedding"].to_numpy())
book_embeddings = np.stack(books_df["embedding"].to_numpy())

song_to_movie_sim = sentence_transformers.util.cos_sim(song_embeddings, movie_embeddings)
song_to_book_sim = sentence_transformers.util.cos_sim(song_embeddings, book_embeddings)
movie_to_book_sim = sentence_transformers.util.cos_sim(movie_embeddings, book_embeddings)

for i in range(len(songs_df)):
    best_movie_idx = int(song_to_movie_sim[i].argmax())
    best_book_idx = int(song_to_book_sim[i].argmax())

    song_title = songs_df["title"][i]
    best_movie = movies_df["title"][best_movie_idx]
    best_movie_score = float(song_to_movie_sim[i][best_movie_idx])
    best_book = books_df["title"][best_book_idx]
    best_book_score = float(song_to_book_sim[i][best_book_idx])

    print(f"{song_title}")
    print(f"  → movie: {best_movie} (score: {best_movie_score:.4f})")
    print(f"  → book:  {best_book} (score: {best_book_score:.4f})")

song_idx = songs_df[songs_df["title"] == "One"].index[0]
jgh_idx = books_df[books_df["title"].str.contains("Johnny Got His Gun")].index[0]
prince_idx = books_df[books_df["title"].str.contains("A prince of the captivity")].index[0]

conn.close()
