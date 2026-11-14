"""Explicit database initialization and SQLite connection settings."""

from pathlib import Path

import click
from sqlalchemy import event

from dashboard.extensions import db


def _enable_foreign_keys(connection, connection_record):
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def register_database(app):
    # Register all tables without creating a database during app construction.
    from dashboard import models 

    with app.app_context():
        engine = db.engine
        if engine.dialect.name == "sqlite":
            event.listen(engine, "connect", _enable_foreign_keys)

    @app.cli.command("init-db")
    def init_db():
        """Create missing tables. Existing tables and records are preserved."""
        engine = db.engine
        if engine.dialect.name == "sqlite":
            database = engine.url.database
            if database and database != ":memory:":
                Path(database).parent.mkdir(parents=True, exist_ok=True)
        db.create_all()
        click.echo("Database initialized: io_manager, ai_manager, logic_manager, Incidents.")
