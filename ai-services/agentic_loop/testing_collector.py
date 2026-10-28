
"""Collect evidence for the Release 2 Testing Report Review.

Read existing security and CI/CD reports.
Do not execute tests or infer success from workflow files.
"""

import json
import re
from pathlib import Path


MAX_FILE_BYTES = 100_000
MAX_EVIDENCE_CHARS = 14000

STUDENTS = range(1, 6)



def read_report(path: Path) -> dict:
    """Read a report as untrusted evidence."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Report too large: {path.name}")

    raw = path.read_bytes()

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        content = raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        content = raw.decode("utf-8-sig")
    else:
        content = raw.decode("utf-8")

    return {
        "filename": path.name,
        "source": str(path),
        "content": content,
    }


def summarize_ci_log(path: Path) -> dict:
    """Extract verified test results from a CI/CD execution log."""

    raw = read_report(path)
    content = raw["content"]
    clean_lines = [
        re.sub(
            r"^\d{4}-\d{2}-\d{2}T\S+Z\s*",
            "",
            line,
        ).strip()
        for line in content.splitlines()
    ]

    test_cases = []

    for line in clean_lines:
        match = re.search(
            r"([\w./-]+::test_[\w-]+)\s+"
            r"(PASSED|FAILED|SKIPPED|ERROR)\b",
            line,
        )

        if match:
            test_cases.append({
                "test": match.group(1),
                "result": match.group(2),
            })

    summary_match = re.search(
        r"(\d+)\s+passed(?:\s+in\s+[\d.]+s)?",
        "\n".join(clean_lines),
        re.IGNORECASE,
    )

    return {
        "filename": path.name,
        "source": str(path),
        "evidence_type": "github_actions_execution_log",
        "test_cases": test_cases,
        "pytest_passed_count": (
            int(summary_match.group(1))
            if summary_match else None
        ),
        "verification_status": (
            "test_results_found"
            if test_cases or summary_match
            else "no_test_results_found"
        ),
    }


def summarize_precommit_report(path: Path) -> dict:
    """Summarize hook outcomes while retaining failed finding details."""
    import re

    report = read_report(path)
    lines = report["content"].splitlines()

    hooks = []
    findings = []
    current_hook = None

    for line in lines:
        clean = line.strip()

        match = re.match(
            r"^(.+?)\.{3,}(Passed|Failed|Skipped)$",
            clean,
            re.IGNORECASE,
        )

        if match:
            current_hook = {
                "name": match.group(1).strip(),
                "status": match.group(2),
            }
            hooks.append(current_hook)
            continue

        if current_hook and current_hook["status"].lower() == "failed":
            if re.search(
                r"\b(S\d{3}|PYSEC-\d{4}-\d+|GHSA-[\w-]+)\b"
                r"|severity:\s*(critical|high|moderate|low)"
                r"|found \d+ known vulnerabilities",
                clean,
                re.IGNORECASE,
            ):
                findings.append({
                    "hook": current_hook["name"],
                    "detail": clean[:300],
                })

    if not hooks:
        return {
            "filename": path.name,
            "source": str(path),
            "evidence_type": "security_or_remediation_report",
            "verification_status": "not_structurally_parsed",
            "note": (
                "This document uses a different format. "
                "Zero parsed hooks does not mean zero findings. "
                "Refer to the original evidence before making a conclusion."
            ),
        }

    return {
        "filename": path.name,
        "source": str(path),
        "evidence_type": "pre_commit_security_scan",
        "hooks": hooks,
        "passed_count": sum(
            hook["status"].lower() == "passed" for hook in hooks
        ),
        "failed_count": sum(
            hook["status"].lower() == "failed" for hook in hooks
        ),
        "security_findings": findings,
        "summary_limitations": (
            "Extracted hook statuses and selected security finding lines. "
            "Refer to the original report for full vulnerability details."
        ),
    }


def collect(app_dir: Path,repo_root: Path,student: str = "all",) -> tuple[bool, str]:
    """Collect available testing evidence and identify missing reports."""

    evidence_dir = app_dir / "evidence" / "testing"
    pre_dir = evidence_dir / "pre_commit"
    post_dir = evidence_dir / "post_commit"

    if not pre_dir.is_dir():
        return False, "Missing pre_commit evidence directory."

    try:
        pre_reports = []
        
        for path in sorted(pre_dir.glob("*")):
            if not path.is_file() or path.suffix.lower() not in (
                ".md", ".txt", ".log", ".json"
            ):
                continue
            
            report = read_report(path)
            
            
            pre_reports.append(summarize_precommit_report(path))


        post_reports = []
        if post_dir.is_dir():
            if student == "all":
                paths = sorted(post_dir.rglob("*"))
            else:
                student_dir = post_dir / student
                paths = sorted(student_dir.rglob("*")) if student_dir.is_dir() else []
            
            for path in paths:
                if not path.is_file():
                    continue
                
                if path.suffix.lower() not in (".md", ".txt", ".log", ".json"):
                    continue
                
                post_reports.append( summarize_ci_log(path))

        if not pre_reports and not post_reports:
            return False, "No testing execution reports were found."

        workflow_configs = {}
        for student_number in STUDENTS:
            name = f"student-{student_number}"
            workflow = repo_root / ".github" / "workflows" / f"{name}.yml"
            workflow_configs[name] = {
                "workflow_file_exists": workflow.is_file(),
                "note": (
                    "Configuration existence is not evidence "
                    "of a successful GitHub Actions run."
                ),
            }

        evidence = {
            "review_mode": "testing",
            "selected_student": student,
            "evidence_scope": "Available reports only",
            "pre_commit_reports": pre_reports,
            "post_commit_reports": post_reports,
            "github_workflows": workflow_configs,
            "post_commit_evidence_status": (
                "provided" if post_reports else "not_provided"
            ),
            "limitations": [
                "Missing reports must be treated as unverified.",
                "A test file does not prove a test executed.",
                "A workflow YAML file does not prove CI/CD passed.",
                "Initial security findings remain relevant after partial fixes.",
                "No release approval is implied by review completion.",
            ],
        }

        output = json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if len(output) > MAX_EVIDENCE_CHARS:
            return False, (
                "Testing evidence exceeds the input limit. "
                "Reduce or split the reports without removing findings."
            )

        return True, output

    except (OSError, UnicodeError, ValueError) as exc:
        return False, f"Testing evidence collection failed: {exc}"
