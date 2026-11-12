"""Application factory for the Workplace Incident Triage dashboard.

The factory pattern keeps the Flask app configurable: ``create_app`` binds
the extensions and registers the blueprints, while entry points (``app.py``,
the CLI, the test suites) choose the configuration class they need.

Flask itself is imported inside ``create_app`` on purpose: importing the
``dashboard`` package must stay cheap so the section objects (and the
managers that create them) load without the web or database stack.
"""

from dashboard.config import DevConfig


def create_app(config_class=DevConfig):
    """Create and configure the Flask application.

    Args:
        config_class: A configuration class (see dashboard.config) whose
            attributes are loaded into ``app.config``. Test suites pass a
            subclass pointing SQLALCHEMY_DATABASE_URI at a temporary file.

    Returns:
        flask.Flask: The configured application with extensions bound.
    """
    from flask import Flask

    from dashboard.extensions import db

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    from dashboard.database import register_database
    register_database(app)

    # Routes: every page is a MethodView class on the dashboard blueprint.
    # Feature view modules register their url rules on the shared blueprint
    # at import time, so they must be imported before the blueprint itself
    # is registered on the app.
    from dashboard.routes import bp as dashboard_bp
    from dashboard import views_trends  # noqa: F401  (registers /trends)
    app.register_blueprint(dashboard_bp)

    return app
