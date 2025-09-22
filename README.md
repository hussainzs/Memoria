# Memoria

Long-term memory database and reasoning pipeline that grounds LLM outputs with citations while giving users full control over their memories.

## Run with Docker

1. **Start the services**:
   ```bash
   docker compose up --build
   ```

API available at `http://localhost:8000` with automatic docs at `http://localhost:8000/docs`.

If using Docker, an `ollama` service is included and exposed on `http://localhost:11434`. The backend defaults to `LLM_PROVIDER=ollama` and `LLM_MODEL=llama3.2:3b-instruct`.

Frontend dev server:

```bash
cd frontend && npm install && npm run dev
```

## Backend endpoints (stubs)
- POST `/memories` — ingest new memory
- GET `/memories?user_id=...` — list user memories
- POST `/retrieve` — hybrid retrieval placeholder
- POST `/ask` — orchestration placeholder (will add grounding + verifier)
- POST `/feedback` — user feedback signal

## Database schema (pgvector + graph)
See `backend/app/db/schema.sql`. Uses `memories`, `entities`, and `memory_links` with `VECTOR(1536)`.

## Project structure
- `backend/` FastAPI app, services for indexer, retriever, memory manager
- `frontend/` Next.js app with basic UI skeleton
- `docker-compose.yml` brings up Postgres (pgvector) and Redis
