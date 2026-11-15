"""Offline tests for Werkzeug ProxyFix behind Azure App Service / Easy Auth."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from werkzeug.middleware.proxy_fix import ProxyFix

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import create_app
from dashboard.config import DevConfig, TestConfig
from dashboard.extensions import db


class ProxyFixConfigTests(unittest.TestCase):
    """Verify ProxyFix and Azure App Service HTTPS settings activate safely."""

    def _temp_db_uri(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        db_path = Path(directory.name) / "proxyfix_test.db"
        return f"sqlite:///{db_path.as_posix()}"

    def test_proxy_fix_and_azure_security_activate_when_website_site_name_set(self):
        class AzureDevConfig(DevConfig):
            SQLALCHEMY_DATABASE_URI = self._temp_db_uri()

        with mock.patch.dict(os.environ, {"WEBSITE_SITE_NAME": "incident-triage"}):
            app = create_app(AzureDevConfig)
            self.addCleanup(lambda: _dispose(app))

        self.assertIsInstance(app.wsgi_app, ProxyFix)
        self.assertFalse(app.debug)
        self.assertTrue(app.config["SESSION_COOKIE_SECURE"])
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")

        @app.route("/_proxy_echo")
        def _proxy_echo():
            from flask import request, url_for

            return {
                "scheme": request.scheme,
                "host": request.host,
                "remote_addr": request.remote_addr,
                "is_secure": request.is_secure,
                "external_home": url_for("dashboard.home", _external=True),
            }

        resp = app.test_client().get(
            "/_proxy_echo",
            headers={
                "X-Forwarded-For": "203.0.113.42",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "incident-triage.azurewebsites.net",
                "X-Forwarded-Port": "443",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["scheme"], "https")
        self.assertEqual(data["host"], "incident-triage.azurewebsites.net")
        self.assertEqual(data["remote_addr"], "203.0.113.42")
        self.assertTrue(data["is_secure"])
        self.assertEqual(data["external_home"], "https://incident-triage.azurewebsites.net/")

    def test_proxy_fix_disabled_for_test_config_and_plain_local_dev(self):
        class LocalTestConfig(TestConfig):
            SQLALCHEMY_DATABASE_URI = self._temp_db_uri()

        with mock.patch.dict(os.environ, {"WEBSITE_SITE_NAME": "incident-triage"}):
            test_app = create_app(LocalTestConfig)
            self.addCleanup(lambda: _dispose(test_app))
        self.assertNotIsInstance(test_app.wsgi_app, ProxyFix)

        class LocalDevConfig(DevConfig):
            SQLALCHEMY_DATABASE_URI = self._temp_db_uri()

        env = os.environ.copy()
        env.pop("WEBSITE_SITE_NAME", None)
        env.pop("ENABLE_PROXY_FIX", None)
        with mock.patch.dict(os.environ, env, clear=True):
            dev_app = create_app(LocalDevConfig)
            self.addCleanup(lambda: _dispose(dev_app))
        self.assertNotIsInstance(dev_app.wsgi_app, ProxyFix)


def _dispose(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
