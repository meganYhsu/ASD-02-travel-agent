# Student 1 - Traveler Preferences Microservice

**Kyu Ri Kim (24988432)** - Feature 1 of the ASD-02 AI Travel Agent.

Travellers build a profile - budget range, travel style, interests, dietary and
accessibility needs - and the feature turns that profile into a **structured
preference set** the other four features consume when personalising a trip.

## Microservices

| Service | Port | Container | Responsibility |
|---|---|---|---|
| Frontend | 3001 | `student1-frontend` | HTMX page, proxies `/api/*` to the backend |
| Backend/API | 5001 | `student1-backend` | HTML fragments, AI-Mode, validation |
| Database | 6001 | `student1-database` | Owns `preferences.db`, JSON CRUD API |

The database container is the **only** service that opens the SQLite file.
The backend reaches it over HTTP, and so must every other team's backend.

## Database schema

| Table | Columns | Seeded |
|---|---|---|
| `Travelers` | name, email (unique), home_location, travel_style | 10 |
| `Preferences` | traveler_id (unique), budget_min, budget_max, pace, currency | 10 |
| `Interests` | traveler_id, interest_category, priority (1-5) | 14 |
| `AccessibilityNeeds` | traveler_id, requirement, dietary_restriction | 10 |

Child rows cascade on traveller delete. `travel_style` is one of
`budget` / `mid-range` / `luxury`; `pace` is `relaxed` / `balanced` / `packed`.

## Database API (port 6001)

CRUD on every table, all statements parameterised, all payloads validated:

```
GET    /travelers                     GET    /travelers/<id>
POST   /travelers                     PUT    /travelers/<id>
DELETE /travelers/<id>

GET    /preferences                   GET    /preferences/<traveler_id>
POST   /preferences                   (upsert - one row per traveller)
PUT    /preferences/<traveler_id>     DELETE /preferences/<traveler_id>

GET    /interests?traveler_id=<id>    GET    /interests/<id>
POST   /interests                     PUT    /interests/<id>
DELETE /interests/<id>

GET    /accessibility-needs?traveler_id=<id>   GET /accessibility-needs/<id>
POST   /accessibility-needs                    PUT /accessibility-needs/<id>
DELETE /accessibility-needs/<id>

GET    /preference-set/<traveler_id>  the whole profile in one document
GET    /health
```

## Cross-feature contract

Other backends read a traveller's preferences from **one** endpoint:

```
GET http://student1-backend:5001/preference-set/<traveler_id>
```

```jsonc
{
  "traveler":            { "traveler_id": 1, "name": "...", "travel_style": "mid-range" },
  "preferences":         { "budget_min": 2000, "budget_max": 3500, "pace": "balanced" },
  "interests":           [ { "interest_category": "Food and dining", "priority": 5 } ],
  "accessibility_needs": [ { "requirement": "...", "dietary_restriction": "Vegetarian" } ],
  "completeness":        { "score": 100, "ready_for_trip_planning": true, "gaps": [] }
}
```

`completeness.ready_for_trip_planning` lets Trip Planning refuse to generate an
itinerary for a profile that is not filled in yet.

## AI-Mode

Ollama with `qwen2.5:0.5b` (same model as students 2 and 3), reached through
the OpenAI-compatible API. Prompt assets live in `backend/prompts/`.

Two AI endpoints, both callable from the frontend:

- `POST /summarise/<traveler_id>` - turns the stored profile into the four-line
  structured preference set.
- `POST /completeness/<traveler_id>` - a deterministic check scores the profile,
  then the model explains the gaps. **The AI never decides the score.**

## Agentic loop: Plan -> Act -> Observe -> Adapt

`POST /summarise/<id>` runs the full loop and prints each stage to stdout, so it
is visible live in `docker compose logs -f student1-backend`:

| Stage | What happens |
|---|---|
| **Plan** | Decide which evidence the preference set needs |
| **Act** | Fetch the profile from the database API, call the LLM |
| **Observe** | Check the answer against the evidence - all four labels present, and no section claiming "none recorded" when the database holds real data |
| **Adapt** | Re-prompt once with the faults named; keep the retry only if it has fewer faults |

A real example - the model dropped a traveller's dietary requirement, and the
loop caught and corrected it:

```
[AGENTIC LOOP][PLAN] Summarise traveler 3: need profile, budget, interests and accessibility needs from the database API.
[AGENTIC LOOP][ACT] Retrieved profile for Traveller Three from Melbourne, Australia; calling qwen2.5:0.5b for the structured preference set.
[AGENTIC LOOP][OBSERVE] Model returned 104 characters; issues found: 1 (CONSTRAINTS claims nothing is recorded, but this traveller has accessibility or dietary needs that must be listed)
[AGENTIC LOOP][ADAPT] Re-prompting once with the rejected answer's faults named.
[AGENTIC LOOP][OBSERVE] After adapt, issues: 0. Retry accepted.
```

## Running it

As part of the integrated application, from the repository root:

```bash
docker compose up --build
```

Then open the shared home page at http://127.0.0.1:8080 and follow
**Traveler Preferences**, or go straight to http://127.0.0.1:3001.

Pull the model once, into the shared Ollama container:

```bash
docker compose exec ollama ollama pull qwen2.5:0.5b
```

Locally without Docker (three terminals, from `student-1/`):

```bash
python database/db_api.py
python backend/app.py
python frontend/app.py
```

## Tests

```bash
python tests/check_seed.py        # every table has at least 10 records
python tests/test_endpoints.py    # 16 endpoint and validation checks
python tests/test_crud_cycle.py   # 12 checks: create -> read -> update -> delete -> cascade
```

`.github/workflows/student-1.yml` runs all three on every push, then builds the
three Docker images.

## Known issues and limitations

- `qwen2.5:0.5b` is small and sometimes drops a line from the preference set.
  The Observe stage catches this and re-prompts once; if the retry is no better
  the response is shown as returned, flagged for human review.
- The database container has no volume, so it reseeds on recreate. Intentional
  for Release 0 demos - the ten seed records are always present.
- Login is handled by the shared home page; this feature does not yet scope the
  traveller list to the logged-in user.
