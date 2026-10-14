#for recalculating embeddings when needed
# Pull the text + id for each table fresh from the database
movies_df = pd.read_sql_query("SELECT id, title, overview FROM movies", conn)
books_df = pd.read_sql_query("SELECT id, title, description FROM books", conn)
songs_df = pd.read_sql_query("SELECT id, title, theme FROM songs", conn)

# Encode with the new model
movie_embeddings = model.encode(movies_df["overview"].tolist())
book_embeddings = model.encode(books_df["description"].tolist())
song_embeddings = model.encode(songs_df["theme"].tolist())

# Overwrite the old embeddings
save_embeddings("movies", movies_df["id"], movie_embeddings)
save_embeddings("books", books_df["id"], book_embeddings)
save_embeddings("songs", songs_df["id"], song_embeddings)

