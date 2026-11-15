"""Small, fail-safe recovery for a corrupt local SQLite file.

For the single-process coursework app only. Never use this to reset a remote
server, repair individual records, or recover a database with active journals.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from threading import Lock
from uuid import uuid4

from flask import flash, has_request_context
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from dashboard.extensions import db


class SQLiteRecoveryError(RuntimeError):
    """Recovery could not safely finish; the original or backup is preserved."""


def sqlite_has_journal_files(engine):
    """Check before reading too: SQLite may clean up sidecars while opening."""
    name = engine.url.database
    if engine.dialect.name != "sqlite" or not name or name == ":memory:" or name.startswith("file:"):
        return False
    return any(Path(str(Path(name).resolve()) + suffix).exists()
               for suffix in ("-wal", "-shm", "-journal"))


def recover_corrupt_sqlite(app, engine, error, had_journals=False):
    """Return True after a successful reset, False for a non-corruption error.

    SQLAlchemy wraps the sqlite3 error in ``orig``. Extended SQLite error codes
    retain the primary code in the low byte. Only CORRUPT/NOTADB justify reset.
    The caller must close its read session before calling this function.
    """
    original = getattr(error, "orig", None)
    code = getattr(original, "sqlite_errorcode", None)
    if (engine.dialect.name != "sqlite" or not isinstance(original, sqlite3.DatabaseError)
            or not isinstance(code, int)
            or code & 0xff not in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB)):
        return False
    database_name = engine.url.database
    if not database_name or database_name == ":memory:" or database_name.startswith("file:"):
        return False
    database = Path(database_name).resolve()
    state = app.extensions.setdefault("sqlite_corruption_recovery", {"lock": Lock(), "attempted": False})
    with state["lock"]:
        if state["attempted"]:
            raise SQLiteRecoveryError("Database recovery was already attempted. Stop the app and inspect the database before restarting.")
        state["attempted"] = True
        backup, replacement = None, None
        try:
            # Close pooled connections, including Windows file handles, after
            # the failing read's own session has closed. Other app processes
            # must not be using this database during recovery.
            engine.dispose()
            if not database.is_file():
                raise SQLiteRecoveryError("The corrupt database file could not be found; no reset was performed.")
            if had_journals or sqlite_has_journal_files(engine):
                raise SQLiteRecoveryError("The database has SQLite journal files. Stop the app and recover it manually; no reset was performed.")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = database.with_name(f"{database.stem}.corrupt-{timestamp}-{uuid4().hex[:8]}{database.suffix}")
            # Exclusive creation prevents overwriting any previous backup.
            with database.open("rb") as source, backup.open("xb") as target:
                shutil.copyfileobj(source, target)

            # Build and close a complete replacement BEFORE touching the old
            # path. Failure here leaves the original database in place.
            handle, name = tempfile.mkstemp(prefix=database.name + ".recover-", suffix=".tmp", dir=database.parent)
            os.close(handle)
            replacement = Path(name)
            fresh_engine = create_engine(URL.create("sqlite", database=str(replacement)))
            try:
                db.metadata.create_all(fresh_engine)
            finally:
                fresh_engine.dispose()
            os.replace(replacement, database)
            replacement = None
        except (OSError, SQLAlchemyError) as exc:
            detail = f" Backup, if created: {backup.name}." if backup else ""
            raise SQLiteRecoveryError("Could not safely reset the corrupt database; existing files were preserved." + detail) from exc
        finally:
            if replacement is not None:
                try:
                    replacement.unlink(missing_ok=True)
                except OSError:
                    app.logger.warning("Could not remove temporary recovery file: %s", replacement)
        message = ("The incident database was corrupt. A new empty database was created. "
                   f"The previous file is preserved as {backup.name}; its records have not been restored.")
        app.logger.warning(message)
        if has_request_context():
            flash(message, "warning")
        else:
            print(message)
        return True
