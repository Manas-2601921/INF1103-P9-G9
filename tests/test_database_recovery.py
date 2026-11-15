"""Recovery uses disposable SQLite files only, never the application's data file."""
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sqlalchemy import inspect
from sqlalchemy.exc import DatabaseError, OperationalError

from dashboard.database_recovery import recover_corrupt_sqlite
from dashboard.extensions import db
from dashboard.incident import Incident
from data_manager import DataLoadError, DataManager
import test_incident_sqlite


class DatabaseRecoveryTests(unittest.TestCase):
    setUp = test_incident_sqlite.IncidentSQLiteTests.setUp
    record = test_incident_sqlite.IncidentSQLiteTests.record
    CORRUPT_BYTES = b"This is a damaged incident database, not an SQLite file." * 20

    def damage_database(self):
        database = Path(db.engine.url.database)
        db.session.remove()
        db.engine.dispose()
        database.write_bytes(self.CORRUPT_BYTES)
        return database

    def backups(self, database):
        return list(database.parent.glob("incidents.corrupt-*.db"))

    def test_corrupt_file_is_preserved_and_replaced_with_usable_empty_schema(self):
        database = self.damage_database()
        manager = DataManager(self.app)
        self.assertEqual(manager.load(), [])
        backups = self.backups(database)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(set(inspect(db.engine).get_table_names()),
                         {"Incidents", "io_manager", "ai_manager", "logic_manager"})
        record = self.record()
        record.pop("record_id")
        incident = manager.save(Incident.from_dict(record))
        self.assertEqual(manager.load()[0].record_id, incident.record_id)
        self.assertEqual(len(self.backups(database)), 1)

    def test_malformed_sqlite_page_is_backed_up_too(self):
        database = Path(db.engine.url.database)
        db.session.remove()
        db.engine.dispose()
        damaged = bytearray(database.read_bytes())
        # Corrupt the schema page's b-tree header while preserving the SQLite
        # file header. This exercises SQLITE_CORRUPT rather than NOTADB.
        damaged[100] = 0xff
        database.write_bytes(damaged)
        self.assertEqual(DataManager(self.app).load(), [])
        self.assertEqual(self.backups(database)[0].read_bytes(), bytes(damaged))
        self.assertEqual(len(inspect(db.engine).get_table_names()), 4)

    def test_category_read_also_recovers_and_warns_in_search_page(self):
        database = self.damage_database()
        response = self.app.test_client().get("/search")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"database was corrupt", response.data)
        self.assertIn(b"previous file is preserved", response.data)
        self.assertIn(b"0 incidents found", response.data)
        self.assertEqual(len(self.backups(database)), 1)

    def test_dashboard_recovers_without_crashing(self):
        database = self.damage_database()
        response = self.app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"database was corrupt", response.data)
        self.assertEqual(len(self.backups(database)), 1)

    def test_details_read_recovers_and_redirects_with_warning(self):
        self.damage_database()
        response = self.app.test_client().get("/incidents/INC-0001", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"database was corrupt", response.data)
        self.assertIn(b"Incident not found", response.data)

    def test_init_db_can_recover_a_corrupt_file_before_startup(self):
        database = self.damage_database()
        result = self.runner.invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("database was corrupt", result.output)
        self.assertEqual(self.backups(database)[0].read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(DataManager(self.app).load(), [])

    def test_backup_failure_never_replaces_the_original(self):
        database = self.damage_database()
        with patch("dashboard.database_recovery.shutil.copyfileobj", side_effect=PermissionError("no backup access")):
            with self.assertRaises(DataLoadError):
                DataManager(self.app).load()
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(list(database.parent.glob("*.recover-*.tmp")), [])

    def test_schema_creation_failure_preserves_original_and_backup(self):
        database = self.damage_database()
        with patch.object(db.metadata, "create_all", side_effect=OperationalError("CREATE", {}, Exception("disk full"))):
            with self.assertRaises(DataLoadError):
                DataManager(self.app).load()
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(self.backups(database)[0].read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(list(database.parent.glob("*.recover-*.tmp")), [])

    def test_replace_failure_preserves_original_and_backup(self):
        database = self.damage_database()
        with patch("dashboard.database_recovery.os.replace", side_effect=PermissionError("file in use")):
            with self.assertRaises(DataLoadError):
                DataManager(self.app).load()
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)
        self.assertEqual(self.backups(database)[0].read_bytes(), self.CORRUPT_BYTES)

    def test_noncorruption_database_errors_do_not_reset_data(self):
        database = Path(db.engine.url.database)
        original = database.read_bytes()
        # Busy, locked, readonly, full, inaccessible, I/O, and missing-table errors.
        for code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_READONLY,
                     sqlite3.SQLITE_FULL, sqlite3.SQLITE_CANTOPEN, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_ERROR):
            original_error = sqlite3.OperationalError("synthetic non-corruption failure")
            original_error.sqlite_errorcode = code
            error = OperationalError("SELECT", {}, original_error)
            with self.subTest(code=code), patch("data_manager.Session.scalars", side_effect=error):
                with self.assertRaises(DataLoadError):
                    DataManager(self.app).load()
            self.assertEqual(database.read_bytes(), original)
            self.assertEqual(self.backups(database), [])

    def test_journal_files_prevent_unsafe_reset(self):
        database = self.damage_database()
        journal = Path(str(database) + "-wal")
        journal.write_bytes(b"preserve journal")
        with self.assertRaises(DataLoadError):
            DataManager(self.app).load()
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)
        # SQLite itself may discard an invalid sidecar during the failing open.
        self.assertEqual(self.backups(database), [])

    def test_recovery_is_not_repeated_for_the_same_app(self):
        database = self.damage_database()
        manager = DataManager(self.app)
        self.assertEqual(manager.load(), [])
        self.damage_database()
        with self.assertRaises(DataLoadError):
            manager.load()
        self.assertEqual(len(self.backups(database)), 1)
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)

    def test_remote_and_memory_databases_are_never_reset(self):
        original_error = sqlite3.DatabaseError("corrupt")
        original_error.sqlite_errorcode = sqlite3.SQLITE_CORRUPT
        error = DatabaseError("SELECT", {}, original_error)
        for dialect, database in (("postgresql", "/not-a-local-db"), ("sqlite", ":memory:"),
                                  ("sqlite", "file:incidents?mode=memory")):
            engine = SimpleNamespace(dialect=SimpleNamespace(name=dialect), url=SimpleNamespace(database=database))
            self.assertFalse(recover_corrupt_sqlite(self.app, engine, error))

    def test_failed_recovery_shows_friendly_dashboard_error(self):
        database = self.damage_database()
        with patch("dashboard.database_recovery.shutil.copyfileobj", side_effect=PermissionError("denied")):
            response = self.app.test_client().get("/")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Dashboard incidents could not be loaded", response.data)
        self.assertNotIn(b"No incidents are stored yet", response.data)
        self.assertEqual(database.read_bytes(), self.CORRUPT_BYTES)
