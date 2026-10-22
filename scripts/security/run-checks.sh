#!/usr/bin/env bash
set -euo pipefail
umask 077

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"

security_python="$repository_root/.venv-security/bin/python"
if [[ ! -x "$security_python" ]]; then
    echo "Install the security environment using student-4/README.md first."
    exit 1
fi

mkdir -p .security-reports
report_path=".security-reports/pre-commit-$(date -u +%Y%m%dT%H%M%SZ).log"

{
    date -u '+Scan started: %Y-%m-%dT%H:%M:%SZ'
    git rev-parse HEAD
    "$security_python" -m pre_commit --version
} > "$report_path"

scan_status=0
"$security_python" -m pre_commit run --all-files >> "$report_path" 2>&1 || scan_status=$?
printf '\nScan exit code: %s\n' "$scan_status" >> "$report_path"
echo "Security report saved to $report_path"
if [[ "$scan_status" -ne 0 ]]; then
    echo "Checks did not pass. Review the report for findings or tool/network errors."
else
    echo "All configured security checks passed."
fi
exit "$scan_status"
