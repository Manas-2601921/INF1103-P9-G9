from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from flask.views import MethodView

from data_manager import DataLoadError, DataSaveError
from dashboard.ai_section import AISection
from dashboard.incident import Incident
from dashboard.input_section import InputSection
from dashboard.logic_section import LogicSection
import managers


class AddIncident(MethodView):
    """Create and persist incident reports submitted through the dashboard."""

    reporter_roles = {
        "Employee", "Supervisor", "Manager", "Safety Officer",
        "Contractor", "Visitor", "Other",
    }

    def get(self):
        return render_template("add_incident.html", form_data={})

    def post(self):
        field_names = (
            "incident_name", "description", "incident_datetime", "location",
            "reporter_role", "injury_reported", "immediate_action",
        )
        form_data = {
            name: request.form.get(name, "").strip()
            for name in field_names
        }

        missing_fields = [
            name for name in field_names
            if not form_data[name]
        ]
        if missing_fields:
            flash("Please complete all required fields.", "error")
            return render_template("add_incident.html", form_data=form_data), 400

        if form_data["reporter_role"] not in self.reporter_roles:
            flash("Please select a valid reporter role.", "error")
            return render_template("add_incident.html", form_data=form_data), 400

        if form_data["injury_reported"] not in {"yes", "no"}:
            flash("Please indicate whether an injury was reported.", "error")
            return render_template("add_incident.html", form_data=form_data), 400

        try:
            incident_datetime = datetime.fromisoformat(
                form_data["incident_datetime"]
            ).isoformat(timespec="seconds")
        except ValueError:
            flash("Please enter a valid incident date and time.", "error")
            return render_template("add_incident.html", form_data=form_data), 400

        record_input = {
            **form_data,
            "incident_datetime": incident_datetime,
            "injury_reported": form_data["injury_reported"] == "yes",
        }

        try:
            history = [
                incident.to_dict() for incident in managers.data_manager.load()
            ]
        except DataLoadError:
            current_app.logger.exception("Failed to load incident history")
            flash("Incident history could not be loaded. Please try again later.", "error")
            return render_template("add_incident.html", form_data=form_data), 500

        record = {"record_id": "", "input": record_input}
        try:
            from main import analyse_incident

            ai_output = analyse_incident(record)
        except RuntimeError:
            current_app.logger.exception("Incident analysis is unavailable")
            flash("Incident analysis is unavailable. Please try again later.", "error")
            return render_template("add_incident.html", form_data=form_data), 503

        incident = Incident(
            input_section=InputSection.from_dict(record_input),
            ai_section=AISection.from_dict(ai_output),
            logic_section=LogicSection.from_dict(
                managers.logic_manager.determine_final_status(
                    record_input, ai_output, history
                )
            ),
        )

        try:
            managers.data_manager.save(incident)
        except DataSaveError:
            current_app.logger.exception("Failed to save submitted incident")
            flash("The incident could not be saved. Please try again later.", "error")
            return render_template("add_incident.html", form_data=form_data), 500

        if ai_output.get("ai_error"):
            flash(
                "The incident was saved for manual review because automatic "
                "analysis failed.",
                "warning",
            )
        else:
            flash("Incident report submitted successfully.", "success")
        return redirect(
            url_for("dashboard.incident_details", record_id=incident.record_id)
        )