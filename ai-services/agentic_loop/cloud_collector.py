
"""Collect evidence for Release 2 Cloud Deployment Report Review.

Configuration files do not prove deployment execution or success.
Do not execute deployment commands or access AWS credentials.
"""

import json
import re
from pathlib import Path

MAX_FILE_BYTES = 100_000
MAX_EVIDENCE_CHARS = 14000

DEPLOYMENT_FILES = (
    "deployment/aws/compose.yaml",
    "deployment/aws/deploy.sh",
    "deployment/aws/smoke.sh",
    "deployment/aws/tunnel.sh",
    "deployment/aws/test_sqlite_entrypoint.py",
)


def describe_file(path: Path, repo_root: Path) -> dict:
    """Record file presence without treating it as execution evidence."""
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "exists": path.is_file(),
    }



def summarize_workflow(path: Path, repo_root: Path) -> dict:
    """Extract configuration indicators without executing the workflow."""

    summary = describe_file(path, repo_root)

    if not path.is_file():
        return {
            **summary,
            "configuration_status": "missing",
            "features": {},
        }

    content = path.read_text(encoding="utf-8-sig")

    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Cloud workflow exceeds file size limit.")

    # These are text indicators, not proof of correct YAML semantics
    # or successful execution.
    features = {
        "push_trigger_mentioned": bool(
            re.search(r"^\s*push\s*:", content, re.MULTILINE)
        ),
        "manual_trigger_mentioned": "workflow_dispatch:" in content,
        "validation_job_mentioned": bool(
            re.search(r"^\s{2}validate\s*:", content, re.MULTILINE)
        ),
        "deployment_job_mentioned": bool(
            re.search(r"^\s{2}deploy\s*:", content, re.MULTILINE)
        ),
        "github_secrets_referenced": "secrets." in content, # pragma: allowlist secret
        "ec2_ssh_mentioned": bool(
            re.search(r"\bssh\b", content, re.IGNORECASE)
        ),
        "docker_compose_mentioned": "docker compose" in content,
        "smoke_check_mentioned": "smoke.sh" in content,
        "rollback_mentioned": bool(
            re.search(r"\brollback\b", content, re.IGNORECASE)
        ),
    }

    return {
        **summary,
        "configuration_status": "present_not_executed",
        "features": features,
        "limitations": (
            "Text-based indicators only; YAML syntax, job behavior, "
            "secrets availability and deployment success are unverified."
        ),
    }



def collect_report_files(directory: Path, repo_root: Path) -> list:
    """Collect deployment evidence with execution results and log endings."""
    reports = []

    if not directory.is_dir():
        return reports

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in (".txt", ".log", ".md", ".json"):
            continue

        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"Cloud evidence file too large: {path.name}")

        content = path.read_text(encoding="utf-8-sig")
        lines = content.splitlines()

        # Capture relevant lines from the actual execution log.
        pattern = re.compile(
            r"successfully|succeeded|passed|failed|error|"
            r"smoke|health|exit code|outcome|completed",
            re.IGNORECASE,
        )

        matches = [
            line[:250]
            for line in lines
            if pattern.search(line)
        ]

        # Include both beginning and ending of the log.
        excerpt = (
            "LOG START:\n"
            + content[:500]
            + "\n\nKEY EXECUTION LINES:\n"
            + "\n".join(matches[-12:])
            + "\n\nLOG END:\n"
            + content[-1200:]
        )

        reports.append({
            "filename": path.name,
            "source": path.relative_to(repo_root).as_posix(),
            "evidence_type": "supplied_execution_evidence",
            "content_excerpt": excerpt[:3500],
            "verification_status": "requires_review",
        })

    return reports


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    """Collect shared AWS deployment configuration and execution evidence."""

    try:
        workflow_path = repo_root / ".github" / "workflows" / "cloud-deployment.yml"

        cloud_dir = app_dir / "evidence" / "cloud"

        configuration = {
            "workflow": summarize_workflow(workflow_path, repo_root),
            "deployment_files": [
                describe_file(repo_root / relative_path, repo_root)
                for relative_path in DEPLOYMENT_FILES
            ],
        }

        deployment_logs = collect_report_files(
            cloud_dir / "deployment_logs",
            repo_root,
        )

        health_checks = collect_report_files(
            cloud_dir / "health_checks",
            repo_root,
        )

        deployment_reports = collect_report_files(
            cloud_dir / "deployment_reports",
            repo_root,
        )

        evidence = {
            "review_mode": "cloud",
            "selected_student": "all",
            "deployment_scope": "shared_aws_ec2",
            "configuration": configuration,
            "deployment_logs": deployment_logs,
            "health_checks": health_checks,
            "deployment_reports": deployment_reports,
            "deployment_verification_status": (
                "execution_evidence_supplied_requires_validation"
                if deployment_logs
                else "unverified"
            ),
            "limitations": [
                "Configuration existence does not prove successful execution.",
                "Supplied logs require validation against actual run outcomes.",
                "No EC2 deployment success is inferred from YAML or scripts.",
                "Missing runtime evidence must be reported as unverified.",
                "Human review does not itself approve deployment.",
            ],
        }

        output = json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if len(output) > MAX_EVIDENCE_CHARS:
            return False, (
                "Cloud evidence exceeds input limit. "
                "Summarize logs without dropping important failures."
            )

        return True, output

    except (OSError, UnicodeError, ValueError) as exc:
        return False, f"Cloud evidence collection failed: {exc}"
