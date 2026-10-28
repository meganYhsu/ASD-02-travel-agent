# Student 1 on AWS (ECR + ECS Fargate)

What the group deployment needs to run the Traveler Preferences services.
Each service is its own ECS service in the shared cluster. Only the frontend
is public.

## Services

| ECS service / Service Connect name | ECR image (build context) | Port | Public | Health check | CPU / memory |
|---|---|---|---|---|---|
| `student1-database` | `student-1/database` | 6001 | no | `GET /health` | 256 / 512 |
| `student1-backend` | `student-1/backend` | 5001 | no | `GET /health` | 256 / 512 |
| `student1-frontend` | `student-1/frontend` | 3001 | yes, load balancer listener on port 3001 | `GET /health` | 256 / 512 |

Use the same names as `docker-compose.yml` for the Service Connect (Cloud
Map) discovery names, so the internal URLs below match the local ones.

## Environment (cloud baseline: every AI service off)

```hcl
student1_database = {
  DATABASE_PATH = "/app/data/preferences.db"   # already the image default
}

student1_backend = {
  DB_API_URL          = "http://student1-database:6001"
  AI_MODE_ENABLED     = "false"
  MCP_ENABLED         = "false"
  RAG_ENABLED         = "false"
  MULTI_AGENT_ENABLED = "false"
}

student1_frontend = {
  BACKEND_URL     = "http://student1-backend:5001"
  SHARED_HOME_URL = "http://<load-balancer-dns>:8080"   # public shared home page
}
```

The four AI flags already default to `false` in the code; setting them
explicitly makes the baseline visible in the task definition. For the bonus
cloud AI profile, set the flags to `true` and point `OLLAMA_BASE_URL`,
`MCP_BASE_URL`, `RAG_BASE_URL` and `MULTI_AGENT_SERVICE_URL` at the
cloud-hosted services.

## Notes

- **Serve the frontend at the root of its own listener.** The page and the
  HTML returned by the backend use absolute paths (`/api/...`), so a
  path-prefix rule such as `/preferences/*` would break them. A listener on
  port 3001 (or a host-header rule) works.
- **Data.** SQLite lives in `/app/data` and is seeded on start. Without a
  volume the data resets to the seed data whenever the task restarts, which is
  fine for the CRUD demo. To keep data, mount an EFS access point at
  `/app/data` with POSIX user and group `10001` (the image runs as the
  non-root user `appuser`, uid 10001).
- **Image platform.** Fargate defaults to `linux/amd64`. On an Apple Silicon
  Mac build with `docker build --platform linux/amd64 ...`.
- **Logs.** gunicorn writes access logs to stdout, so the `awslogs` log driver
  sends them to CloudWatch.
- **No secrets.** Student 1 needs no API keys or passwords in the cloud.

## Check the deployment

```bash
python student-1/tests/cloud_smoke.py --frontend http://<load-balancer-dns>:3001 --json student-1/evidence/cloud/cloud-smoke.json
```

15 checks through the public frontend: frontend and backend health, all AI
services reported off, page render, traveller list read from the database,
create / update / delete a traveller, add an interest, the deterministic
completeness check, and the four AI routes refused with HTTP 503.
