import joblib
import sqlite3
import pandas as pd
import numpy as np
import sentence_transformers

# Load trained model
model = joblib.load("reranker_model.pkl")

conn = sqlite3.connect("media.db")
cur = conn.cursor()


def load_embeddings(table_name):
    df = pd.read_sql_query(f"SELECT id, title, embedding FROM {table_name}", conn)
    df["embedding"] = df["embedding"].apply(
        lambda b: np.frombuffer(b, dtype=np.float32)
    )
    return df


# --- Load everything ---
movies_df = load_embeddings("movies")
books_df = load_embeddings("books")

movie_embeddings = np.stack(movies_df["embedding"].to_numpy())
book_embeddings = np.stack(books_df["embedding"].to_numpy())


# --- Raw similarity ---
movie_to_book_sim = sentence_transformers.util.cos_sim(
    movie_embeddings, book_embeddings
).numpy()


# --- Hub correction ---
book_baseline = movie_to_book_sim.mean(axis=0)
adjusted_movie_to_book_sim = movie_to_book_sim - book_baseline

adjusted_book_to_movie_sim = adjusted_movie_to_book_sim.T


sim_lookup = {
    ("movie", "book"): (adjusted_movie_to_book_sim, movies_df, books_df),
    ("book", "movie"): (adjusted_book_to_movie_sim, books_df, movies_df),
}

def find_idx(df, title):
    matches = df[df["title"].str.contains(title, case=False, na=False)]
    if matches.empty:
        print(f"No match found for '{title}'")
        return None
    return matches.index[0]

def rate_specific_book_against_movies(book_title, movie_indices, label=0):
    book_idx = find_idx(books_df, book_title)
    if book_idx is None:
        return
    book_id = int(books_df["id"][book_idx])
    book_display_title = books_df["title"][book_idx]

    # Full ranking of this book's similarity across ALL movies, to get its true rank per movie
    book_to_movie_row = np.array(adjusted_movie_to_book_sim.T[book_idx])
    sorted_movie_idxs = np.argsort(-book_to_movie_row)

    for movie_idx in movie_indices:
        movie_id = int(movies_df["id"][movie_idx])
        movie_title = movies_df["title"][movie_idx]
        score = float(book_to_movie_row[movie_idx])
        rank = int(np.where(sorted_movie_idxs == movie_idx)[0][0]) + 1

        print(f"{book_display_title} vs {movie_title} — cosine={score:.4f}, rank={rank}, labeling as {label}")

        cur.execute("""
            INSERT OR IGNORE INTO ratings 
            (source_id, source_media_type, candidate_id, candidate_media_type, cosine_score, rank_position, label)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (movie_id, "movie", book_id, "book", score, rank, label))

    conn.commit()

def recommend_with_model(source_type, source_idx, target_type, n=3):
    sim_matrix, source_df, target_df = sim_lookup[(source_type, target_type)]

    # Sort candidates by similarity
    all_sorted_idxs = np.argsort(-np.asarray(sim_matrix[source_idx]))

    # Candidate features
    features = []

    for rank, idx in enumerate(all_sorted_idxs, start=1):
        idx = int(idx)
        cosine_score = float(sim_matrix[source_idx][idx])
        candidate_hub_score = float(target_df.iloc[idx]["hub_score"])
        features.append([cosine_score, rank, candidate_hub_score])

    X = pd.DataFrame(features, columns=["cosine_score", "rank_position", "candidate_hub_score"])

    # Model prediction
    predictions = model.predict(X)

    # If your model supports predict_proba
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)[:, 1]
    else:
        probabilities = predictions.astype(float)

    # Rank by probability that candidate is a good match
    best_positions = np.argsort(-probabilities)[:n]

    source_title = source_df.iloc[source_idx]["title"]

    print(f"\nBecause you liked the " f"{source_type} '{source_title}':")

    for rank, position in enumerate(best_positions, start=1):

        idx = int(all_sorted_idxs[position])

        title = target_df.iloc[idx]["title"]
        cosine_score = float(sim_matrix[source_idx][idx])
        probability = float(probabilities[position])

        print(
            f"  {rank}. {target_type}: {title} "
            f"(cosine={cosine_score:.4f}, "
            f"model_probability={probability:.4f})"
        )

# Find some movie indices to test against — pick a spread of genres unrelated to these books
unrelated_movie_titles = ["Jaws", "28 Years Later", "Hungry", "Return to Silent Hill", "Saccharine"]
unrelated_movie_idxs = [find_idx(movies_df, t) for t in unrelated_movie_titles]
unrelated_movie_idxs = [i for i in unrelated_movie_idxs if i is not None]

rate_specific_book_against_movies("Beast Quest", unrelated_movie_idxs, label=0)
rate_specific_book_against_movies("Wet Magic", unrelated_movie_idxs, label=0)
rate_specific_book_against_movies("Frenchman's Creek", unrelated_movie_idxs, label=0)

book_hub_scores = movie_to_book_sim.mean(axis=0)  # one number per book
movie_hub_scores = movie_to_book_sim.mean(axis=1)
books_df["hub_score"] = np.array(book_hub_scores)
movies_df["hub_score"] = np.array(movie_hub_scores)



for i in range(400):
    recommend_with_model("movie", i, "book", n=5)

