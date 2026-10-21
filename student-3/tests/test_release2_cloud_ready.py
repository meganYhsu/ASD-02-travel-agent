"""Release 2 - cloud readiness of the three Student 3 services (AWS ECS).

    database  BUDGET_DB_PATH moves the SQLite file to a mountable data
              directory; /health answers the load-balancer health check;
              wsgi.py creates the schema and seed data at container start
    frontend  SHARED_HOME_URL replaces the hard-coded localhost links;
              /health answers without depending on the backend
"""

import importlib.util
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[1]


def load_fresh(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # lets Flask find templates/ next to the file
    spec.loader.exec_module(module)
    return module


def test_database_path_comes_from_environment(monkeypatch, tmp_path):
    target = tmp_path / "data" / "budget.db"
    monkeypatch.setenv("BUDGET_DB_PATH", str(target))
    db = load_fresh("db_env_check", STUDENT_DIR / "database" / "db_api.py")

    db.init_db()

    assert db.DB_PATH == target
    assert target.exists()                      # parent folder created too


def test_database_health(db_api):
    resp = db_api.get("/health")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["status"] == "ok" and data["categories"] >= 10


def test_wsgi_entry_point_seeds_a_new_database(monkeypatch, tmp_path):
    target = tmp_path / "fresh.db"
    monkeypatch.setenv("BUDGET_DB_PATH", str(target))
    monkeypatch.syspath_prepend(str(STUDENT_DIR / "database"))
    for name in ("db_api", "wsgi"):
        sys.modules.pop(name, None)

    import wsgi

    resp = wsgi.app.test_client().get("/categories")
    assert resp.status_code == 200 and len(resp.get_json()) >= 10
    for name in ("db_api", "wsgi"):
        sys.modules.pop(name, None)


def test_frontend_uses_shared_home_url(monkeypatch):
    monkeypatch.setenv("SHARED_HOME_URL", "http://travel-alb.example.com:8080/")
    frontend = load_fresh("frontend_env_check", STUDENT_DIR / "frontend" / "app.py")

    html = frontend.app.test_client().get("/").get_data(as_text=True)

    assert 'href="http://travel-alb.example.com:8080/css/styles.css"' in html
    assert 'href="http://travel-alb.example.com:8080/budget"' in html
    assert "127.0.0.1:8080" not in html and "localhost:8080" not in html


def test_frontend_health_does_not_need_the_backend(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://backend-not-running.invalid:5003")
    frontend = load_fresh("frontend_health_check", STUDENT_DIR / "frontend" / "app.py")

    resp = frontend.app.test_client().get("/health")

    assert resp.status_code == 200
    assert resp.get_json() == {"service": "student-3-frontend", "status": "ok"}


def test_container_images_skip_local_data_and_secrets():
    for service in ("database", "backend", "frontend"):
        ignored = (STUDENT_DIR / service / ".dockerignore").read_text().splitlines()
        assert "*.db" in ignored and ".env" in ignored
        dockerfile = (STUDENT_DIR / service / "Dockerfile").read_text()
        assert "USER appuser" in dockerfile          # not root
        assert '"gunicorn"' in dockerfile            # production server
