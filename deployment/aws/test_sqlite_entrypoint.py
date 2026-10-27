from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "sqlite_entrypoint", Path(__file__).with_name("sqlite-entrypoint.py")
)
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


class SQLiteEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "image.db"
        self.destination = self.root / "data" / "persistent.db"

    def seed(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as database, database:
            database.execute("CREATE TABLE records (value TEXT)")
            database.execute("INSERT INTO records VALUES (?)", (value,))

    def read(self, path):
        with closing(sqlite3.connect(path)) as database:
            return database.execute("SELECT value FROM records").fetchall()

    def test_copies_initial_database_and_links_source(self):
        self.seed(self.source, "initial")
        entrypoint.prepare_database(self.source, self.destination)
        self.assertTrue(self.source.is_symlink())
        self.assertEqual(self.read(self.source), [("initial",)])

    def test_existing_persistent_database_wins_over_replacement_image(self):
        self.seed(self.source, "image")
        self.seed(self.destination, "persistent")
        entrypoint.prepare_database(self.source, self.destination)
        self.assertEqual(self.read(self.source), [("persistent",)])

    def test_missing_image_database_can_be_initialized_through_link(self):
        entrypoint.prepare_database(self.source, self.destination)
        self.seed(self.source, "new")
        self.assertEqual(self.read(self.destination), [("new",)])

    def test_repeated_preparation_preserves_writes(self):
        self.seed(self.source, "initial")
        entrypoint.prepare_database(self.source, self.destination)
        with closing(sqlite3.connect(self.source)) as database, database:
            database.execute("INSERT INTO records VALUES ('added')")
        entrypoint.prepare_database(self.source, self.destination)
        self.assertEqual(self.read(self.source), [("initial",), ("added",)])

    def test_wal_sidecar_is_created_in_persistent_directory(self):
        entrypoint.prepare_database(self.source, self.destination)
        with closing(sqlite3.connect(self.source)) as database, database:
            database.execute("PRAGMA journal_mode=WAL")
            database.execute("CREATE TABLE records (value TEXT)")
            self.assertTrue(Path(str(self.destination) + "-wal").exists())

    def test_invalid_image_database_is_not_destroyed(self):
        self.source.write_text("not a database")
        with self.assertRaises(sqlite3.DatabaseError):
            entrypoint.prepare_database(self.source, self.destination)
        self.assertFalse(self.source.is_symlink())
        self.assertFalse(self.destination.exists())

    def test_identical_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            entrypoint.prepare_database(self.source, self.source)


if __name__ == "__main__":
    unittest.main()
