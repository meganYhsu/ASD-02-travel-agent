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

## Shared MCP tools (Release 1)

The **MCP tools** card on the page runs a tool on the shared MCP server for the
selected traveller:

```
frontend (3001) -> backend POST /mcp/tool (5001) -> shared MCP HTTP server (7004)
  -> mcp_mode.py -> tools.py -> database API GET /preference-set/<id> (6001)
```

| Tool | Returns |
|---|---|
| `get_traveler_profile` | name, home location, travel style, budget range, pace |
| `get_traveler_interests` | interests ranked by priority |
| `get_accessibility_needs` | accessibility requirements and dietary restrictions |

Boundaries: the backend only forwards these three tool names (anything else is
a 400), and each tool only accepts a positive integer `traveler_id`.

The MCP server is not containerised. Start it on the host before using the card:

```bash
python3 ai-services/mcp-server/http_server.py
```

In Docker the backend reaches it at `http://host.docker.internal:7004`
(`MCP_BASE_URL`). `MCP_ENABLED=false` switches the integration off; CI does
this, and the route then answers `503 MCP is disabled`.

## Shared RAG questions (Release 1)

The **Ask the travel knowledge base** card sends a question to the shared RAG
server and shows a grounded answer:

```
frontend (3001) -> backend POST /rag/ask (5001) -> shared RAG server POST /rag/answer (7001)
  -> ChromaDB search (nomic-embed-text) -> grounded answer (llama3.1:8b)
```

- Each answer shows a **confidence** rating and the **source chunks** it used.
- If the server answers "Insufficient evidence", or answers without citing a
  retrieved chunk, the page shows an **insufficient-context** message instead.
- Questions must be 1-300 characters.

Student 1's data is indexed as one chunk per traveller (`student1-traveller-<id>`),
built from `/preference-set/<id>` in `rag-server/rag_pipeline.py`. A chunk
covers the traveller's home, style, budget, pace, interests and needs, so a
question that names a traveller retrieves all of it.

Run the RAG server on the host, with Ollama running and both models pulled:

```bash
ollama pull nomic-embed-text
pip install -r rag-server/requirements.txt
BOOKING_SERVICE_URL=http://127.0.0.1:6002 TRAVEL_PLAN_SERVICE_URL=http://127.0.0.1:6004 \
  python rag-server/rag_http_server.py
curl -X POST http://127.0.0.1:7001/rag/refresh   # rebuild the index from live data
```

The two URLs point the student-2 and student-4 loaders at their docker-compose
ports. In Docker the backend reaches the server at
`http://host.docker.internal:7001` (`RAG_BASE_URL`). `RAG_ENABLED=false`
switches it off; CI does this, and the route answers `503 RAG is disabled`.

Example questions: "What dietary restriction does Traveller One have?",
"Which travellers have a luxury travel style?"

## Multi-Agent preference review (Release 2)

Frontend -> backend -> shared Multi-Agent server (`ai-services/multi-agent-server`,
port 6767, not containerised) -> Planner -> Worker -> Reviewer -> Human Review.

The backend sends the selected traveller's preference set (profile without
the email address, budget and pace, interests, accessibility needs, and the
deterministic completeness verdict) as `service=traveller`,
`task=review_preferences`. The Planner decides what to check, the Worker
reviews the profile and writes a trip-planning brief, and the Reviewer checks
that brief against the evidence. The person using the page then records
**Accept**, **Partially Accept** or **Reject** with a reason or correction of
at least 20 characters. The shared server saves the decision; it never
changes the traveller's data.

| Backend route | Purpose |
|---|---|
| `POST /multi-agent/workflow` | `traveler_id`, optional `user_request` (max 500 chars). Runs the workflow, returns the four stages as HTML. |
| `GET /multi-agent/workflows/<id>` and `GET /multi-agent/lookup?workflow_id=<id>` | Reload a saved workflow with its latest decision. |
| `POST /multi-agent/workflows/<id>/review` | `decision`, `reason`, optional `evidence`. Records the human decision. |
| `GET /multi-agent/evidence/<traveler_id>` | The JSON body sent to the shared server (used by the terminal client). |

Workflow IDs must be UUIDs, and only workflows with this feature's service and
task are shown or reviewed, because the shared server keeps every student's
history together.

From the terminal (backend and shared server running):

```bash
python student-1/tools/preferences_review_cli.py --traveler-id 1
```

It prints each stage, prompts for the human decision, and can save the
result with `--save`. Pass `--decision` and `--reason` to run it without prompts.

### AI switches

`AI_MODE_ENABLED`, `MCP_ENABLED`, `RAG_ENABLED` and `MULTI_AGENT_ENABLED` are
**off unless set to `true`**, so CI and the AWS deployment run the cloud
baseline with no extra configuration. `docker-compose.yml` and
`.env.example` turn them on for local runs. With them off, the AI routes
answer 503 and the completeness score still works without the AI explanation.

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

Start the shared AI services on the host first (each in its own terminal):
the MCP server, the RAG server, and the Multi-Agent server
(`python ai-services/multi-agent-server/app.py`).

Locally without Docker (three terminals, from `student-1/`, after
`cp .env.example .env` so the AI switches are on):

```bash
python database/db_api.py
python backend/app.py
python frontend/app.py
```

## Tests

Release 2 pytest suites (no servers needed; the backend and database API run
in-process and the Multi-Agent server is stubbed):

```bash
cd student-1
python -m pytest -v
```

| Suite | What it covers |
|---|---|
| `test_release2_endpoints.py` | **The two post-commit endpoint functions:** `POST /travelers` (`add_traveler`) and `POST /travelers/<id>/update` (`update_traveler`). Success, persistence, validation, duplicate email, unknown ID, HTML escaping, database down. |
| `test_release2_multi_agent.py` | Evidence sent to the shared server, the four stages rendered, human-review validation and recording, foreign or malformed workflow IDs, server down. |
| `test_release2_cloud_ready.py` | AI switches default to off, AI routes refuse with 503, CRUD and health still work, configurable navigation URL. |

Live-server scripts (database API and backend running):

```bash
python tests/check_seed.py        # every table has at least 10 records
python tests/test_endpoints.py    # 16 endpoint and validation checks
python tests/test_crud_cycle.py   # 12 checks: create -> read -> update -> delete -> cascade
python tests/test_mcp.py          # MCP boundaries, plus tool results (or the disabled response)
python tests/test_rag.py          # RAG input checks, grounded + insufficient-context answers (or disabled)
python tests/cloud_smoke.py --frontend http://127.0.0.1:3001   # deployment smoke test
```

`.github/workflows/student-1.yml` runs on every push to `student-1/**` with
every AI switch off. It runs pip-audit, the seed check, the two endpoint
suites (JUnit XML uploaded as the `student-1-test-results` artifact), the
Multi-Agent and cloud-baseline suites, and the live scripts. It then builds
the three images and runs them on a Docker network the way ECS does, smoke
testing them through the frontend.

### Pre-commit security scans

From the repository root, once per clone:

```bash
pip install pre-commit
pre-commit install
```

Each commit then runs the team's shared hooks plus the Student 1 hooks:
detect-secrets, the Ruff security (`S`) rules on `student-1/`, pip-audit on
the three student-1 requirement files, and the student-1 pytest suites. See
`evidence/security/pre-commit-security-report.md` for the results.

## Known issues and limitations

- `qwen2.5:0.5b` is small and sometimes drops a line from the preference set.
  The Observe stage catches this and re-prompts once; if the retry is no better
  the response is shown as returned, flagged for human review.
- The database container has no volume, so it reseeds on recreate. Intentional
  for Release 0 demos - the ten seed records are always present.
- The Multi-Agent workflow is synchronous: the page waits for all three agents
  (up to 420 s). With `qwen2.5:0.5b` the Reviewer often repeats the Worker's
  answer; `qwen2.5:3b` (the shared server's default) gives more useful reviews.
- Login is handled by the shared home page; this feature does not yet scope the
  traveller list to the logged-in user.
