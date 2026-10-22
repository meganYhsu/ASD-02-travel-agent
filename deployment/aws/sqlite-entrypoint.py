from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


def prepare_database(source: Path, destination: Path) -> None:
    if source.absolute() == destination.absolute():
        raise ValueError("Source and destination must be different paths")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() and source.is_file():
        descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent)
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
                with closing(sqlite3.connect(temporary_path)) as copied:
                    original.backup(copied)
            temporary_path.replace(destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    if source.is_symlink() and source.resolve() == destination.resolve():
        return
    source.unlink(missing_ok=True)
    source.symlink_to(destination)


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("Usage: sqlite-entrypoint.py SOURCE DESTINATION COMMAND [ARGS...]")
    prepare_database(Path(sys.argv[1]), Path(sys.argv[2]))
    os.execvp(sys.argv[3], sys.argv[3:])


if __name__ == "__main__":
    main()
