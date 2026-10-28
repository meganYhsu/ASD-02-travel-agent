# Student 1 - Release 2 evidence

Generated on 22 Oct 2026 from a local run. All services were started
natively in separate terminals: the shared Multi-Agent server, then the
student-1 database API, backend (AI-Mode and Multi-Agent on) and frontend.
The Multi-Agent server used `qwen2.5:0.5b` through Ollama.

| Folder / file | What it shows | Report section |
|---|---|---|
| `security/pre-commit-security-report.md` | Ruff S rules, detect-secrets and pip-audit results, the 7 Release 1 findings, and how each was fixed | Pre-Commit Security Testing |
| `security/*.txt` | Raw output of each scan and of `pre-commit run` | Pre-Commit Security Testing |
| `multi-agent/cli-run.txt`, `cli-workflow.json` | Terminal run: Planner -> Worker -> Reviewer -> Human Review (Partially Accept) for traveller 1 | Multi-Agent Workflow Evidence |
| `multi-agent/ui-workflow.html`, `ui-review.html`, `ui-lookup.html` | The same workflow through the frontend proxy for traveller 2, rejected by the human reviewer, then reloaded | Multi-Agent Workflow Evidence |
| `multi-agent/workflow_history.jsonl`, `coordination_audit.jsonl`, `human_reviews.jsonl` | Student-1 entries copied from the shared server's history, audit and review logs | Multi-Agent Workflow Evidence |
| `local/terminal-*.log` | One log per terminal from the multi-server run | Local Deployment Evidence |
| `local/smoke-ai-on.*`, `local/smoke-ai-off.*` | `tests/cloud_smoke.py` through the frontend with AI on (10/10) and with every AI switch off, the cloud baseline (15/15) | Local Deployment Evidence |
| `cloud/` | Empty until the shared AWS EC2 deployment runs (the Cloud Deployment workflow deploys every push to `main`). The EC2 ports are bound to loopback, so open the tunnel first (`bash deployment/aws/tunnel.sh <key.pem> ubuntu@<EC2_PUBLIC_IP>`), then run `python student-1/tests/cloud_smoke.py --frontend http://127.0.0.1:3001 --json student-1/evidence/cloud/cloud-smoke.json` | Cloud Deployment Report |

## Post-commit CI/CD

GitHub Actions run [39862401793](https://github.com/meganYhsu/ASD-02-travel-agent/actions/runs/39862401793)
(**Student 1 - Build and Validate Microservices**, push to `kyu` at `3e5bbaa`,
22 Oct 2026) passed every step: pip-audit, seed check, both endpoint suites,
the Multi-Agent and cloud-baseline suites, the live CRUD/MCP/RAG scripts, and
the container smoke test. Its `student-1-test-results` artifact holds the JUnit
XML for the two endpoint suites plus the container smoke-test JSON. A step
summary is in `ai-services/agentic_loop/evidence/testing/post_commit/student-1/`.

## Shared agentic loop reviews (Release 2)

Student 1's evidence was also reviewed by the team's shared agentic loop
(`ai-services/agentic_loop/`) on 28 Oct 2026, from the `student-1-release2` branch:

| Review | Command | Log in `ai-services/agentic_loop/review_logs/` |
|---|---|---|
| Testing Review | `python ai-services/agentic_loop/run_testing_review.py --student student-1` | `testing_review_20261028T082120Z_9c7a95c1.json` (qwen2.5:3b) |
| Multi-Agent Workflow Review | Copy `multi-agent/*.jsonl` into `ai-services/multi-agent-server/`, then `python ai-services/agentic_loop/run_multi_agent_review.py` | `multi_agent_review_2d742c90-...json` (llama3.1:8b) and `...-qwen2.5-3b.json` |

Inputs added for these reviews: `evidence/testing/pre_commit/student1-precommit-20261028.txt`
(a full `pre-commit run` over `student-1/` on the merged tree: Ruff clean, no
known vulnerabilities, 45 tests passed) and `student1-pre-commit-security-report.md`
(a copy of `security/pre-commit-security-report.md`).

What the reviews found, and the human view of each:

- **Testing:** the Testing Review flagged that Student 1's raw CI log was not in
  the evidence folder; only the step summary was. Download the raw job log
  from the run page into `post_commit/student-1/` and rerun the review.
- **Multi-Agent (qwen2.5:3b):** reported the human decision as missing. That is
  a model misreading: the history record keeps its own `human_decision.status`
  as `pending`, and the Reject decision is in `human_reviews.jsonl`, which the
  collector passed to the model.
- **Multi-Agent (llama3.1:8b):** said the Worker's brief for traveller 2 does not
  address the request with the stored evidence. This agrees with the human
  Reject ("Worker brief does not mention the accessibility requirement").

The human release decision stays pending; neither review approves anything.
