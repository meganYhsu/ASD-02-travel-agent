# Student 1 - pre-commit security testing report

Scope: `student-1/` (database, backend, frontend, tests, tools) and
`.github/workflows/student-1.yml`. The Student 1 hooks are added to the
team's shared `.pre-commit-config.yaml` and run on every `git commit` once
`pre-commit install` has been run (or with `bash scripts/security/run-checks.sh`).

| Hook | Tool / version | What it checks |
|---|---|---|
| Ruff security rules for Student 1 | ruff 0.14.0, `--select S` (asserts allowed in `test_*.py`) | flake8-bandit rules: hard-coded secrets, SQL built from strings, debug servers, binding to all interfaces, requests without timeouts |
| Scan tracked files for secrets (team hook) | Yelp detect-secrets 1.5.0 | API keys, tokens, passwords and high-entropy strings in staged files |
| Audit Student 1 Python dependencies | pip-audit 2.9.0 | Pinned `backend`, `database`, `frontend` requirements against the PyPI advisory database |
| Student 1 Release 2 endpoint tests | pytest | The Release 2 endpoint, Multi-Agent and cloud-baseline suites (45 tests) |

## Findings and resolution

Ruff on the Release 1 code (`ruff-before.txt`) reported 7 findings. All are
resolved in Release 2 (`ruff-after.txt`: all checks passed).

| Rule | Where | Risk | Resolution |
|---|---|---|---|
| S201 debug=True | `backend/app.py`, `database/db_api.py`, `frontend/app.py` | The Werkzeug debugger allows remote code execution if reachable | Debug is off unless `FLASK_DEBUG=true`. Containers now run gunicorn, so the debugger can never be active in Docker or AWS. |
| S104 bind 0.0.0.0 | same three files | Direct runs exposed the service on every network interface | Direct runs bind `127.0.0.1` unless `FLASK_HOST` is set. Inside containers (gunicorn, or the database image's `FLASK_HOST=0.0.0.0`) the service listens only on the private compose/cloud network; no database or backend port is published. |
| S608 SQL from string | `tests/check_seed.py` | String-built SQL | Table names come from a fixed list in the script, never from input. Kept with `# noqa: S608` and a comment saying why. The database API itself already uses parameterised queries everywhere. |

Other scans:

- **detect-secrets**: no secrets found (`detect-secrets.txt`). The key the
  backend passes to the Ollama client is the fixed placeholder string
  "ollama", which Ollama's OpenAI-compatible API ignores. It is not a
  credential.
- **pip-audit**: requirements were unpinned in Release 1, so builds could pull
  any version. They are now pinned (Flask 3.1.3, requests 2.34.2, openai
  3.35.1, python-dotenv 1.2.4, MarkupSafe 3.0.4, gunicorn 26.2.0). No known
  vulnerabilities (`pip-audit.txt`). CI repeats the audit on every push.

Related hardening done in the same change: containers run as a non-root user
(uid 10001), only the data directories (`/app/data`, `/data`) are writable in
the database image, and the
Multi-Agent routes accept only UUID workflow IDs and refuse workflows that
belong to other students.

## Evidence files

| File | Content |
|---|---|
| `pre-commit-run.txt` | `pre-commit run --files <student-1 files>`: every hook passed |
| `ruff-before.txt` / `ruff-after.txt` | Ruff S-rule results before and after the fixes |
| `detect-secrets.txt` | detect-secrets scan results |
| `pip-audit.txt` | pip-audit results for the pinned requirements |
