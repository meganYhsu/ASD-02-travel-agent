# AWS EC2 private validation deployment

This is a separate, opt-in Compose project for the existing Ubuntu EC2 instance.
It does not change application source, Dockerfiles, the root Compose file, shared
nginx configuration, or GitHub workflows. It does not provision AWS resources.
No deployment, passing cloud CRUD tests, or completed assignment is claimed.

## Important boundary

**This package is a private validation environment, not a finished public release.**
The existing applications embed browser URLs such as `127.0.0.1:3001` and
`localhost:5004`. Instead of rewriting teammates' application files, this setup
binds every published port to EC2 loopback and uses SSH forwarding to retain those
origins in your browser. Users cannot open the app directly through the EC2 public
IP. SSH access is required. Stop your local application before opening the tunnel
so its ports do not conflict. Do not use this environment with real personal data.

## What is included

- All 16 core services: shared home and five frontend/backend/database sets.
- No Ollama, RAG, MCP, or multi-agent server containers or AI dependencies.
- Existing supported MCP/RAG flags set to false. AI service URLs point to a closed
  loopback port inside each backend, not to shared AI services or your laptop.
- Separate named volumes for all five SQLite database services.
- Bounded Docker logs, a manual deployment script, HTTP reachability checks, and
  an SSH tunnel helper. All scripts must be invoked with `bash`.

Flags and unreachable URLs **do not disable every AI route or hide AI controls**.
Student 4 and parts of Student 5 lack complete feature controls; unsupported AI
requests can fail instead of returning a clean disabled response. Student 4's
Groq-dependent generation also requires separate review. The deployment script
loads `deployment/aws/.env` for the shared homepage's `FLASK_SECRET_KEY`. No AI
provider keys or student application `.env` files are loaded by this configuration. Existing
Dockerfiles can still copy files present in build contexts: review `.dockerignore`
files and remove secrets/personal data from those contexts before building. Never
upload keys, database exports, `.env` files, or raw logs containing secrets to Git.

## Before running

1. Use the approved `dev` checkout for staging. Record its commit and review the
   deployment directory before committing it. Changing the checkout later is not
   a database rollback; take backups before releasing a new version.
2. Install Docker Engine, Docker Compose, Git, and curl on Ubuntu. Use `sudo` for
   Docker commands on the current EC2 instance. Verify available disk and memory.
3. Keep SSH port 22 restricted to your own IP. Do not open database/API ports.
   This private environment does not require inbound HTTP/HTTPS rules.
4. Do not run the root Compose project alongside this one: published loopback
   ports may conflict. Existing root-project volumes are separate and are not
   automatically migrated into the AWS project.

## Cloud session secret

Before using the deployment script on EC2, securely copy the administrator-managed
`deployment/aws/.env` file to that same path in the EC2 checkout, then restrict it:

```bash
chmod 600 deployment/aws/.env
```

The file must contain a non-empty `FLASK_SECRET_KEY`. Reuse the stored random key
for subsequent deployments of this environment. The file is ignored by Git; do
not commit it or print it in logs. The script explicitly loads this file, and
Compose passes the key only to `shared-home`. Avoid plain `docker compose config`
when recording evidence because it prints resolved secrets; use `config --quiet`.

## On EC2, from the repository root

```bash
sudo bash deployment/aws/deploy.sh validate
sudo bash deployment/aws/deploy.sh build
sudo bash deployment/aws/deploy.sh start
sudo bash deployment/aws/deploy.sh status
sudo bash deployment/aws/smoke.sh
```

The AWS project has its own image names, so run its build even if the original
Compose images were built earlier. Docker can reuse matching cached build layers.
Start does not build, fetch Git changes, migrate existing volumes, or delete data.
Compose dependency ordering does not guarantee database readiness; the smoke
script retries startup connections. If it fails, inspect logs rather than claiming
that the deployment succeeded:

```bash
sudo bash deployment/aws/deploy.sh logs
```

Build, start, status, logs, and smoke output are saved under `deployment/aws/reports/`
and excluded from Git. Review/redact them before including them in group evidence.

## On your Mac, from this repository's root

Stop your locally running application to free ports 8080, 3001–3004, 5004, and 8505.
Use the EC2 instance's current public IP (it can change after stop/start):

```bash
bash deployment/aws/tunnel.sh "$HOME/Documents/Travel-Agent-app-key.pem" ubuntu@EC2_PUBLIC_IP
```

Keep that terminal open and visit `http://127.0.0.1:8080` in your browser. A quiet
terminal is normal. Close the tunnel with Ctrl+C. Verify the host fingerprint
before accepting a new SSH host. Never share the private key; teammates should
use their own approved SSH access and forward the same ports on their computers.

## Database storage

Volumes belong to the separate `travel-agent-aws` Compose project. Students 1–3
use the deployment-only SQLite startup helper: it snapshots an image's existing
database with SQLite's backup API on first use, then symlinks the original database
path to a persistent `/data` file inside the container. Application source is not
rewritten. Student 2's idempotent schema initialization runs before its server.
Students 1 and 3 retain their existing initialization; Student 2 is not reseeded
automatically. Students 4 and 5 retain their `/app/data` and `/data` storage paths.
Existing volume data takes priority over database files in replacement images.

The helper changes only database-file placement in disposable containers. It does
not copy live databases from your laptop or migrate existing local/root volumes.
Review image-bundled demo databases before creating volumes. Do not change volume
or project names casually, run `down -v`, or prune volumes. Test create/read/update/
delete and container recreation for each database before treating persistence as
verified. Named volumes survive container replacement, **not deletion of the EC2
root EBS disk**. Take a consistent backup or EBS snapshot before destructive changes
or instance termination. This package does not automate backups or restore.

## Safe stop

```bash
sudo bash deployment/aws/deploy.sh stop
```

This stops this project's containers without deleting its volumes. Stopping
containers does not stop EC2 compute charges. Stopping EC2 can leave EBS and other
charges, and can change its public IP. Do not terminate it without verified backups.

## Remaining public-release and assignment work

- Agree cloud-safe browser URLs/routing with service owners. Configure a real
  public reverse proxy and HTTPS after reviewing conflicting API/static paths.
  The existing `shared/frontend/nginx.conf` is not used by this package.
- Implement and verify complete AI-disable controls, including unsupported routes
  and UI elements; unreachable AI endpoints alone do not satisfy this requirement.
- Replace demo authentication/session secrets, disable Flask debug servers, and
  review access controls, CORS, dependency findings, and image-bundled secrets/data.
- Verify all CRUD flows and cross-service calls, readiness/recovery, persistent
  storage after recreation, and restore from backups. Reachability is not CRUD.
- Add a reviewed CI-gated deployment workflow, immutable image/commit tracking,
  rollback procedures, and the required report/demo evidence. Manual scripts here
  are not a GitHub Actions deployment pipeline or lecture ECS/Fargate infrastructure.
- Confirm the EC2 approach is acceptable for the assignment. Release approved
  `main` only after the integrated staging build passes the agreed checks.

See [Docker volume documentation](https://docs.docker.com/engine/storage/volumes/)
for the distinction between persistent volumes and container filesystems.
