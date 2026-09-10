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


def recommend_with_model(source_type, source_idx, target_type, n=3):
    sim_matrix, source_df, target_df = sim_lookup[(source_type, target_type)]

    # Sort candidates by similarity
    all_sorted_idxs = np.argsort(-np.asarray(sim_matrix[source_idx]))

    # Candidate features
    features = []

    for rank, idx in enumerate(all_sorted_idxs, start=1):
        idx = int(idx)

        cosine_score = float(sim_matrix[source_idx][idx])

        # MUST match the features used during model training
        features.append([cosine_score, rank])

    # Convert to numpy array
    X = pd.DataFrame(features, columns=["cosine_score", "rank_position"])

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


for i in range(200, 250):
    recommend_with_model("movie", i, "book", n=5)
