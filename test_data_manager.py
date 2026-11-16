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
            ("input_section", InputSection.from_dict({"description": "Report"})),
            ("ai_section", AISection.from_dict({"ai_error": "Unavailable"})),
            ("logic_section", LogicSection.from_dict({"final_queue": "Manual Review"})),
        ):
            with self.assertRaises(ValueError):
                self.manager().save(incident)
            setattr(incident, section_name, section)
        self.assertIs(self.manager().save(incident), incident)
        self.assertEqual(incident.record_id, "INC-0001")
        self.assertEqual(self.manager().load()[0].ai_section.to_dict()["ai_error"], "Unavailable")
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
        self.assertEqual([item.to_dict() for item in manager.query_location("Warehouse")], [incident.to_dict()])
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
        self.assertEqual(loaded.input_section.to_dict()["location"], "Warehouse")

    def test_search_helpers_combine_filters_and_treat_wildcards_literally(self):
        manager = self.manager()
        target = self.completed()
        target.input_section.manager_json["incident_name"] = "Forklift 100% check"
        target.ai_section.manager_json["hazard_category"] = "mechanical"
        manager.save(target)
        other = self.completed()
        other.input_section.manager_json["incident_name"] = "Forklift 1000 check"
        manager.save(other)
        self.assertEqual(manager.query_record_id(target.record_id)[0].record_id, target.record_id)
        self.assertEqual(manager.query_record_id("INC-invalid"), [])
        self.assertEqual(manager.query_incident_name("FORKLIFT 100% CHECK")[0].record_id, target.record_id)
        matches = manager.search_incidents(incident_name="100%", hazard_category="mechanical",
                                           location="ware", injury_reported=False)
        self.assertEqual([item.record_id for item in matches], [target.record_id])
        self.assertEqual(manager.search_incidents(incident_name="100%", injury_reported=True), [])

    def test_datetime_range_handles_legacy_dates_boundaries_and_invalid_values(self):
        manager = self.manager()
        stored_ids = []
        for value in ("2026-11-11T09:00:00", "11-11-2026 09:00", "invalid", "2026-11-11T09:00:00+08:00"):
            incident = self.completed()
            incident.input_section.manager_json["incident_datetime"] = value
            manager.save(incident)
            stored_ids.append(incident.record_id)
        matches = manager.query_datetime_range("2026-11-11T09:00:00", "2026-11-11T09:00:00")
        self.assertEqual([item.record_id for item in matches], stored_ids[:2])
        self.assertEqual([item.record_id for item in manager.query_datetime_range("2026-11-11T09:00:00+08:00", None)], stored_ids[3:])
        for start, end in (("bad", None), ("2026-11-12", "2026-11-11"),
                           ("2026-11-11T09:00:00+08:00", "2026-11-11T09:00:00")):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                manager.query_datetime_range(start, end)

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

    def test_created_at_uses_wrapped_input_datetime_or_processing_time(self):
        incident = self.completed()
        incident.metadata = {}
        self.manager().save(incident)
        self.assertEqual(incident.metadata["created_at"],
                         incident.input_section.to_dict()["incident_datetime"])
        self.assertEqual(self.manager().load()[0].metadata, incident.metadata)

        incident = self.completed()
        incident.metadata = {}
        incident.input_section.manager_json.pop("incident_datetime")
        self.manager().save(incident)
        self.assertEqual(incident.metadata["created_at"], incident.metadata["processed_at"])

    def test_invalid_web_submission_does_not_analyse_or_save(self):
        from incident_analyzer import incident_analyzer
        import managers

        manager = self.manager()
        with patch.object(managers, "data_manager", manager), \
                patch.object(incident_analyzer, "analyse_incident") as analyse:
            response = self.app.test_client().post("/incidents/add", data={"incident_name": "Missing fields"})
        self.assertEqual(response.status_code, 400)
        analyse.assert_not_called()
        self.assertEqual(manager.load(), [])

    def test_io_search_uses_shared_manager(self):
        from IOManager import IOManager

        manager = self.manager()
        incident = self.completed()
        incident.ai_section.manager_json["hazard_category"] = "mechanical"
        manager.save(incident)
        io = IOManager()
        with patch.object(io, "_data_manager", manager):
            self.assertEqual([item.to_dict() for item in io.find_by_title("test")], [incident.to_dict()])
            self.assertEqual([item.to_dict() for item in io.find_by_category("mechanical")], [incident.to_dict()])
            self.assertEqual(io.get_all_incident_categories(), ["mechanical"])

    def test_interactive_search_options_use_shared_manager(self):
        import managers
        from IOManager import IOManager

        manager = self.manager()
        incident = self.completed()
        incident.ai_section.manager_json["hazard_category"] = "mechanical"
        manager.save(incident)
        cases = (
            (1, ["Test"]),
            (2, ["mechanical"]),
            (3, ["1", "11-11-2026 08:00", "11-11-2026 10:00"]),
            (3, ["2", "11-11-2026 09:00"]),
        )
        with patch.object(managers, "data_manager", manager):
            for option, answers in cases:
                with self.subTest(option=option, answers=answers), \
                        patch("builtins.input", side_effect=answers):
                    records, _ = IOManager().handle_search_option(option)
                    self.assertEqual([item.to_dict() for item in records], [incident.to_dict()])

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
