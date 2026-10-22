# REEL RIOT

**Find your next favorite book through a movie — or your next favorite movie through a book.**

REEL RIOT is a cross-media recommendation system that connects movies and books using semantic similarity and machine-learning reranking. It combines text embeddings, hubness correction, fuzzy title matching, and a trained ranking model to find meaningful connections across media.

The project is under active development and is intended to run locally or on a self-hosted server.

## Demo

![REEL RIOT interface](docs/images/reel-riot-screenshot.png)

![REEL RIOT recommendation demo](docs/images/reel-riot-demo.gif)

> If these images are not present in the repository yet, add them at the paths above or remove the image references until they are available.

## Features

- **Cross-media recommendations:** Discover books related to a movie and movies related to a book.
- **Semantic search:** Use Sentence Transformers embeddings to represent media descriptions as vectors.
- **Hubness correction:** Adjust similarity scores to reduce the influence of candidates that appear similar to many items.
- **Fuzzy title matching:** Find titles from partial or slightly different input with RapidFuzz.
- **Machine-learning reranking:** Refine the initial candidate order using a trained model and candidate features.
- **Catalog ingestion:** Fetch book metadata from Open Library and movie metadata from TMDB.
- **Incremental updates:** Store pagination progress in JSON offset files between ingestion runs.
- **Embedding refresh:** Recalculate embeddings when the catalog changes.
- **Web app and API:** Use the FastAPI application to search titles and request recommendations.

## How It Works

REEL RIOT follows a pipeline from title matching to ranked recommendations:

1. **Match the input title.** RapidFuzz compares the submitted title with titles in the catalog.
2. **Identify the source item.** The application determines the matching title and whether it is a movie or a book.
3. **Find candidates.** The system compares the source item's embedding with items in the opposite media category.
4. **Adjust similarity scores.** Hubness correction modifies the raw similarity scores.
5. **Rerank candidates.** The trained model uses candidate features to refine the recommendation order.
6. **Return recommendations.** The API returns the matched source item and the ranked results.

### Architecture

```mermaid
flowchart TD
    User["User"] --> App["FastAPI Web App / API"]
    App --> Match["Fuzzy Title Matching"]
    Match --> Source["Matched
