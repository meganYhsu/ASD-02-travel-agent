# Shared RAG Server

Shared retrieval-augmented travel assistant used by student microservices. It indexes approved Markdown documents at startup, retrieves relevant sections with deterministic term scoring, and optionally asks Ollama to compose a grounded answer.

## API

- `GET /health` returns service status and indexed chunk count.
- `POST /query` accepts `{ "question": "..." }` and returns an answer, retrieval mode, disclaimer, and source metadata.

If Ollama is unavailable, the query still succeeds in `retrieval_only` mode using the highest-ranked source. Questions with no relevant source return `no_match` rather than an invented answer.

Docker Compose defaults to retrieval-only mode so the assistant remains usable on machines with limited Docker memory. Set `RAG_GENERATION_ENABLED: "true"` for the `rag-server` service when Ollama generation has been verified on the host.

## Configuration

- `PORT`, default `7005`
- `RAG_DOCUMENT_PATHS`, OS path-separated Markdown files or directories
- `RAG_GENERATION_ENABLED`, default `true`
- `OLLAMA_BASE_URL`, default `http://127.0.0.1:11434`
- `OLLAMA_MODEL`, default `qwen2.5:3b`
- `OLLAMA_TIMEOUT_SECONDS`, default `120`

## Run and verify

From the repository root:

```powershell
docker compose up --build -d rag-server student5-database student5-backend student5-frontend
docker compose exec ollama ollama pull qwen2.5:3b
curl.exe http://localhost:7005/health
curl.exe -X POST http://localhost:7005/query -H "Content-Type: application/json" -d '{"question":"What should I check before travelling with my passport?"}'
```

Run its isolated tests with:

```powershell
python -m pytest ai-services/rag-server/test_app.py -q
```