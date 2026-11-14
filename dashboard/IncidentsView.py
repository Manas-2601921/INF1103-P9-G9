from dashboard.shared_imports import *
from flask import current_app
from data_manager import DataLoadError
import managers

class IncidentsView(MethodView):

    def get(self):
        try:
            incidents_data = managers.data_manager.load()
        except DataLoadError:
            current_app.logger.exception("Failed to load incidents")
            managers.io_manager.notify("Incidents could not be loaded. Please try again later.")
            return render_template("incidents.html", error=True), 500
        return render_template("incidents.html", incidents=incidents_data)