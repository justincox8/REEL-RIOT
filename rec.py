import joblib
import sqlite3
import pandas as pd
import numpy as np
import sentence_transformers
from rapidfuzz import process, fuzz
import requests

def fetch_single_book(title):
    search_url = "https://openlibrary.org/search.json"
    params = {"q": title, "limit": 1}
    response = requests.get(search_url, params=params)
    data = response.json()

    if not data["docs"]:
        return None

    doc = data["docs"][0]
    work_key = doc["key"]

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
# Load trained model
model = joblib.load("reranker_model.pkl")

conn = sqlite3.connect("media.db")
cur = conn.cursor()

def insert_books(books, theme):
    for book in books:
        cur.execute("""
            INSERT OR IGNORE INTO books (openlibrary_id, title, author, description, theme, first_publish_year)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            book["openlibrary_id"],
            book["title"],
            book["author"],
            book["description"],
            theme,
            book["first_publish_year"],
        ))
    conn.commit()


def load_embeddings(table_name):
    if table_name == "books":
        query = "SELECT id, title, author, embedding FROM books"
    else:
        query = "SELECT id, title, embedding FROM movies"

    df = pd.read_sql_query(query, conn)

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

def find_source(title, high_threshold=70, low_threshold=50):
    normalized_input = title.lower().strip()

    movie_titles_lower = movies_df["title"].str.lower().tolist()
    book_titles_lower = books_df["title"].str.lower().tolist()

    movie_result = process.extractOne(normalized_input, movie_titles_lower, scorer=fuzz.token_set_ratio)
    book_result = process.extractOne(normalized_input, book_titles_lower, scorer=fuzz.token_set_ratio)

    candidates = []
    if movie_result is not None:
        matched_title, score, pos = movie_result
        candidates.append(("movie", matched_title, score, pos))
    if book_result is not None:
        matched_title, score, pos = book_result
        candidates.append(("book", matched_title, score, pos))

    if not candidates:
        print(f"No match found for '{title}'")
        return None, None

    # Pick whichever candidate (movie or book) scored higher
    candidates.sort(key=lambda c: c[2], reverse=True)
    best_type, best_title, best_score, best_pos = candidates[0]

    if best_score >= high_threshold:
        if best_score < 90:
            print(f"Showing results for the {best_type} '{best_title}'")
        idx = movies_df.index[best_pos] if best_type == "movie" else books_df.index[best_pos]
        return best_type, idx

    elif best_score >= low_threshold:
        confirm = input(f"Did you mean the {best_type} '{best_title}'? ({best_score:.0f}% match) [y/n]: ").strip().lower()
        if confirm == "y":
            idx = movies_df.index[best_pos] if best_type == "movie" else books_df.index[best_pos]
            return best_type, idx
        else:
            print("No confirmed match.")
            return None, None

    else:
        print(f"No confident match found for '{title}' (best guess was the {best_type} '{best_title}' at {best_score:.0f}%)")
        return None, None

def find_source_web(title, threshold=50):
    normalized_input = title.lower().strip()

    movie_titles_lower = movies_df["title"].str.lower().tolist()
    book_titles_lower = books_df["title"].str.lower().tolist()

    movie_result = process.extractOne(
        normalized_input,
        movie_titles_lower,
        scorer=fuzz.token_set_ratio
    )

    book_result = process.extractOne(
        normalized_input,
        book_titles_lower,
        scorer=fuzz.token_set_ratio
    )

    candidates = []

    if movie_result is not None:
        matched_title, score, pos = movie_result
        candidates.append(("movie", matched_title, score, pos))

    if book_result is not None:
        matched_title, score, pos = book_result
        candidates.append(("book", matched_title, score, pos))

    if not candidates:
        return None, None

    candidates.sort(key=lambda c: c[2], reverse=True)

    best_type, best_title, best_score, best_pos = candidates[0]

    if best_score < threshold:
        return None, None

    idx = (
        movies_df.index[best_pos]
        if best_type == "movie"
        else books_df.index[best_pos]
    )

    return best_type, idx

def get_source(prompt):
    while True:
        title = input(prompt).strip()
        source_type, idx = find_source(title)
        if idx is not None:
            return source_type, idx
        print("Let's try again.")

def rate_specific_book_against_movies(book_title, movie_indices, label=0):
    book_idx = find_source(books_df, book_title)
    if book_idx == None:
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

    recommendations = []

    for rank, position in enumerate(best_positions, start=1):

        idx = int(all_sorted_idxs[position])

        title = target_df.iloc[idx]["title"]

        cosine_score = float(sim_matrix[source_idx][idx])

        probability = float(probabilities[position])

        recommendations.append({
            "rank": rank,
            "type": target_type,
            "title": title,
            "author": target_df.iloc[idx]["author"]
            if target_type == "book" and "author" in target_df.columns
            else None,
            "cosine": round(cosine_score, 4),
            "score": round(probability * 100, 1),
})

    return recommendations



book_hub_scores = movie_to_book_sim.mean(axis=0)  # one number per book
movie_hub_scores = movie_to_book_sim.mean(axis=1)
books_df["hub_score"] = np.array(book_hub_scores)
movies_df["hub_score"] = np.array(movie_hub_scores)





