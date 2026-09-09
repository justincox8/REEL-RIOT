import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

conn = sqlite3.connect("media.db")

ratings_df = pd.read_sql_query("""
    SELECT * FROM ratings 
    WHERE source_media_type IN ('movie', 'book') 
    AND candidate_media_type IN ('movie', 'book')
""", conn)
print(ratings_df.shape)
print(ratings_df["label"].value_counts())

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

ratings_df["sentiment_diff"] = (ratings_df["source_sentiment"] - ratings_df["candidate_sentiment"]).abs()
print(ratings_df.groupby("label")["sentiment_diff"].describe())
feature_cols = ["cosine_score", "rank_position", "sentiment_diff"]
X = ratings_df[feature_cols]
y = ratings_df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

reranker = LogisticRegression(class_weight="balanced")
reranker.fit(X_train, y_train)
predictions = reranker.predict(X_test)

print("Accuracy:", accuracy_score(y_test, predictions))
print(classification_report(y_test, predictions))
print(reranker.coef_)