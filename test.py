from sentence_transformers import SentenceTransformer
import sentence_transformers
import requests
import os
from dotenv import load_dotenv

"""movie_titles = ["Interstellar","The Martian","JoJo Rabbit"]
book_titles = ["A Farewell to Arms", "Beneath a Scarlet Sky","Sci-fi" ]
sentences1 = [
    "In a dystopian future where Earth has become near-uninhabitable, a team of astronauts embark on a mission to find a new home for humanity.",
    "An astronaut stranded on Mars must rely on his ingenuity to survive and arrange a potential rescue.",
    "A young German boy in the Hitler Youth, whose hero and imaginary friend is the country's dictator, is shocked to discover that his mother is hiding a Jewish girl in their home.",
]
sentence2 = [
    "An American ambulance driver and an English nurse fall in love in Italy during World War I.",
    "A young Italian man helps Jews escape to Switzerland during World War II.",
    "A wise man tries to save human knowledge from a dark age.",
]
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embeddings1 = model.encode(sentences1)
embeddings2 = model.encode(sentence2)
sim_matrix = sentence_transformers.util.cos_sim(embeddings1, embeddings2)
best_match = 0
for i in range(sim_matrix.shape[0]):
    best_match = int(sim_matrix[i].argmax())
    print(f"best match for {movie_titles[i]} is {book_titles[best_match]} (score: {sim_matrix[i][best_match]:.4f})")"""
load_dotenv()
movie_key = os.getenv("MOVIE_KEY")
search_movie = input("movie: ")
url = "https://api.themoviedb.org/3/search/movie"
headers = {"accept": "application/json"}
params = {"api_key": movie_key, "query": search_movie, "language": "en-US", "page": 1}

response = requests.get(url, headers=headers, params=params)
data = response.json()

for movie in data["results"]:
    print(f"{movie["title"]} - {movie["overview"]}")
