"""Offline tests for the environment-driven database URI resolution.

The deployed environment (Azure App Service) injects ``DATABASE_URL`` so
the app runs on PostgreSQL while local runs stay on SQLite; some cloud
providers hand out the legacy ``postgres://`` scheme which SQLAlchemy
rejects, so ``dashboard.config.database_url`` normalises it.
"""

import os
import unittest
from unittest import mock

from dashboard.config import Config, database_url


class DatabaseUrlTests(unittest.TestCase):
    def test_default_is_the_local_sqlite_file(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("DATABASE_URL", None)
            url = database_url()
        self.assertTrue(url.startswith("sqlite:///"), url)
        self.assertTrue(url.endswith("incidents.db"), url)

    def test_legacy_postgres_scheme_is_normalised(self):
        with mock.patch.dict(os.environ,
                             {"DATABASE_URL": "postgres://user:pw@host:5432/incident"}):
            url = database_url()
        self.assertEqual(url, "postgresql://user:pw@host:5432/incident")
        self.assertFalse(url.startswith("postgres://"))

    def test_standard_postgresql_scheme_passes_through_unchanged(self):
        with mock.patch.dict(os.environ,
                             {"DATABASE_URL": "postgresql://user:pw@host/db"}):
            url = database_url()
        self.assertEqual(url, "postgresql://user:pw@host/db")

    def test_config_class_uses_the_resolved_url(self):
        # Config resolves once at import; database_url() resolves live.
        # Without DATABASE_URL set in this environment they must agree,
        # proving the class attribute is wired to the same helper.
        with mock.patch.dict(os.environ):
            os.environ.pop("DATABASE_URL", None)
            self.assertEqual(Config.SQLALCHEMY_DATABASE_URI, database_url())


if __name__ == "__main__":
    unittest.main()
