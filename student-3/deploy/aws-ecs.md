# Student 3 on AWS (ECR + ECS Fargate)

What the group Terraform (`deployment/aws/`) needs to run the Budget &
Expense Tracking services. Each service is its own ECS service in the shared
cluster, as in Lecture 11. Only the frontend is public.

## Services

| ECS service / Service Connect name | ECR image (build context) | Port | Public | Health check | CPU / memory |
|---|---|---|---|---|---|
| `student3-database` | `student-3/database` | 6003 | no | `GET /health` | 256 / 512 |
| `student3-backend` | `student-3/backend` | 5003 | no | `GET /health` | 256 / 512 |
| `student3-frontend` | `student-3/frontend` | 3003 | yes, load balancer listener on port 3003 | `GET /health` | 256 / 512 |

Use the same names as `docker-compose.yml` for the Service Connect (Cloud
Map) discovery names, so the internal URLs below are the same as locally.

## Environment (cloud baseline: every AI service off)

```hcl
student3_database = {
  BUDGET_DB_PATH = "/app/data/budget.db"     # already the image default
}

student3_backend = {
  DB_API_URL          = "http://student3-database:6003"
  TRIP_API_URL        = "http://student4-database:5002"
  AI_MODE_ENABLED     = "false"
  MCP_ENABLED         = "false"
  RAG_ENABLED         = "false"
  MULTI_AGENT_ENABLED = "false"
}

student3_frontend = {
  BACKEND_URL     = "http://student3-backend:5003"
  SHARED_HOME_URL = "http://<load-balancer-dns>:8080"   # public shared home page
}
```

The four AI flags already default to `false` in the code; setting them
explicitly makes the baseline visible in the task definition.

## Notes

- **Serve the frontend at the root of its own listener.** The page and the
  HTML returned by the backend use absolute paths (`/api/...`), so a
  path-prefix rule such as `/budget/*` would break them. A listener on port
  3003 (or a host-header rule) works.
- **Data.** SQLite lives in `/app/data`. Without a volume the data is reset to
  the seed data whenever the task restarts, which is fine for the CRUD demo.
  To keep data, mount an EFS access point at `/app/data` with POSIX user and
  group `10001` (the image runs as the non-root user `appuser`, uid 10001).
- **Image platform.** Fargate defaults to `linux/amd64`. On an Apple Silicon
  Mac build with `docker build --platform linux/amd64 ...`.
- **Logs.** gunicorn writes access logs to stdout, so the `awslogs` log driver
  sends them to CloudWatch.
- **No secrets.** Student 3 needs no API keys or passwords in the cloud.

## Check the deployment

```powershell
cd student-3
python tests/cloud_smoke.py --frontend http://<load-balancer-dns>:3003 --json cloud-smoke.json
```

14 checks: frontend and health, frontend -> backend -> database, create /
read / update / delete an expense, the four AI services refused with HTTP 503,
and the average response time over five dashboard requests.
