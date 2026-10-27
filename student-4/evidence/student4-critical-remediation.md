# Student 4 critical dependency remediation

## Verified finding and applicability

On 22 October 2026, npm audit reported `proxy-addr` 2.0.7 as a critical
transitive dependency in both Student 4 backend and database lockfiles.
The advisory is [GHSA-jqcg-44mw-7w3h](https://github.com/advisories/GHSA-jqcg-44mw-7w3h).
The maintainer identifies 2.0.8 as the patched release.

The flaw can incorrectly trust arbitrary IPv4 clients when an application uses
certain malformed IPv4-mapped IPv6 proxy-trust subnets. It can undermine controls
that rely on trusted client IP addresses.

Inspection found no `trust proxy` configuration or use of `req.ip`/`req.ips` in
Student 4 backend or database source. Express defaults to disabled proxy trust,
which was verified against both installed service dependency trees. Therefore,
the advisory's triggering configuration was not found in the current services.
This limits demonstrated applicability; it does not make the vulnerable dependency
a false positive or guarantee safety under future deployment configuration.

## Targeted change

- Updated only `node_modules/proxy-addr` from 2.0.7 to 2.0.8 in each service's
  `package-lock.json`, including its registry URL, integrity hash, and upstream
  funding metadata.
- Kept the existing compatible Express dependency constraints and top-level
  dependencies unchanged; no override or new direct dependency was necessary.
- Used targeted `npm update proxy-addr --package-lock-only --ignore-scripts
  --no-audit --no-fund`, not a blanket audit fix.
- Installed the updated lockfiles locally with Node 20.19.6, matching the major
  version used in Student 4 CI and Docker images.
- Did not change application source, Docker configuration, teammates' services,
  the original checkout, or saved application databases.

Running deployments are not updated by these lockfile edits. They must install
from the patched lockfiles or rebuild their images before using the fix.

## Verification results

| Check | Result |
| --- | --- |
| Backend audit | Critical findings reduced from 1 to 0; `proxy-addr` no longer listed |
| Database audit | Critical findings reduced from 1 to 0; `proxy-addr` no longer listed |
| Backend endpoint suite | All eight tests passed under Node 20.19.6 |
| Proxy-trust regression, both dependency trees | Malformed mapped subnet did not trust an external test IP; correctly written IPv4 and mapped subnets retained expected matching |
| Native SQLite compatibility | In-memory create/read/update/delete smoke passed; no real itinerary records accessed |

Local evidence under ignored `.security-reports/`:

- `student4-backend-before-critical-fix.json`
- `student4-database-before-critical-fix.json`
- `student4-backend-after-critical-fix.json`
- `student4-database-after-critical-fix.json`
- `student4-critical-fix-endpoint-tests.log`
- `student4-critical-fix-validation.log`

The updated JUnit report is also available at
`student-4/backend/reports/endpoint-tests.xml`. These are local checks; no new
GitHub Actions execution, cloud deployment, or full integrated runtime test is
claimed for this change.

## Remaining findings and decisions

- Backend: five dependency entries remain (one moderate and four high), affecting
  `brace-expansion`, `braces`/`chokidar`/`nodemon`, and `qs`. Review runtime versus
  development exposure and select compatible updates before retesting.
- Database: four high dependency entries remain, affecting `brace-expansion` and
  `braces`/`chokidar`/`nodemon`. Review separately from this critical patch.
- Frontend: its two high dependency entries from the initial scan were not changed
  or re-audited in this critical-only remediation.
- Shared Python, RAG, Ruff, and secret-scan findings remain for owner review.
  Three Ollama placeholder values were previously verified as non-credentials;
  they have not been silently allowlisted.

No findings were suppressed. The complete pre-commit security gate is not yet
passing, and documenting unresolved findings does not unblock it. No commit or
push was performed. Review remaining risks with service owners, preserve retest
evidence, and use it for the agentic-loop Testing Report Review before a final
human release decision.
