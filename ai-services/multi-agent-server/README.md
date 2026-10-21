# Shared multi-agent service

All students can use the same planner, worker, reviewer, and human-review API.
Each microservice backend fetches its own source records and sends only the
fields needed for the task. The shared service analyses supplied evidence;
it does not fetch records, make bookings, or apply database changes.

## Integrate another microservice

Start the Python service as described below, then call `POST /workflow` from
your backend using this common request format:

```json
{
  "service": "booking",
  "task": "summarise",
  "user_request": "Summarise my bookings and flag missing details.",
  "context": {
    "bookings": [{"booking_id": 12, "type": "hotel", "status": "confirmed"}]
  }
}
```

`service`, `task`, and `user_request` must be non-empty strings. `context` must
be a JSON object; its nested structure belongs to the calling microservice.
An empty object is allowed so agents can explain missing evidence. Service
and task names are descriptive labels, not registered tools or executable actions.

| Example service | Example task | Suggested context |
| --- | --- | --- |
| `traveller` | `summarise_preferences` | Profile and travel preferences |
| `booking` | `check_bookings` | Booking records and confirmation status |
| `budget` | `review_spending` | Budget, currency, and expense records |
| `itinerary` | `summarise` | Itinerary and activities |
| `documents` | `check_missing_details` | Document metadata and supplied requirements |

Backend URL: `http://127.0.0.1:6767` when running locally, or
`http://host.docker.internal:6767` from a Docker backend on the same computer.
For another computer, configure the reachable address of the shared server.
The Python service still runs separately from Docker Compose.

For a Node backend with built-in `fetch`:

```js
const response = await fetch(`${process.env.MULTI_AGENT_SERVICE_URL}/workflow`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  signal: AbortSignal.timeout(420000),
  body: JSON.stringify({
    service: "booking",
    task: "summarise",
    user_request: "Summarise my bookings and flag missing details.",
    context: { bookings: bookingRecords }
  })
});
const workflow = await response.json();
if (!response.ok) throw new Error(workflow.error || "Multi-agent request failed");
```

Display `planner_result`, `worker_result`, and `reviewer_result`, checking their
statuses and the top-level `status` (`success` or `partial_failure`). Retain
`workflow_id` to retrieve results through `GET /workflow/:workflow_id` and send
human decisions through `POST /workflow/:workflow_id/review` using `decision`,
`reason`, and optional `evidence` as described below. A recorded review does not
execute changes in the caller's microservice.

History retains `service`, `task`, and the supplied `context`; audit records and
human reviews also identify the service and task. These labels do not provide
authentication or isolate access between students. The API currently shares
workflow history across callers. Send only the evidence required for the task.

Legacy requests using `user_request` and `itinerary_context` remain supported.
They are converted to service `itinerary`, task `answer_question`, and compact
itinerary context internally; existing itinerary response fields are preserved.
Do not combine `itinerary_context` with `service`, `task`, or `context`.
Requests containing only `user_request` also remain supported with empty context.

## Student 4 integration

The saved-itinerary button passes `itineraryId` to the multi-agent page in React
Router state. The page displays the selected ID and calls the Express API to
generate agent output, retrieve workflow status, and save human decisions.
Generation and review controls require a selected saved itinerary. Requests show
loading and error states; review confirmation appears only after the server
confirms that the decision was recorded.

The frontend uses `VITE_API_BASE_URL`, defaulting to `http://localhost:5004`
(Student 4's Docker backend). Set it to `http://localhost:5001` when running the
Express backend directly. Vite environment changes require restarting the dev
server or rebuilding the frontend. The Python port is configured separately.

## Run the Python service

From the repository root:

```sh
python3 -m venv ai-services/multi-agent-server/.venv
ai-services/multi-agent-server/.venv/bin/pip install -r ai-services/multi-agent-server/requirements.txt
ai-services/multi-agent-server/.venv/bin/python ai-services/multi-agent-server/app.py
```

The default port is `6767`, avoiding Student 4's Docker backend port `5004`.
Override it with `PORT`. Configure `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
`OLLAMA_REVIEW_MODEL` for the available model server and models.

Planner, worker, and reviewer default to `qwen2.5:3b`. Each model request has a
120-second timeout (`OLLAMA_TIMEOUT_SECONDS`), and each coordinator wait has a
130-second timeout (`AGENT_STEP_TIMEOUT_SECONDS`). The Express request timeout is
420 seconds to allow for the three coordinator waits and request overhead.
Restart the Python service and Express backend after changing these settings.
Existing environment variables override the Python defaults.

Each workflow runs planner, then worker, then reviewer using a single executor
thread. The worker is submitted after the planner wait, and the reviewer after
the worker wait. A call still running after a coordinator timeout holds that
thread; subsequent calls wait in its queue rather than overlapping. Queued calls
that exceed their coordinator wait are canceled. Separate workflows can still
run concurrently, and client timeouts cannot guarantee cancellation inside Ollama.

Model calls disable automatic SDK retries. The Python terminal logs each agent's
model URL, model name, timeout, prompt character count, and elapsed time. Failures
include the exception traceback. Prompt contents are not logged.

The Express backend uses `MULTI_AGENT_SERVICE_URL`, defaulting to
`http://127.0.0.1:6767`. Docker Compose sets it to
`http://host.docker.internal:6767` for a Python service running on the host.
The Python service is not started by Compose.

## Express API

All responses use `{ "success": true, "data": ... }` or
`{ "success": false, "error": "..." }`.

| Route | Request | Behavior |
| --- | --- | --- |
| `POST /api/multi-agent/workflow` | `{ "itineraryId": 42, "userRequest": "Review my itinerary" }` | Fetches the saved itinerary and activities through the database API, then calls Python `POST /workflow`. |
| `GET /api/multi-agent/workflows/:id` | Workflow ID from the generation response | Calls Python `GET /workflow/:id` for the saved result and latest human decision. |
| `POST /api/multi-agent/workflows/:id/review` | `{ "decision": "Partially Accept", "reason": "Day two needs fewer activities to fit my budget.", "evidence": "Day two activity costs" }` | Calls Python `POST /workflow/:id/review` and persists the review. |

`itineraryId` must be a positive integer. Decisions are `Accept`,
`Partially Accept`, or `Reject`. A trimmed reason of at least 20 characters is
required; evidence is an optional string. Both Express and Python validate
review input. The frontend's radio values use these API decision values.

The Python generation API accepts an optional `itinerary_context` containing an
`itinerary` object with `itinerary_id` and an `activities` list. It supplies this
context to the agents and saves it with the workflow. Existing callers can still
send only `user_request`.

Generation is synchronous. Lookup returns saved results, not live agent
progress. Review events are appended to `human_reviews.jsonl` and linked to the
workflow and itinerary; lookup overlays the latest recorded decision without
rewriting the original output. Keep the service directory on persistent storage
to retain history and reviews. Recording a review does not apply itinerary
changes or start another workflow.

The agents plan, answer, and review travel-service tasks using supplied evidence.
Model inputs exclude project file lists and detected student names. Legacy itinerary metadata is
limited to travel fields, and activities use compact rows with named columns;
the complete original context remains in workflow history. No answers are
hardcoded or substituted for model output.

## Tests

From the repository root:

```sh
ai-services/multi-agent-server/.venv/bin/python -m unittest discover -s ai-services/multi-agent-server -p 'test_*.py' -v
```

Tests mock model calls and use temporary history files, leaving real workflow
history and Docker data untouched.

Agent results report `timeout` or `error` with exception details when model calls
fail, rather than labeling fallback messages as successful. Empty responses are
errors. The workflow status is `partial_failure` if any agent fails; transport
still returns the workflow for inspection and human review. All three agents
continue to make real model calls.
