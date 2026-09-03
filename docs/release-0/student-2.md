# Student-2 Release 0

Feature documentation lives in [student-2/README.md](../../student-2/README.md).

This microservice covers traveller profiles, budget and pace preferences, interest
selection, accessibility and dietary needs, and the AI-assisted profile-completeness
check that gates trip planning.

## Architecture

```
Browser
  |  HTMX
  v
student2-frontend  :8502   Flask + Jinja + HTMX
  |  REST (BACKEND_URL)
  v
student2-backend   :5502   Flask REST API, validation, AI-Mode
  |                    \
  |  REST               \  POST /api/generate
  v                      v
student2-database :5402   ollama :11434  ->  qwen2.5 / llama3.1
  |
  v
SQLite (student2_data volume)
```

The backend reaches the SQLite data **only** through the database API, so no other
team microservice touches this schema directly. Trip Planning (student-4) consumes
`GET /api/travelers/<id>/profile`, which returns the flattened `preference_set`.

## Data design

**Conceptual** — one traveller has one preference set, many interests, and many
accessibility/dietary needs.

**ERD**

```
Travelers 1 --- 1 Preferences
    | 1
    |---< Interests           (many)
    |---< AccessibilityNeeds  (many)
```

**Logical / physical** — see [schema.sql](../../student-2/database/schema.sql).
Every child table has `ON DELETE CASCADE` against `Travelers(id)`; controlled
vocabularies are `CHECK` constraints; `Travelers.email`, `Travelers.username`,
`Preferences.traveler_id` and `(traveler_id, interest_category)` are unique.
Seed data in [seed.sql](../../student-2/database/seed.sql) provides 12 travellers,
12 preference sets, 26 interests and 12 accessibility needs.

## Plan → Act → Observe → Adapt

| Phase | Endpoint | Behaviour |
|---|---|---|
| Plan | `POST /api/ai/summarise-profile` | Builds the deterministic preference set, then asks the LLM for a summary, planning hints and suggested interests |
| Act | `POST /api/ai/apply-suggested-interests` | Persists only the suggestions a human accepted |
| Observe | `POST /api/ai/check-completeness` | Re-scores the profile and reports what is still missing |
| Adapt | `GET /api/agentic/status` | Recommends the next step until the profile clears the threshold |

`GET /api/agentic/status` returns all four phases in one response for demonstration.

## AI grounding

Prompts include the traveller's stored records and explicitly instruct the model
not to invent preferences. Two guards run on the response:

1. Suggested interest categories outside the schema's allowed list are dropped.
2. Categories the traveller already selected are dropped.

The completeness score is always computed in `backend/preferences.py` from stored
records — the LLM only explains it, never overwrites it. This keeps the gate
reproducible and testable with no LLM running.

## GitHub Actions — `student-2.yml`

Two jobs, triggered on pushes and pull requests touching `student-2/**`:

- **test** — Python 3.12, installs `student-2/requirements.txt`, runs
  `python -m compileall` over all four packages, then `pytest` (56 tests).
  A stubbed Ollama client means CI needs no LLM.
- **docker** — builds the database, backend and frontend images to prove the
  Dockerfiles are valid before Compose integration.

## Testing evidence

56 tests: CRUD across all four tables, constraint and validation failures,
SQL-injection resistance, completeness scoring, AI endpoints with a stubbed LLM,
and the agentic loop.

Verified locally against real Ollama (`llama3.1:8b` and `qwen2.5:0.5b`):
`Frontend → Backend/API → Ollama → LLM` returns a grounded summary in ~14s warm.

## Known issues and limitations

- The Ollama container starts with no models; `qwen2.5:3b` must be pulled once
  before AI-Mode works (`docker compose exec ollama ollama pull qwen2.5:3b`).
- The first AI call after a cold start can take up to a minute while the model
  loads. The client timeout is 120s to absorb this.
- Suggestion quality varies with model size; the 0.5b model often returns no
  suggested interests at all.
