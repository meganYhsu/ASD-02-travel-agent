# Student 4 pre-commit security scan

This document preserves the initial scan. The subsequent targeted fix and retest
of Student 4's two critical dependency findings are recorded in
[student4-critical-remediation.md](student4-critical-remediation.md). Other
findings remain unresolved unless that follow-up explicitly states otherwise.

## Execution evidence

- Date: 22 October 2026 (UTC).
- Checkout: `ASD-02-travel-agent-clean`, branch `Zeel`.
- Application revision scanned: `2e2015a` (security configuration and documentation
  were uncommitted working-tree additions).
- Command: `bash scripts/security/run-checks.sh`.
- Local raw report: `.security-reports/pre-commit-20261022T015451Z.log`.
- Result: exit code 1; one hook passed and seven hooks reported findings.
- Tool configuration: pre-commit 4.3.0, detect-secrets 1.5.0, Ruff 0.14.0,
  pip-audit 2.9.0; npm audit used the existing Student 4 lockfiles.

The local pre-commit hook is installed. Configuration and shell syntax validation
passed. This was a manual all-tracked-files scan, not evidence of a successful
commit with hooks passing. No commit or push was performed.

## Results and follow-up

| Check | Result | Required follow-up |
| --- | --- | --- |
| Secret scanning | Four candidates in the three multi-agent agent files and `shared/frontend/app.py` | Three agent API-key values were confirmed to be local Ollama placeholders, not external credentials. Review the shared frontend candidate with its owner. No baseline or allowlist was created. |
| Ruff security rules | Eight findings across shared Python code | Review URL handling, interface bindings, Flask debug mode, and a swallowed exception. These are static-analysis findings, not proof of exploitation. |
| Multi-agent Python dependencies | Five advisories affecting `flask` and `flask-cors` | Coordinate dependency changes and integration tests with the shared service owner. |
| MCP Python dependencies | Passed | No known vulnerabilities reported in the resolved dependency set at scan time. |
| Local RAG Python dependencies | Four advisories affecting resolved `chromadb` 1.5.9 | Review advisories and mitigations with the RAG owner; the audit reported no fixed versions for these entries. |
| Student 4 backend dependencies | Six affected dependency entries: one moderate, four high, one critical | Review `brace-expansion`, `braces`/`chokidar`/`nodemon`, `proxy-addr`, and `qs`; plan targeted updates and retest. |
| Student 4 database dependencies | Five affected dependency entries: four high, one critical | Review `brace-expansion`, `braces`/`chokidar`/`nodemon`, and `proxy-addr`; plan targeted updates and retest. |
| Student 4 frontend dependencies | Two high-severity dependency entries | Review `source-map-js` and `vite`; plan targeted updates and rebuild/retest. |

Node counts include development dependencies and audit dependency-chain entries;
they are not counts of independently exploitable production flaws. Python
requirements contain unpinned dependencies, so future resolution may differ.
Package audits report known advisories and do not establish application-level
exploitability or the absence of unknown vulnerabilities.

Ruff's assert warning is excluded only for `test_*.py` files. Other security rules
still apply to tests. No production-code rules, dependency advisories, or secret
candidates were suppressed. Binary files and package-lock integrity data are
excluded from secret scanning; Node lockfiles are checked by npm audit.

## Scope and preservation

Secret scanning covers tracked text files. Ruff covers shared Python under
`ai-services/` and `rag-server/`. Python audits cover the multi-agent, MCP, and
local `rag-server/` manifests. npm audit covers Student 4 backend, database, and
frontend lockfiles. This is not a complete dependency audit of every teammate's
service; each teammate must retain coverage for their own contribution.

The scan commands did not apply fixes, change application code or dependency
manifests/lockfiles, access application databases, or modify the original checkout.
Git diff verification confirmed no changes under Student 4 application code,
database/frontend, shared AI services, RAG, or shared frontend.

The hooks deliberately block commits while audit findings remain unresolved.
Documenting a finding does not make the hook pass. Agree corrections with owners,
apply targeted changes separately, rerun application tests and these checks, and
retain both the initial findings and retest evidence. Do not run blanket
`npm audit fix --force` updates or hide findings to obtain a passing report.

Review raw logs locally before sharing: scanner output can include source excerpts.
This summary omits credential values. Use the original report and approved retest
results as input to the shared agentic-loop Testing Report Review. No agentic
review or final human release approval is claimed by this document.

## Commit audit scope adjustment

The three shared Python dependency hooks now run when their respective
requirements files are included in a commit. Student 4's three Node dependency
audits still run on every commit. The manual all-files scan continues to audit
all three shared Python manifests. This explicitly scopes the commit gate to
relevant shared dependency changes without modifying shared service code or
requirements, ignoring advisory IDs, or declaring unresolved findings fixed.
The initial findings above remain part of the assessment evidence. A skipped
shared hook is not evidence of a vulnerability-free shared service.
