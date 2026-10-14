from transformers import pipeline
import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import joblib

conn = sqlite3.connect("media.db")
cursor = conn.cursor()

ratings_df = pd.read_sql_query("""
    SELECT * FROM ratings 
    WHERE source_media_type IN ('movie', 'book') 
    AND candidate_media_type IN ('movie', 'book')
""", conn)
#print(ratings_df.shape)
#print(ratings_df["label"].value_counts())

movies_df = pd.read_sql_query("SELECT id, theme, sentiment FROM movies", conn)
books_df = pd.read_sql_query("SELECT id, theme, sentiment FROM books", conn)

# Merge in source's theme/sentiment (source can be movie OR book now)
movie_sources = ratings_df[ratings_df["source_media_type"] == "movie"].merge(
    movies_df, left_on="source_id", right_on="id", suffixes=("", "_source")
)
book_sources = ratings_df[ratings_df["source_media_type"] == "book"].merge(
    books_df, left_on="source_id", right_on="id", suffixes=("", "_source")
)
ratings_df = pd.concat([movie_sources, book_sources], ignore_index=True)
ratings_df = ratings_df.rename(columns={"theme": "source_theme", "sentiment": "source_sentiment"})

# Merge in candidate's theme/sentiment
movie_candidates = ratings_df[ratings_df["candidate_media_type"] == "movie"].merge(
    movies_df, left_on="candidate_id", right_on="id", suffixes=("", "_candidate")
)
book_candidates = ratings_df[ratings_df["candidate_media_type"] == "book"].merge(
    books_df, left_on="candidate_id", right_on="id", suffixes=("", "_candidate")
)
ratings_df = pd.concat([movie_candidates, book_candidates], ignore_index=True)
ratings_df = ratings_df.rename(columns={"theme": "candidate_theme", "sentiment": "candidate_sentiment"})
movies_lookup = pd.read_sql_query("SELECT id, theme FROM movies", conn)
books_lookup = pd.read_sql_query("SELECT id, theme FROM books", conn)

# Recompute hub scores fresh here too (or store them in the DB — see note below)
# For now assume movies_df/books_df with hub_score are already loaded, same as in rec.py

movies_lookup = pd.read_sql_query("SELECT id, hub_score FROM movies", conn)
books_lookup = pd.read_sql_query("SELECT id, hub_score FROM books", conn)

# Merge candidate hub_score onto ratings_df (candidate could be movie or book)
movie_candidates = ratings_df[ratings_df["candidate_media_type"] == "movie"].merge(
    movies_lookup[["id", "hub_score"]], left_on="candidate_id", right_on="id", suffixes=("", "_cand")
)
book_candidates = ratings_df[ratings_df["candidate_media_type"] == "book"].merge(
    books_lookup[["id", "hub_score"]], left_on="candidate_id", right_on="id", suffixes=("", "_cand")
)
ratings_df = pd.concat([movie_candidates, book_candidates], ignore_index=True)
ratings_df = ratings_df.rename(columns={"hub_score": "candidate_hub_score"})

feature_cols = ["cosine_score", "rank_position", "candidate_hub_score"]
X = ratings_df[feature_cols]
y = ratings_df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

reranker = LogisticRegression(class_weight="balanced")
reranker.fit(X_train, y_train)
predictions = reranker.predict(X_test)

print("Accuracy:", accuracy_score(y_test, predictions))
print(classification_report(y_test, predictions))
print(reranker.coef_)

reranker.fit(X,y)
joblib.dump(reranker, "reranker_model.pkl")
print("Final model trained on:", len(X), "samples")
print("Saved to reranker.pkl")

print(ratings_df.groupby("label")["candidate_hub_score"].describe())

