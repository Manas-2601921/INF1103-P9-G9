from flask import current_app, redirect, render_template, url_for
from flask.views import MethodView
from data_manager import DataLoadError
import managers


class IncidentDetailsView(MethodView):
    
    def get(self, record_id):
        try:
            incident_record = managers.data_manager.query(lambda record: record.get("record_id") == record_id)
        except DataLoadError:
            current_app.logger.exception("Failed to load incident")
            managers.io_manager.notify("The incident could not be loaded. Please try again later.")
            return render_template("incidents.html", error=True), 500

        if not incident_record:
            current_app.logger.warning("Incident not found: %s", record_id)
            managers.io_manager.notify("Incident not found.", category="warning")
            return redirect(url_for("dashboard.incidents"))

        return render_template(
            "incident_details.html",
            incident=incident_record[0],
            format_datetime=managers.io_manager.format_incident_datetime,
        )
        # return render_template("incident_details.html", record_id=record_id)
