"""Base configuration shared by every dashboard environment."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
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
