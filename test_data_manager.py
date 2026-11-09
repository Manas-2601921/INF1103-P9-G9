"""Offline tests for loading incident records and preserving unreadable data."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from data_manager import DataManager, DataLoadError, DataSaveError, InvalidIncidentDataError


class DataManagerLoadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "incidents.json"
        self.manager = DataManager(self.path)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.enterContext(redirect_stdout(self.stdout))
        self.enterContext(redirect_stderr(self.stderr))

    def tearDown(self):
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.stderr.getvalue(), "")

    def test_missing_file_and_parent_are_empty_without_creating_files(self):
        self.assertEqual(self.manager.load(), [])
        nested = self.path / "missing" / "incidents.json"
        self.assertEqual(DataManager(nested).load(), [])
        self.assertFalse(self.path.exists())

    def test_valid_records_and_empty_list(self):
        for content, expected in [('[]', []), ('[{"description": "安全"}]', [{"description": "安全"}])]:
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                self.assertEqual(self.manager.load(), expected)

    def test_invalid_data_is_rejected_and_preserved(self):
        for content in [b'', b'[{', b'null', b'{}', b'42', b'[null]', b'[1]', b'[[]]', b'\xff']:
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(InvalidIncidentDataError):
                    self.manager.load()
                self.assertEqual(self.path.read_bytes(), content)

    def test_file_access_errors_preserve_cause(self):
        for error in [PermissionError("denied"), IsADirectoryError("directory"),
                      NotADirectoryError("bad parent"), OSError("read failed"),
                      ValueError("embedded null character")]:
            with self.subTest(error=error):
                with patch.object(Path, "open", side_effect=error):
                    with self.assertRaises(DataLoadError) as caught:
                        self.manager.load()
                self.assertIs(caught.exception.__cause__, error)

    def test_parse_errors_preserve_cause(self):
        self.path.write_bytes(b'{')
        with self.assertRaises(InvalidIncidentDataError) as caught:
            self.manager.load()
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_unexpected_errors_propagate(self):
        with patch.object(Path, "open", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                self.manager.load()

    def test_save_does_not_overwrite_corrupt_database(self):
        self.path.write_bytes(b'broken JSON')
        with self.assertRaises(InvalidIncidentDataError):
            self.manager.save({})
        self.assertEqual(self.path.read_bytes(), b'broken JSON')

    @staticmethod
    def sample_record():
        return {"input": {"description": "Incident"},
                "ai": {"repeat_pattern_indicators": {"datetime": "2026-11-07T12:00:00"}},
                "logic": {}}

    def test_save_returns_persisted_record_without_changing_input(self):
        record = self.sample_record()
        original = json.dumps(record)
        stored = self.manager.save(record)
        self.assertEqual(stored["record_id"], "INC-0001")
        self.assertEqual(self.manager.load(), [stored])
        self.assertEqual(json.dumps(record), original)
        self.assertEqual(self.manager.save(record)["record_id"], "INC-0002")

    def test_save_uses_highest_id_in_unsorted_history(self):
        self.path.write_text('[{"record_id":"INC-0009"},{"record_id":"INC-0002"}]')
        self.assertEqual(self.manager.save(self.sample_record())["record_id"], "INC-0010")

    def test_invalid_input_preserves_existing_database(self):
        self.manager.save(self.sample_record())
        original = self.path.read_bytes()
        unserializable = self.sample_record()
        unserializable["input"]["bad"] = object()
        for record in [None, {}, {"input": [], "ai": {}, "logic": {}},
                       {"input": {}, "ai": {}, "logic": {}}, unserializable]:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    self.manager.save(record)
                self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_or_duplicate_stored_ids_prevent_save(self):
        for records in [[{}], [{"record_id": "INC-no"}],
                        [{"record_id": "INC-0001"}, {"record_id": "INC-0001"}]]:
            with self.subTest(records=records):
                self.path.write_text(json.dumps(records))
                original = self.path.read_bytes()
                with self.assertRaises(InvalidIncidentDataError):
                    self.manager.save(self.sample_record())
                self.assertEqual(self.path.read_bytes(), original)

    def test_write_and_replace_failures_preserve_database_and_clean_temp_file(self):
        self.manager.save(self.sample_record())
        original = self.path.read_bytes()
        for target in ["data_manager.os.fsync", "data_manager.os.replace",
                       "data_manager.tempfile.NamedTemporaryFile", "data_manager.Path.mkdir"]:
            with self.subTest(target=target):
                error = OSError("storage unavailable")
                with patch(target, side_effect=error):
                    with self.assertRaises(DataSaveError) as caught:
                        self.manager.save(self.sample_record())
                self.assertIs(caught.exception.__cause__, error)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
