"""Start the student-5 database, backend and frontend together.

Visual Studio cannot debug VS Code compound launch.json profiles.
Use this script (or the student5-all project) as a single startup item.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def start(name: str, cwd: Path, env_extra: dict[str, str]) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(env_extra)
    print(f"Starting {name} in {cwd} ...")
    return subprocess.Popen([PYTHON, "app.py"], cwd=str(cwd), env=env)


def main() -> int:
    processes = [
        start(
            "database",
            ROOT / "database",
            {
                "PORT": "5405",
                "DATABASE_PATH": str(ROOT / "database" / "data" / "travel_docs.db"),
            },
        )
    ]
    time.sleep(1)
    processes.append(
        start(
            "backend",
            ROOT / "backend",
            {
                "PORT": "5505",
                "DATABASE_SERVICE_URL": "http://127.0.0.1:5405",
                "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
            },
        )
    )
    time.sleep(1)
    processes.append(
        start(
            "frontend",
            ROOT / "frontend",
            {
                "PORT": "8505",
                "BACKEND_URL": "http://127.0.0.1:5505",
            },
        )
    )

    print("Database  http://127.0.0.1:5405/health")
    print("Backend   http://127.0.0.1:5505/health")
    print("Frontend  http://127.0.0.1:8505")
    print("Press Ctrl+C to stop all services.")

    exit_code = 0
    try:
        for proc in processes:
            code = proc.wait()
            if code:
                exit_code = code
    except KeyboardInterrupt:
        print("Stopping services...")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
