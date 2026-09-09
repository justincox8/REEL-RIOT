from sentence_transformers import SentenceTransformer
import sentence_transformers
import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect("media.db")
cur = conn.cursor()

def load_embeddings(table_name):
    df = pd.read_sql_query(f"SELECT id, title, embedding FROM {table_name}", conn)
    df["embedding"] = df["embedding"].apply(lambda b: np.frombuffer(b, dtype=np.float32))
    return df

# --- Load everything ---
movies_df = load_embeddings("movies")
books_df = load_embeddings("books")

movie_embeddings = np.stack(movies_df["embedding"].to_numpy())
book_embeddings = np.stack(books_df["embedding"].to_numpy())

# --- Raw similarity ---
movie_to_book_sim = sentence_transformers.util.cos_sim(movie_embeddings, book_embeddings)

# --- Hub correction ---
book_baseline = movie_to_book_sim.mean(axis=0)
adjusted_movie_to_book_sim = movie_to_book_sim - book_baseline

movie_baseline = movie_to_book_sim.mean(axis=1)  # note: axis=1 here, correcting the other direction
adjusted_book_to_movie_sim = (movie_to_book_sim.T) - movie_baseline.unsqueeze(1).T if False else None
# simpler and correct: just transpose the movie-corrected version for the reverse direction
adjusted_book_to_movie_sim = adjusted_movie_to_book_sim.T

# --- Lookup table ---
sim_lookup = {
    ("movie", "book"): (adjusted_movie_to_book_sim, movies_df, books_df),
    ("book", "movie"): (adjusted_book_to_movie_sim, books_df, movies_df),
}

def recommend(source_type, source_idx, target_type, n=3):
    sim_matrix, source_df, target_df = sim_lookup[(source_type, target_type)]
    top_idxs = np.argsort(-np.array(sim_matrix[source_idx]))[:n]
    source_title = source_df["title"][source_idx]
    print(f"Because you liked the {source_type} '{source_title}':")
    for rank, idx in enumerate(top_idxs, start=1):
        idx = int(idx)
        title = target_df["title"][idx]
        score = float(sim_matrix[source_idx][idx])
        print(f"  {rank}. {target_type}: {title} (score: {score:.4f})")

def find_idx(df, title):
    matches = df[df["title"].str.contains(title, case=False, na=False)]
    if matches.empty:
        print(f"No match found for '{title}'")
        return None
    return matches.index[0]

def recommend_by_title(source_type, title, target_type, n=3):
    df_lookup = {"movie": movies_df, "book": books_df}
    idx = find_idx(df_lookup[source_type], title)
    if idx is not None:
        recommend(source_type, idx, target_type, n)

# --- Rating loop ---
def rate_top_matches(source_type, source_idx, target_type):
    sim_matrix, source_df, target_df = sim_lookup[(source_type, target_type)]
    source_title = source_df["title"][source_idx]
    source_id = int(source_df["id"][source_idx])

    print(f"\n=== {source_title} ({source_type}) ===")
    top_idxs = np.argsort(-np.array(sim_matrix[source_idx]))[:3]
    for rank, idx in enumerate(top_idxs, start=1):
        idx = int(idx)
        title = target_df["title"][idx]
        score = float(sim_matrix[source_idx][idx])
        print(f"{rank}. {title} (score: {score:.4f})")
        label = input("   Good match? (1=yes, 0=no): ").strip()
        while label not in ("0", "1"):
            label = input("   Please enter 1 or 0: ").strip()
        cur.execute("""
            INSERT OR IGNORE INTO ratings 
            (source_id, source_media_type, candidate_id, candidate_media_type, cosine_score, rank_position, label)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source_id, source_type, int(target_df["id"][idx]), target_type, score, rank, int(label)))
    conn.commit()

# Example usage:
for i in range(40):
    rate_top_matches("movie", i, "book")
