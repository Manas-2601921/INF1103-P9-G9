"""Configuration classes for the dashboard application factory.

Each environment is one class inheriting from ``Config``; the factory calls
``app.config.from_object`` on the selected class. Test suites pass their own
subclass with a temporary SQLite database so runs never share state.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Config:
    """Base configuration shared by every environment."""

    # Flask-WTF needs a secret key for CSRF tokens; override with the
    # SECRET_KEY environment variable outside local development.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLite lives beside the legacy JSON store so the Docker volume
    # (/app/data) keeps persisting incident data across restarts.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(DATA_DIR / 'incidents.db').as_posix()}"
    )

    DEBUG = False


class DevConfig(Config):
    """Local development: verbose errors on, CSRF still enabled."""

    DEBUG = True


class TestConfig(Config):
    """Automated test suites: no CSRF so the test client can post forms,
    quiet output. Each suite overrides SQLALCHEMY_DATABASE_URI with a
    temporary database path so runs never share state."""

    TESTING = True
    WTF_CSRF_ENABLED = False
