"""Offline checks for the incident aggregate and four-table SQLite schema."""

from pathlib import Path
import tempfile
import unittest

from sqlalchemy import inspect, null, text
from sqlalchemy.exc import IntegrityError

from dashboard import create_app
from dashboard.config import TestConfig
from dashboard.extensions import db
from dashboard.incident import Incident
from dashboard.models import IncidentModel, IOManagerModel


class IncidentSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = Path(self.directory.name) / "nested" / "incidents.db"

        class Config(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database.as_posix()}"

        self.app = create_app(Config)
        self.runner = self.app.test_cli_runner()
        result = self.runner.invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.context = self.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        self.addCleanup(db.engine.dispose)
        self.addCleanup(db.session.remove)

    def record(self, severity="high"):
        return {
            "record_id": "INC-0012",
            "input": {"incident_name": "Test", "description": "安全", "location": "Warehouse",
                      "reporter_role": "Employee", "incident_datetime": "2026-11-11T09:00:00",
                      "injury_reported": False, "immediate_action": "Stopped work"},
            "ai": {"severity": severity, "confidence": 0.0,
                   "indicators": {"injury": False},
                   "repeat_pattern_indicators": {"activity": "lifting"}},
            "logic": {"risk_score": 0, "escalation_required": False},
            "metadata": {"created_at": "2026-11-11T09:00:00",
                         "processed_at": "2026-11-11T09:01:00"},
        }

    def test_schema_and_initialization_preserve_existing_data(self):
        tables = set(inspect(db.engine).get_table_names())
        self.assertEqual(tables, {"Incidents", "io_manager", "ai_manager", "logic_manager"})
        db.session.add(Incident.from_dict(self.record()).convert_to_db_model())
        db.session.commit()
        self.assertEqual(self.runner.invoke(args=["init-db"]).exit_code, 0)
        self.assertEqual(db.session.query(IncidentModel).count(), 1)

    def test_round_trip_preserves_section_values_and_legacy_severity(self):
        for severity in ("high", "0.86", 0.86):
            record = self.record(severity)
            model = Incident.from_dict(record).convert_to_db_model()
            db.session.add(model)
            db.session.commit()
            db.session.remove()
            loaded = db.session.get(IncidentModel, 12)
            self.assertEqual(Incident.from_db_model(loaded).to_dict(), record)
            db.session.delete(loaded)
            db.session.commit()

    def test_partial_ai_failure_and_generated_id(self):
        record = self.record()
        record.pop("record_id")
        record["ai"] = {"ai_error": "Unavailable"}
        model = Incident.from_dict(record).convert_to_db_model()
        self.assertIsNone(model.id)
        self.assertEqual(db.session.query(IncidentModel).count(), 0)
        db.session.add(model)
        db.session.commit()
        db.session.expire_all()
        result = Incident.from_db_model(model).to_dict()
        self.assertEqual(result["ai"], record["ai"])
        self.assertEqual(result["record_id"], "INC-0001")

    def test_foreign_keys_on_new_connections_and_orphan_rejection(self):
        db.session.remove()
        db.engine.dispose()
        self.assertEqual(db.session.execute(text("PRAGMA foreign_keys")).scalar(), 1)
        db.session.add(IOManagerModel(incident_id=999))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_failed_section_insert_rolls_back_entire_incident(self):
        model = Incident.from_dict(self.record()).convert_to_db_model()
        model.input_section.description = null()
        db.session.add(model)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(db.session.query(IncidentModel).count(), 0)
        self.assertEqual(db.session.query(IOManagerModel).count(), 0)


if __name__ == "__main__":
    unittest.main()
