from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import sqlite3
import time
from sentence_transformers import SentenceTransformer
import sentence_transformers
import numpy as np

conn = sqlite3.connect("media.db")
cur = conn.cursor()


analyzer = SentimentIntensityAnalyzer()

def compute_and_save_sentiment(table_name, text_column):
    df = pd.read_sql_query(f"SELECT id, {text_column} FROM {table_name}", conn)
    for _, row in df.iterrows():
        text = row[text_column] or ""  # guard against NULL/empty text
        score = analyzer.polarity_scores(text)["compound"]
        conn.execute(
            f"UPDATE {table_name} SET sentiment = ? WHERE id = ?",
            (score, int(row["id"]))
        )
    conn.commit()

compute_and_save_sentiment("movies", "overview")
compute_and_save_sentiment("books", "description")
compute_and_save_sentiment("songs", "theme")

movies_df = pd.read_sql_query("SELECT id, theme AS candidate_theme, sentiment AS candidate_sentiment FROM movies", conn)
books_df = pd.read_sql_query("SELECT id, theme AS candidate_theme, sentiment AS candidate_sentiment FROM books", conn)
songs_df = pd.read_sql_query("SELECT id, genre AS song_genre, sentiment AS song_sentiment FROM songs", conn)