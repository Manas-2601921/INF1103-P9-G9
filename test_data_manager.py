"""Offline tests for staged incidents and transactional SQLite persistence."""

import unittest
from unittest.mock import patch
from sqlalchemy import text

from data_manager import DataManager, DataSaveError, DataLoadError, InvalidIncidentDataError
from dashboard.incident import Incident
from dashboard.input_section import InputSection
from dashboard.ai_section import AISection
from dashboard.logic_section import LogicSection
from dashboard.extensions import db
import test_incident_sqlite


class DataManagerTests(unittest.TestCase):
    setUp = test_incident_sqlite.IncidentSQLiteTests.setUp
    record = test_incident_sqlite.IncidentSQLiteTests.record

    def manager(self):
        return DataManager(self.app)

    def completed(self):
        record = self.record()
        record.pop("record_id")
        return Incident.from_dict(record)

    def test_staged_incident_and_incomplete_save(self):
        incident = Incident()
        self.assertIsNone(incident.input_section)
        self.assertIsNone(incident.ai_section)
        self.assertIsNone(incident.logic_section)
        self.assertIsNone(incident.to_dict()["input"])
        for section_name, section in (
            ("input_section", InputSection(description="Report")),
            ("ai_section", AISection(ai_error="Unavailable")),
            ("logic_section", LogicSection(final_queue="Manual Review")),
        ):
            with self.assertRaises(ValueError):
                self.manager().save(incident)
            setattr(incident, section_name, section)
        self.assertIs(self.manager().save(incident), incident)
        self.assertEqual(incident.record_id, "INC-0001")
        self.assertEqual(self.manager().load()[0].ai_section.ai_error, "Unavailable")
        with self.assertRaises(TypeError):
            incident.input_section = {}

    def test_save_load_and_queries(self):
        manager = self.manager()
        self.assertEqual(manager.load(), [])
        incident = self.completed()
        manager.save(incident)
        loaded = DataManager(self.app).load()[0]
        self.assertIsInstance(loaded, Incident)
        self.assertIsInstance(loaded.input_section, InputSection)
        self.assertEqual(loaded.to_dict(), incident.to_dict())
        self.assertEqual(manager.query_location("Warehouse"), [incident.to_dict()])
        self.assertEqual(manager.query_stored_incident_summaries()[0]["record_id"], incident.record_id)
        with self.assertRaises(ValueError):
            manager.save(incident)
        with self.assertRaises(TypeError):
            manager.save(incident.to_dict())
        second = self.completed()
        manager.save(second)
        self.assertEqual([i.record_id for i in manager.load()], ["INC-0001", "INC-0002"])
        # Plain sections remain usable after all database sessions close.
        db.session.remove()
        self.assertEqual(loaded.input_section.location, "Warehouse")

    def test_failed_commit_preserves_caller_and_rolls_back(self):
        incident = self.completed()
        original = incident.to_dict()
        from sqlalchemy.exc import OperationalError
        with patch.object(db.engine.dialect, "do_commit", side_effect=OperationalError("COMMIT", {}, Exception("fail"))):
            with self.assertRaises(DataSaveError):
                self.manager().save(incident)
        self.assertEqual(incident.to_dict(), original)
        self.assertEqual(self.manager().load(), [])
        self.manager().save(incident)
        self.assertEqual(len(self.manager().load()), 1)

    def test_io_search_uses_shared_manager(self):
        import managers
        from IOManager import IOManager

        manager = self.manager()
        incident = self.completed()
        incident.ai_section.hazard_category = "mechanical"
        manager.save(incident)
        with patch.object(managers, "data_manager", manager):
            self.assertEqual(IOManager.find_by_title("test"), [incident.to_dict()])
            self.assertEqual(IOManager.find_by_category("mechanical"), [incident.to_dict()])
            self.assertEqual(IOManager.get_all_incident_categories(), ["mechanical"])

    def test_uninitialized_database_and_missing_section_are_reported(self):
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        db.session.execute(text("INSERT INTO Incidents (id) VALUES (99)"))
        db.session.commit()
        with self.assertRaises(InvalidIncidentDataError):
            self.manager().load()
        db.drop_all()
        with self.assertRaises(DataLoadError):
            self.manager().load()


if __name__ == "__main__":
    unittest.main()
