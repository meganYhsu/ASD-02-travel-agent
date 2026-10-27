## Student 4 - Testing Instructions


### Pre-commit security checks

From the repository root, create an isolated tooling environment and install the
local Git hook:

```bash
python3.12 -m venv .venv-security
.venv-security/bin/python -m pip install pre-commit==4.3.0
.venv-security/bin/python -m pre_commit validate-config
.venv-security/bin/python -m pre_commit install
bash scripts/security/run-checks.sh
```

Python 3.12 and Node.js/npm must be available. The first scan downloads the pinned
hook tools; dependency audits require internet access. No application dependencies
are upgraded or application databases accessed by these commands.

The root `.pre-commit-config.yaml` checks staged files for secrets without online
credential verification, runs Ruff security rules on changed shared Python code,
audits the shared Multi-Agent/MCP/local RAG Python requirements, and audits all
three Student 4 Node lockfiles. Other students' Node dependency manifests are not
audited by this Student 4 setup. Their individual scanning coverage remains their
responsibility. Node audit checks use the lockfiles without running package scripts.

Normal commits run the hooks automatically after local installation. Each teammate
must install the hook in their own clone; committing the configuration alone does
not install hooks on other computers. Ruff and secret scanning inspect staged files
on commit; the manual command above scans all tracked matching files. New files
must be staged to be included. Node dependency audits run on every commit. Each
shared Python dependency audit runs when its corresponding requirements file is
included in the commit. The manual all-files scan still runs all three Python
audits. Shared findings remain unresolved until reviewed and remediated by the
owners; skipping an unchanged manifest is not a passing audit of that service.
Findings and scanner/network errors from executed checks block the commit.
Ruff's assert warning is excluded only for `test_*.py` files because assertions
are expected in tests; the remaining security rules still apply to those files.

The report script writes timestamped logs, the commit SHA, and the pre-commit
version under `.security-reports/`. That directory and `.venv-security/` are ignored
by Git. Keep raw scan logs local: findings may contain sensitive source excerpts.
Review/redact evidence before sharing it or including it in the group report.
Record findings, affected files/dependencies, agreed remediation, and retest results
for the Testing Report Review. This configuration does not automatically fix files,
upgrade dependencies, or suppress existing findings. Documenting a finding does
not make the hook pass; corrections to shared code require coordination with its
owner.


### Automated backend endpoint tests

From `student-4/backend`, run:

```bash
npm ci
npm test
```

The Node.js test runner exercises the real Express itinerary router, controllers,
and database HTTP client against a temporary local database API stub. Tests use
random local ports and fixed data without reading or changing the application
database. Docker, Groq, Ollama, and API keys are not required.

The two backend endpoint functions covered are:

- `GET /api/saved_itineraries`: saved records, an empty list, and database errors.
- `GET /api/saved_itineraries/:id`: itinerary/activity contents, invalid IDs,
  missing records, and database errors.

To also generate a JUnit XML report, run `npm run test:ci`. The report is written
to `student-4/backend/reports/endpoint-tests.xml` relative to the repository root.
Generated reports are ignored by Git.

After a push or pull request affecting Student 4, `.github/workflows/student-4.yml`
runs these tests as a required step within its validation job. A failing test
fails the job and prevents subsequent build steps from running. The workflow
uploads the XML report as `student-4-endpoint-test-results`, including when tests
fail, and retains it for 30 days. Download the artifact and preserve the workflow
run URL, commit SHA, and execution logs for the testing report and agentic-loop
review. Required branch protection checks must be configured separately in GitHub
if merges should also be blocked.

Student 4's Plan Itinerary component uses the Groq API to generate itineraries.

The Groq API key is not committed to GitHub for security reasons.

### Student 4 environment setup

Create the Student 4 backend environment file:

cp student-4/backend/.env.example student-4/backend/.env

Then add the required API key to:

student-4/backend/.env



### 1. Configure the Groq API key

The `.env` file is not included in the repository because it contains a private API key.

From the project root, create the Student 4 backend `.env` file by running:

```bash
cp student-4/backend/.env.example student-4/backend/.env
```

Then open:

```text
student-4/backend/.env
```

and replace the placeholder with your own Groq API key:

```env
GROQ_API_KEY=your_actual_groq_api_key
```

A valid Groq API key is required for itinerary generation.

Do not commit the `.env` file.

To generate a Groq API key:
open https://groq.com/
navigate to Start Building Option (or simply opem, https://console.groq.com/home?utm_source=website&utm_medium=outbound_link&utm_campaign=dev_console_click&_gl=1*1n4q29l*_gcl_au*Nzk5NTIyNTk5LjE3ODcyNzMyMTM.*_ga*Nzc0MDk5NDk3LjE3Nzg3NTE4MDU.*_ga_4TD0X2GEZG*czE3ODg4MzYyNzAkbzE0JGcwJHQxNzg4ODM2MjcwJGo2MCRsMCRoMA..)
You will be able to generate the API key.




### 2. Start the application

From the project root:

```bash
docker compose up -d --build
```

### 3. Start the local RAG and MCP servers

Student 4's RAG assistant and MCP integration depend on two local services that are not started by the Student 4 Docker Compose application:

- RAG server on port `7001`
- MCP server on port `7004`

Start both services before testing the Student 4 RAG page or MCP integration page.

In a new terminal, start the RAG server from the project root:

```bash
cd rag-server
python3 rag_http_server.py
```

The RAG server should be available at:

```text
http://127.0.0.1:7001
```

In another terminal, start the MCP server from the project root:

```bash
cd ai-services/mcp-server
python3 http_server.py
```

The MCP server should be available at:

```text
http://127.0.0.1:7004
```

To confirm the MCP server is running:

```bash
curl -s http://127.0.0.1:7004/mcp/tools
```

### 4. Open the application

Shared application:

```text
http://localhost:8080
```

Student 4 directly:

```text
http://localhost:3004
```

### 5. Test the Plan Itinerary component

1. Open the Plan Itinerary page.
2. Enter destination and travel preferences.
3. Select cities.
4. Generate itinerary options.
5. Select an itinerary.
6. Review/refine the itinerary.
7. Save the itinerary.

### 6. Test the Development Agentic AI Loop

From the project root:

```bash
node ai-services/ai-mode/agents/agenticLoop.js \
  --student student-4 \
  --task "Validate Student 4 Plan Itinerary microservice"
```

### 7. Test Student 4 RAG integration

Student 4 uses the shared RAG server to answer questions about saved itineraries. Before testing Student 4's RAG page, refresh the RAG corpus so the RAG server regenerates the latest Student 4 chunks from the Student 4 database.

Make sure the RAG server is running on port `7001`, then run:

```bash
curl -X POST http://127.0.0.1:7001/rag/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

This rebuilds `rag-server/corpus/corpus.jsonl` and refreshes the Chroma vector store. It is required after saving, deleting, or changing Student 4 itineraries; otherwise, the RAG server may answer using stale Student 4 chunks.

To test retrieval directly:

```bash
curl -X POST http://127.0.0.1:7001/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "In itinerary ID 3, what activities is the user doing?",
    "k": 5
  }'
```

To test the generated RAG answer:

```bash
curl -X POST http://127.0.0.1:7001/rag/answer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "In itinerary ID 3, what activities is the user doing?",
    "k": 5
  }'
```
