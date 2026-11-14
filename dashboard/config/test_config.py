"""Automated test suite configuration."""

from dashboard.config.base_config import Config


class TestConfig(Config):
    """Automated test suites: no CSRF so the test client can post forms,
    quiet output. Each suite overrides SQLALCHEMY_DATABASE_URI with a
    temporary database path so runs never share state."""

    TESTING = True
    WTF_CSRF_ENABLED = False
