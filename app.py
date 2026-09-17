from pathlib import Path

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import rec

BASE_DIR = Path(__file__).resolve().parent


app = FastAPI(title="REEL RIOT", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")



@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )

@app.get("/api/search")
def search(
    q: str = Query(min_length=1, max_length=200),
):
    try:
        source_type, source_idx = rec.find_source_web(q)

        if source_idx is None:
            return {
                "query": q,
                "found": False,
                "source": None,
            }

        df = (
            rec.movies_df
            if source_type == "movie"
            else rec.books_df
        )

        return {
            "query": q,
            "found": True,
            "source": {
                "type": source_type,
                "title": df.iloc[source_idx]["title"],
                "index": int(source_idx),
            },
        }

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )

@app.get("/api/recommend")
def recommend(
    q: str = Query(min_length=1, max_length=200),
    n: int = Query(default=5, ge=1, le=10),
):
    try:
        source_type, source_idx = rec.find_source_web(q)

        if source_idx is None:
            return {
                "source": None,
                "recommendations": [],
            }

        source_df = (
            rec.movies_df
            if source_type == "movie"
            else rec.books_df
        )

        source_title = source_df.iloc[source_idx]["title"]

        target_type = (
            "book"
            if source_type == "movie"
            else "movie"
        )

        recommendations = rec.recommend_with_model(
            source_type,
            source_idx,
            target_type,
            n=n,
        )

        return {
            "source": {
                "type": source_type,
                "title": source_title,
                "index": int(source_idx),
            },
            "recommendations": recommendations,
        }

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )

@app.get("/health")
def health():
    return {"status": "ok"}
