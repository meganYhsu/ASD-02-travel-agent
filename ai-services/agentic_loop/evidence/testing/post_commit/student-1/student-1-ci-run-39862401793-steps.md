# Student 1 - post-commit CI run 39862401793 (step results)

Source: GitHub REST API (`/actions/runs/39862401793`, `/jobs`, `/artifacts`), read on 28 Oct 2026.
This is the step-level result of the run, not the raw job log. The raw log with
per-test lines and the JUnit XML artifact need a GitHub login to download.

| Field | Value |
|---|---|
| Workflow | Student 1 - Build and Validate Microservices |
| Run | https://github.com/meganYhsu/ASD-02-travel-agent/actions/runs/39862401793 |
| Event | push |
| Branch | kyu |
| Commit | 3e5bbaaa5bc724f1b1e1019a6a37a6555f93ff99 |
| Started | 2026-10-22T22:05:58Z |
| Finished | 2026-10-22T22:07:17Z |
| Conclusion | success |

## Job `validate-student-1`: success

https://github.com/meganYhsu/ASD-02-travel-agent/actions/runs/39862401793/job/120116100114

| # | Step | Result |
|---|---|---|
| 1 | Set up job | success |
| 2 | Checkout repository | success |
| 3 | Set up Python | success |
| 4 | Install microservice and test dependencies | success |
| 5 | Validate Python syntax | success |
| 6 | Audit pinned dependencies (pip-audit) | success |
| 7 | Create database and validate seed data | success |
| 8 | Post-commit endpoint tests: POST /travelers and POST /travelers/<id>/update | success |
| 9 | Release 2 Multi-Agent and cloud-baseline tests | success |
| 10 | Start microservices | success |
| 11 | Smoke test live endpoints | success |
| 12 | Test full CRUD cycle | success |
| 13 | Validate MCP integration (disabled in CI) | success |
| 14 | Validate RAG integration (disabled in CI) | success |
| 15 | Build Docker images | success |
| 16 | Run the containers like the cloud deployment and smoke test them | success |
| 17 | Container logs | skipped |
| 18 | Upload test reports | success |
| 35 | Post Set up Python | success |
| 36 | Post Checkout repository | success |
| 37 | Complete job | success |

## Artifacts

- `student-1-test-results` (2075 bytes, expires 2027-01-20): JUnit XML for `release2-endpoints.xml` and `release2-multi-agent-cloud.xml`, plus `cloud-smoke-ci.json`
