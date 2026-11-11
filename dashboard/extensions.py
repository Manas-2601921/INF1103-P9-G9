"""Shared Flask extension instances.

The extensions are created once at module level and bound to the app inside
the application factory (``dashboard.create_app``), so every module can
import them without importing the app package itself.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
