"""Base configuration shared by every dashboard environment."""

import os

from dashboard.config.database_url_resolver import BASE_DIR, DATA_DIR, DatabaseUrlResolver


class Config:
    """Base configuration shared by every environment."""

    # Flask-WTF needs a secret key for CSRF tokens; override with the
    # SECRET_KEY environment variable outside local development.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy's built-in engine logger prints SQL and bound parameters.
    # Set in the shell before starting the app; keep normal runs quiet.
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() in (
        "1", "true", "yes",
    )

    # SQLite lives beside the legacy JSON store so the Docker volume
    # (/app/data) keeps persisting incident data across restarts; a
    # deployed environment swaps in PostgreSQL via DATABASE_URL.
    SQLALCHEMY_DATABASE_URI = DatabaseUrlResolver().resolve()

    DEBUG = False
