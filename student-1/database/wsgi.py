"""Container entry point: gunicorn --preload wsgi:app

The schema and seed data are created once, in the gunicorn master process,
before the worker starts (db_api.init_db is idempotent).
"""

from db_api import app, init_db

init_db()

__all__ = ["app"]
