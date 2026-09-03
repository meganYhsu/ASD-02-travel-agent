# Student-5: Travel Documents & Pre-Trip Preparation

Release 0 microservice for travel document management, demonstration entry requirements, compliance checking, packing lists and pre-trip tasks.

**Disclaimer:** Entry requirements in this release are demonstration data only. They are not official immigration advice. Always verify requirements with government sources before travelling.

## Feature purpose

Help a traveller prepare for a trip by storing travel documents, comparing them with demonstration destination requirements, raising expiry alerts, generating a personalised packing list and pre-trip tasks with Ollama, and tracking checklist completion.

## Architecture

User -> HTMX frontend (port 8505) -> Flask REST API (port 5505) -> SQLite database service (port 5405)

AI flow: User -> frontend -> Flask API -> Ollama (port 11434) -> qwen2.5:3b -> structured JSON -> frontend

The frontend never queries SQLite. SQL lives in `database/db.py` and uses parameterised queries.

## Frontend

`student-5/frontend` is a Flask + HTMX dashboard with sections for documents, compliance, entry requirements, packing, pre-trip tasks, and the Plan -> Act -> Observe -> Adapt board.

## Backend / API

`student-5/backend` exposes REST CRUD plus AI, alerts, completion and agentic status endpoints.

JSON shape:

- success: `{ "success": true, "data": ... }`
- error: `{ "success": false, "error": "..." }`

## Database

SQLite tables and seed counts:

- Documents: 12
- EntryRequirements: 12
- PackingLists: 10
- ChecklistItems: 20
- PreTripTasks: 12

`trip_id` and `traveller_id` are string references so this service does not create duplicate Trip/Traveller tables.

## API endpoints

- GET/POST `/api/documents`
- GET/PUT/DELETE `/api/documents/<id>`
- GET/POST `/api/entry-requirements`
- GET/PUT/DELETE `/api/entry-requirements/<id>`
- GET/POST `/api/packing-lists`
- GET/PUT/DELETE `/api/packing-lists/<id>`
- GET `/api/packing-lists/<id>/progress`
- GET/POST `/api/checklist-items`
- GET/PUT/DELETE `/api/checklist-items/<id>`
- PATCH `/api/checklist-items/<id>/complete`
- GET/POST `/api/pre-trip-tasks`
- GET `/api/pre-trip-tasks/progress`
- GET/PUT/DELETE `/api/pre-trip-tasks/<id>`
- PATCH `/api/pre-trip-tasks/<id>/complete`
- POST `/api/ai/check-compliance`
- POST `/api/ai/generate-pretrip-checklist`
- POST `/api/ai/save-pretrip-checklist`
- POST `/api/alerts/compliance`
- GET `/api/agentic/status`
- GET `/health`

Filters include `traveller_id`, `status`, `destination`, `nationality`, `trip_id` and `packing_list_id`.

## Ollama / LLM

- `OLLAMA_BASE_URL` default `http://127.0.0.1:11434`
- `OLLAMA_MODEL` default `qwen2.5:3b`
- Timeouts and connection failures return 503
- Malformed model JSON returns 502
- The model is instructed not to invent immigration rules
- AI suggestions are not saved until the traveller reviews and accepts them

## Plan -> Act -> Observe -> Adapt

1. PLAN: compliance check and packing/task generation using destination, dates, climate, activities, documents and stored requirements.
2. ACT: traveller reviews suggestions, saves approved items, completes packing/tasks, updates documents.
3. OBSERVE: alerts, expiry, missing documents, incomplete items and days until departure.
4. ADAPT: rerun compliance or regenerate checklists when inputs or progress change.

## Run locally

```
python -m venv .venv
.venv\Scripts\activate
pip install -r student-5/requirements.txt

# terminal 1
set DATABASE_PATH=student-5/database/data/travel_docs.db
python student-5/database/app.py

# terminal 2
set DATABASE_SERVICE_URL=http://127.0.0.1:5405
python student-5/backend/app.py

# terminal 3
set BACKEND_URL=http://127.0.0.1:5505
python student-5/frontend/app.py
```

- UI: http://localhost:8505
- API: http://localhost:5505
- Database: http://localhost:5405
- Homepage: http://localhost:8080 (Docker shared frontend)

Optional local Ollama:

```
ollama serve
ollama pull qwen2.5:3b
```

## Seed database

The database service creates schema and loads `database/seed.sql` automatically when the database is empty.

## Tests

```
cd student-5
pip install -r requirements.txt
pytest
```

Ollama is mocked. GitHub Actions does not need a live model.

## Docker

From the repository root:

```
docker compose up --build
```

Then open http://localhost:8505 or the homepage at http://localhost:8080.

```
docker compose exec ollama ollama pull qwen2.5:3b
```

## Environment variables

- `DATABASE_PATH` SQLite file path
- `DATABASE_SERVICE_URL` Backend to database
- `BACKEND_URL` Frontend to backend
- `OLLAMA_BASE_URL` Ollama host
- `OLLAMA_MODEL` Approved local model
- `OLLAMA_TIMEOUT_SECONDS` AI timeout
- `EXPIRY_WARNING_DAYS` Expiry alert window

## Known limitations

- Entry requirements are sample data, not live immigration rules.
- No login/auth in Release 0; traveller and trip IDs are demo strings.
- Live AI quality depends on the local Ollama model being pulled.
- RAG / MCP / multi-agent features are out of scope for Release 0.
