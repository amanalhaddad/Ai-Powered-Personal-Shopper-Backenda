# AI Personal Shopper — Backend (FastAPI + MongoDB + FAISS + sentence-transformers)

This is a minimal MVP backend for the "AI Personal Shopper" FYP.
It supports:
- Ingesting product metadata (title, description, price, url, platform)
- Creating & persisting embeddings (sentence-transformers)
- Storing product metadata in MongoDB
- Searching recommendations via FAISS vector similarity + simple re-ranking

## Requirements
- Python 3.10+ (3.11 recommended)
- MongoDB (local or remote)
- Optional: GPU for faster embeddings

## Quick start (local)
1. Create venv:
   python -m venv .venv
   source .venv/bin/activate   # mac/linux
   .venv\Scripts\activate      # windows

2. Install dependencies:
   pip install -r requirements.txt

3. Start MongoDB (local) or use a connection string. Default in code: mongodb://localhost:27017

4. Start the API:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

5. Endpoints:
   - POST /ingest/product   <-- ingest product
   - POST /recommend        <-- get recommendations

## Docker (optional)
A Dockerfile and docker-compose.yml are included for local testing (FastAPI + MongoDB).
Use: docker-compose up --build

## Example usage
Ingest product:
curl -X POST http://localhost:8000/ingest/product -H "Content-Type: application/json" -d @sample_product.json

Get recommendations:
curl -X POST http://localhost:8000/recommend -H "Content-Type: application/json" -d '{"query":"waterproof earbuds under 150","top_k":10}'

## Notes & next steps
- For production, use a managed vector DB (Milvus / Pinecone) and a persistent FAISS store (index file + metadata mapping).
- Add authentication, rate limiting, monitoring and background workers for batch embedding ingestion.
- Consider user-event pipeline and personalization (user embedding aggregation, daily recommendation job).

