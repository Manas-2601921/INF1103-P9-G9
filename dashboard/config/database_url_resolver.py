"""Database URL resolution helper for local SQLite and deployed PostgreSQL."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class DatabaseUrlResolver:
    """Resolve and normalise the database URI from environment variables.

    Locally (no ``DATABASE_URL`` set) every consumer uses the SQLite file
    beside the legacy JSON store, so the CLI, the tests and the Docker
    image keep working unchanged. A deployed environment (Azure App
    Service with its PostgreSQL add-on) injects ``DATABASE_URL`` instead,
    and the app switches automatically — the models are dialect-agnostic
    ORM. Some cloud providers still hand out the legacy ``postgres://``
    scheme, which SQLAlchemy rejects, so it is normalised here.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self._data_dir = data_dir

    def resolve(self) -> str:
        """Return the active SQLAlchemy database URI."""
        url = os.getenv(
            "DATABASE_URL", f"sqlite:///{(self._data_dir / 'incidents.db').as_posix()}"
        )
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
