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
| `cloud/` | Empty until the AWS deployment exists. Run `tests/cloud_smoke.py --frontend <alb-url>:3001 --json evidence/cloud/cloud-smoke.json` | Cloud Deployment Report |

Post-commit CI/CD evidence lives in GitHub Actions: the **Student 1 - Build
and Validate Microservices** run and its `student-1-test-results` artifact
(JUnit XML for the two endpoint suites, plus the container smoke-test JSON).
