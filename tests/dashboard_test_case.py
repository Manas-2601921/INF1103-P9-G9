"""Shared isolated SQLite test fixture for dashboard test cases."""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from dashboard import create_app
from dashboard.analytics.stats_service import StatsService
from dashboard.config import TestConfig
from dashboard.extensions import db
from dashboard.incident import Incident
from data_manager import DataManager


class DashboardTestCase(unittest.TestCase):
    """Base test case provisioning an isolated temporary SQLite database."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = Path(self.directory.name) / "stats.db"

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
        self.data_manager = DataManager(self.app)
        self.stats = StatsService(self.data_manager)
        self.today = datetime.now().date()

    def days_ago(self, days, hour=9):
        """An ISO incident_datetime string placed ``days`` days before today."""
        return (datetime.now() - timedelta(days=days)).replace(
            hour=hour, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")

    def seed(self, days_ago=0, location="Warehouse", hazard_category="mechanical",
             severity="high", severity_score=None, final_queue="Routine Log"):
        """Insert one fully specified incident through the real DataManager."""
        ai = {"severity": severity, "confidence": 0.9,
              "severity_explanation": "Seeded for the statistics tests.",
              "hazard_category": hazard_category, "incident_type": "near-miss",
              "indicators": {"injury": False, "immediate_danger": False,
                             "exposure": False, "equipment_involvement": True,
                             "work_stoppage": False, "uncontrolled_hazard": False},
              "repeat_pattern_indicators": {"location": location,
                                            "hazard_category": hazard_category},
              "recommended_immediate_action": "Monitor the area.",
              "supporting_phrase": "Seeded supporting phrase."}
        if severity_score is not None:
            ai["severity_score"] = severity_score
        record = {
            "input": {"incident_name": "Stats seed", "description": "Seeded incident.",
                      "location": location, "reporter_role": "Employee",
                      "incident_datetime": self.days_ago(days_ago),
                      "injury_reported": False, "immediate_action": "Area cleared"},
            "ai": ai,
            "logic": {"final_queue": final_queue, "escalation_required": False,
                      "recurring": False, "duplicate_possible": False,
                      "risk_score": 1, "rule_applied": "seed",
                      "ai_explanation": "Seeded.", "supporting_phrase": "Seeded."},
        }
        self.data_manager.save(Incident.from_dict(record))
