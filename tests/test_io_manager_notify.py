"""Offline tests for IOManager.notify and base.html flash alert rendering."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import managers
from tests.dashboard_test_case import DashboardTestCase


class IOManagerNotifyTests(DashboardTestCase):
    """Verify flash notifications map categories to Bootstrap alerts."""

    def test_notify_flashes_and_renders_bootstrap_alerts_in_base_template(self):
        io_manager = managers.io_manager

        @self.app.route("/_test_notify")
        def _test_notify():
            io_manager.notify("AI analysis failed.", category="error")
            io_manager.notify("Rising hazard detected.", category="warning")
            io_manager.notify("Incident saved.", category="success")
            io_manager.notify("Heads up.", category="info")
            from flask import redirect, url_for
            return redirect(url_for("dashboard.home"))

        client = self.app.test_client()
        response = client.get("/_test_notify", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alert-danger", response.data)
        self.assertIn(b"AI analysis failed.", response.data)
        self.assertIn(b"alert-warning", response.data)
        self.assertIn(b"Rising hazard detected.", response.data)
        self.assertIn(b"alert-success", response.data)
        self.assertIn(b"Incident saved.", response.data)
        self.assertIn(b"alert-info", response.data)
        self.assertIn(b"Heads up.", response.data)


if __name__ == "__main__":
    unittest.main()
