# Student-2 — Traveller Preferences Microservice

Kyu Ri Kim · Feature 1 (Traveller Preferences) · ASD-02 Travel Agent

Captures a traveller's profile, budget, pace, interests, accessibility and dietary
needs, and exposes a **structured preference set** that the other microservices
(notably Trip Planning) consume to personalise itineraries.

## Services

| Service | Port | Role |
|---|---|---|
| `student2-database` | 5402 | SQLite store + CRUD API over the four tables |
| `student2-backend`  | 5502 | Public REST API, validation, AI-Mode via Ollama |
| `student2-frontend` | 8502 | HTMX dashboard |

The backend never opens the SQLite file. All data access goes through the
database API over HTTP, per the Release 0 cross-feature integration rule.

## Database

Four tables, each seeded with **at least ten records**:

- **Travelers** — `full_name`, `username`, `email` (unique), `home_location`, `travel_style`
- **Preferences** — `traveler_id`, `budget_min`/`budget_max`, `currency`, `pace`, `preferred_trip_length_days` (one set per traveller)
- **Interests** — `traveler_id`, `interest_category`, `priority`
- **AccessibilityNeeds** — `traveler_id`, `requirement`, `dietary_restriction`, `notes`

Foreign keys cascade on delete, so removing a traveller removes their whole
preference set. Controlled vocabularies are enforced by `CHECK` constraints in
`schema.sql` *and* re-validated in `backend/validation.py`.

## API

CRUD on `/api/travelers`, `/api/preferences`, `/api/interests`,
`/api/accessibility-needs`, plus:

| Endpoint | Purpose |
|---|---|
| `GET /api/travelers/<id>/profile` | Aggregated profile + preference set + completeness — **this is what other services call** |
| `GET /api/travelers/<id>/completeness` | Deterministic completeness gate (no LLM) |
| `POST /api/ai/summarise-profile` | AI summary + planning hints + suggested interests |
| `POST /api/ai/check-completeness` | AI explanation of what is missing |
| `POST /api/ai/apply-suggested-interests` | Persists only human-accepted suggestions |
| `GET /api/agentic/status` | Plan → Act → Observe → Adapt |

### Completeness scoring

Traveller record 25 · preferences 30 · interests 25 (half credit below three) ·
accessibility 20. A profile is `ready_for_trip_planning` at ≥ 75 with both
preferences and at least one interest. The score is computed from stored records
only — the LLM explains it but can never change it.

## Plan → Act → Observe → Adapt

| Phase | In this service |
|---|---|
| **Plan** | `summarise-profile` proposes a structured preference set and suggested interests |
| **Act** | `apply-suggested-interests` persists only what the user accepted |
| **Observe** | `check-completeness` re-scores the profile and reports what is missing |
| **Adapt** | `agentic/status` recommends the next step until the profile clears the threshold |

## Running locally

Docker Compose (from the repository root) is the supported path:

```bash
docker compose up --build student2-database student2-backend student2-frontend ollama
```

Then pull the model **once** into the Ollama container:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

Open <http://localhost:8502>, or the team home page at <http://localhost:8080>.

### Without Docker

```bash
cd student-2 && pip install -r requirements.txt
PORT=5402 python database/app.py &
PORT=5502 DATABASE_SERVICE_URL=http://127.0.0.1:5402 python backend/app.py &
PORT=8502 BACKEND_URL=http://127.0.0.1:5502 python frontend/app.py
```

See `.env.example` for every supported variable.

## Tests

```bash
cd student-2 && pytest
```

56 tests covering CRUD on all four tables, constraint and validation failures,
SQL-injection resistance, the completeness scoring rules, the AI endpoints
(with a stubbed LLM, so no Ollama needed) and the agentic loop.

## Known limitations

- Interest suggestions come from a small local model; output quality varies by model.
- The first AI call after a cold container start is slow while Ollama loads the model — the client allows 120s.
- `qwen2.5:3b` must be pulled into the Ollama container before AI-Mode works.
