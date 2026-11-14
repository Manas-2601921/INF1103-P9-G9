"""Dashboard routes as class-based views.

Every page is a ``MethodView`` subclass registered on the blueprint via
``as_view`` — the Flask object-oriented pattern: views are classes, routing
carries no decorators. The HTTP verb becomes a method name (``get``,
``post``, ...).
"""

from flask import Blueprint
from .HomeView import HomeView
from .IncidentsView import IncidentsView
from .IncidentDetailsView import IncidentDetailsView
from .AddIncident import AddIncident



bp = Blueprint("dashboard", __name__)


bp.add_url_rule("/", view_func=HomeView.as_view("home"))
bp.add_url_rule("/incidents/add", view_func=AddIncident.as_view("add_incident"))
bp.add_url_rule("/incidents", view_func=IncidentsView.as_view("incidents"))
bp.add_url_rule("/incidents/<record_id>", view_func=IncidentDetailsView.as_view("incident_details"))
