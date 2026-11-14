from urllib.parse import parse_qsl, urlencode

from flask import request, current_app, redirect, render_template, url_for
from flask.views import MethodView
from data_manager import DataLoadError
import managers


class IncidentDetailsView(MethodView):
    
    def get(self, record_id):
        try:
            incident_record = managers.data_manager.get_by_record_id(record_id)
        except DataLoadError:
            current_app.logger.exception("Failed to load incident")
            managers.io_manager.notify("The incident could not be loaded. Please try again later.")
            return render_template("incidents.html", error=True), 500

        if not incident_record:
            current_app.logger.warning("Incident not found: %s", record_id)
            managers.io_manager.notify("Incident not found.", category="warning")
            return redirect(url_for("dashboard.incidents"))

        record = incident_record.to_dict()
        analysis, triage = record.get("ai") or {}, record.get("logic") or {}
        review = {key: value for key, value in analysis.items()
                  if key not in {"repeat_pattern_indicators", "recommended_immediate_action"}}
        review.update(triage)
        back_url = url_for("dashboard.incidents")
        if "search" in request.args:
            back_url = url_for("dashboard.search") + "?" + urlencode(
                parse_qsl(request.args["search"], keep_blank_values=True)
            ) + "#results-heading"
        return render_template(
            "incident_details.html",
            incident=record, review=review, back_url=back_url,
            from_search="search" in request.args,
            format_datetime=managers.io_manager.format_incident_datetime,
        )
