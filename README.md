
# REEL RIOT — FastAPI frontend

A punk-rock frontend for the existing movie/book recommender.

## What it uses

- FastAPI for the API/web server
- RapidFuzz `token_set_ratio` for title matching
- Your existing `reranker_model.pkl`
- Your existing `media.db`
- The same sentence-transformer embeddings and hub correction used by `rec.py`
- A three-color palette: black, cream, red

## Project layout

```text
punk_media_recommender/
├── app.py
├── media.db                 # copy your existing database here
├── reranker_model.pkl       # copy your existing model here
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    └── style.css
```

## Setup

Create/activate your virtual environment, then:

```bash
pip install -r requirements.txt
```

Copy your existing `media.db` into this folder.

Then run:

```bash
uvicorn app:app --reload
```

Open:

http://127.0.0.1:8000

## API

Search RapidFuzz matches:

```text
GET /api/search?q=animal
```

Get recommendations:

```text
GET /api/recommend?q=animal%20farm&n=5
```

Health check:

```text
GET /health
```

## Important

Do not import `rec.py` from the FastAPI app. That script contains setup/test behavior that runs at import time (including Open Library inserts and deletion of omnibus entries). This frontend copies the actual matching/recommendation pipeline into a server-safe class instead.

The app also intentionally makes the 50–70 RapidFuzz range non-interactive: the best fuzzy match is displayed in the UI rather than using Python's `input()`, which would block a web request.
