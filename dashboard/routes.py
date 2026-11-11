"""Dashboard routes as class-based views.

Every page is a ``MethodView`` subclass registered on the blueprint via
``as_view`` — the Flask object-oriented pattern: views are classes, routing
carries no decorators. The HTTP verb becomes a method name (``get``,
``post``, ...).
"""

from flask import Blueprint, render_template
from flask.views import MethodView

bp = Blueprint("dashboard", __name__)


class HomeView(MethodView):
    """Placeholder home page; the dashboard views arrive in a later step."""

    def get(self):
        return render_template("index.html")


bp.add_url_rule("/", view_func=HomeView.as_view("home"))
